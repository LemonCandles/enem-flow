"""Tipos de layout das questões (`layout-types-v1`) e preditor JSON + figuras → tipo.

Só biblioteca padrão: este arquivo também é publicado como `predict.py` do modelo, de modo que o
experimento e quem usa o modelo calculam as mesmas características pelo mesmo código.

Um tipo combina três eixos independentes, derivados da assinatura estrutural do adaptador de layout
(por exemplo `P Cr P ALT:texto`):

- corpo: sequência canônica dos blocos do enunciado: texto (P), crédito (Cr), figura (F), figura com
  crédito (F+Cr), figura com legenda (F+Cap), tabela (T);
- alternativas: texto (uma por linha), linha (várias por linha), figura (empilhadas), grade (figuras
  em colunas) ou misto;
- marcas: texto de apoio compartilhado (S), linhas numeradas (P#), blocos lado a lado (|).

Regra de fusão: repetir imediatamente um bloco ou um par de blocos não muda a apresentação, pois o
renderizador repete o mesmo motivo (`P Cr P Cr P` é `P Cr P`). A assinatura exata continua guardada
por questão na referência. Medidas contínuas (largura da figura, alinhamento) não são classes.

Uso como preditor:

    python predict.py questao.json --figures figuras.json
    python predict.py questao.json --assets pasta-das-figuras
"""

import argparse
import json
import math
from pathlib import Path
import re
import struct
import sys
import zlib

VERSION = 'layout-types-v1'
AXES = ('corpo', 'alternativas', 'marcas')
BODY = {
    'P': 'texto',
    'Cr': 'credito',
    'T': 'tabela',
    'F': 'figura',
    'F+Cr': 'figura+credito',
    'F+Cap': 'figura+legenda',
    'F+Cap+Cr': 'figura+legenda+credito',
}
BODY_PT = {
    'P': 'texto',
    'Cr': 'crédito',
    'T': 'tabela',
    'F': 'figura',
    'F+Cr': 'figura com crédito',
    'F+Cap': 'figura com legenda',
    'F+Cap+Cr': 'figura com legenda e crédito',
}
ALTERNATIVES = {
    'texto': 'alternativas em texto, uma por linha',
    'linha': 'alternativas curtas, várias na mesma linha',
    'figura': 'alternativas em figura, uma abaixo da outra',
    'grade': 'alternativas em figura, dispostas em colunas',
    'misto': 'alternativas que misturam texto e figura',
}
MARKS = {
    'compartilhado': 'Texto de apoio compartilhado com outras questões.',
    'linhas-numeradas': 'Texto com as linhas numeradas.',
    'lado-a-lado': 'Blocos impressos lado a lado.',
}
UNREPRESENTABLE = {
    'linhas-numeradas': 'O contrato de conteúdo não representa a numeração das linhas.',
    'lado-a-lado': 'O contrato de conteúdo não representa blocos lado a lado.',
    'misto': 'O contrato de conteúdo não representa alternativas que misturam texto e figura.',
}
NO_MARKS = 'nenhuma'
# Mesma expressão de `backend.app.preparation.rules.CREDIT`; o teste garante que não divergem.
CREDIT = re.compile(r'^(?:Dispon[ií]vel em|Acesso em|Fonte\s*:|https?://|[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ -]{2,},\s)')
LINE_NUMBER = re.compile(r'\d{1,3}')
SEVERAL_TEXTS = re.compile(r'^TEXTO\s+[IVX]+\b')


# Eixos e identificadores


def fuse(tokens):
    """Remove repetições imediatas de um bloco ou de um par de blocos."""
    result = []
    for token in tokens:
        if not result or result[-1] != token:
            result.append(token)
    repeated = True
    while repeated:
        repeated = False
        for i in range(len(result) - 3):
            if result[i : i + 2] == result[i + 2 : i + 4]:
                del result[i + 2 : i + 4]
                repeated = True
                break
    return result


