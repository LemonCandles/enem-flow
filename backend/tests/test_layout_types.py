"""Tipos de layout: eixos, identificadores, decisões manuais, partições e preditor publicado."""

import ast
import copy
import json
import struct
import subprocess
import sys
import zlib

import pymupdf as fitz
import pytest

from backend.app.preparation.rules import CREDIT
from experiments.common import ROOT, digest, file_digest, read_json
from experiments.layout_types import feature_sets, split_reference
from ingestion.layout import reference, types
from ingestion.layout.analysis import line_numbers, printed_beside

CATALOG = ROOT / 'data/catalog/layout-types.json'
REFERENCE = ROOT / 'data/datasets/layout-types-reference-v1.json'
DECISIONS = ROOT / 'data/datasets/layout-types-decisions-v1.json'


@pytest.mark.parametrize(
    ('signature', 'expected'),
    [
        ('P Cr P ALT:texto', 'texto-credito-texto.alt-texto'),
        ('P Cr P Cr P Cr P ALT:texto', 'texto-credito-texto.alt-texto'),
        ('P F P F P ALT:texto', 'texto-figura-texto.alt-texto'),
        ('P F+Cr P ALT:figura', 'texto-figura+credito-texto.alt-figura'),
        ('S P# Cr P ALT:texto', 'texto-credito-texto.alt-texto.compartilhado.linhas-numeradas'),
        ('P F|F Cr P ALT:texto', 'texto-figura-credito-texto.alt-texto.lado-a-lado'),
        ('P T|F P ALT:texto', 'texto-tabela-figura-texto.alt-texto.lado-a-lado'),
    ],
)
def test_signature_decomposes_into_stable_identifiers(signature, expected):
    value = types.axes(signature)
    assert types.type_id(signature) == expected
    assert types.parse_identifier(expected) == value
    assert types.identifier(types.labels(types.parse_identifier(expected))) == expected


@pytest.mark.parametrize(
    'signature', ['P T|N P ALT:texto', 'P N ALT:texto', 'P ALT:?', 'P Cap P ALT:texto', 'P S ALT:texto']
)
def test_unknown_tokens_fail_instead_of_creating_silent_types(signature):
    with pytest.raises(ValueError):
        types.axes(signature)


def test_marks_and_mixed_alternatives_are_catalogued_as_not_yet_representable():
    assert not types.unrepresentable(types.axes('P F+Cr P ALT:grade'))
    assert len(types.unrepresentable(types.axes('S P# Cr P ALT:texto'))) == 1
    assert types.unrepresentable(types.axes('P F ALT:misto'))
    assert types.unrepresentable(types.axes('P P|P Cr P ALT:texto'))


def test_published_credit_rule_matches_the_preparation_rule():
    assert types.CREDIT.pattern == CREDIT.pattern


def test_committed_catalog_and_reference_cover_every_question_with_a_known_type():
    catalog, labeled = read_json(CATALOG), read_json(REFERENCE)
    assert labeled['counts']['questions'] == len(labeled['items']) == 370
    assert labeled['decisions_sha256'] == file_digest(DECISIONS)
    ids = {entry['id'] for entry in catalog['types']}
    assert {item['type'] for item in labeled['items']} == ids
    for entry in catalog['types']:
        assert all(types.type_id(signature) == entry['id'] for signature in entry['signatures'])
        assert entry['representable'] == (not types.unrepresentable(entry['axes']))
    for item in labeled['items']:
        assert 'ALT:?' not in item['signature'] and 'ALT:misto' not in item['signature']
        assert item['type'] == types.type_id(item['signature'])
        if item['provenance']['origin'] == 'manual':
            assert len(item['provenance']['justification']) >= 20
        else:
            assert item['eligible'] and item['signature'] == item['adapter_signature']


def rows_and_decisions():
    row = {
        'question_id': 'q1',
        'exam': 'prova',
        'number': 1,
        'occurrence_ids': [{'exam': 'prova', 'number': 1, 'question_id': 'q1'}],
        'signature': 'F ALT:texto',
        'eligible': False,
        'issues': [{'code': 'whole_region_image', 'severity': 'error'}],
        'content_form': 'imagem-unica',
        'support_group': None,
        'figures': [],
        'source_sha256': 'a' * 64,
        'content_sha256': 'b' * 64,
        'adapter': 'pdf-geometry-v4',
    }
    eligible = {**row, 'question_id': 'q2', 'number': 2, 'signature': 'P ALT:texto', 'eligible': True, 'issues': []}
    decisions = {
        'version': reference.DECISIONS_VERSION,
        'decisions': [
            {
                'question_id': 'q1',
                'source_sha256': 'a' * 64,
                'content_sha256': 'b' * 64,
                'observed_signature': 'F ALT:texto',
                'signature': 'P F+Cr P ALT:texto',
                'decision': 'correcao-manual',
                'justification': 'Questão impressa como imagem única; leitura do caderno.',
            }
        ],
    }
    return [row, eligible], decisions


