#!/usr/bin/env python3
"""Imagens rotuladas para a rede neural de tipos de layout (`layout-types-archive-v1`).

- Treino e desenvolvimento: provas impressas do acervo de 2009 a 2023, geradas por
  `build_archive_exams.py`. Rótulo fraco automático (`automatic-weak`) só nas questões elegíveis
  ao adaptador; as demais ficam sem rótulo e fora do treino.
- Teste: as 370 questões revisadas de `layout-types-reference-v1` (2024 e 2025), com os rótulos
  da referência. Questões do acervo que reaparecem no teste ficam fora do treino.

As imagens (150 dpi, uma por questão) vão para `tmp/layout-dataset/<versão>/`, fora do Git e
reproduzíveis a partir do PDF; o manifesto versionado vai para `data/datasets/`, com o SHA-256 de
cada imagem. Duas execuções sobre as mesmas fontes dão o mesmo manifesto.

    .venv/bin/python scripts/layout_dataset.py --workers 4
"""

import _bootstrap  # noqa: F401
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

from experiments.common import digest, read_json
from experiments.layout_types import family
from ingestion.layout import types
from ingestion.layout.analysis import ADAPTER
from layout_groups import profile_exams, run

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'layout-types-archive-v1'
CATALOG_VERSION = 'layout-types-v2'
REFERENCE = ROOT / 'data/datasets/layout-types-reference-v1.json'
YEARS = range(2009, 2024)


def archive_exams(years):
    """Provas impressas do acervo nos anos pedidos, fora do perfil local (que é o teste)."""
    profile = {Path(p).resolve() for p in profile_exams()}
    result = []
    for path in sorted((ROOT / 'data/derived/exams').glob('enem-*.json')):
        if path.name.endswith('.report.json') or path.resolve() in profile:
            continue
        exam = read_json(path)
        if exam['year'] in years and 'digital' not in exam['application'].lower():
            result.append(path)
    return result


def by_source(paths):
    """Uma tarefa por PDF: cadernos de inglês e espanhol compartilham itens e são deduplicados juntos."""
    groups = defaultdict(list)
    for path in paths:
        groups[read_json(path)['source']['sha256']].append(path)
    return [paths for _, paths in sorted(groups.items())]  # ordem de entrada: a primeira ocorrência é a da referência


def identity(content):
    """Identidade canônica e texto, para agrupar a mesma questão em cadernos e aplicações diferentes."""
    from backend.app.services.identity import signatures
    from experiments.classification import tokens, visible_text

    try:
        canonical = 'enem-' + signatures(content)[0][:32]
    except ValueError:
        canonical = None
    return canonical, digest(sorted(tokens(visible_text(content))))