def axes(signature):
    """Eixos de uma assinatura do adaptador; token desconhecido é erro, não um tipo novo silencioso."""
    tokens = signature.split()
    if not tokens or not tokens[-1].startswith('ALT:'):
        raise ValueError(f'Assinatura sem alternativas: {signature!r}')
    alternatives = tokens[-1].removeprefix('ALT:')
    if alternatives not in ALTERNATIVES:
        raise ValueError(f'Alternativas sem tipo reconhecido: {tokens[-1]}')
    marks, body = set(), []
    for position, token in enumerate(tokens[:-1]):
        if token == 'S':
            if position:
                raise ValueError(f'Marca de texto compartilhado fora do início: {signature!r}')
            marks.add('compartilhado')
            continue
        parts = token.split('|')
        if len(parts) > 1:
            marks.add('lado-a-lado')
        for part in parts:
            if part == 'P#':
                marks.add('linhas-numeradas')
                part = 'P'
            if part not in BODY:
                raise ValueError(f'Bloco desconhecido na assinatura: {part!r} em {signature!r}')
            body.append(part)
    if not body:
        raise ValueError(f'Assinatura sem enunciado: {signature!r}')
    return {'corpo': fuse(body), 'alternativas': alternatives, 'marcas': [m for m in MARKS if m in marks]}


def labels(value):
    """Rótulo de cada eixo, como os classificadores o veem."""
    return {
        'corpo': '-'.join(BODY[token] for token in value['corpo']),
        'alternativas': value['alternativas'],
        'marcas': '.'.join(value['marcas']) or NO_MARKS,
    }


def identifier(axis_labels):
    """Identificador estável e legível do tipo, por exemplo `texto-credito-texto.alt-texto`."""
    parts = [axis_labels['corpo'], 'alt-' + axis_labels['alternativas']]
    if axis_labels['marcas'] != NO_MARKS:
        parts.append(axis_labels['marcas'])
    return '.'.join(parts)


def parse_identifier(type_id):
    """Inverso de `identifier`: eixos a partir do identificador."""
    body, alternatives, *marks = type_id.split('.')
    names = {name: token for token, name in BODY.items()}
    value = {
        'corpo': [names.get(name) for name in body.split('-')],
        'alternativas': alternatives.removeprefix('alt-'),
        'marcas': marks,
    }
    if (
        None in value['corpo']
        or not alternatives.startswith('alt-')
        or value['alternativas'] not in ALTERNATIVES
        or [m for m in MARKS if m in marks] != marks
        or fuse(value['corpo']) != value['corpo']
    ):
        raise ValueError(f'Identificador de tipo inválido: {type_id!r}')
    return value


def type_id(signature):
    return identifier(labels(axes(signature)))


def unrepresentable(value):
    """Motivos pelos quais o contrato de conteúdo atual ainda não representa o tipo."""
    return [UNREPRESENTABLE[key] for key in (*value['marcas'], value['alternativas']) if key in UNREPRESENTABLE]


def description(value):
    items = [BODY_PT[token] for token in value['corpo']]
    body = items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' e ' + items[-1]
    text = f'Enunciado com {body}; {ALTERNATIVES[value["alternativas"]]}.'
    return ' '.join([text, *(MARKS[mark] for mark in value['marcas'])])


# Regra determinística sobre o JSON de conteúdo


def is_credit(block):
    return block.get('role') == 'credit' or bool(CREDIT.match(block.get('text', '').strip()))


def content_blocks(content):
    blocks = content.get('blocks') or []
    if not blocks:
        blocks = [{'type': 'paragraph', 'text': content.get('statement', '')}]
        blocks += [{'type': 'image', 'asset': image} for image in content.get('images') or []]
    return blocks


def line_numbers(content):
    return [
        int(block['text'].strip())
        for block in content_blocks(content)
        if block['type'] == 'paragraph' and LINE_NUMBER.fullmatch(block['text'].strip())
    ]


