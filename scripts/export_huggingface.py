#!/usr/bin/env python3
"""Monta os repositórios do Hugging Face (modelo e Space) a partir de um treino concluído.

    .venv/bin/python scripts/export_huggingface.py tmp/experiments/layout-neural-01 --repo-id CONTA/enem-layout-types

Saídas em `tmp/huggingface/<nome>/` (modelo) e `tmp/huggingface/<nome>-space/` (demonstração). Confere
`status: complete` e os hashes do relatório, do manifesto e dos pesos. Os exemplos são questões
reais do Inep sem conteúdo de terceiros (sem crédito, sem "Disponível em", figuras sem fonte
externa), uma por tipo comum; a lista sai em `exemplos/fontes.json` para conferência antes do envio.
"""

import _bootstrap  # noqa: F401
import argparse
from datetime import date
import json
from pathlib import Path
import shutil

from experiments.common import digest, file_digest, read_json
from ingestion.layout import types
from layout_groups import profile_exams

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'huggingface'
GITHUB = 'https://github.com/LemonCandles/enem-flow'
AUTHORS = ('Cassio Lima Silva', 'Diogo Vieira de Castro')
MODEL_FILES = {
    'README.md',
    'LICENSE',
    'CITATION.cff',
    'config.json',
    'model.safetensors',
    'layout-types.json',
    'requirements.txt',
    'enem_layout',
    'exemplos',
}
THIRD_PARTY = ('disponível em', 'disponivel em', 'acesso em', 'fonte:', 'http', 'adaptado')


def verified(run):
    metadata, report = read_json(run / 'run.json'), read_json(run / 'report.json')
    if metadata.get('status') != 'complete' or metadata['report_sha256'] != digest(report):
        raise SystemExit('Treino incompleto ou relatório divergente do run.json.')
    if file_digest(ROOT / metadata['manifest']) != metadata['manifest_sha256']:
        raise SystemExit('O manifesto mudou desde o treino.')
    seed = report['selected_seed']
    folder = run / f'seed-{seed}' / 'model'
    if file_digest(folder / 'model.safetensors') != report['runs'][str(seed)]['model_sha256']:
        raise SystemExit('Pesos divergentes do relatório.')
    for name, expected in metadata['code_files'].items():
        if file_digest(ROOT / name) != expected:
            raise SystemExit(f'{name} mudou desde o treino: treine de novo.')
    return metadata, report, folder


def own_content(content):
    """Questão sem texto nem figura de terceiros: nenhum crédito, link ou fonte externa."""
    texts = [b.get('text', '') for b in content.get('blocks') or []]
    texts += [b.get('credit', '') + b.get('caption', '') for b in content.get('blocks') or [] if b['type'] == 'image']
    texts += [a.get('text', '') for a in content['alternatives']]
    if any(
        b.get('role') == 'credit' or types.is_credit(b) for b in content.get('blocks') or [] if b['type'] == 'paragraph'
    ):
        return False
    return not any(marker in text.lower() for text in texts for marker in THIRD_PARTY)


def examples(manifest, limit):
    """Uma questão do teste por tipo comum, de autoria do Inep, com a fonte e o hash do caderno."""
    contents = {}
    for path in profile_exams():
        exam = read_json(path)
        for question in exam['questions']:
            contents[question['question_id']] = question['content']
    chosen, seen = [], set()
    test = [item for item in manifest['items'] if item['split'] == 'test' and item['content_form'] == 'estruturado']
    counts = {}
    for item in test:
        counts[item['type']] = counts.get(item['type'], 0) + 1
    for item in sorted(test, key=lambda i: (-counts[i['type']], i['type'], i['exam'], i['number'])):
        if item['type'] in seen or not own_content(contents[item['question_id']]):
            continue
        seen.add(item['type'])
        chosen.append(item)
        if len(chosen) == limit:
            break
    return chosen


def percent(value):
    return '—' if value is None else f'{100 * value:.1f}%'


def number(value):
    return '—' if value is None else f'{value:.3f}'


def interval(values):
    return '—' if not values else f'{100 * values[0]:.1f}–{100 * values[1]:.1f}%'


