"""Comparação temática: maioria, regras, NB multinomial e centróides TF-IDF.

Só a partição de treino participa do vocabulário, IDF, priors e centróides.
Rótulos, gabaritos, números, nomes de arquivo e metadados editoriais nunca
entram nas representações. Implementações pequenas, serializáveis em JSON.
"""

from collections.abc import Callable
from dataclasses import dataclass
from collections import Counter, defaultdict
import math
import re
import time
import unicodedata

from .common import ROOT, classification_metrics, digest, file_digest, latency_summary, read_json, write_json
from .contracts import ExternalPredictions, ThemeProposal

STOP = set(
    'a ao aos as o os um uma umas uns de da das do dos e em na nas no nos por para com que se sua seu suas seus esse essa este esta isso isto qual quais como mais menos entre sobre sendo foi sao ser tem uma'.split()
)


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def tokens(text):
    return [word for word in re.findall(r'[a-z]{2,}', normalized(text)) if word not in STOP]


def visible_text(content):
    """Uma única representação de cada trecho; não duplica statement e blocks."""
    blocks = content.get('blocks') or []
    pieces = []
    for block in blocks:
        if block['type'] == 'paragraph' and block.get('role') != 'credit':
            pieces.append(block['text'])
        elif block['type'] == 'math':
            pieces.append(block['tex'])
        elif block['type'] == 'table':
            pieces += block['headers'] + [cell for row in block['rows'] for cell in row]
        elif block['type'] == 'image':
            # Descrições/legendas técnicas podem conter o tema. O experimento é
            # textual e não finge observar a imagem ou usar essas anotações.
            pieces += block.get('equations', [])
    if not blocks:
        pieces.append(content['statement'])
    pieces += sorted(option['text'] for option in content['alternatives'])
    return '\n'.join(pieces)


def word_counts(words):
    return Counter(words)


def word_and_bigram_counts(words):
    return Counter(words + [' '.join(pair) for pair in zip(words, words[1:])])


def character_counts(words):
    padded = ' ' + ' '.join(words) + ' '
    return Counter(padded[i : i + n] for n in (3, 4, 5) for i in range(len(padded) - n + 1))


def features(text, kind):
    return CLASSIFIERS[kind].features(tokens(text))


def load_reference(config):
    from backend.app.installers.curated import classified
    from backend.app.services.presentation import content_fingerprint
    from backend.app.services.identity import signatures

    reference_path = ROOT / config['reference']
    reference = read_json(reference_path)
    catalog = read_json(ROOT / 'data/catalog/manifest.json')
    content = {}
    for entry in catalog['exams']:
        exam = classified(read_json(ROOT / entry['path']))
        for question in exam.questions:
            content[question.question_id] = (question.content.model_dump(), exam.source.sha256)
    rows = []
    for item in reference['items']:
        c, source_hash = content[item['question_id']]
        signature, _ = signatures(c)
        if (
            content_fingerprint(c) != item['content_sha256']
            or source_hash != item['source_sha256']
            or item['canonical_id'] != 'enem-' + signature[:32]
            or item['split_group'] != item['canonical_id']
        ):
            raise ValueError(f'Referência não corresponde à versão: {item["question_id"]}')
        if c['annulled'] or c['area'] != 'Matemática' or len(item['themes']) != 1:
            raise ValueError('Este protocolo inicial exige itens válidos com um tema de Matemática.')
        text = visible_text(c)
        rows.append(
            {
                **item,
                'text': text,
                'text_sha256': digest(text),
                'duplicate_sha256': digest(sorted(tokens(text))),
                'theme': item['themes'][0],
                'visual': any(b['type'] == 'image' for b in c.get('blocks', []))
                or any(a.get('image') for a in c['alternatives']),
            }
        )
    if len(rows) != reference['eligible_items'] or len({r['question_id'] for r in rows}) != len(rows):
        raise ValueError('Contagem/identificadores da referência inconsistentes.')
    return rows, {
        'reference': config['reference'],
        'sha256': file_digest(reference_path),
        'technical_annotations': True,
        'independent_review': False,
    }


