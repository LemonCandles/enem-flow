#!/usr/bin/env python3
"""Monta a pasta do modelo de tipos de layout para o Hugging Face a partir de uma execução concluída.

Confere `status: complete` e os hashes do relatório, do modelo, do catálogo e do código do preditor.
A pasta não contém textos nem figuras das provas: só pesos/regras em JSON, catálogo, `predict.py`
(só biblioteca padrão), configuração, model card e um exemplo fictício.

    .venv/bin/python scripts/export_layout_model.py tmp/experiments/layout-types-01
    .venv/bin/python scripts/export_layout_model.py tmp/experiments/layout-types-01 --verify
    .venv/bin/python scripts/export_layout_model.py tmp/experiments/layout-types-01 --check-copy <pasta baixada>

`--verify` copia a pasta exportada para fora do repositório e roda o `predict.py` dela, isolado, no
conjunto de teste; as previsões precisam ser iguais às do experimento. `--check-copy` faz o mesmo com
uma pasta já existente, por exemplo o repositório baixado do Hugging Face. As entradas de teste ficam
em `tmp/huggingface/<repo>-verificacao/`, nunca na pasta publicada.
"""

import _bootstrap  # noqa: F401
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from experiments.common import digest, file_digest, read_json
from ingestion.layout import types

ROOT = Path(__file__).resolve().parents[1]
PREDICTOR = ROOT / 'ingestion/layout/types.py'
FILES = ('README.md', 'LICENSE', 'config.json', 'model.json', 'layout-types.json', 'predict.py', 'exemplos')
EXAMPLE = {
    'number': 1,
    'area': 'Ciências da Natureza',
    'statement': 'Questão fictícia de exemplo.',
    'page': 1,
    'blocks': [
        {'type': 'paragraph', 'text': 'Um texto de apoio fictício descreve um experimento simples com plantas.'},
        {'type': 'paragraph', 'text': 'SOBRENOME, N. Título fictício. Disponível em: https://exemplo.org.'},
        {'type': 'image', 'asset': {'path': '/assets/exemplo/figura.png', 'alt': 'Esquema fictício.'}},
        {'type': 'paragraph', 'text': 'Qual conclusão o experimento permite?'},
    ],
    'alternatives': [{'letter': letter, 'text': f'Conclusão fictícia {letter}.'} for letter in 'ABCDE'],
}
EXAMPLE_FIGURES = {'/assets/exemplo/figura.png': {'width': 600, 'height': 300, 'ink': 0.08}}


def verified_run(run):
    metadata = read_json(run / 'run.json')
    if metadata.get('status') != 'complete':
        raise SystemExit('A execução não terminou (status diferente de complete).')
    report, model = read_json(run / 'layout-types-report.json'), read_json(run / 'layout-types-model.json')
    if metadata['report_sha256'].get('layout-types') != digest(report):
        raise SystemExit('Relatório diverge do hash registrado na execução.')
    if report['model_sha256'] != digest(model):
        raise SystemExit('Modelo diverge do hash registrado no relatório.')
    if metadata['code_files'].get('ingestion/layout/types.py') != file_digest(PREDICTOR):
        raise SystemExit('O preditor mudou desde a execução: rode o experimento de novo.')
    inputs = report['inputs']
    for key in ('reference', 'catalog'):
        if file_digest(ROOT / inputs[key]) != inputs[f'{key}_sha256']:
            raise SystemExit(f'{inputs[key]} mudou desde a execução: rode o experimento de novo.')
    return metadata, report, model


def percent(value):
    return '—' if value is None else f'{100 * value:.1f}%'


def number(value):
    return '—' if value is None else f'{value:.3f}'