def analyze(task):
    paths, images = task
    scratch = images / '.recortes' / hashlib.sha256(str(paths[0]).encode()).hexdigest()[:12]
    try:
        rows = run(paths, images, scratch, overlays=False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    contents = {}
    for path in paths:
        exam = read_json(path)
        for question in exam['questions']:
            contents[question['question_id']] = (exam, question['content'])
    result = []
    for row in rows:
        exam, content = contents[row['question_id']]
        canonical, text = identity(content)
        image = images / row['image']
        result.append(
            {
                **row,
                'year': exam['year'],
                'application': exam['application'],
                'source_url': exam['source']['url'],
                'canonical_id': canonical or 'conteudo-' + row['content_sha256'][:32],
                'text_sha256': text,
                'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                'baselines': {'rule': types.identifier(types.rule(content)), 'adapter': adapter_type(row['signature'])},
            }
        )
    return result


def adapter_type(signature):
    try:
        return types.type_id(signature)
    except ValueError:
        return None


def weak_label(row):
    """Eixos do rótulo automático: só questão elegível com assinatura que o catálogo sabe decompor."""
    if not row['eligible']:
        return None, 'nao-elegivel'
    try:
        return types.labels(types.axes(row['signature'])), None
    except ValueError:
        return None, 'assinatura-desconhecida'


def split(rows, seed, development_fraction):
    """Grupos transitivos (identidade, texto, apoio compartilhado) estratificados por família."""
    parents = list(range(len(rows)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        keys = [('canonical', row['canonical_id']), ('text', row['text_sha256'])]
        if row['support_group']:
            keys.append(('support', row['support_group']))
        for key in keys:
            if key in seen:
                parents[find(i)] = find(seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    strata = defaultdict(list)
    for members in groups.values():
        group_id = min(row['canonical_id'] for row in members)
        for row in members:
            row['split_group'] = group_id
        labeled = sorted(family(row['axes']) for row in members if row['axes'])
        strata[labeled[0] if labeled else 'sem-rotulo'].append(group_id)
    assigned = {}
    for name, ids in strata.items():
        ordered = sorted(ids, key=lambda group_id: digest([seed, group_id]))
        development = max(1, round(len(ordered) * development_fraction)) if len(ordered) >= 3 else 0
        for i, group_id in enumerate(ordered):
            assigned[group_id] = 'development' if i < development else 'train'
    for row in rows:
        row['split'] = assigned[row['split_group']] if row['axes'] else 'unlabeled'


def catalog_v2(archive, reference, min_support):
    """Catálogo v1 mais os tipos do acervo com suporte mínimo; o resto do acervo é corpo `outro`."""
    v1 = read_json(ROOT / 'data/catalog/layout-types.json')
    known = {entry['id']: entry for entry in v1['types']}
    counts = Counter(row['type'] for row in archive if row['type'])
    signatures = defaultdict(Counter)
    for row in archive:
        if row['type']:
            signatures[row['type']][row['signature']] += 1
    test_counts = Counter(item['type'] for item in reference['items'])
    entries = []
    for type_id in sorted(set(known) | {t for t, n in counts.items() if n >= min_support}):
        value = types.parse_identifier(type_id)
        reasons = types.unrepresentable(value)
        entries.append(
            {
                'id': type_id,
                'axes': value,
                'labels': types.labels(value),
                'description': types.description(value),
                'origin': 'layout-types-v1' if type_id in known else 'acervo',
                'review': 'revisado' if type_id in known else 'pendente',
                'questions_archive': counts[type_id],
                'questions_reference': test_counts[type_id],
                'archive_signatures': dict(sorted(signatures[type_id].items())),
                'representable': not reasons,
                'reasons': reasons,
            }
        )
    entries.sort(key=lambda entry: (-(entry['questions_archive'] + entry['questions_reference']), entry['id']))
    return {
        'version': CATALOG_VERSION,
        'extends': v1['version'],
        'dataset': VERSION,
        'adapter': ADAPTER,
        'axes': v1['axes'],
        'fusion_rule': v1['fusion_rule'],
        'min_archive_support': min_support,
        'other_policy': 'Corpo fora do catálogo vira `outro` no treino; o tipo exato continua no manifesto.',
        'counts': {
            'types': len(entries),
            'new_from_archive': sum(entry['origin'] == 'acervo' for entry in entries),
            'archive_labeled': sum(counts.values()),
            'archive_outside_catalog': sum(n for t, n in counts.items() if t not in {e['id'] for e in entries}),
        },
        'types': entries,
    }


def manifest_item(row, split_name, labels, provenance, reason=None):
    return {
        'id': f'{row["exam"]}#{row["number"]}',
        'question_id': row['question_id'],
        'exam': row['exam'],
        'year': row['year'],
        'application': row['application'],
        'number': row['number'],
        'occurrences': row['occurrence_ids'],
        'source_url': row['source_url'],
        'source_sha256': row['source_sha256'],
        'content_sha256': row['content_sha256'],
        'image': row['image'],
        'image_sha256': row['image_sha256'],
        'signature': row['signature'],
        'eligible': row['eligible'],
        'blocking_issues': sorted({i['code'] for i in row['issues'] if i['severity'] == 'error'}),
        'axes': labels,
        'type': types.identifier(labels) if labels else None,
        'label_origin': provenance,
        'unlabeled_reason': reason,
        'content_form': row['content_form'],
        'support_group': row['support_group'],
        'canonical_id': row['canonical_id'],
        'split_group': row.get('split_group', row['canonical_id']),
        'split': split_name,
        'baselines': row['baselines'],
    }


def write_manifest(path, header, items):
    lines = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in items]
    head = json.dumps(header, ensure_ascii=False, sort_keys=True, indent=1)[:-2]
    path.write_text(head + ',\n "items": [\n' + ',\n'.join(lines) + '\n ]\n}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=ROOT / 'tmp/layout-dataset' / VERSION)
    parser.add_argument('--manifest', type=Path, default=ROOT / f'data/datasets/{VERSION}.json')
    parser.add_argument('--catalog', type=Path, default=ROOT / f'data/catalog/{CATALOG_VERSION}.json')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--min-support', type=int, default=20)
    parser.add_argument('--development-fraction', type=float, default=0.15)
    args = parser.parse_args()
    seed = read_json(ROOT / 'experiments/config.json')['seed']
    archive_paths = archive_exams(YEARS)
    if not archive_paths:
        raise SystemExit(
            'Nenhuma prova do acervo em data/derived/exams: rode archive_enem.py e build_archive_exams.py.'
        )
    test_paths = [Path(p) for p in profile_exams()]
    tasks = [(paths, args.output / 'images') for paths in by_source(archive_paths) + by_source(test_paths)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(analyze, tasks))
    test_ids = {read_json(p)['source']['sha256'] for p in test_paths}
    rows = [row for result in results for row in result]
    test_rows = [row for row in rows if row['source_sha256'] in test_ids]
    archive = [row for row in rows if row['source_sha256'] not in test_ids]
    reference = read_json(REFERENCE)
    labels = {item['question_id']: item for item in reference['items']}
    test_canonical = {row['canonical_id'] for row in test_rows} | {row['text_sha256'] for row in test_rows}
    for row in archive:
        row['axes'], row['reason'] = weak_label(row)
        if row['canonical_id'] in test_canonical or row['text_sha256'] in test_canonical:
            row['axes'], row['reason'] = None, 'reaparece-no-teste'
        row['type'] = types.identifier(row['axes']) if row['axes'] else None
    split(archive, seed, args.development_fraction)
    items = []
    for row in archive:
        origin = 'automatic-weak' if row['axes'] else None
        items.append(manifest_item(row, row['split'], row['axes'], origin, row['reason']))
    for row in test_rows:
        item = labels[row['question_id']]
        if item['content_sha256'] != row['content_sha256'] or item['source_sha256'] != row['source_sha256']:
            raise SystemExit(f'Referência desatualizada para {row["question_id"]}.')
        origin = 'manual' if item['provenance']['origin'] == 'manual' else 'automatic-reviewed'
        items.append(manifest_item(row, 'test', item['axes'], origin))
    items.sort(key=lambda item: (item['split'] != 'test', item['exam'], item['number']))
    catalog = catalog_v2(archive, reference, args.min_support)
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + '\n')
    sources = sorted({(row['exam'], row['source_url'], row['source_sha256']) for row in rows})
    header = {
        'version': VERSION,
        'catalog_version': CATALOG_VERSION,
        'reference_version': reference['version'],
        'adapter': ADAPTER,
        'seed': seed,
        'images': 'PNG de 150 dpi gerados por scripts/layout_dataset.py em tmp/layout-dataset/; não versionados.',
        'policy': 'Rótulo fraco automático só para questão elegível do acervo; teste com rótulos revisados.',
        'sources': [{'exam': e, 'url': u, 'sha256': s} for e, u, s in sources],
        'counts': {
            'items': len(items),
            **Counter(item['split'] for item in items),
            'unlabeled_reasons': dict(Counter(item['unlabeled_reason'] for item in items if item['unlabeled_reason'])),
        },
    }
    write_manifest(args.manifest, header, items)
    print(json.dumps(header['counts'], ensure_ascii=False))
    print(f'Catálogo {CATALOG_VERSION}: {catalog["counts"]}')


if __name__ == '__main__':
    main()
