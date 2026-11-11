"""Tipo de layout a partir do JSON de conteúdo e das figuras: maioria, regra, árvore e Naive Bayes.

Um preditor por eixo (corpo, alternativas, marcas); o tipo é a combinação dos três. As características
vêm de `ingestion.layout.types`, o mesmo código publicado como `predict.py`, e usam só o que o
produto terá: blocos do JSON e atributos das figuras. Sem PDF, imagem da questão, ano, número,
página, descrição ou caminho das figuras.

Partições agrupadas por identidade canônica, texto repetido e texto de apoio compartilhado,
estratificadas por família de layout. Tipos com menos grupos que o mínimo vão inteiros para o treino
e são reportados à parte. Só o treino ajusta; a escolha usa macro-F1 de desenvolvimento por eixo e o
teste nunca escolhe nem reajusta.
"""

from collections import Counter, defaultdict
import time

from ingestion.layout import types

from .common import ROOT, classification_metrics, digest, file_digest, latency_summary, read_json, write_json
from .layout import fit_tree

MODELS = ('majority', 'rule', 'tree:dimensoes', 'tree:completo', 'naive_bayes:dimensoes', 'naive_bayes:completo')
SPLITS = ('train', 'development', 'test')


def feature_sets():
    names = sorted(types.features({'alternatives': [{'text': ''}] * 5, 'blocks': []}, {}))
    return {'completo': names, 'dimensoes': [name for name in names if name not in types.INK_FEATURES]}


def family(axes):
    """Família grossa de layout, usada só para estratificar a partição."""
    if axes['marcas'] != types.NO_MARKS:
        return 'marcas'
    if axes['alternativas'] != 'texto':
        return 'alternativas-graficas'
    if 'tabela' in axes['corpo']:
        return 'tabela'
    if 'figura' in axes['corpo']:
        return 'figura'
    return 'texto'


def load_reference(config):
    from backend.app.services.identity import signatures
    from backend.app.services.presentation import content_fingerprint

    from .classification import tokens, visible_text

    reference_path, catalog_path = ROOT / config['reference'], ROOT / config['catalog']
    reference, catalog = read_json(reference_path), read_json(catalog_path)
    if reference['version'] != 'layout-types-reference-v1' or catalog['version'] != types.VERSION:
        raise ValueError('Versões da referência ou do catálogo de layout inesperadas.')
    contents = {}
    for source in reference['sources']:
        exam = read_json(ROOT / source['path'])
        if exam['source']['sha256'] != source['sha256']:
            raise ValueError(f'Fonte divergente da referência: {source["exam"]}')
        for question in exam['questions']:
            contents[question['question_id']] = (question['content'], exam['source']['sha256'])
    assets_root = (ROOT / 'data/assets').resolve()
    attributes, rows = {}, []
    for item in reference['items']:
        content, source_hash = contents[item['question_id']]
        if content_fingerprint(content) != item['content_sha256'] or source_hash != item['source_sha256']:
            raise ValueError(f'Referência não corresponde ao conteúdo atual: {item["question_id"]}')
        for path in types.asset_paths(content):
            if path not in attributes:
                file = (assets_root / path.removeprefix('/assets/')).resolve()
                if not file.is_relative_to(assets_root):
                    raise ValueError('Figura fora de data/assets.')
                attributes[path] = types.figure_attributes(file)
        signature, _ = signatures(content)
        rows.append(
            {
                **item,
                'content': content,
                'canonical_id': 'enem-' + signature[:32],
                'duplicate_sha256': digest(sorted(tokens(visible_text(content)))),
                'family': family(item['axes']),
            }
        )
    if {row['type'] for row in rows} != {entry['id'] for entry in catalog['types']}:
        raise ValueError('Catálogo e referência discordam sobre os tipos.')
    inputs = {
        'reference': config['reference'],
        'reference_sha256': file_digest(reference_path),
        'catalog': config['catalog'],
        'catalog_sha256': file_digest(catalog_path),
        'independent_review': False,
    }
    return rows, attributes, [entry['id'] for entry in catalog['types']], inputs