def marks_warning(report):
    """Avisa quando desenvolvimento e teste não têm nenhuma questão com marca: a métrica do eixo nada mede."""
    evaluated = {
        label
        for split in ('development', 'test')
        for label, row in report['models']['marcas']['majority'][split]['per_class'].items()
        if row['support']
    }
    if evaluated - {types.NO_MARKS}:
        return []
    return [
        'O eixo marcas não tem nenhuma questão marcada no desenvolvimento nem no teste: todos os tipos com marca '
        'são raros e ficaram no treino. O macro-F1 desse eixo abaixo não mede a detecção de marcas.',
        '',
    ]


def card(repo, metadata, report, model, catalog, reference, example_output):
    selection = report['selection']['axes']
    test, development = report['type']['test'], report['type']['development']
    names = {
        'majority': 'maioria',
        'rule': 'regra determinística',
        'tree': 'árvore de decisão',
        'naive_bayes': 'Naive Bayes gaussiano',
    }

    def label(name):
        kind, _, feature_set = name.partition(':')
        return names[kind] + (f' ({"com" if feature_set == "completo" else "sem"} tinta)' if feature_set else '')

    attributes = model['figure_attributes']
    lines = [
        '---',
        'language: pt',
        'license: mit',
        'tags:',
        '- enem',
        '- layout',
        '- document-layout',
        '- tabular-classification',
        '---',
        '',
        f'# {repo}',
        '',
        'Classifica o layout de impressão de uma questão do ENEM em um tipo do catálogo fechado '
        f'`{catalog["version"]}`, a partir do JSON de conteúdo da questão (blocos de texto, crédito, figura, '
        'tabela e fórmula, e alternativas). O tipo diz como apresentar a questão com o mesmo layout do caderno.',
        '',
        'O repositório não contém textos nem figuras das provas: só o catálogo, as regras e pesos em JSON, '
        'o preditor e um exemplo fictício.',
        '',
        '## Entrada e saída',
        '',
        '- Entrada: o JSON de conteúdo de uma questão (`blocks` e `alternatives`, no contrato do Enem Flow). '
        'Não usa PDF, imagem da questão, ano, número, página, descrição nem caminho das figuras.',
        '- Atributos de figura: '
        + (
            f'`{", ".join(attributes)}` de cada figura citada, fornecidos em `--figures` ou calculados dos PNG com `--assets`.'
            if attributes
            else 'esta versão não usa; `--figures` e `--assets` são aceitos e ignorados pelos preditores escolhidos.'
        ),
        '- Saída: `type` (identificador do tipo), `axes` (corpo, alternativas, marcas), `in_catalog`, '
        '`representable` e os motivos quando o contrato de conteúdo ainda não representa o tipo.',
        '',
        'Um tipo combina três eixos:',
        '',
        '- corpo: sequência canônica dos blocos do enunciado (texto, crédito, figura, figura com crédito, '
        'figura com legenda, tabela);',
        '- alternativas: ' + '; '.join(f'`{k}` ({v})' for k, v in types.ALTERNATIVES.items()) + ';',
        '- marcas: ' + '; '.join(f'`{k}` ({v.rstrip(".").lower()})' for k, v in types.MARKS.items()) + '.',
        '',
        f'**Regra de fusão.** {catalog["fusion_rule"]}',
        '',
        '## Uso',
        '',
        'Só a biblioteca padrão do Python (verificado com 3.11 e 3.14).',
        '',
        '```bash',
        'python predict.py exemplos/questao-ficticia.json'
        + ('' if not attributes else ' --figures exemplos/figuras-ficticias.json'),
        '```',
        '',
        '```json',
        json.dumps(example_output, ensure_ascii=False, indent=2),
        '```',
        '',
        'Para várias questões, passe uma lista `[{"id": ..., "content": ..., "figures": {...}}]`.',
        '',
        '## Modelo publicado',
        '',
        'Um preditor por eixo, escolhido pelo macro-F1 de desenvolvimento (empate pelo macro-F1 de treino e '
        'depois pelo mais simples). O teste não escolheu nem reajustou preditores. Ressalva: a regra '
        'determinística foi revista uma vez (crédito que o JSON põe antes da figura; comando final em texto) '
        'depois de uma execução cujos números agregados de teste já tinham sido vistos; a revisão partiu só dos '
        'erros de treino e desenvolvimento.',
        '',
        '| Eixo | Preditor escolhido |',
        '| --- | --- |',
        *(f'| {axis} | {label(selection[axis])} |' for axis in types.AXES),
        '',
    ]
    if all(name == 'rule' for name in selection.values()):
        lines += [
            'Nesta versão a regra determinística, que deriva o tipo da ordem e do papel dos blocos do JSON, '
            'venceu a árvore de decisão e o Naive Bayes no desenvolvimento nos três eixos. O modelo publicado é '
            'essa regra; os preditores aprendidos aparecem nas métricas para comparação.',
            '',
            'A regra nunca emite as alternativas `linha` e `grade` nem as marcas `compartilhado` e `lado-a-lado`: '
            'o JSON atual não traz pistas delas. Questões desses tipos recebem o tipo sem a marca e com '
            'alternativas `texto` ou `figura`; isso explica o macro-F1 de alternativas no teste.',
            '',
        ]
    lines += [
        'Ablação da densidade de tinta (macro-F1 de desenvolvimento, sem → com):',
        '',
        *(
            f'- {axis}, {names[kind]}: {number(values["dimensoes"])} → {number(values["completo"])}'
            for axis, kinds in report['ink_ablation_development_macro_f1'].items()
            for kind, values in kinds.items()
        ),
        '',
        '## Métricas',
        '',
        f'Tipo exato (as {report["split_counts"]["test"]} questões de teste e as '
        f'{report["split_counts"]["development"]} de desenvolvimento):',
        '',
        '| Partição | Modelo | Maioria | Regra | Macro-F1 do modelo |',
        '| --- | --- | --- | --- | --- |',
        f'| desenvolvimento | {percent(development["model"]["accuracy"])} | {percent(development["majority"]["accuracy"])} '
        f'| {percent(development["rule"]["accuracy"])} | {number(development["model"]["macro_f1"])} |',
        f'| teste | {percent(test["model"]["accuracy"])} | {percent(test["majority"]["accuracy"])} '
        f'| {percent(test["rule"]["accuracy"])} | {number(test["model"]["macro_f1"])} |',
        '',
        f'A maioria prevê sempre `{test["majority_type"]}`.',
        '',
        *marks_warning(report),
        'Macro-F1 por eixo e preditor (desenvolvimento / teste):',
        '',
        '| Eixo | ' + ' | '.join(label(name) for name in report['models']['corpo']) + ' |',
        '| --- |' + ' --- |' * len(report['models']['corpo']),
        *(
            f'| {axis} | '
            + ' | '.join(
                f'{number(result["development"]["macro_f1"])} / {number(result["test"]["macro_f1"])}'
                for result in report['models'][axis].values()
            )
            + ' |'
            for axis in types.AXES
        ),
        '',
        'Por tipo, no teste (suporte = questões do tipo no teste):',
        '',
        '| Tipo | Precisão | Revocação | F1 | Suporte |',
        '| --- | --- | --- | --- | --- |',
    ]
    per_class = test['model']['per_class']
    support = test['support']
    sufficient = [kind for kind, row in support.items() if row['sufficient']]
    insufficient = [kind for kind, row in support.items() if not row['sufficient']]
    lines += [
        f'| `{kind}` | {number(per_class[kind]["precision"])} | {number(per_class[kind]["recall"])} '
        f'| {number(per_class[kind]["f1"])} | {per_class[kind]["support"]} |'
        for kind in sufficient
    ]
    lines += [
        '',
        'Tipos com suporte insuficiente no teste (uma questão, ou ausentes do treino), fora da leitura da média: '
        + (', '.join(f'`{kind}` ({support[kind]["support"]})' for kind in insufficient) or 'nenhum')
        + '.',
        '',
        'Tipos raros, com menos de três grupos no corpus, ficaram inteiros no treino e não têm avaliação: '
        + ', '.join(f'`{kind}`' for kind in report['rare_types_in_train_only'])
        + '.',
        '',
        'Fatias do teste:',
        '',
        '| Fatia | Questões | Acurácia do tipo |',
        '| --- | --- | --- |',
        *(f'| {name} | {row["samples"]} | {percent(row["accuracy"])} |' for name, row in test['slices'].items()),
        '',
        '## Partições',
        '',
        f'Seed `{report["seed"]}`. Grupos transitivos por identidade canônica da questão, texto repetido e texto '
        'de apoio compartilhado (as ocorrências dos cadernos de inglês e espanhol são uma só questão), '
        'estratificados por família de layout: '
        + ', '.join(f'{split} {report["split_counts"][split]}' for split in ('train', 'development', 'test'))
        + ' questões.',
        '',
        '## Tipos do catálogo',
        '',
        '| Tipo | Descrição | Questões | Representável |',
        '| --- | --- | --- | --- |',
        *(
            f'| `{entry["id"]}` | {entry["description"]} | {entry["questions"]} | '
            f'{"sim" if entry["representable"] else "não"} |'
            for entry in catalog['types']
        ),
        '',
        '“Representável” quer dizer que o contrato de conteúdo atual já tem os elementos do tipo; não é avaliação '
        'pedagógica.',
        '',
        '## Origem dos rótulos',
        '',
        f'{reference["counts"]["questions"]} questões impressas únicas ({reference["counts"]["occurrences"]} '
        f'ocorrências) de seis cadernos do Inep de 2024 e 2025. O rótulo vem do PDF original pelo adaptador '
        f'`{reference["adapter"]}`: automático ({reference["counts"]["automatic"]}) quando os canais vetorial e '
        'raster concordam e nenhuma invariante falha; decisão manual justificada '
        f'({reference["counts"]["manual"]}) nos demais casos. Sem segunda revisão independente.',
        '',
        '| Caderno | URL | SHA-256 |',
        '| --- | --- | --- |',
        *(f'| {s["exam"]} | {s["url"]} | `{s["sha256"]}` |' for s in reference['sources']),
        '',
        '## Limites',
        '',
        *(f'- {item}' for item in report['limitations']),
        '- O tipo descreve o layout; “disponível” ou “representável” não é aprovação pedagógica.',
        '',
        '## Licença',
        '',
        'Código, regras, pesos e catálogo sob a licença MIT (arquivo `LICENSE`). As provas e gabaritos são '
        'publicações do Inep e não são redistribuídos aqui.',
        '',
        '## Versões',
        '',
        f'`{model["version"]}` com o catálogo `{model["catalog_version"]}`. Cada versão do catálogo ou do modelo '
        'corresponde a uma tag deste repositório.',
        '',
    ]
    return '\n'.join(lines)