def test_manual_decisions_are_preserved_and_eligible_questions_are_automatic():
    rows, decisions = rows_and_decisions()
    first, second = reference.label(rows, decisions)
    assert first['provenance']['origin'] == 'manual' and first['type'] == 'texto-figura+credito-texto.alt-texto'
    assert first['adapter_signature'] == 'F ALT:texto'
    assert second['provenance'] == {'origin': 'automatic', 'independent_review': False}
    changed = copy.deepcopy(rows)
    changed[0]['signature'] = 'F P ALT:texto'
    again = reference.label(changed, decisions)[0]
    assert again['type'] == first['type'] and again['provenance']['adapter_signature_changed']


@pytest.mark.parametrize('field', ['content_sha256', 'source_sha256'])
def test_content_or_source_change_invalidates_the_manual_label(field):
    rows, decisions = rows_and_decisions()
    rows[0][field] = 'c' * 64
    with pytest.raises(reference.LabelError, match='mudou'):
        reference.label(rows, decisions)


def test_ineligible_questions_need_a_justified_decision():
    rows, decisions = rows_and_decisions()
    with pytest.raises(reference.LabelError, match='sem decisão'):
        reference.label(rows, {**decisions, 'decisions': []})
    decisions['decisions'][0]['justification'] = 'curta'
    with pytest.raises(reference.LabelError, match='justificativa'):
        reference.label(rows, decisions)
    rows, decisions = rows_and_decisions()
    decisions['decisions'][0]['decision'] = 'tipo-legitimo'
    with pytest.raises(reference.LabelError, match='correção'):
        reference.label(rows, decisions)
    rows, decisions = rows_and_decisions()
    with pytest.raises(reference.LabelError, match='fora das provas'):
        reference.label(rows[1:], decisions)


def block(kind, box, text='', entries=None, page=1):
    return {'type': kind, 'page': page, 'bbox': box, 'text': text, 'entries': entries or [{'text': text}]}


def test_line_numbers_need_an_increasing_aligned_column_beside_text():
    column = [block('numbers', [40, 100 + 12 * i, 46, 110 + 12 * i], str(i + 1)) for i in range(4)]
    text = block('paragraph', [50, 98, 300, 150], 'texto numerado')
    fraction = block('numbers', [200, 300, 205, 310], '2')
    line_numbers([*column, text, fraction])
    assert [b['type'] for b in column] == ['numbers'] * 4
    assert fraction['type'] == 'paragraph'
    shuffled = [block('numbers', [40, 100 + 12 * i, 46, 110 + 12 * i], str(v)) for i, v in enumerate([3, 1, 2])]
    line_numbers([*shuffled, text])
    assert {b['type'] for b in shuffled} == {'paragraph'}


def test_side_by_side_needs_a_gutter_and_content_on_both_sides():
    left = block('paragraph', [30, 100, 200, 112], 'telas medindo 3 1')
    split_line = block('paragraph', [195, 104, 280, 116], 'polegadas, com 2')
    column = block('paragraph', [230, 100, 280, 112], '−0,69 V')
    digit = block('paragraph', [230, 100, 236, 112], '2')
    assert not printed_beside(left, split_line)
    assert printed_beside(left, column)
    assert not printed_beside(left, digit)


def content(blocks, alternatives=None):
    return {
        'number': 1,
        'page': 1,
        'statement': 'Enunciado fictício.',
        'blocks': blocks,
        'alternatives': alternatives or [{'letter': x, 'text': f'Opção {x}', 'image': None} for x in 'ABCDE'],
    }


def test_rule_reads_order_roles_and_line_numbers_from_the_json():
    figure = {'type': 'image', 'asset': {'path': '/assets/x/f.png', 'alt': 'Figura fictícia.'}}
    question = content(
        [
            {'type': 'paragraph', 'text': 'Texto de apoio.'},
            {'type': 'paragraph', 'text': 'Disponível em: https://exemplo.org.'},
            figure,
            {'type': 'paragraph', 'text': 'Pergunta?'},
        ]
    )
    assert types.rule(question) == {'corpo': 'texto-figura+credito-texto', 'alternativas': 'texto', 'marcas': 'nenhuma'}
    numbered = content(
        [p for i in range(1, 5) for p in ({'type': 'paragraph', 'text': str(i)}, {'type': 'paragraph', 'text': 'L.'})]
    )
    assert types.rule(numbered)['marcas'] == 'linhas-numeradas'
    graphic = content([], [{'letter': x, 'text': '', 'image': figure['asset']} for x in 'ABCDE'])
    assert types.rule(graphic)['alternativas'] == 'figura'


def test_features_ignore_number_page_descriptions_and_paths():
    figure = {'type': 'image', 'asset': {'path': '/assets/x/f.png', 'alt': 'Figura da questão 1, página 1.'}}
    question = content([{'type': 'paragraph', 'text': 'Texto.'}, figure])
    attributes = {'/assets/x/f.png': {'width': 300, 'height': 200, 'ink': 0.1}}
    other = copy.deepcopy(question)
    other.update(number=170, page=30)
    other['blocks'][1]['asset'] = {'path': '/assets/y/g.png', 'alt': 'Outra descrição, questão 170.'}
    assert types.features(question, attributes) == types.features(
        other, {'/assets/y/g.png': attributes['/assets/x/f.png']}
    )
    assert set(types.features(question, attributes)) == set(feature_sets()['completo'])