def card(repo_id, report, catalog, manifest, chosen, version):
    seed = str(report['selected_seed'])
    run = report['runs'][seed]
    test, development = run['test'], run['development']
    config = report['model_config']
    baselines = test['baselines']
    counts = manifest['counts']
    years = sorted({item['year'] for item in manifest['items'] if item['split'] in ('train', 'development')})
    labels = {
        'majority': 'Maioria (tipo mais comum do treino)',
        'rule_json': 'Regra sobre o JSON',
        'adapter': 'Adaptador do PDF',
    }
    yaml = [
        '---',
        'language:',
        '- pt',
        'license: mit',
        'library_name: pytorch',
        'pipeline_tag: image-classification',
        'tags:',
        '- enem',
        '- document-layout',
        '- layout-analysis',
        '- education',
        '- portuguese',
        'model-index:',
        f'- name: {repo_id.split("/")[-1]}',
        '  results:',
        '  - task:',
        '      type: image-classification',
        '      name: Tipo de layout de questões do ENEM',
        '    dataset:',
        '      type: enem-flow/layout-types-reference-v1',
        '      name: Questões revisadas do ENEM 2024 e 2025',
        '    metrics:',
        '    - type: accuracy',
        f'      value: {round(test["type_accuracy"], 4)}',
        '      name: Acurácia do tipo exato',
        *(
            line
            for axis in ('corpo', 'alternativas', 'marcas')
            for line in (
                '    - type: f1',
                f'      value: {round(test["axes"][axis]["macro_f1"] or 0, 4)}',
                f'      name: Macro-F1 ({axis})',
            )
        ),
        '---',
    ]
    body = [
        '# Enem Flow — tipos de layout de questões do ENEM',
        '',
        'Rede neural convolucional que recebe a **imagem de uma questão do ENEM** e devolve um **JSON** com o '
        f'tipo de layout de impressão, segundo o catálogo `{catalog["version"]}`: como os blocos do enunciado se '
        'sucedem (texto, crédito, figura, tabela), como as alternativas estão dispostas e se há marcas como texto '
        'compartilhado, linhas numeradas ou blocos lado a lado.',
        '',
        f'Faz parte do [Enem Flow]({GITHUB}), plataforma aberta de estudos para o ENEM, onde o tipo de layout '
        'orienta a apresentação de cada questão com a mesma diagramação do caderno.',
        '',
        f'**Autores:** {AUTHORS[0]} e {AUTHORS[1]}  ',
        f'**Código, dados de treino e protocolo:** {GITHUB}  ',
        f'**Versão:** `{version}` · catálogo `{catalog["version"]}` · licença MIT',
        '',
        '## Uso',
        '',
        '```bash',
        'pip install -r requirements.txt',
        f'python -m enem_layout.predict exemplos/{Path(chosen[0]["image"]).name} --model {repo_id}',
        '```',
        '',
        '```python',
        'from PIL import Image',
        'from enem_layout import EnemLayoutClassifier, predict_images',
        '',
        f'model = EnemLayoutClassifier.from_pretrained("{repo_id}")',
        'print(predict_images(model, [Image.open("questao.png")]))',
        '```',
        '',
        'A imagem deve conter **uma questão inteira** (do título "QUESTÃO n" até a última alternativa), sem o '
        'resto da página. O modelo foi treinado com recortes renderizados do PDF a 150 dpi.',
        '',
        '## Saída',
        '',
        '| Campo | Significado |',
        '| --- | --- |',
        '| `type` | Identificador do tipo, por exemplo `texto-figura+credito-texto.alt-texto`; `null` quando o corpo é `outro`. |',
        '| `axes` | Rótulo de cada eixo: `corpo`, `alternativas`, `marcas`. |',
        '| `probabilities` | Probabilidades calibradas por eixo (marcas são independentes). |',
        '| `confidence` | Produto das probabilidades escolhidas. |',
        f'| `needs_review` | Verdadeiro abaixo de {number(config["review_threshold"])} de confiança, fora do catálogo ou com corpo `outro`. |',
        '| `in_catalog`, `representable` | Se o tipo existe no catálogo e se o contrato de conteúdo do Enem Flow já o representa. |',
        '',
        '## Desempenho',
        '',
        f'Teste: **{test["samples"]} questões revisadas das provas de 2024 e 2025**, nenhuma vista no treino. '
        f'O treino usa o acervo de {years[0]} a {years[-1]}.',
        '',
        '| Método | Acurácia do tipo exato | IC 95% |',
        '| --- | --- | --- |',
        f'| **Esta rede (imagem)** | **{percent(test["type_accuracy"])}** | {interval(test["type_accuracy_ci95"])} |',
        *(
            f'| {labels[name]} | {percent(values["type_accuracy"])} | {interval(values["type_accuracy_ci95"])} |'
            for name, values in baselines.items()
        ),
        '',
        f'Média de três seeds no teste: {percent(report["test_type_accuracy_mean"])} '
        f'(desvio {100 * report["test_type_accuracy_std"]:.1f} p.p.). A seed publicada foi escolhida pelo '
        'desenvolvimento, sem olhar o teste.',
        '',
        'O adaptador lê o PDF original (texto, vetores e imagem) e foi a fonte dos rótulos automáticos; '
        'ele é uma referência, não um concorrente justo. A regra sobre o JSON exige o conteúdo já estruturado.',
        '',
        '| Eixo | Macro-F1 (teste) | Acurácia (teste) | Macro-F1 (desenvolvimento) |',
        '| --- | --- | --- | --- |',
        *(
            f'| {axis} | {number(test["axes"][axis]["macro_f1"])} | {percent(test["axes"][axis]["accuracy"])} '
            f'| {number(development["axes"][axis]["macro_f1"])} |'
            for axis in ('corpo', 'alternativas', 'marcas')
        ),
        '',
        f'Calibração (ECE) no teste: {number(test["calibration_error"])}. Com o limiar de revisão, o modelo aceita '
        f'{percent(test["review"]["coverage"])} das questões de teste, com {percent(test["review"]["accuracy_accepted"])} '
        'de acerto nelas.',
        '',
        'Por fatia do teste:',
        '',
        '| Fatia | Questões | Acurácia do tipo |',
        '| --- | --- | --- |',
        *(f'| {name} | {row["samples"]} | {percent(row["accuracy"])} |' for name, row in test['slices'].items()),
        '',
        'Por tipo no teste (suporte = questões do tipo):',
        '',
        '| Tipo | Precisão | Revocação | F1 | Suporte |',
        '| --- | --- | --- | --- | --- |',
        *(
            f'| `{kind}` | {number(row["precision"])} | {number(row["recall"])} | {number(row["f1"])} | {row["support"]} |'
            for kind, row in sorted(test['type']['per_class'].items(), key=lambda kv: -kv[1]['support'])
            if row['support']
        ),
        '',
        '## Dados de treino',
        '',
        f'- **Treino e desenvolvimento:** {counts.get("train", 0)} e {counts.get("development", 0)} questões de '
        f'provas impressas do acervo oficial do Inep ({years[0]}–{years[-1]}), com rótulo fraco automático: o '
        'adaptador de layout do Enem Flow lê o PDF original e só rotula as questões em que os canais vetorial e '
        'raster concordam e nenhuma invariante falha. As demais ficam fora do treino.',
        f'- **Teste:** {counts.get("test", 0)} questões impressas únicas de seis cadernos de 2024 e 2025, com rótulos '
        'revisados, incluindo decisões manuais justificadas.',
        '- **Sem vazamento:** questões agrupadas por identidade do conteúdo, texto repetido e texto de apoio '
        'compartilhado; questões do acervo que reaparecem no teste ficam fora do treino.',
        f'- **Partições e rótulos:** manifesto `{manifest["version"]}` (hashes de fonte, conteúdo e imagem) no '
        f'[repositório do projeto]({GITHUB}). As imagens não são redistribuídas; são geradas dos PDFs oficiais.',
        '',
        '## Arquitetura e treino',
        '',
        f'CNN de cerca de 10 milhões de parâmetros treinada do zero (sem pesos pré-treinados de terceiros), entrada '
        f'em tons de cinza de {config["width"]}×{config["height"]} com a proporção preservada, grade de posições '
        'verticais que preserva a ordem dos blocos, três cabeças (corpo e alternativas com softmax; marcas '
        'multirrótulo), perda ponderada por classe, aumentos leves sem espelhamento, precisão mista e parada pelo '
        'macro-F1 de desenvolvimento. Temperatura e limiar de revisão calibrados no desenvolvimento.',
        '',
        '## Tipos do catálogo',
        '',
        '| Tipo | Descrição | Representável |',
        '| --- | --- | --- |',
        *(
            f'| `{entry["id"]}` | {entry["description"]} | {"sim" if entry["representable"] else "não"} |'
            for entry in catalog['types']
        ),
        '',
        'Corpos com menos de 10 exemplos no treino saem como `outro`; o vocabulário do modelo está em `config.json`.',
        '',
        '## Exemplos',
        '',
        'Questões reais do Inep, de autoria do próprio Inep (sem textos ou imagens de terceiros), em `exemplos/`; '
        'origem e SHA-256 de cada caderno em `exemplos/fontes.json`.',
        '',
        '| Imagem | Questão | Tipo revisado |',
        '| --- | --- | --- |',
        *(
            f'| `{Path(item["image"]).name}` | {item["exam"]}, questão {item["number"]} | `{item["type"]}` |'
            for item in chosen
        ),
        '',
        '## Uso pretendido e limites',
        '',
        '- Uso pretendido: organizar e apresentar questões do ENEM com a diagramação do caderno, e triagem de '
        'provas novas na ingestão. Não avalia conteúdo pedagógico nem corrige respostas.',
        '- Treinado só em provas impressas (regular, reaplicação e segunda aplicação) a partir de 2009; provas '
        'anteriores, digitais e formatos acessíveis estão fora.',
        '- Os rótulos de treino são automáticos e podem repetir erros do adaptador; o teste revisado mede isso.',
        '- Tipos raros e marcas têm pouco suporte; use `needs_review` e as probabilidades.',
        '- A imagem precisa ser o recorte de uma questão; páginas inteiras ou fotos de celular não foram avaliadas.',
        '',
        '## Licença e fontes',
        '',
        'Código e pesos sob a licença MIT (`LICENSE`). As provas são publicações do Inep; as imagens de exemplo '
        'são questões de autoria do Inep e trazem a fonte. O treino usou os cadernos oficiais listados no manifesto '
        'do projeto, vinculados por URL e SHA-256.',
        '',
        '## Citação',
        '',
        '```bibtex',
        '@software{enem_flow_layout_types,',
        f'  author = {{{AUTHORS[0]} and {AUTHORS[1]}}},',
        '  title = {Enem Flow: tipos de layout de questões do ENEM},',
        f'  year = {{{date.today().year}}},',
        f'  version = {{{version}}},',
        f'  url = {{https://huggingface.co/{repo_id}}},',
        f'  note = {{Código: {GITHUB}}}',
        '}',
        '```',
        '',
    ]
    return '\n'.join(yaml + body)