def export(run, output, repo):
    metadata, report, model = verified_run(run)
    catalog_path, reference_path = ROOT / report['inputs']['catalog'], ROOT / report['inputs']['reference']
    catalog, reference = read_json(catalog_path), read_json(reference_path)
    if output.exists():
        shutil.rmtree(output)
    (output / 'exemplos').mkdir(parents=True)
    shutil.copyfile(run / 'layout-types-model.json', output / 'model.json')
    shutil.copyfile(catalog_path, output / 'layout-types.json')
    shutil.copyfile(PREDICTOR, output / 'predict.py')
    shutil.copyfile(ROOT / 'LICENSE', output / 'LICENSE')
    write(output / 'exemplos/questao-ficticia.json', EXAMPLE)
    write(output / 'exemplos/figuras-ficticias.json', EXAMPLE_FIGURES)
    write(
        output / 'config.json',
        {
            'model_version': model['version'],
            'catalog_version': catalog['version'],
            'reference_version': reference['version'],
            'adapter': reference['adapter'],
            'experiment_config_version': metadata['config']['version'],
            'seed': report['seed'],
            'selection': report['selection'],
            'figure_attributes': model['figure_attributes'],
            'sources': [{k: s[k] for k in ('exam', 'url', 'sha256')} for s in reference['sources']],
            'hashes': {
                'model.json': file_digest(output / 'model.json'),
                'layout-types.json': file_digest(output / 'layout-types.json'),
                'predict.py': file_digest(output / 'predict.py'),
                'model_sha256': report['model_sha256'],
                'reference_sha256': report['inputs']['reference_sha256'],
                'decisions_sha256': reference['decisions_sha256'],
                'split_manifest_sha256': report['split_manifest_sha256'],
                'experiment_config_sha256': metadata['config_sha256'],
                'code_sha256': metadata['code_sha256'],
            },
            'license': 'MIT',
        },
    )
    example_output = types.predict(model, EXAMPLE, EXAMPLE_FIGURES)
    (output / 'README.md').write_text(card(repo, metadata, report, model, catalog, reference, example_output))
    return report