def split_reference(rows, config, seed):
    """Grupos transitivos (identidade, texto, apoio compartilhado) estratificados por família."""
    parents = list(range(len(rows)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen = {}
    for i, row in enumerate(rows):
        keys = [('canonical', row['canonical_id']), ('text', row['duplicate_sha256'])]
        if row['support_group']:
            keys.append(('support', row['support_group']))
        for key in keys:
            if key in seen:
                parents[find(i)] = find(seen[key])
            else:
                seen[key] = i
    grouped = defaultdict(list)
    for i, row in enumerate(rows):
        grouped[find(i)].append(row)
    groups = [(min(row['canonical_id'] for row in members), members) for members in grouped.values()]
    groups_per_type = Counter(kind for _, members in groups for kind in {row['type'] for row in members})
    rare = {kind for kind, count in groups_per_type.items() if count < config['min_type_groups']}
    strata, assigned = defaultdict(list), {}
    for group_id, members in groups:
        if {row['type'] for row in members} & rare:
            assigned[group_id] = 'train'
        else:
            strata[min(row['family'] for row in members)].append(group_id)
    for name, ids in sorted(strata.items()):
        ordered = sorted(ids, key=lambda group_id: digest([seed, group_id]))
        test = max(1, round(len(ordered) * config['test_fraction'])) if len(ordered) >= 3 else 0
        development = max(1, round(len(ordered) * config['development_fraction'])) if len(ordered) >= 3 else 0
        for i, group_id in enumerate(ordered):
            assigned[group_id] = 'test' if i < test else 'development' if i < test + development else 'train'
    result = [
        {**row, 'split': assigned[group_id], 'split_group': group_id} for group_id, members in groups for row in members
    ]
    return sorted(result, key=lambda row: (row['exam'], row['number'])), sorted(rare)


def fit_axis(name, axis, rows, vectors, config, sets):
    labels = [row['axes'][axis] for row in rows]
    counts = Counter(labels)
    kind, _, feature_set = name.partition(':')
    if kind == 'majority':
        return {'kind': 'majority', 'label': min(counts, key=lambda label: (-counts[label], label))}
    if kind == 'rule':
        return {'kind': 'rule'}
    names = sets[feature_set]
    matrix = [[vector[n] for n in names] for vector in vectors]
    if kind == 'tree':
        tree = fit_tree(list(zip(matrix, labels)), config['tree_max_depth'], config['tree_min_leaf'])
        return {'kind': 'tree', 'feature_set': feature_set, 'features': names, 'tree': tree}
    if kind == 'naive_bayes':
        overall = [statistics([row[j] for row in matrix])[1] for j in range(len(names))]
        floor = [config['variance_floor'] * value + 1e-9 for value in overall]
        classes = {}
        for label in sorted(counts):
            members = [row for row, target in zip(matrix, labels) if target == label]
            moments = [statistics([row[j] for row in members]) for j in range(len(names))]
            classes[label] = {
                'prior': len(members) / len(matrix),
                'mean': [m for m, _ in moments],
                'variance': [v + f for (_, v), f in zip(moments, floor)],
            }
        return {
            'kind': 'naive_bayes',
            'feature_set': feature_set,
            'features': names,
            'labels': sorted(counts),
            'classes': classes,
        }
    raise ValueError(f'Modelo desconhecido: {name}')


def statistics(values):
    average = sum(values) / len(values)
    return average, sum((v - average) ** 2 for v in values) / len(values)


def metrics(expected, predicted, vocabulary):
    labels = sorted(set(vocabulary) | set(predicted) | set(expected))
    return classification_metrics(expected, predicted, labels)


def support_table(rows, train_types):
    counts = Counter(row['type'] for row in rows)
    return {
        kind: {'support': count, 'in_train': kind in train_types, 'sufficient': count >= 2 and kind in train_types}
        for kind, count in sorted(counts.items())
    }


def run(config, seed, output):
    rows, attributes, catalog_types, inputs = load_reference(config)
    rows, rare = split_reference(rows, config, seed)
    sets = feature_sets()
    vectors = {row['question_id']: types.features(row['content'], attributes) for row in rows}
    partitions = {split: [row for row in rows if row['split'] == split] for split in SPLITS}
    train_vectors = [vectors[row['question_id']] for row in partitions['train']]
    vocabulary = {axis: sorted({row['axes'][axis] for row in rows}) for axis in types.AXES}
    models, results = {}, {}
    for axis in types.AXES:
        models[axis], results[axis] = {}, {}
        for name in config['models']:
            model = fit_axis(name, axis, partitions['train'], train_vectors, config, sets)
            models[axis][name] = model
            results[axis][name] = {}
            for split in SPLITS:
                selected_rows = partitions[split]
                predicted, latencies = [], []
                for row in selected_rows:
                    started = time.perf_counter()
                    predicted.append(types.predict_axis(model, axis, row['content'], vectors[row['question_id']]))
                    latencies.append((time.perf_counter() - started) * 1000)
                results[axis][name][split] = {
                    **metrics([row['axes'][axis] for row in selected_rows], predicted, vocabulary[axis]),
                    'latency': latency_summary(latencies),
                }
    # O teste não participa da escolha: desenvolvimento, depois treino (o desenvolvimento pode não ter
    # exemplos de uma classe rara), depois a ordem da configuração, que põe os mais simples antes.
    selection = {
        axis: min(
            config['models'],
            key=lambda name: (
                -(results[axis][name]['development']['macro_f1'] or 0),
                -(results[axis][name]['train']['macro_f1'] or 0),
                config['models'].index(name),
            ),
        )
        for axis in types.AXES
    }
    published = {
        'version': 'layout-types-model-v1',
        'catalog_version': types.VERSION,
        'catalog': catalog_types,
        'axes': {axis: models[axis][selection[axis]] for axis in types.AXES},
        'selection': selection,
    }
    published['figure_attributes'] = types.required_attributes(published)
    train_types = {row['type'] for row in partitions['train']}
    majority_type = Counter(row['type'] for row in partitions['train']).most_common(1)[0][0]
    predictions, combined = [], {}
    for split in SPLITS:
        expected, chosen, baseline, by_rule = [], [], [], []
        for row in partitions[split]:
            result = types.predict(published, row['content'], attributes)
            expected.append(row['type'])
            chosen.append(result['type'])
            baseline.append(majority_type)
            by_rule.append(types.identifier(types.rule(row['content'])))
            predictions.append(
                {
                    'question_id': row['question_id'],
                    'split': split,
                    'expected': row['type'],
                    'predicted': result['type'],
                    'axes': result['axes'],
                    'content_form': row['content_form'],
                    'origin': row['provenance']['origin'],
                }
            )
        if split == 'train':
            combined[split] = {'accuracy': sum(a == b for a, b in zip(expected, chosen)) / len(expected)}
            continue
        selected_rows = partitions[split]

        def accuracy(subset, values):
            pairs = [(row['type'], value) for row, value in zip(selected_rows, values) if subset(row)]
            return {'samples': len(pairs), 'accuracy': sum(a == b for a, b in pairs) / len(pairs) if pairs else None}

        combined[split] = {
            'model': metrics(expected, chosen, catalog_types),
            'majority_type': majority_type,
            'majority': accuracy(lambda row: True, baseline),
            'rule': accuracy(lambda row: True, by_rule),
            'slices': {
                **{
                    f'prova:{exam}': accuracy(lambda row, exam=exam: row['exam'] == exam, chosen)
                    for exam in sorted({row['exam'] for row in selected_rows})
                },
                'conteudo:estruturado': accuracy(lambda row: row['content_form'] == 'estruturado', chosen),
                'conteudo:imagem-unica': accuracy(lambda row: row['content_form'] == 'imagem-unica', chosen),
                'rotulo:automatico': accuracy(lambda row: row['provenance']['origin'] == 'automatic', chosen),
                'rotulo:manual': accuracy(lambda row: row['provenance']['origin'] == 'manual', chosen),
            },
            'support': support_table(selected_rows, train_types),
        }
    test = combined['test']
    ablation = {
        axis: {
            kind: {
                feature_set: results[axis][f'{kind}:{feature_set}']['development']['macro_f1']
                for feature_set in ('dimensoes', 'completo')
            }
            for kind in ('tree', 'naive_bayes')
            if f'{kind}:completo' in config['models'] and f'{kind}:dimensoes' in config['models']
        }
        for axis in types.AXES
    }
    manifest = [
        {
            key: row[key]
            for key in ('question_id', 'canonical_id', 'support_group', 'split_group', 'split', 'family', 'type')
        }
        for row in rows
    ]
    report = {
        'inputs': inputs,
        'seed': seed,
        'split_manifest_sha256': digest(manifest),
        'split_counts': {split: len(partitions[split]) for split in SPLITS},
        'split_groups': {split: len({row['split_group'] for row in partitions[split]}) for split in SPLITS},
        'rare_types_in_train_only': rare,
        'class_counts': {split: dict(Counter(row['type'] for row in partitions[split])) for split in SPLITS},
        'features': sets,
        'figure_attributes': attributes_summary(attributes),
        'models': results,
        'selection': {
            'axes': selection,
            'criterion': 'macro_f1 de desenvolvimento por eixo; empate pelo macro_f1 de treino e depois pela ordem da configuração',
            'test_used_for_selection': False,
            'refitted_on_test': False,
        },
        'ink_ablation_development_macro_f1': ablation,
        'published_figure_attributes': published['figure_attributes'],
        'type': combined,
        'beats_majority_on_test': (test['model']['accuracy'] or 0) > (test['majority']['accuracy'] or 0),
        'model_sha256': digest(published),
        'limitations': [
            'Seis provas de duas edições (2024 e 2025): os tipos comuns têm suporte; a cauda não.',
            'Rótulos técnicos, sem segunda revisão independente; decisões manuais com justificativa registrada.',
            'Questões publicadas como imagem única no JSON têm o layout impresso como rótulo, '
            'mas o JSON não o reproduz: são reportadas à parte.',
            'Marcas (texto compartilhado, lado a lado) têm poucas pistas no JSON atual.',
        ],
    }
    write_json(output / 'layout-types-report.json', report)
    write_json(output / 'layout-types-model.json', published)
    write_json(output / 'layout-types-splits.json', manifest)
    write_json(output / 'layout-types-predictions.json', predictions)
    return report


def attributes_summary(attributes):
    values = list(attributes.values())
    return {
        'figures': len(values),
        'ink_mean': sum(v['ink'] for v in values) / len(values) if values else None,
        'attributes_sha256': digest(attributes),
        'source': 'PNG em data/assets lidos por ingestion.layout.types.figure_attributes',
    }
