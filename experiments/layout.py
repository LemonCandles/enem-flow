"""Localização, classificação e relações de blocos em regiões de questão.

A região da questão é entrada comum a todos os métodos. As anotações de
blocos ficam só no treino/avaliador; nunca são passadas ao detector.
"""

from collections import Counter, defaultdict
from contextlib import nullcontext
import math
import re
import time

import pymupdf as fitz

from .common import (
    ROOT,
    classification_metrics,
    digest,
    file_digest,
    human_timings,
    latency_summary,
    read_json,
    source_path,
    write_json,
)
from .contracts import BLOCK_TYPES, LayoutBlock, LayoutProposal, LayoutReference


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap
    return overlap / area if area > 0 else 0.0


def match_blocks(expected, predicted, threshold):
    """Pareamento geométrico um-a-um, sem usar classes para escolher os pares."""
    pairs = sorted(
        (
            (iou(a['bbox'], b['bbox']), i, j)
            for i, a in enumerate(expected)
            for j, b in enumerate(predicted)
            if a['page'] == b['page']
        ),
        reverse=True,
    )
    used_a, used_b, matches = set(), set(), []
    for overlap, i, j in pairs:
        if overlap >= threshold and i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            matches.append((i, j, overlap))
    return matches


def option_letter(text):
    match = re.match(r'^\s*([ABCDE])(?:\t|\s+[ABCDE]\s|[.)]\s|\s+|$)', text)
    return match[1] if match else None


def block_features(block):
    """Somente características observáveis; ids, split e rótulos não entram."""
    text = block.get('text', '')
    box = block['bbox']
    width, height = block.get('_page_size', [600, 800])
    chars = max(1, len(text))
    return [
        (box[2] - box[0]) / width,
        (box[3] - box[1]) / height,
        box[0] / width,
        box[1] / height,
        math.log1p(len(text)),
        block.get('_font_size', 10) / 12,
        sum(c.isdigit() for c in text) / chars,
        sum(c.isupper() for c in text) / chars,
        float(bool(option_letter(text))),
        float(bool(re.search(r'Dispon[ií]vel em|Acesso em|adaptado|Fonte:|https?://', text))),
        float(bool(re.match(r'^(Figura|Gr[aá]fico|Esquema|Tabela)\b', text))),
        float(bool(re.search(r'[=∑∫√]|\\(?:frac|log)', text))),
        float(text.rstrip().endswith('.')),
    ]


def fit_tree(samples, max_depth=5, min_leaf=2):
    """CART numérico por Gini; limiares e classes aprendidos só no treino."""
    if not samples:
        raise ValueError('Sem blocos pareados no treino de layout.')

    def impurity(rows):
        counts = Counter(label for _, label in rows)
        return len(rows) - sum(n * n for n in counts.values()) / len(rows) if rows else 0

    def grow(rows, depth):
        counts = Counter(label for _, label in rows)
        label = min(counts, key=lambda key: (-counts[key], key))
        leaf = {'label': label, 'support': len(rows), 'class_counts': dict(counts)}
        if depth >= max_depth or len(counts) == 1 or len(rows) < 2 * min_leaf:
            return leaf
        best = None
        for feature in range(len(rows[0][0])):
            values = sorted({vector[feature] for vector, _ in rows})
            for low, high in zip(values, values[1:]):
                threshold = (low + high) / 2
                left = [row for row in rows if row[0][feature] <= threshold]
                right = [row for row in rows if row[0][feature] > threshold]
                if min(len(left), len(right)) < min_leaf:
                    continue
                loss = impurity(left) + impurity(right)
                if best is None or loss < best[0]:
                    best = (loss, feature, threshold, left, right)
        if best is None or best[0] >= impurity(rows):
            return leaf
        return {
            **leaf,
            'feature': best[1],
            'threshold': best[2],
            'left': grow(best[3], depth + 1),
            'right': grow(best[4], depth + 1),
        }

    return grow(samples, 0)


def tree_predict(tree, vector):
    while 'feature' in tree:
        tree = tree['left'] if vector[tree['feature']] <= tree['threshold'] else tree['right']
    return tree['label']