def test_inputs(run, folder):
    """Questões de teste com os atributos das figuras, gravadas fora da pasta publicada."""
    from experiments.layout_types import load_reference

    report = read_json(run / 'layout-types-report.json')
    config = {'reference': report['inputs']['reference'], 'catalog': report['inputs']['catalog']}
    rows, attributes, _, _ = load_reference(config)
    expected = {p['question_id']: p for p in read_json(run / 'layout-types-predictions.json') if p['split'] == 'test'}
    items = [
        {
            'id': row['question_id'],
            'content': row['content'],
            'figures': {path: attributes[path] for path in types.asset_paths(row['content'])},
        }
        for row in rows
        if row['question_id'] in expected
    ]
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'test-inputs.json', items)
    return folder / 'test-inputs.json', expected


def check(run, copy, folder):
    inputs, expected = test_inputs(run, folder)
    result = subprocess.run(
        [sys.executable, '-I', str(copy.resolve() / 'predict.py'), str(inputs.resolve())],
        cwd=folder,
        capture_output=True,
        text=True,
        check=True,
    )
    predictions = {item['id']: item for item in json.loads(result.stdout)}
    differences = [
        key
        for key, row in expected.items()
        if predictions[key]['type'] != row['predicted'] or predictions[key]['axes'] != row['axes']
    ]
    if differences or predictions.keys() != expected.keys():
        raise SystemExit(f'Previsões divergentes do experimento: {differences[:10]}')
    hits = sum(row['predicted'] == row['expected'] for row in expected.values())
    print(f'{len(expected)} questões de teste: previsões iguais às do experimento ({hits} tipos corretos).')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path, help='Pasta de uma execução de run_experiments.py --only layout-types.')
    parser.add_argument('--repo', default='enem-flow-layout-types', help='Nome do repositório do modelo.')
    parser.add_argument('--output', type=Path, help='Pasta de saída; padrão: tmp/huggingface/<repo>.')
    parser.add_argument('--verify', action='store_true', help='Roda o predict.py exportado numa cópia isolada.')
    parser.add_argument('--check-copy', type=Path, help='Só verifica uma pasta existente, como a baixada do Hub.')
    args = parser.parse_args()
    base = (ROOT / 'tmp/huggingface').resolve()
    output = (args.output or base / args.repo).resolve()
    if not output.is_relative_to(base) or output == base:
        parser.error('A pasta exportada fica em tmp/huggingface/<repo>.')
    verification = base / f'{args.repo}-verificacao'
    if args.check_copy:
        check(args.run, args.check_copy, verification)
        return
    verified_run(args.run)
    export(args.run, output, args.repo)
    unexpected = sorted(p.name for p in output.iterdir() if p.name not in FILES)
    if unexpected:
        raise SystemExit(f'Arquivos inesperados na pasta exportada: {unexpected}')
    print(f'Modelo exportado: {output}')
    if args.verify:
        copy = verification / 'copia'
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(output, copy)
        check(args.run, copy, verification)


if __name__ == '__main__':
    main()