def split_reference(rows, config, seed):
    """Agrupa antes de estratificar; transitividade inclui aliases e textos repetidos."""
    parents = list(range(len(rows)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen = {}
    for i, row in enumerate(rows):
        for key in [
            ('canonical', row['canonical_id']),
            ('text', row['duplicate_sha256']),
            ('group', row['split_group']),
        ]:
            if key in seen:
                parents[find(i)] = find(seen[key])
            else:
                seen[key] = i
    grouped = defaultdict(list)
    for i, row in enumerate(rows):
        grouped[find(i)].append(row)
    strata = defaultdict(list)
    for group in grouped.values():
        labels = {row['theme'] for row in group}
        if len(labels) != 1:
            raise ValueError('Duplicata com rótulos conflitantes: exige adjudicação antes do split.')
        group_id = min(row['canonical_id'] for row in group)
        strata[next(iter(labels))].append((group_id, group))
    result = []
    for theme, groups in sorted(strata.items()):
        if len(groups) < 3:
            raise ValueError(f'{theme}: são necessários três grupos para treino/desenvolvimento/teste.')
        ordered = sorted(groups, key=lambda pair: digest([seed, pair[0]]))
        test_count = max(1, round(len(ordered) * config['test_fraction']))
        dev_count = max(1, round(len(ordered) * config['development_fraction']))
        if test_count + dev_count >= len(ordered):
            raise ValueError('Frações deixam a classe sem treino.')
        for i, (group_id, group) in enumerate(ordered):
            split = 'test' if i < test_count else 'development' if i < test_count + dev_count else 'train'
            result.extend({**row, 'split': split, 'split_group': group_id} for row in group)
    return sorted(result, key=lambda row: row['question_id'])


def unit(vector):
    norm = math.sqrt(sum(value * value for value in vector.values()))
    return {key: value / norm for key, value in vector.items()} if norm else {}


def fit_majority(model, rows, config, counts):
    return model


def score_majority(model, vector):
    return {label: float(label == model['majority']) for label in model['labels']}


def fit_keywords(model, rows, config, counts):
    if set(config['keywords']) != set(model['labels']):
        raise ValueError('Regras precisam cobrir as classes do treino.')
    return {**model, 'keywords': config['keywords']}


def score_keywords(model, vector):
    return {label: sum(vector[word] for word in model['keywords'][label]) for label in model['labels']}


def fit_naive_bayes(model, rows, config, counts):
    vectors = [features(row['text'], model['kind']) for row in rows]
    by_class = {label: Counter() for label in model['labels']}
    for row, vector in zip(rows, vectors):
        by_class[row['theme']].update(vector)
    return {
        **model,
        'vocabulary': sorted({word for vector in vectors for word in vector}),
        'alpha': config['alpha'],
        'counts': {label: dict(values) for label, values in by_class.items()},
        'class_counts': dict(counts),
        'samples': len(rows),
    }


def score_naive_bayes(model, vector):
    vocabulary = set(model['vocabulary'])
    alpha = model['alpha']
    scores = {}
    for label in model['labels']:
        label_counts = model['counts'][label]
        total = sum(label_counts.values()) + alpha * len(vocabulary)
        scores[label] = math.log(model['class_counts'][label] / model['samples']) + sum(
            count * math.log((label_counts.get(word, 0) + alpha) / total)
            for word, count in vector.items()
            if word in vocabulary
        )
    return scores


def fit_centroid(model, rows, config, counts):
    vectors = [features(row['text'], model['kind']) for row in rows]
    vocabulary = sorted({word for vector in vectors for word in vector})
    df = Counter(word for vector in vectors for word in vector)
    idf = {word: math.log((1 + len(rows)) / (1 + df[word])) + 1 for word in vocabulary}
    centroids = {label: Counter() for label in model['labels']}
    for row, vector in zip(rows, vectors):
        centroids[row['theme']].update(
            unit({word: (1 + math.log(count)) * idf[word] for word, count in vector.items()})
        )
    return {**model, 'idf': idf, 'centroids': {label: unit(values) for label, values in centroids.items()}}


def score_centroid(model, vector):
    vector = unit(
        {word: (1 + math.log(count)) * model['idf'][word] for word, count in vector.items() if word in model['idf']}
    )
    return {
        label: sum(value * model['centroids'][label].get(word, 0) for word, value in vector.items())
        for label in model['labels']
    }


@dataclass(frozen=True)
class Classifier:
    features: Callable
    fit: Callable
    score: Callable


# Each method compared in the experiment; `config.models` chooses among them by name.
CLASSIFIERS = {
    'majority': Classifier(word_counts, fit_majority, score_majority),
    'keywords': Classifier(word_counts, fit_keywords, score_keywords),
    'multinomial_nb': Classifier(word_counts, fit_naive_bayes, score_naive_bayes),
    'tfidf_word_centroid': Classifier(word_and_bigram_counts, fit_centroid, score_centroid),
    'tfidf_character_centroid': Classifier(character_counts, fit_centroid, score_centroid),
}


def fit(kind, rows, config):
    if not rows:
        raise ValueError('Treino vazio.')
    if kind not in CLASSIFIERS:
        raise ValueError(f'Modelo desconhecido: {kind}')
    labels = sorted({row['theme'] for row in rows})
    counts = Counter(row['theme'] for row in rows)
    majority = min(labels, key=lambda label: (-counts[label], label))
    model = {
        'kind': kind,
        'labels': labels,
        'majority': majority,
        'version': '1.0',
        'training_groups': sorted({r['split_group'] for r in rows}),
        'training_content': sorted(r['content_sha256'] for r in rows),
    }
    return CLASSIFIERS[kind].fit(model, rows, config, counts)


def predict(model, text):
    kind, labels = model['kind'], model['labels']
    scores = CLASSIFIERS[kind].score(model, features(text, kind))
    ordered = sorted(labels, key=lambda label: (-scores[label], label != model['majority'], label))
    first, second = ordered[:2] if len(ordered) > 1 else (ordered[0], ordered[0])
    return {'theme': first, 'margin': scores[first] - scores[second], 'margin_is_probability': False, 'scores': scores}


def evaluate(model, rows):
    predictions, latencies, errors, repeats = [], [], [], []
    for row in rows:
        started = time.perf_counter()
        prediction = predict(model, row['text'])
        latencies.append((time.perf_counter() - started) * 1000)
        predictions.append(prediction['theme'])
        repeats.append(all(predict(model, row['text'])['theme'] == prediction['theme'] for _ in range(2)))
        if prediction['theme'] != row['theme']:
            errors.append(
                {
                    'question_id': row['question_id'],
                    'expected': row['theme'],
                    'predicted': prediction['theme'],
                    'visual': row['visual'],
                    'text_excerpt': row['text'][:350],
                    'content_sha256': row['content_sha256'],
                    'error_type': 'theme_confusion_with_visual_context' if row['visual'] else 'theme_confusion',
                }
            )
    return {
        **classification_metrics([row['theme'] for row in rows], predictions, model['labels']),
        'latency': latency_summary(latencies),
        'repeat_consistency': sum(repeats) / len(repeats) if repeats else None,
        'external_cost_usd': 0.0,
        'local_compute_cost_usd': None,
        'errors': errors,
    }


def external_evaluation(path, rows, labels, train_groups):
    payload = ExternalPredictions.model_validate(read_json(path))
    if set(payload.training_groups) - train_groups:
        raise ValueError('LLM declara grupos de desenvolvimento/teste no treinamento.')
    expected = {blind_id(r): r for r in rows if r['split'] in {'development', 'test'}}
    records = {r.question_id: r for r in payload.records}
    if len(records) != len(payload.records) or records.keys() != expected.keys():
        raise ValueError('LLM precisa prever exatamente os itens de desenvolvimento e teste, sem duplicatas.')
    for key, record in records.items():
        if (
            record.content_sha256 != expected[key]['content_sha256']
            or record.theme not in labels
            or any(theme not in labels for theme in record.repeat_themes)
        ):
            raise ValueError('Previsão externa com versão ou classe inválida.')
    evaluations = {}
    for split in ('development', 'test'):
        selected = [r for r in rows if r['split'] == split]
        subset = [records[blind_id(r)] for r in selected]
        evaluations[split] = {
            **classification_metrics([r['theme'] for r in selected], [r.theme for r in subset], labels),
            'latency': latency_summary([r.latency_ms for r in subset]),
            'external_cost_usd': sum(r.cost_usd for r in subset),
            'repeat_consistency': sum(all(t == r.theme for t in r.repeat_themes) for r in subset) / len(subset),
            'errors': [
                {
                    'question_id': row['question_id'],
                    'expected': row['theme'],
                    'predicted': record.theme,
                    'evidence': record.evidence,
                    'visual': row['visual'],
                }
                for row, record in zip(selected, subset)
                if row['theme'] != record.theme
            ],
        }
    return {
        'status': 'evaluated_external_submission',
        'model': payload.model,
        'prompt_sha256': payload.prompt_sha256,
        'data_policy': payload.data_policy,
        'input_sha256': file_digest(path),
        'training_groups': payload.training_groups,
        'pretraining_contamination': 'unknown; provas públicas podem ter integrado o pré-treino',
        **evaluations,
    }


def blind_id(row):
    return 'sample-' + digest(row['content_sha256'])[:20]


def proposal(row, model):
    output = predict(model, row['text'])
    return ThemeProposal.model_validate(
        {
            'schema_version': '1.0',
            'question_id': row['question_id'],
            'canonical_id': row['canonical_id'],
            'source_sha256': row['source_sha256'],
            'content_sha256': row['content_sha256'],
            'taxonomy_version': 'enem-content-v1',
            'labels': {'discipline': 'Matemática', 'themes': [output['theme']], 'skills': []},
            'origin': {'experiment': 'data-ai-v1', 'model': model['kind'], 'model_sha256': digest(model)},
            'evidence': row['text'][:350],
            'margin': output['margin'],
            'margin_is_probability': False,
            'review_status': 'proposed',
            'needs_review': True,
            'independent_review': False,
            'evaluation_split': row.get('split', 'unlabeled_archive'),
            'review_reasons': ['technical_reference_requires_independent_review']
            + (['visual_context_not_observed'] if row['visual'] else []),
        }
    ).model_dump()


def run(config, seed, output, external=None, archive=False, limit=200):
    rows, inputs = load_reference(config)
    rows = split_reference(rows, config, seed)
    partitions = {split: [r for r in rows if r['split'] == split] for split in ('train', 'development', 'test')}
    models, results = {}, {}
    for name in config['models']:
        start = time.perf_counter()
        model = fit(name, partitions['train'], config)
        training_ms = (time.perf_counter() - start) * 1000
        models[name] = model
        results[name] = {
            'training_ms': training_ms,
            **{split: evaluate(model, partitions[split]) for split in ('development', 'test')},
        }
    # O teste não participa da escolha ou do ajuste do modelo.
    selected = min(
        config['models'], key=lambda name: (-results[name]['development']['macro_f1'], config['models'].index(name))
    )
    proposals = [proposal(row, models[selected]) for row in rows]
    external_result = (
        external_evaluation(external, rows, models[selected]['labels'], {r['split_group'] for r in partitions['train']})
        if external
        else {
            'status': 'not_run',
            'reason': 'Sem provedor, modelo, orçamento e previsões externas declarados. Importação offline disponível; nenhuma chamada paga executada.',
        }
    )
    archive_info = {'requested': archive, 'exam_files': 0, 'proposals': 0, 'limit': limit}
    if archive:
        from backend.app.schemas import ExamImport
        from backend.app.services.presentation import content_fingerprint
        from backend.app.services.identity import signatures

        paths = sorted((ROOT / 'data/derived/exams').glob('enem-*.json'))
        paths = [path for path in paths if not path.name.endswith('.report.json')]
        archive_info['exam_files'] = len(paths)
        archive_info['available'] = bool(paths)
        identity_path = ROOT / 'data/derived/exams/identities.json'
        identities = read_json(identity_path).get('items', {}) if identity_path.exists() else {}
        for path in paths:
            exam = ExamImport.model_validate(read_json(path))
            for q in exam.questions:
                if q.content.annulled or q.content.area != 'Matemática' or archive_info['proposals'] >= limit:
                    continue
                c = q.content.model_dump()
                signature, _ = signatures(c)
                linked = identities.get(q.question_id, {})
                canonical_id = (
                    linked.get('canonical_id')
                    if linked.get('content_sha256') == content_fingerprint(c)
                    and linked.get('source_sha256') == exam.source.sha256
                    else None
                )
                text = visible_text(c)
                row = {
                    'question_id': q.question_id,
                    'canonical_id': canonical_id or 'enem-' + signature[:32],
                    'content_sha256': content_fingerprint(c),
                    'source_sha256': exam.source.sha256,
                    'text': text,
                    'visual': any(b['type'] == 'image' for b in c.get('blocks', []))
                    or any(a.get('image') for a in c['alternatives']),
                }
                proposals.append(proposal(row, models[selected]))
                archive_info['proposals'] += 1
            if archive_info['proposals'] >= limit:
                break
    manifest = [
        {
            k: r[k]
            for k in (
                'question_id',
                'canonical_id',
                'split_group',
                'split',
                'theme',
                'source_sha256',
                'content_sha256',
                'text_sha256',
            )
        }
        for r in rows
    ]
    report = {
        'reference': inputs,
        'split_manifest_sha256': digest(manifest),
        'split_counts': {key: len(value) for key, value in partitions.items()},
        'class_counts': {key: dict(Counter(r['theme'] for r in value)) for key, value in partitions.items()},
        'selection': {
            'model': selected,
            'criterion': 'development macro_f1; ties use config order',
            'test_used_for_selection': False,
            'refitted_on_test': False,
        },
        'models': results,
        'llm': external_result,
        'archive': archive_info,
        'limitations': [
            'Referência técnica assistida; segunda anotação independente pendente.',
            'Amostra pequena, de dois anos e uma disciplina; sem generalização presumida.',
            'Descrições/legendas editoriais, rótulos e gabarito excluídos das features.',
            'Margens não calibradas; nenhuma proposta é aprovação.',
        ],
    }
    write_json(output / 'classification-report.json', report)
    write_json(output / 'classification-splits.json', manifest)
    write_json(output / 'classification-model.json', models[selected])
    write_json(output / 'classification-proposals.json', proposals)
    # Payload sem gabarito/rótulo de referência para um eventual provedor externo.
    write_json(
        output / 'llm-input.json',
        {
            'schema_version': '1.0',
            'taxonomy': models[selected]['labels'],
            'items': [
                {'question_id': blind_id(r), 'content_sha256': r['content_sha256'], 'text': r['text']}
                for r in rows
                if r['split'] != 'train'
            ],
        },
    )
    return report