def content_body(content):
    """Sequência canônica do corpo derivada só da ordem e do papel dos blocos do JSON."""
    tokens = []
    for block in content_blocks(content):
        kind = block['type']
        if kind == 'paragraph':
            if LINE_NUMBER.fullmatch(block['text'].strip()):
                continue
            token = 'Cr' if is_credit(block) else 'P'
        elif kind == 'math':
            token = 'P'
        elif kind == 'table':
            token = 'T'
        elif kind == 'image':
            token = 'F' + ('+Cap' if block.get('caption') else '') + ('+Cr' if block.get('credit') else '')
        else:
            raise ValueError(f'Bloco de conteúdo desconhecido: {kind!r}')
        previous = tokens[-1] if tokens else ''
        if token == 'Cr' and previous.startswith('F'):
            # O crédito impresso logo depois da figura é o crédito dela.
            if not previous.endswith('+Cr'):
                tokens[-1] = previous + '+Cr'
            continue
        if token.startswith('F') and not token.endswith('+Cr') and previous == 'Cr':
            # No JSON a figura pode vir depois do próprio crédito; no caderno o crédito fica sob a figura.
            tokens[-1] = token + '+Cr'
            continue
        tokens.append(token)
    if tokens and tokens[-1] != 'P':
        # Toda questão impressa termina com o comando em texto antes das alternativas.
        tokens.append('P')
    return fuse(tokens)


def content_marks(content):
    numbers = line_numbers(content)
    return ['linhas-numeradas'] if len(numbers) >= 3 and numbers == sorted(set(numbers)) else []


def content_alternatives(content):
    images = sum(bool(a.get('image')) for a in content['alternatives'])
    if not images:
        return 'texto'
    return 'figura' if images == len(content['alternatives']) else 'misto'


def rule(content):
    """Rótulos dos três eixos pela regra determinística."""
    return labels(
        {
            'corpo': content_body(content),
            'alternativas': content_alternatives(content),
            'marcas': content_marks(content),
        }
    )


# Figuras