def png(path, rows, color=0):
    channels = {0: 1, 2: 3}[color]
    raw = b''.join(b'\x00' + bytes(v for pixel in row for v in ([pixel] * channels)) for row in rows)
    chunk = lambda kind, data: (
        struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    )
    header = struct.pack('>IIBBBBB', len(rows[0]), len(rows), 8, color, 0, 0, 0)
    path.write_bytes(
        b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    )


def test_standard_library_png_reader_matches_pymupdf(tmp_path):
    rows = [[0, 255, 255, 30], [255, 255, 10, 255]]
    png(tmp_path / 'g.png', rows)
    png(tmp_path / 'c.png', rows, color=2)
    for name in ('g.png', 'c.png'):
        assert types.figure_attributes(tmp_path / name) == {'width': 4, 'height': 2, 'ink': 0.375}
    real = next((ROOT / 'data/assets/enem-2024-dia2-azul/native').glob('*.png'))
    pixmap = fitz.Pixmap(str(real))
    width, height, luminance = types.read_png(real)
    assert (width, height) == (pixmap.width, pixmap.height)
    if pixmap.n == 1:
        assert bytes(v for row in luminance for v in row) == pixmap.samples


def test_published_predictor_imports_only_the_standard_library():
    tree = ast.parse((ROOT / 'ingestion/layout/types.py').read_text())
    imported = {
        alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    } | {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 0}
    assert imported <= sys.stdlib_module_names
    assert not any(isinstance(node, ast.ImportFrom) and node.level for node in ast.walk(tree))


def test_partitions_keep_groups_and_shared_support_text_together():
    rows = []
    for i in range(30):
        kind = ['texto.alt-texto', 'texto-figura-texto.alt-texto', 'texto-tabela-texto.alt-texto'][i % 3]
        rows.append(
            {
                'question_id': f'q{i}',
                'exam': 'prova',
                'number': i,
                'type': kind,
                'family': kind.split('.')[0],
                'canonical_id': f'c{i // 2}',
                'duplicate_sha256': f'd{i}',
                'support_group': 'apoio' if i < 4 else None,
            }
        )
    rows.append({**rows[0], 'question_id': 'rara', 'number': 99, 'type': 'rara', 'canonical_id': 'rara'})
    config = {'test_fraction': 0.2, 'development_fraction': 0.2, 'min_type_groups': 3}
    result, rare = split_reference(rows, config, 'semente')
    assert rare == ['rara'] and next(r for r in result if r['question_id'] == 'rara')['split'] == 'train'
    by_group = {}
    for row in result:
        by_group.setdefault(row['split_group'], set()).add(row['split'])
    assert all(len(splits) == 1 for splits in by_group.values())
    assert len({row['split'] for row in result if row['question_id'] in {'q0', 'q1', 'q2', 'q3'}}) == 1
    assert {row['split'] for row in result} == {'train', 'development', 'test'}
    assert split_reference(rows, config, 'semente') == (result, rare)


def test_predictor_cli_runs_from_a_clean_copy_without_the_repository(tmp_path):
    model = {
        'version': 'layout-types-model-v1',
        'catalog': ['texto.alt-texto'],
        'axes': {axis: {'kind': 'rule'} for axis in types.AXES},
    }
    folder = tmp_path / 'modelo'
    folder.mkdir()
    (folder / 'predict.py').write_text((ROOT / 'ingestion/layout/types.py').read_text())
    (folder / 'model.json').write_text(json.dumps(model))
    (tmp_path / 'questao.json').write_text(json.dumps(content([{'type': 'paragraph', 'text': 'Texto.'}])))
    output = subprocess.run(
        [sys.executable, '-I', str(folder / 'predict.py'), str(tmp_path / 'questao.json')],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(output.stdout)
    assert result['type'] == 'texto.alt-texto' and result['in_catalog'] and result['representable']
    assert digest(model) == digest(json.loads((folder / 'model.json').read_text()))


def test_rule_model_predicts_questions_with_figures_without_figure_attributes():
    figure = {'type': 'image', 'asset': {'path': '/assets/x/f.png', 'alt': 'Figura fictícia.'}}
    question = content([{'type': 'paragraph', 'text': 'Texto.'}, figure, {'type': 'paragraph', 'text': 'Pergunta?'}])
    rule_model = {'catalog': [], 'axes': {axis: {'kind': 'rule'} for axis in types.AXES}}
    assert types.required_attributes(rule_model) == []
    assert types.predict(rule_model, question, {})['type'] == 'texto-figura-texto.alt-texto'
    names = feature_sets()['dimensoes']
    tree_model = {
        'catalog': [],
        'axes': {
            axis: {'kind': 'tree', 'features': names, 'tree': {'label': 'texto' if axis != 'marcas' else 'nenhuma'}}
            for axis in types.AXES
        },
    }
    assert types.required_attributes(tree_model) == ['width', 'height']
    with pytest.raises(ValueError, match='Figura sem'):
        types.predict(tree_model, question, {})
