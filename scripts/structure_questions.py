"""Turn the existing JSON transcription into native question content.

Text and alternatives come ONLY from the JSON. The associated PDF is consulted
solely to isolate the figures referenced by that JSON; no question is rasterized.
The original extraction is retained so this transformation is reproducible.
"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/enem-2024-dia2-azul.json"
SOURCE = ROOT / "data/derived/baselines/enem-2024-dia2-azul-extraction.json"
ASSETS = ROOT / "data/assets/enem-2024-dia2-azul/native"
GRAPHIC_OPTIONS = {112, 121, 127, 131, 161, 168, 174}

DESCRIPTIONS = {
    91: "Diagrama de colisão de um carro, com a região deformável, o airbag e os cintos de segurança identificados.",
    92: "Esquema das duas câmaras da célula a combustível microbiana, com ânodo, cátodo, membrana e fluxo de elétrons.",
    94: "Estrutura química da nimesulida com os grupamentos sulfonamida, metila, fenila, nitro e éter destacados.",
    96: "Roda de automóvel com o centro de massa CM e os cinco pontos possíveis para fixação da peça de chumbo.",
    98: "Cladograma de mamíferos com monotremados, marsupiais e placentários, mostrando suas relações evolutivas.",
    100: "Mirascópio e esquema dos espelhos côncavos E1 e E2, com suas dimensões e os raios de luz.",
    101: "Infográfico da sala de aula e gráfico da diminuição do nível sonoro em função da distância ao professor.",
    103: "Esquema de aquecedor solar com coletor, reservatório térmico e os sentidos de circulação da água.",
    104: "Fluxograma que relaciona urbanização, ausência de saneamento básico, contaminação da água, redução da biodiversidade aquática e riscos à saúde humana.",
    110: "Fotografias de uma cobra coral-verdadeira e de uma falsa-coral, com seus padrões de coloração.",
    113: "Esquemas dos ciclos do nitrogênio e do carbono e das etapas numeradas de 1 a 5 realizadas por procariontes.",
    114: "Gráfico das emissões de gases CO2, HC, CO, NO e O2 em função da razão ar/combustível.",
    115: "Experimento com amebas: grupo controle e células tratadas com citocalasina B.",
    119: "Circuito aquático com quatro boias, lados de 800 e 400 metros e vetores da corrente e da velocidade do nadador.",
    121: "Tirinha de Calvin no balanço e sua queda no chão, com as falas originais dos quadrinhos.",
    122: "Tirinha de Laerte com esquimós em um iglu e uma geladeira, preservando as falas dos personagens.",
    123: "Fórmulas estruturais dos compostos orgânicos 1 e 2 usados na defesa das plantas.",
    124: "Três tubos de ensaio, numerados de 1 a 3, com diferentes distribuições de células bacterianas.",
    125: "Placa de saída de emergência com figura humana e indicação de deslocamento.",
    127: "Esquema das linhas de campo elétrico entre as barras metálicas A e B.",
    128: "Diagrama de uma placa de grafeno em contato com água da chuva e seus íons, indicando baixo potencial e movimentação de elétrons.",
    130: "Diagrama pressão-volume do ciclo de Otto, com os estados de 0 a 4.",
    131: "Símbolo do LED com o sentido permitido da corrente elétrica indicado.",
    132: "Circuito das lâmpadas L1 e L2, amperímetro, bateria e fio resistivo QR com os pontos A a E.",
    134: "Diagrama dos métodos de fitorremediação: fitovolatilização, fitoestabilização, fitodegradação, fitoestimulação e fitoextração.",
    136: "Microscópio óptico com a lente ocular e o conjunto de lentes objetivas indicados.",
    138: "Teclado alfanumérico com as teclas numéricas e as respectivas letras associadas.",
    141: "Gráficos que relacionam as grandezas I e II e as grandezas II e III, formados por segmentos de reta.",
    144: "Trapézio retângulo PQRS fixado pelo lado PS em uma vareta, com o sentido de rotação indicado.",
    147: "Visor da máquina caça-números com seis compartimentos, numerados de I a VI, contendo representações de números racionais.",
    148: "Gráfico da temperatura da caneca em função do tempo, iniciando em 100 graus Celsius e chegando a 40 graus em 20 minutos.",
    150: "Planta retangular da sala, de dimensões 3 por 6 metros, com a posição das colunas circulares.",
    152: "Gráfico dos valores de exportações e importações brasileiras, com junho de 2009, janeiro de 2010 e junho de 2010 destacados.",
    155: "Setor circular de cobertura do sensor, com centro S, raio R e ângulo alfa.",
    158: "Cartaz da promoção: máscara grátis na compra de pelo menos 35 litros de defensivo A; tipo A a R$ 4,20/litro, tipo B a R$ 3,00/litro e máscara a R$ 12,50.",
    161: "Tanque retangular com dois anteparos de alturas H/2 e H/4 e entrada de água pela parte superior.",
    163: "Sistema de duas polias de raios 4 e 6 centímetros, com centros distantes 15 centímetros e ângulo de 150 graus indicado.",
    164: "Esquema dos postos de saúde P1, P2 e P3 e do hospital H, com 10 quilômetros entre os postos.",
    167: "Dois celulares cujas telas têm medidas de 3 e meio e 4 e cinco sextos de polegada.",
    172: "Trecho entre os terminais 1 e 2 de um aeroporto, com as cinco regiões de cobertura das câmeras I a V.",
    173: "Gráfico de funcionários dos setores administrativo, logística e produção, por faixa etária.",
    174: "Trajetória espacial ABCDEF do personagem, com os planos e o plano da base representados.",
    175: "Duas formas de enrolar a folha de alumínio de 10 por 20 centímetros para produzir embalagens cilíndricas.",
    176: "Gráfico das receitas anuais de 2014 a 2021 com a reta de tendência para estimar os anos seguintes.",
}


def split_options(text):
    markers = list(re.finditer(r"^([ABCDE])(?:[ \t]+|\n|$)", text, re.M))
    candidates = [i for i in range(len(markers) - 4)
                  if "".join(m.group(1) for m in markers[i:i + 5]) == "ABCDE"]
    if not candidates:
        raise ValueError("Não foi possível identificar cinco alternativas A–E no JSON")
    options = markers[candidates[-1]:candidates[-1] + 5]
    body = text[:options[0].start()].strip()
    choices = [text[m.end():options[i + 1].start() if i < 4 else len(text)].strip()
               for i, m in enumerate(options)]
    return body, choices


def typography(text):
    replacements = {
        "CH3COO−": "CH₃COO⁻", "H2O": "H₂O", "CO2": "CO₂", "O2": "O₂", "H+": "H⁺", "e−": "e⁻",
        "Ca5(PO4)3OH": "Ca₅(PO₄)₃OH", "PO4\n3−": "PO₄³⁻", "Ca2+": "Ca²⁺", "Mg2+": "Mg²⁺",
        "Ca(OH)2": "Ca(OH)₂", "Mg(OH)2": "Mg(OH)₂", "Al2O3": "Al₂O₃", "10-3": "10⁻³",
        "m2": "m²", "m3": "m³", "f0": "f₀", "fr": "fᵣ", "E1": "E₁", "E2": "E₂",
        "S1": "S₁", "S2": "S₂", "S3": "S₃", "L1": "L₁", "L2": "L₂", "VQR": "V_QR",
        "P1": "P₁", "P2": "P₂", "P3": "P₃", "fi guras": "figuras", "codifi cado": "codificado",
    }
    # Literal replacements are restricted to this reviewed transcription (not a general language processor).
    for old, new in replacements.items():
        if old == "fr":
            text = re.sub(r"\bfr\b", new, text)
        else:
            text = text.replace(old, new)
    return text


def paragraphs(text):
    text = typography(text)
    parts, line_buffer = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if line_buffer:
                parts.append(" ".join(line_buffer)); line_buffer = []
            continue
        if line.startswith("•") and line_buffer:
            parts.append(" ".join(line_buffer)); line_buffer = []
        line_buffer.append(line)
        if re.search(r"[.!?:;]$", line):
            parts.append(" ".join(line_buffer)); line_buffer = []
    if line_buffer:
        parts.append(" ".join(line_buffer))
    return [{"type": "paragraph", "text": re.sub(r"[ \t]+", " ", p)} for p in parts]


def table(headers, rows, caption):
    return {"type": "table", "headers": headers, "rows": rows, "caption": caption}


def replace_region(body, start, end, marker):
    begin = body.index(start)
    stop = body.index(end, begin)
    return body[:begin] + f"\n\n[[{marker}]]\n\n" + body[stop:]


def structure_body(number, body):
    inserts = {}
    if number == 112:
        body = replace_region(body, "Considere a legenda:", "GRIFFITHS", "table")
        inserts['table'] = table(["Símbolo", "Significado"], [
            ["Círculo com ponto vermelho", "Mulher heterozigota portadora do gene para daltonismo"],
            ["Círculo vazio", "Mulher não daltônica"], ["Círculo vermelho", "Mulher daltônica"],
            ["Quadrado vazio", "Homem não daltônico"], ["Quadrado azul", "Homem daltônico"]], "Legenda dos heredogramas")
    if number == 118:
        body = replace_region(body, "Ca5(PO4)3OH (s)", "O uso de creme dental", "reaction")
        inserts['reaction'] = {"type": "math", "tex": r"\mathrm{Ca_5(PO_4)_3OH\,(s)+H^+\,(aq)}\ \underset{\text{Mineralização}}{\overset{\text{Desmineralização}}{\rightleftharpoons}}\ \mathrm{5\,Ca^{2+}\,(aq)+3\,PO_4^{3-}\,(aq)+H_2O\,(l)}"}
        body = replace_region(body, "Creme dental\n", "STORGATTO", "table")
        inserts['table'] = table(["Creme dental", "Agente de polimento", "pH"], [
            ["I", "Bicarbonato de sódio", "9,5"], ["II", "Carbonato de cálcio", "11,0"],
            ["III", "Citrato de potássio", "7,7"], ["IV", "Dióxido de silício", "6,9"],
            ["V", "Fosfato de cálcio", "7,3"]], "Composição e pH dos cremes dentais")
    if number == 130:
        body = replace_region(body, "Etapa Processo", "Disponível em:", "table")
        inserts['table'] = table(["Etapa", "Processo", "Descrição"], [
            ["I", "0 a 1", "Admissão isobárica da mistura ar-combustível no cilindro do motor."],
            ["II", "1 a 2", "Compressão adiabática da mistura."],
            ["III", "2 a 3", "Introdução de energia na forma de calor da combustão."],
            ["IV", "3 a 4", "Expansão adiabática."], ["V", "4 a 1", "Liberação de energia na forma de calor."],
            ["VI", "1 a 0", "Liberação dos gases resultantes da combustão."]], "Etapas do ciclo de Otto")
    if number == 139:
        body = replace_region(body, "Lojas\n", "Ele confeccionará", "table")
        inserts['table'] = table(["Loja", "Componente X (R$)", "Componente Y (R$)"], [["I", "3,00", "1,00"], ["II", "2,00", "4,00"]], "Preços dos componentes")
    if number == 142:
        body = replace_region(body, "Etapas\n", "A criança seguiu", "table")
        inserts['table'] = table(["Etapa", "Procedimento", "Visor de escrita"], [
            ["1ª", "Inseriu três figuras do tipo 🙂 no visor de escrita da mensagem.", "🙂🙂🙂"],
            ["2ª", "Copiou o que havia inserido anteriormente e colou ao lado.", "🙂🙂🙂🙂🙂🙂"],
            ["3ª", "Copiou o que tinha no visor na 2ª etapa e colou ao lado.", "🙂🙂🙂🙂🙂🙂🙂🙂🙂🙂🙂🙂"]], "Construção da mensagem")
    if number == 150:
        body = replace_region(body, "Loja\n", "A compra será realizada", "table")
        inserts['table'] = table(["Loja", "Raio (cm)", "Preço por unidade (R$)"], [["I", "5", "60"], ["II", "10", "70"], ["III", "12", "75"], ["IV", "15", "90"], ["V", "20", "120"]], "Orçamentos das colunas")
    if number == 154:
        body = replace_region(body, "Tipo de \nserviço", "ROMERO", "table")
        inserts['table'] = table(["Tipo de serviço", "Tempo de leitura (minutos)"], [["A", "36"], ["B", "17"], ["C", "27"], ["D", "13"], ["E", "13"], ["F", "13"]], "Tempo necessário para ler cada contrato")
    if number == 169:
        body = replace_region(body, "A B C D E F", "Disponível em:", "table")
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        inserts['table'] = table(["Letra do texto original", "Letra do texto codificado"], [[c, alphabet[(i + 3) % 26]] for i, c in enumerate(alphabet)], "Correspondência na Cifra de César ilustrada")
    if number == 177:
        body = replace_region(body, "Quantidade de \nmochilas", "O custo total, em real", "table")
        inserts['table'] = table(["Quantidade de mochilas", "Custo total (R$)"], [["30", "1 050,00"], ["50", "1 650,00"], ["100", "3 150,00"]], "Custo total de produção")
    if number == 178:
        body = replace_region(body, "Meses\n", "Nessa cidade", "table")
        inserts['table'] = table(["Mês", "Média mensal da umidade relativa do ar (%)"], [["Maio", "66"], ["Junho", "64"], ["Julho", "54"], ["Agosto", "46"], ["Setembro", "60"], ["Outubro", "64"]], "Umidade relativa do ar")
    if number == 135:
        body = body.replace("4,0 × 105", "4,0 × 10⁵")
    if number == 148:
        body = body.replace("T(t) = a + 80 bt", r"$T(t) = a + 80b^t$")
    if number == 165:
        body = body.replace("15\n60", r"$\frac{15}{60}$").replace("4\n100", r"$\frac{4}{100}$")
    if number == 167:
        body = body.replace("3 1\n2", r"$3\frac{1}{2}$").replace("4 5\n6", r"$4\frac{5}{6}$")
    if number == 170:
        body = replace_region(body, "M\nM\nE", "Estudos mais abrangentes", "formula")
        inserts['formula'] = {"type": "math", "tex": r"M_2-M_1=\frac{2}{3}\log\left(\frac{E_2}{E_1}\right)"}
    if number == 172:
        body = body.replace("1\n5", r"$\frac{1}{5}$").replace("3\n10", r"$\frac{3}{10}$").replace("1\n10", r"$\frac{1}{10}$")
    # Retain vector notation without dislocating an arrow onto the following line.
    body = body.replace("υc\n→", r"$\vec{v}_c$").replace("υn\n→", r"$\vec{v}_n$")
    blocks = []
    for part in re.split(r"(\[\[\w+\]\])", body):
        if re.fullmatch(r"\[\[\w+\]\]", part):
            blocks.append(inserts[part[2:-2]])
        else:
            blocks.extend(paragraphs(part))
    return blocks


def math_choices(number, choices):
    overrides = {
        142: [r"3\times2^{19}", r"3\times2^{20}", r"3\times2^{21}", r"3\times2^{20}-1", r"3\times2^{20}-3"],
        148: [r"a=20;\ b=\log(0{,}5)", r"a=100;\ b=0{,}5", r"a=20;\ b=(0{,}5)^{\frac{1}{10}}", r"a=20;\ b=\frac{40^{\frac{1}{10}}}{80}", r"a=20;\ b=40"],
        149: ["6", "18", r"6\sqrt{6}", r"6\sqrt[3]{6}", r"3\sqrt[3]{12}"],
        159: [r"\mathrm{mL}\cdot\mathrm{s}\cdot\mathrm{cm}^2", r"\frac{\mathrm{mL}}{\mathrm{s}}\cdot\mathrm{cm}^2", r"\frac{\mathrm{mL}}{\mathrm{cm}^2\cdot\mathrm{s}}", r"\frac{\mathrm{cm}^2\cdot\mathrm{s}}{\mathrm{mL}}", r"\frac{\mathrm{cm}^2}{\mathrm{mL}\cdot\mathrm{s}}"],
        166: [rf"d(Q)=\frac{{{a}}}{{{b}}}d(R)" for a,b in [(1,4),(1,2),(3,4),(3,2),(2,3)]],
        169: [r"\frac{1}{25}+\frac{1}{25}+\frac{1}{25}", r"\frac{24}{25}+\frac{23}{24}+\frac{1}{23}", r"\frac{1}{25}\times\frac{1}{24}\times\frac{1}{23}", r"\frac{24}{25}\times\frac{23}{25}\times\frac{1}{25}", r"\frac{24}{25}\times\frac{23}{24}\times\frac{1}{23}"],
        175: [r"4\,000\pi", r"2\,000\pi", r"\frac{4\,000}{\pi}", r"\frac{1\,000}{\pi}", r"\frac{500}{\pi}"],
        180: [r"\frac{7!}{4!}\times\frac{6!}{4!}", r"\frac{7!}{3!\times4!}\times\frac{6!}{2!\times4!}", r"\frac{7!}{3!\times4!}+\frac{6!}{2!\times4!}+\frac{5!}{1!\times4!}",
              r"\left(\frac{7!}{3!\times4!}+\frac{6!}{2!\times4!}\right)\times\left(\frac{7!}{4!\times3!}+\frac{6!}{1!\times5!}\right)\times\left(\frac{7!}{5!\times2!}+\frac{6!}{0!\times6!}\right)",
              r"\left(\frac{7!}{3!\times4!}\times\frac{6!}{2!\times4!}\right)+\left(\frac{7!}{4!\times3!}\times\frac{6!}{1!\times5!}\right)+\left(\frac{7!}{5!\times2!}\times\frac{6!}{0!\times6!}\right)"],
    }
    if number in overrides:
        return [f"${expression}$" for expression in overrides[number]]
    if number == 171:
        descriptions = ["hexágono regular", "hexágono regular", "quadrado", "triângulo equilátero", "triângulo equilátero"]
        formulas = [r"\frac{k^2\sqrt{3}}{24}", r"\frac{3k^2\sqrt{3}}{2}", r"\frac{k^2}{16}", r"\frac{k^2\sqrt{3}}{36}", r"\frac{k^2\sqrt{3}}{4}"]
        return [f"{shape}, pois a área do jardim, em metro quadrado, será ${formula}$." for shape, formula in zip(descriptions, formulas)]
    if number == 135:
        choices = [re.sub(r"10([4567])", lambda m: "10" + m.group(1).translate(str.maketrans("4567", "⁴⁵⁶⁷")), v) for v in choices]
    return [" ".join(typography(v).split()) for v in choices]


def isolate_figures(doc, content):
    number = content['number']
    found = []
    for region in content['layout']['blocks']:
        page = doc[region['page'] - 1]
        bounds = pymupdf.Rect(region['bbox'])
        for info in page.get_image_info():
            rect = pymupdf.Rect(info['bbox'])
            if rect.get_area() > 100 and (rect & bounds).get_area() / rect.get_area() > .98:
                found.append((region['page'], rect))
    option_regions = found[-5:] if number in GRAPHIC_OPTIONS and number != 112 else []
    figure_regions = found[:-5] if option_regions else found
    if number == 112:
        option_regions = [(7, pymupdf.Rect(304, 385 + i * 72.267, 422, 451 + i * 72.267)) for i in range(5)]
    if number == 113:
        figure_regions = [(8, pymupdf.Rect(31, 141, 279, 711))]
    figures, options = [], []
    for group, regions, target in [('figure', figure_regions, figures), ('option', option_regions, options)]:
        for i, (page_number, rect) in enumerate(regions):
            path = ASSETS / f"q{number}-{group}-{i + 1}.png"
            doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=rect).save(path)
            alt = DESCRIPTIONS.get(number, f"Figura da questão {number}.") if group == 'figure' else f"Diagrama da alternativa {'ABCDE'[i]} da questão {number}."
            target.append({"path": f"/assets/enem-2024-dia2-azul/native/{path.name}", "alt": alt})
    if number in GRAPHIC_OPTIONS:
        assert len(options) == 5, number
    return figures, options


def main():
    if not SOURCE.exists():
        SOURCE.write_bytes(TARGET.read_bytes())
    raw = json.loads(SOURCE.read_text())
    data = copy.deepcopy(raw)
    ASSETS.mkdir(parents=True, exist_ok=True)
    pdf = ROOT / "data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf"
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == raw['source']['sha256']
    doc = pymupdf.open(pdf)
    for question in data['questions']:
        content = question['content']
        original = content['statement']
        number = content['number']
        text = re.sub(r'^.*?QUESTÃO\s+\d+\s*', '', original, count=1, flags=re.S)
        body, choices = split_options(text)
        choices = math_choices(number, choices)
        figures, graphic_options = isolate_figures(doc, content)
        blocks = structure_body(number, body)
        # Figures remain separate from text. Insert them before the command paragraph.
        if figures:
            position = max(0, len(blocks) - 1)
            blocks[position:position] = [{"type": "image", "asset": asset} for asset in figures]
        content['statement'] = '\n\n'.join(block['text'] for block in blocks if block['type'] == 'paragraph')
        content['blocks'] = blocks
        content['images'] = []  # images are explicitly positioned blocks, never full-question screenshots
        content['alternatives'] = [{"letter": letter, "text": '' if graphic_options else choices[i],
                                    "image": graphic_options[i] if graphic_options else None}
                                   for i, letter in enumerate('ABCDE')]
        content['original_layout'] = False
        content['layout'] = {**content['layout'], "review_status": "native_json_reviewed", "presentation_version": "native-v1",
                             "legacy_text_sha256": hashlib.sha256(original.encode()).hexdigest(),
                             "text_source": SOURCE.name}
        assert not re.search(r'[\x00-\x08\x0b-\x1f]', content['statement']), number
        assert all(option['text'] or option['image'] for option in content['alternatives']), number
    data['source']['notes'] = 'Caderno completo do segundo dia (90 questões). Questão 129 anulada no gabarito oficial. Enunciados, alternativas, tabelas e fórmulas renderizados a partir do JSON; imagens restritas às figuras e aos diagramas. Temas e habilidades ainda não classificados. Produto independente, sem vínculo com o Inep.'
    # Apply the source-compared presentation review after reconstructing native-v1.
    sys.path.insert(0, str(ROOT))
    from scripts.review_presentation import apply_review
    data = apply_review(data)
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f"Estruturadas {len(data['questions'])} questões do JSON com texto nativo, tabelas e fórmulas.")


if __name__ == '__main__':
    main()