def rule_type(text, size):
    if option_letter(text):
        return 'alternative'
    if re.search(r'Dispon[ií]vel em|Acesso em|adaptado|Fonte:|https?://', text) or (size < 8.5 and ',' in text):
        return 'credit'
    if re.match(r'^(Figura|Gr[aá]fico|Esquema)\b', text):
        return 'caption'
    if len(text) < 100 and re.search(r'[=∑∫√]', text) and len(text.split()) < 14:
        return 'math'
    return 'paragraph'


def table_structure(page, table):
    """Preserva a geometria real das células mescladas; não propaga texto por palpite."""
    rects = [fitz.Rect(cell) for cell in table.cells if cell]
    xs = sorted({round(v, 1) for rect in rects for v in (rect.x0, rect.x1)})
    ys = sorted({round(v, 1) for rect in rects for v in (rect.y0, rect.y1)})
    cells = []
    for rect in rects:
        x0, x1, y0, y1 = map(lambda v: round(v, 1), [rect.x0, rect.x1, rect.y0, rect.y1])
        cells.append(
            {
                'bbox': list(rect),
                'row': ys.index(y0),
                'column': xs.index(x0),
                'rowspan': ys.index(y1) - ys.index(y0),
                'colspan': xs.index(x1) - xs.index(x0),
                'text': page.get_text(clip=rect).strip(),
            }
        )
    return {
        'rows': max(0, len(ys) - 1),
        'columns': max(0, len(xs) - 1),
        'cells': cells,
        'has_spans': any(c['rowspan'] > 1 or c['colspan'] > 1 for c in cells),
        'review_status': 'proposed',
    }