def export(run, repo_id, output, limit):
    metadata, report, model_folder = verified(run)
    manifest = read_json(ROOT / metadata['manifest'])
    catalog_path = ROOT / 'data/catalog' / f'{manifest["catalog_version"]}.json'
    catalog = read_json(catalog_path)
    config = report['model_config']
    version = config['model_version'].rsplit('-', 1)[-1]
    images = ROOT / 'tmp/layout-dataset' / manifest['version'] / 'images'
    if output.exists():
        shutil.rmtree(output)
    (output / 'exemplos').mkdir(parents=True)
    for name in ('model.safetensors', 'config.json'):
        shutil.copyfile(model_folder / name, output / name)
    shutil.copyfile(catalog_path, output / 'layout-types.json')
    for name in ('LICENSE', 'requirements.txt'):
        shutil.copyfile(PACKAGE / name, output / name)
    shutil.copytree(PACKAGE / 'enem_layout', output / 'enem_layout', ignore=shutil.ignore_patterns('__pycache__'))
    chosen = examples(manifest, limit)
    sources = []
    for item in chosen:
        name = f'{item["exam"]}-q{item["number"]:03d}.png'
        shutil.copyfile(images / item['image'], output / 'exemplos' / name)
        item['image'] = name
        sources.append(
            {
                'image': name,
                'image_sha256': file_digest(output / 'exemplos' / name),
                'exam': item['exam'],
                'number': item['number'],
                'source_url': item['source_url'],
                'source_sha256': item['source_sha256'],
                'expected_type': item['type'],
                'publisher': 'Inep',
            }
        )
    (output / 'exemplos/fontes.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n')
    (output / 'CITATION.cff').write_text(
        (PACKAGE / 'CITATION.cff.template')
        .read_text()
        .format(version=version, date=date.today().isoformat(), repo_id=repo_id)
    )
    (output / 'README.md').write_text(card(repo_id, report, catalog, manifest, chosen, version))
    unexpected = sorted(p.name for p in output.iterdir() if p.name not in MODEL_FILES)
    if unexpected:
        raise SystemExit(f'Arquivos inesperados: {unexpected}')
    space = output.with_name(output.name + '-space')
    if space.exists():
        shutil.rmtree(space)
    space.mkdir(parents=True)
    shutil.copytree(PACKAGE / 'enem_layout', space / 'enem_layout', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(output / 'exemplos', space / 'exemplos')
    shutil.copyfile(PACKAGE / 'space/requirements.txt', space / 'requirements.txt')
    shutil.copyfile(PACKAGE / 'LICENSE', space / 'LICENSE')
    (space / 'app.py').write_text((PACKAGE / 'space/app.py').read_text().replace('{repo_id}', repo_id))
    (space / 'README.md').write_text((PACKAGE / 'space/README.md.template').read_text().format(repo_id=repo_id))
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path, help='Pasta do treino (ml/layout_types/train.py).')
    parser.add_argument('--repo-id', required=True, help='CONTA/nome do repositório de modelo.')
    parser.add_argument('--examples', type=int, default=8)
    args = parser.parse_args()
    base = (ROOT / 'tmp/huggingface').resolve()
    output = base / args.repo_id.split('/')[-1]
    chosen = export(args.run.resolve(), args.repo_id, output, args.examples)
    print(
        f'Modelo: {output}\nSpace: {output}-space\nExemplos ({len(chosen)}): confira exemplos/fontes.json antes do envio.'
    )


if __name__ == '__main__':
    main()