def read_png(path):
    """Largura, altura e luminância (0–255) de um PNG de 8 bits por canal, sem dependências."""
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'Não é PNG: {path}')
    position, chunks, palette, header = 8, [], b'', None
    while position < len(data):
        length, kind = struct.unpack('>I4s', data[position : position + 8])
        body = data[position + 8 : position + 8 + length]
        position += 12 + length
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            palette = body
        elif kind == b'IDAT':
            chunks.append(body)
        elif kind == b'IEND':
            break
    if header is None:
        raise ValueError(f'PNG sem cabeçalho: {path}')
    width, height, depth, color, _, _, interlace = header
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if depth != 8 or interlace or channels is None:
        raise ValueError(f'PNG não suportado (8 bits por canal, sem entrelaçamento): {path}')
    raw = zlib.decompress(b''.join(chunks))
    stride = width * channels
    previous = bytearray(stride)
    luminance = []
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1 : start + 1 + stride])
        if kind == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif kind == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, previous))
        elif kind == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = previous[i]
                c = previous[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif kind:
            raise ValueError(f'Filtro PNG inválido: {path}')
        previous = line
        row = []
        for x in range(width):
            pixel = line[x * channels : (x + 1) * channels]
            if color == 3:
                pixel = palette[pixel[0] * 3 : pixel[0] * 3 + 3]
            value = pixel[0] if len(pixel) < 3 else (299 * pixel[0] + 587 * pixel[1] + 114 * pixel[2]) // 1000
            if color in (4, 6):
                alpha = pixel[-1]
                value = (value * alpha + 255 * (255 - alpha)) // 255
            row.append(value)
        luminance.append(row)
    return width, height, luminance


def figure_attributes(path):
    """Dimensões em pixels e densidade de tinta (fração de pixels escuros) de uma figura."""
    width, height, luminance = read_png(path)
    pixels = [value for row in luminance for value in row]
    return {'width': width, 'height': height, 'ink': round(sum(v < 128 for v in pixels) / max(1, len(pixels)), 6)}


def asset_paths(content):
    paths = [b['asset']['path'] for b in content_blocks(content) if b['type'] == 'image']
    paths += [a['image']['path'] for a in content['alternatives'] if a.get('image')]
    return paths


# Características


def mean(values):
    return sum(values) / len(values) if values else 0.0


def features(content, figures):
    """Características observáveis no produto: blocos, textos, tabelas, fórmulas e figuras.

    Não usam PDF, imagem da questão, ano, número, página, descrição das figuras nem caminhos.
    `figures` mapeia o caminho de cada figura citada em `content` aos seus atributos.
    """
    blocks = content_blocks(content)
    paragraphs = [b for b in blocks if b['type'] == 'paragraph' and not LINE_NUMBER.fullmatch(b['text'].strip())]
    credits = [b for b in paragraphs if is_credit(b)]
    texts = [b['text'] for b in paragraphs if not is_credit(b)]
    images = [b for b in blocks if b['type'] == 'image']
    tables = [b for b in blocks if b['type'] == 'table']
    body = content_body(content)
    first = next((b for b in blocks if b in paragraphs or b['type'] != 'paragraph'), None)
    alternatives = content['alternatives']
    alternative_texts = [a.get('text') or '' for a in alternatives]

    def position(prefix):
        index = next((i for i, token in enumerate(body) if token.startswith(prefix)), None)
        return -1.0 if index is None else index / max(1, len(body) - 1)

    def attributes(paths, key):
        return [float(figures[path].get(key, 0.0)) for path in paths]

    body_paths = [b['asset']['path'] for b in images]
    option_paths = [a['image']['path'] for a in alternatives if a.get('image')]
    widths, heights = attributes(body_paths, 'width'), attributes(body_paths, 'height')
    width, height = max(zip(widths, heights), key=lambda size: size[0] * size[1], default=(0.0, 0.0))
    option_widths, option_heights = attributes(option_paths, 'width'), attributes(option_paths, 'height')
    values = {
        'blocos': len(blocks),
        'paragrafos': len(texts),
        'creditos': len(credits),
        'figuras': len(images),
        'figuras_com_credito': sum(token.startswith('F') and token.endswith('+Cr') for token in body),
        'figuras_com_legenda': sum(bool(b.get('caption')) for b in images),
        'tabelas': len(tables),
        'tabela_linhas': max((len(b['rows']) for b in tables), default=0),
        'tabela_colunas': max((len(b['headers']) for b in tables), default=0),
        'formulas': sum(b['type'] == 'math' for b in blocks) + sum(t.count('$') // 2 for t in texts),
        'numeros_de_linha': len(line_numbers(content)),
        'textos_rotulados': sum(bool(SEVERAL_TEXTS.match(t.strip())) for t in texts),
        'comeca_com_figura': float(bool(first) and first['type'] == 'image'),
        'corpo_blocos': len(body),
        'posicao_figura': position('F'),
        'posicao_tabela': position('T'),
        'texto_log': math.log1p(sum(len(t) for t in texts)),
        'paragrafo_medio_log': math.log1p(mean([len(t) for t in texts])),
        'figuras_avulsas': len(content.get('images') or []) if content.get('blocks') else 0,
        'alt_figuras': len(option_paths),
        'alt_texto_max_log': math.log1p(max(len(t) for t in alternative_texts)),
        'alt_texto_medio_log': math.log1p(mean([len(t) for t in alternative_texts])),
        'alt_formulas': sum('$' in t for t in alternative_texts),
        'fig_largura': width,
        'fig_altura': height,
        'fig_proporcao': width / max(1.0, height),
        'fig_tinta': mean(attributes(body_paths, 'ink')) if body_paths else 0.0,
        'alt_fig_largura': mean(option_widths),
        'alt_fig_altura': mean(option_heights),
        'alt_fig_proporcao': mean([w / max(1.0, h) for w, h in zip(option_widths, option_heights)]),
        'alt_fig_tinta': mean(attributes(option_paths, 'ink')) if option_paths else 0.0,
    }
    return {name: float(value) for name, value in values.items()}


INK_FEATURES = ('fig_tinta', 'alt_fig_tinta')


# Inferência


def tree_label(tree, vector):
    while 'feature' in tree:
        tree = tree['left'] if vector[tree['feature']] <= tree['threshold'] else tree['right']
    return tree['label']


def naive_bayes_label(model, vector):
    def score(label):
        stats = model['classes'][label]
        return math.log(stats['prior']) - sum(
            0.5 * math.log(2 * math.pi * var) + (x - mu) ** 2 / (2 * var)
            for x, mu, var in zip(vector, stats['mean'], stats['variance'])
        )

    return min(model['labels'], key=lambda label: (-score(label), label))


def predict_axis(model, axis, content, available):
    """Rótulo de um eixo; cada preditor guarda a lista das características que usa, na ordem."""
    kind = model['kind']
    vector = [available[name] for name in model.get('features', [])]
    if kind == 'majority':
        return model['label']
    if kind == 'rule':
        return rule(content)[axis]
    if kind == 'tree':
        return tree_label(model['tree'], vector)
    if kind == 'naive_bayes':
        return naive_bayes_label(model, vector)
    raise ValueError(f'Preditor desconhecido: {kind!r}')


def required_attributes(model):
    """Atributos de figura que quem chama precisa fornecer para este modelo."""
    names = {name for axis in model['axes'].values() for name in axis.get('features', [])}
    if not any(name.startswith(('fig_', 'alt_fig_')) for name in names):
        return []
    return ['width', 'height'] + (['ink'] if names & set(INK_FEATURES) else [])


def predict(model, content, figures):
    """Tipo de layout de uma questão a partir do JSON de conteúdo e dos atributos das figuras."""
    needed = required_attributes(model)
    for path in asset_paths(content):
        missing = [key for key in needed if key not in figures.get(path, {})]
        if missing:
            raise ValueError(f'Figura sem {", ".join(missing)}: {path}')
    available = features(content, figures)
    result = {axis: predict_axis(model['axes'][axis], axis, content, available) for axis in AXES}
    kind = identifier(result)
    value = parse_identifier(kind)
    return {
        'type': kind,
        'axes': result,
        'in_catalog': kind in model['catalog'],
        'representable': not unrepresentable(value),
        'unrepresentable_reasons': unrepresentable(value),
    }


def resolve_figures(content, assets):
    """Atributos calculados dos arquivos: `/assets/a/b.png` é lido em `<assets>/a/b.png`."""
    root = Path(assets).resolve()
    result = {}
    for path in asset_paths(content):
        file = (root / path.removeprefix('/assets/')).resolve()
        if not file.is_relative_to(root):
            raise ValueError(f'Figura fora da pasta indicada: {path}')
        result[path] = figure_attributes(file)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prevê o tipo de layout de questões a partir do JSON de conteúdo.')
    parser.add_argument(
        'questions', type=Path, help='JSON de uma questão (conteúdo) ou lista de {id, content, figures}.'
    )
    parser.add_argument('--model', type=Path, default=Path(__file__).with_name('model.json'))
    parser.add_argument('--figures', type=Path, help='JSON {caminho da figura: {width, height, ink}}.')
    parser.add_argument('--assets', type=Path, help='Pasta das figuras, para calcular os atributos dos PNG.')
    args = parser.parse_args(argv)
    model = json.loads(args.model.read_text())
    payload = json.loads(args.questions.read_text())
    single = isinstance(payload, dict)
    items = [{'id': None, 'content': payload.get('content', payload)}] if single else payload
    shared = json.loads(args.figures.read_text()) if args.figures else {}
    output = []
    for item in items:
        content = item['content']
        figures = {**shared, **item.get('figures', {})}
        if args.assets:
            figures.update(resolve_figures(content, args.assets))
        output.append({'id': item.get('id'), **predict(model, content, figures)})
    json.dump(output[0] if single else output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