def extract_candidates(pdf, regions, enhanced, document=None):
    from scripts.exam_pdf import graphics, watermark

    candidates, table_proposals = [], []
    if document is not None and str(document.name) != str(pdf):
        raise ValueError('Documento aberto difere da fonte do experimento.')
    with nullcontext(document) if document is not None else fitz.open(pdf) as doc:
        for ri, region in enumerate(regions):
            page = doc[region['page'] - 1]
            clip = fitz.Rect(region['bbox'])
            if not page.rect.contains(clip):
                raise ValueError('Região fora da página original.')
            detector = page.find_tables(clip=clip, use_layout=False) if enhanced else None
            if enhanced and detector is None:
                raise ValueError('Detector de tabelas interrompido; preservar a região para revisão.')
            tables = detector.tables if enhanced else []
            tables = [table for table in tables if table.row_count >= 2 and table.col_count >= 2]
            excluded = [fitz.Rect(table.bbox) for table in tables]
            for table in tables:
                structure = table_structure(page, table)
                table_proposals.append({'page': region['page'], 'bbox': list(table.bbox), **structure})
                candidates.append(
                    {
                        'type': 'table',
                        'page': region['page'],
                        'bbox': list(table.bbox),
                        'text': ' '.join(c['text'] for c in structure['cells']),
                        '_region': ri,
                    }
                )
            rects = (
                graphics(page, clip)
                if enhanced
                else [
                    fitz.Rect(item['bbox']) & clip
                    for item in page.get_image_info()
                    if fitz.Rect(item['bbox']).intersects(clip)
                ]
            )
            for rect in rects:
                if rect.is_empty or any((rect & table).get_area() > 0.7 * rect.get_area() for table in excluded):
                    continue
                if rect.get_area() >= clip.get_area() * 0.90:
                    continue
                excluded.append(rect)
                candidates.append(
                    {'type': 'image', 'page': region['page'], 'bbox': list(rect), 'text': '', '_region': ri}
                )
            raw = page.get_text('dict', clip=clip, flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
            for block in raw['blocks']:
                if block['type'] != 0:
                    continue
                chunks, chunk, previous_option = [], [], None
                for line in block['lines']:
                    if watermark(line):
                        continue
                    text = ''.join(span['text'] for span in line['spans']).strip()
                    if not text or re.match(r'^\s*Q\s*U\s*E\s*S\s*T\s*[ÃA]\s*O\s*\d+', text, re.I):
                        continue
                    rect = fitz.Rect(line['bbox']) & clip
                    center = (rect.tl + rect.br) * 0.5
                    if any(r.contains(center) for r in excluded):
                        continue
                    letter = option_letter(text)
                    if enhanced and letter and letter != previous_option and chunk:
                        chunks.append(chunk)
                        chunk = []
                    chunk.append((line, text, rect))
                    if letter:
                        previous_option = letter
                if chunk:
                    chunks.append(chunk)
                for chunk in chunks:
                    box = fitz.Rect(chunk[0][2])
                    for _, _, rect in chunk[1:]:
                        box |= rect
                    text = ' '.join(text for _, text, _ in chunk)
                    sizes = [span['size'] for line, _, _ in chunk for span in line['spans']]
                    candidates.append(
                        {
                            'type': 'paragraph',
                            'page': region['page'],
                            'bbox': list(box),
                            'text': text,
                            '_font_size': sum(sizes) / len(sizes),
                            '_region': ri,
                            '_page_size': [page.rect.width, page.rect.height],
                        }
                    )
    return candidates, table_proposals


def assemble(candidates, method, tree=None):
    blocks = [dict(block) for block in candidates]
    for b in blocks:
        if b['type'] == 'paragraph' and method != 'coordinates':
            b['type'] = (
                tree_predict(tree, block_features(b))
                if method == 'cart'
                else rule_type(b['text'], b.get('_font_size', 10))
            )
        b['alternative'] = option_letter(b['text']) if b['type'] == 'alternative' else None
    if method != 'coordinates':
        # Só associa uma figura quando os marcadores têm geometria compatível.
        markers = [b for b in blocks if b['type'] == 'alternative' and b['alternative']]
        for image in [b for b in blocks if b['type'] == 'image']:
            x0, y0, x1, y1 = image['bbox']
            beside = [
                b
                for b in markers
                if b['page'] == image['page']
                and b['_region'] == image['_region']
                and y0 - 4 <= (b['bbox'][1] + b['bbox'][3]) / 2 <= y1 + 4
                and 0 <= x0 - b['bbox'][0] <= 65
            ]
            if len(beside) == 1:
                image['alternative'] = beside[0]['alternative']
    blocks.sort(
        key=lambda b: (
            bool(b['alternative']) if method != 'coordinates' else False,
            b['alternative'] or '',
            b['_region'],
            round(b['bbox'][1], 1),
            b['bbox'][0],
        )
    )
    for order, b in enumerate(blocks):
        b.update(id=f'b{order}', order=order, group=f'option-{b["alternative"]}' if b['alternative'] else 'stem')
    links = []
    if method != 'coordinates':
        images = [b for b in blocks if b['type'] == 'image' and not b['alternative']]
        for b in blocks:
            if b['type'] not in {'caption', 'credit'}:
                continue
            nearby = [
                image
                for image in images
                if image['page'] == b['page']
                and image['_region'] == b['_region']
                and min(abs(b['bbox'][1] - image['bbox'][3]), abs(image['bbox'][1] - b['bbox'][3])) < 45
            ]
            if nearby:
                closest = min(
                    nearby,
                    key=lambda image: min(abs(b['bbox'][1] - image['bbox'][3]), abs(image['bbox'][1] - b['bbox'][3])),
                )
                links.append({'source': b['id'], 'target': closest['id'], 'relation': b['type'] + '_of'})
    return {
        'blocks': [{key: value for key, value in b.items() if not key.startswith('_')} for b in blocks],
        'links': links,
        'review_status': 'proposed',
        'needs_review': True,
        'schema_version': '1.0',
    }


def evaluate_example(example, prediction, threshold):
    expected, blocks = example['blocks'], prediction['blocks']
    matches = match_blocks(expected, blocks, threshold)
    precision = len(matches) / len(blocks) if blocks else 0.0
    recall = len(matches) / len(expected) if expected else 0.0
    aligned = {blocks[j]['id']: expected[i]['id'] for i, j, _ in matches}
    expected_links = {(r['source'], r['target'], r['relation']) for r in example['links']}
    predicted_links = {
        (aligned.get(r['source'], '?' + r['source']), aligned.get(r['target'], '?' + r['target']), r['relation'])
        for r in prediction['links']
    }
    alternative_expected = sum(bool(b['alternative']) for b in expected)
    alternative_predicted = sum(bool(b['alternative']) for b in blocks)
    correct_alternatives = sum(
        bool(expected[i]['alternative']) and expected[i]['alternative'] == blocks[j]['alternative']
        for i, j, _ in matches
    )
    matched_order = sorted(matches, key=lambda pair: expected[pair[0]]['order'])
    pair_count = len(matches) * (len(matches) - 1) // 2
    correct_pairs = sum(
        blocks[a[1]]['order'] < blocks[b[1]]['order']
        for k, a in enumerate(matched_order)
        for b in matched_order[k + 1 :]
    )
    token_expected = token_kept = 0
    from .classification import tokens

    for b in expected:
        token_expected += len(tokens(b['text']))
    for i, j, _ in matches:
        token_kept += sum((Counter(tokens(expected[i]['text'])) & Counter(tokens(blocks[j]['text']))).values())
    missed = [b['id'] for i, b in enumerate(expected) if i not in {m[0] for m in matches}]
    mistyped = [
        {'block': expected[i]['id'], 'expected': expected[i]['type'], 'predicted': blocks[j]['type']}
        for i, j, _ in matches
        if expected[i]['type'] != blocks[j]['type']
    ]
    integrity = (
        not missed
        and not mistyped
        and len(matches) == len(blocks)
        and predicted_links == expected_links
        and correct_alternatives == alternative_expected
        and correct_pairs == pair_count
    )
    return {
        'id': example['id'],
        'pattern': example['pattern'],
        'difficult': example['difficult'],
        'expected_blocks': len(expected),
        'predicted_blocks': len(blocks),
        'matched_blocks': len(matches),
        'localization_precision': precision,
        'localization_recall': recall,
        'localization_f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        'mean_iou': sum(m[2] for m in matches) / len(matches) if matches else 0.0,
        'classification': classification_metrics(
            [expected[i]['type'] for i, _, _ in matches], [blocks[j]['type'] for _, j, _ in matches], BLOCK_TYPES
        ),
        'link_counts': {
            'correct': len(predicted_links & expected_links),
            'predicted': len(predicted_links),
            'expected': len(expected_links),
        },
        'alternative_counts': {
            'correct': correct_alternatives,
            'predicted': alternative_predicted,
            'expected': alternative_expected,
        },
        'reading_order': {
            'correct_pairs': correct_pairs,
            'pairs': pair_count,
            'agreement': correct_pairs / pair_count if pair_count else None,
        },
        'text_token_recall': token_kept / token_expected if token_expected else None,
        'integrity': integrity,
        'errors': {
            'missed_blocks': missed,
            'mistyped': mistyped,
            'extra_blocks': len(blocks) - len(matches),
            'missing_links': len(expected_links - predicted_links),
            'wrong_alternative_links': alternative_expected - correct_alternatives,
        },
    }


def summarize(rows):
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    def relationship(key):
        counts = {name: sum(row[key][name] for row in rows) for name in ('correct', 'predicted', 'expected')}
        return {
            **counts,
            'precision': ratio(counts['correct'], counts['predicted']),
            'recall': ratio(counts['correct'], counts['expected']),
        }

    return {
        'samples': len(rows),
        'localization_f1': sum(row['localization_f1'] for row in rows) / len(rows) if rows else None,
        'block_macro_f1': sum(row['classification']['macro_f1'] or 0 for row in rows) / len(rows) if rows else None,
        'mean_iou': sum(row['mean_iou'] for row in rows) / len(rows) if rows else None,
        'links': relationship('link_counts'),
        'alternatives': relationship('alternative_counts'),
        'reading_order_agreement': ratio(
            sum(row['reading_order']['correct_pairs'] for row in rows),
            sum(row['reading_order']['pairs'] for row in rows),
        ),
        'integrity_rate': ratio(sum(row['integrity'] for row in rows), len(rows)),
        'by_pattern': {
            pattern: {
                'samples': sum(row['pattern'] == pattern for row in rows),
                'intact': sum(row['integrity'] for row in rows if row['pattern'] == pattern),
            }
            for pattern in sorted({row['pattern'] for row in rows})
        },
    }


def run(config, output, review_log=None):
    reference_path = ROOT / config['reference']
    reference = LayoutReference.model_validate(read_json(reference_path))
    examples = [example.model_dump() for example in reference.examples]
    cache, table_proposals, extraction_times = {}, {}, {}
    for example in examples:
        pdf = source_path(example['source_path'], example['source_sha256'])
        for enhanced in (False, True):
            start = time.perf_counter()
            cache[(example['id'], enhanced)], tables = extract_candidates(pdf, example['regions'], enhanced)
            extraction_times[(example['id'], enhanced)] = (time.perf_counter() - start) * 1000
            if enhanced:
                table_proposals[example['id']] = tables
    samples = []
    for example in examples:
        if example['split'] != 'train':
            continue
        candidates = cache[(example['id'], True)]
        for i, j, _ in match_blocks(example['blocks'], candidates, config['iou_threshold']):
            if candidates[j]['type'] == 'paragraph':
                samples.append((block_features(candidates[j]), example['blocks'][i]['type']))
    tree = fit_tree(samples, config['tree_max_depth'], config['tree_min_leaf'])
    results, predictions = {}, {}
    for method in config['methods']:
        rows, latencies, consistent = [], [], []
        for example in examples:
            candidates = cache[(example['id'], method != 'coordinates')]
            start = time.perf_counter()
            prediction = assemble(candidates, method, tree)
            latency = (time.perf_counter() - start) * 1000 + extraction_times[(example['id'], method != 'coordinates')]
            for block in prediction['blocks']:
                LayoutBlock.model_validate(block)
            consistent.append(prediction == assemble(candidates, method, tree))
            predictions[(method, example['id'])] = prediction
            latencies.append(latency)
            rows.append({**evaluate_example(example, prediction, config['iou_threshold']), 'split': example['split']})
        results[method] = {
            split: summarize([row for row in rows if row['split'] == split])
            for split in ('train', 'development', 'test')
        }
        results[method].update(
            examples=rows,
            latency=latency_summary(latencies),
            repeat_consistency=sum(consistent) / len(consistent),
            external_cost_usd=0.0,
            local_compute_cost_usd=None,
        )
    selected = min(
        config['methods'],
        key=lambda method: (
            -(results[method]['development']['localization_f1'] or 0),
            -(results[method]['development']['block_macro_f1'] or 0),
            config['methods'].index(method),
        ),
    )
    proposals = [
        LayoutProposal.model_validate(
            {
                **predictions[(selected, example['id'])],
                'id': example['id'],
                'source_sha256': example['source_sha256'],
                'regions': example['regions'],
                'content_sha256': digest(example),
                'origin': {'method': selected, 'experiment': 'data-ai-v1'},
                'table_structures': table_proposals[example['id']],
            }
        ).model_dump()
        for example in examples
    ]
    report = {
        'reference_sha256': file_digest(reference_path),
        'reference_version': reference.version,
        'independent_review': False,
        'partition_unit': 'canonical group and whole source page',
        'training_blocks': len(samples),
        'models': results,
        'selection': {
            'method': selected,
            'criterion': 'development localization_f1 then block_macro_f1',
            'test_used_for_selection': False,
        },
        'human_correction_time': human_timings(review_log, {e['id']: digest(e) for e in examples}),
        'limitations': [
            'Amostra técnica assistida, não benchmark independente.',
            'Regiões de questão são entradas comuns; localização de questões inteiras não é avaliada.',
            'Integridade exige blocos, tipos, ordem e vínculos; texto científico ainda exige conferência.',
            'Tempo humano ausente é null; não é estimado a partir da latência automática.',
        ],
    }
    write_json(output / 'layout-report.json', report)
    write_json(
        output / 'layout-model.json',
        {
            'kind': 'cart',
            'tree': tree,
            'version': '1.0',
            'training_groups': sorted(e['split_group'] for e in examples if e['split'] == 'train'),
        },
    )
    write_json(output / 'layout-proposals.json', proposals)
    return report
