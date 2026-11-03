"""Fronteiras dos experimentos: vazamento, métricas, geometria e propostas offline."""
from collections import Counter
import copy
import json
from pathlib import Path
import subprocess
import sys

import pymupdf as fitz
import pytest
from pydantic import ValidationError

from experiments.classification import blind_id, external_evaluation, fit, load_reference, predict, split_reference, visible_text
from experiments.common import ROOT, classification_metrics, digest, human_timings, read_json, source_path, write_json
from experiments.contracts import CorrectionLog, ExternalPredictions, LayoutProposal, LayoutReference, ThemeProposal
from experiments.layout import assemble, evaluate_example, extract_candidates, fit_tree, tree_predict
from experiments.recovery import alternative_regions, embedded_font_candidates, grid_integrity, ocr_page, visual_answer_key
from scripts.run_experiments import validate_config


def corpus():
    return [{'question_id': f'{label}-{i}', 'canonical_id': f'{label}-{i}', 'split_group': f'{label}-{i}',
             'duplicate_sha256': f'{label}-{i}', 'theme': label, 'text': text,
             'content_sha256': digest([label, i]), 'source_sha256': 'b' * 64, 'visual': False}
            for label, text in [('area', 'triangulo area retangulo'), ('volume', 'cilindro cone volume')]
            for i in range(6)]


def test_splits_group_aliases_transitively_before_stratification():
    rows = corpus()
    clone = {**rows[0], 'question_id': 'outra-cor', 'canonical_id': 'alias', 'split_group': 'alias'}
    indirect = {**clone, 'question_id': 'outro-texto', 'duplicate_sha256': 'changed'}
    result = split_reference([*rows, clone, indirect], {'test_fraction': .2, 'development_fraction': .2}, 'seed')
    partitions = {r['split'] for r in result if r['question_id'] in {rows[0]['question_id'], 'outra-cor', 'outro-texto'}}
    assert len(partitions) == 1
    assert result == split_reference(list(reversed([*rows, clone, indirect])), {'test_fraction': .2, 'development_fraction': .2}, 'seed')
    groups = {}
    for row in result:
        assert groups.setdefault(row['split_group'], row['split']) == row['split']


def test_conflicting_duplicate_labels_require_adjudication():
    rows = corpus()
    rows[-1]['duplicate_sha256'] = rows[0]['duplicate_sha256']
    with pytest.raises(ValueError, match='conflitantes'):
        split_reference(rows, {'test_fraction': .2, 'development_fraction': .2}, 'seed')


def test_text_representation_does_not_include_answer_labels_or_editorial_description(exam_payload):
    c = exam_payload['questions'][0]['content']
    c.update(blocks=[{'type': 'paragraph', 'text': 'Corpo permitido.'},
                     {'type': 'paragraph', 'role': 'credit', 'text': 'autor-privado'},
                     {'type': 'image', 'asset': {'path': '/assets/private.png', 'alt': 'geometria revelada'}, 'caption': 'gabarito-interno'}])
    text = visible_text(c)
    altered = {**c, 'statement': 'SEGREDO', 'correct_answer': 'D', 'page': 900,
               'labels': {'themes': ['vazamento'], 'skills': ['MT.H1']}}
    assert visible_text(altered) == text
    assert all(secret not in text for secret in ['SEGREDO', 'vazamento', 'autor-privado', 'geometria revelada', 'gabarito-interno'])


@pytest.mark.parametrize('kind', ['majority', 'keywords', 'multinomial_nb', 'tfidf_word_centroid', 'tfidf_character_centroid'])
def test_classical_models_fit_only_training_and_survive_json_roundtrip(kind):
    rows = corpus()
    config = {'alpha': 1, 'keywords': {'area': ['triangulo'], 'volume': ['cilindro']}}
    model = fit(kind, rows, config)
    restored = json.loads(json.dumps(model))
    assert predict(model, 'cilindro volume') == predict(restored, 'cilindro volume')
    if kind != 'majority':
        assert predict(model, 'cilindro volume')['theme'] == 'volume'
        assert predict(model, 'triangulo area')['theme'] == 'area'
    assert predict(model, 'palavraexternanuncaobservada')['margin_is_probability'] is False
    assert 'palavraexternanuncaobservada' not in model.get('idf', model.get('vocabulary', []))


def test_metrics_penalize_missing_predictions_and_class_errors():
    metrics = classification_metrics(['A', 'A', 'B'], ['A', 'B', 'B'], ['A', 'B'])
    assert metrics['accuracy'] == pytest.approx(2 / 3)
    assert metrics['per_class']['A']['precision'] == 1
    assert metrics['per_class']['A']['recall'] == .5
    assert metrics['macro_f1'] == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        classification_metrics(['A'], [], ['A'])
    with pytest.raises(ValueError):
        classification_metrics(['A'], ['unknown'], ['A'])


def test_external_llm_submission_checks_content_completeness_and_training_leakage(tmp_path):
    rows = corpus()[:2]
    for row, split in zip(rows, ['development', 'test']):
        row['split'] = split
    payload = {'model': 'modelo-externo-versionado', 'prompt_sha256': 'a' * 64, 'training_groups': ['train-group'],
               'data_policy': 'Somente demonstrações de treino; nenhum rótulo de avaliação.',
               'records': [{'question_id': blind_id(row), 'content_sha256': row['content_sha256'], 'theme': row['theme'],
                            'evidence': 'Trecho de evidência.', 'latency_ms': 10, 'cost_usd': .01,
                            'repeat_themes': [row['theme'], row['theme']]} for row in rows]}
    path = tmp_path / 'llm.json'
    write_json(path, payload)
    result = external_evaluation(path, rows, ['area', 'volume'], {'train-group'})
    assert result['test']['accuracy'] == 1 and result['test']['external_cost_usd'] == .01
    payload['training_groups'].append('test-group')
    write_json(path, payload)
    with pytest.raises(ValueError, match='treinamento'):
        external_evaluation(path, rows, ['area', 'volume'], {'train-group'})
    payload['training_groups'] = []
    payload['records'][0]['content_sha256'] = 'c' * 64
    write_json(path, payload)
    with pytest.raises(ValueError, match='versão'):
        external_evaluation(path, rows, ['area', 'volume'], set())


def test_published_reference_has_89_unique_items_and_no_partition_overlap():
    config = read_json(ROOT / 'experiments/config.json')
    validate_config(config)
    rows, _ = load_reference(config['classification'])
    split = split_reference(rows, config['classification'], config['seed'])
    assert len(split) == 89
    assert Counter(r['split'] for r in split) == {'train': 53, 'development': 18, 'test': 18}
    assert all({r['theme'] for r in split if r['split'] == part} == set(config['classification']['keywords']) for part in ['train', 'development', 'test'])


def test_layout_reference_keeps_whole_pages_and_identities_in_one_partition():
    raw = read_json(ROOT / 'data/datasets/layout-reference-v1.json')
    reference = LayoutReference.model_validate(raw)
    assert len(reference.examples) == 13
    assert sum(len(row.blocks) for row in reference.examples) == 145
    for example in reference.examples:
        assert {b.alternative for b in example.blocks if b.type == 'alternative'} == set('ABCDE')
        assert not example.independent_review
    changed = copy.deepcopy(raw)
    changed['examples'].append({**changed['examples'][0], 'id': 'outra-cor', 'split': 'test'})
    with pytest.raises(ValidationError, match='partição'):
        LayoutReference.model_validate(changed)
    changed = copy.deepcopy(raw)
    changed['examples'][1]['split'] = 'test'
    changed['examples'][1]['split_group'] = changed['examples'][0]['split_group']
    with pytest.raises(ValidationError, match='partição'):
        LayoutReference.model_validate(changed)


def test_cart_learns_numerical_threshold_without_metadata():
    tree = fit_tree([([0.0], 'paragraph'), ([0.1], 'paragraph'), ([0.9], 'credit'), ([1.0], 'credit')], min_leaf=1)
    assert tree_predict(tree, [.05]) == 'paragraph'
    assert tree_predict(tree, [.95]) == 'credit'


def simple_blocks():
    return [{'id': 'figure', 'type': 'image', 'page': 1, 'bbox': [40, 100, 200, 200], 'order': 0, 'text': '', 'group': 'stem', 'alternative': None},
            {'id': 'caption', 'type': 'caption', 'page': 1, 'bbox': [40, 205, 200, 220], 'order': 1, 'text': 'Figura 1.', 'group': 'stem', 'alternative': None}]


def test_layout_metrics_measure_unmatched_blocks_links_and_order_separately():
    blocks = simple_blocks()
    example = {'id': 'example', 'pattern': 'figure', 'difficult': True, 'blocks': blocks,
               'links': [{'source': 'caption', 'target': 'figure', 'relation': 'caption_of'}]}
    perfect = evaluate_example(example, {'blocks': blocks, 'links': example['links']}, .5)
    assert perfect['localization_f1'] == 1 and perfect['integrity']
    wrong = copy.deepcopy(blocks)
    wrong[0]['order'], wrong[1]['order'] = 1, 0
    reversed_result = evaluate_example(example, {'blocks': wrong, 'links': []}, .5)
    assert reversed_result['reading_order']['agreement'] == 0
    assert reversed_result['errors']['missing_links'] == 1
    missing = evaluate_example(example, {'blocks': blocks[:1], 'links': []}, .5)
    assert missing['localization_recall'] == .5 and not missing['integrity']


def synthetic_pdf(tmp_path, duplicate=False, marked=True):
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((40, 100), 'QUESTAO 1', fontsize=12)
    page.insert_text((40, 130), 'Considere o exemplo e marque uma alternativa.', fontsize=10)
    for i, letter in enumerate('ABCDE' + ('F' if duplicate else '')):
        # Pequenas diferenças de x não podem reordenar A–E.
        x, y = 44 - i * .3, 180 + i * 35
        page.draw_circle((x, y), 4, color=(.1, .1, .1), fill=(.1, .1, .1))
        page.insert_text((60, y + 3), letter, fontname='cour', fontsize=10)
        page.insert_text((75, y + 3), f'Opção de teste {letter}', fontsize=10)
        if i == 1 and marked:
            page.draw_circle((x, y), 8, color=(0, .65, .65), width=1.5)
    path = tmp_path / 'synthetic.pdf'
    doc.save(path)
    doc.close()
    return path


def test_interrupted_table_detector_is_not_reported_as_empty_success(tmp_path,monkeypatch):
    pdf=synthetic_pdf(tmp_path)
    monkeypatch.setattr(fitz.Page,'find_tables',lambda *_args,**_kwargs:None)
    with pytest.raises(ValueError,match='interrompido'):
        extract_candidates(pdf,[{'page':1,'bbox':[20,60,550,500]}],True)


def test_vector_answer_marks_use_vertical_order_and_cyan_strokes(tmp_path):
    pdf = synthetic_pdf(tmp_path)
    with fitz.open(pdf) as doc:
        result = visual_answer_key(doc)
    assert result[0]['answer'] == 'B' and result[0]['status'] == 'proposed'
    assert result[0]['needs_review']


@pytest.mark.parametrize('duplicate,marked', [(True, True), (False, False)])
def test_visual_key_abstains_instead_of_inventing_an_answer_or_annulment(tmp_path, duplicate, marked):
    with fitz.open(synthetic_pdf(tmp_path, duplicate, marked)) as doc:
        result = visual_answer_key(doc)
    assert result[0]['answer'] is None and result[0]['status'] == 'unresolved'


def test_geometry_outputs_draft_blocks_and_keeps_five_alternative_regions(tmp_path):
    pdf = synthetic_pdf(tmp_path)
    regions = [{'page': 1, 'bbox': [30, 80, 280, 400]}]
    with fitz.open(pdf) as doc:
        options = alternative_regions(doc, regions)
    assert options['status'] == 'proposed'
    assert [choice['letter'] for choice in options['alternatives']] == list('ABCDE')
    candidates, _ = extract_candidates(pdf, regions, True)
    prediction = assemble(candidates, 'geometry')
    assert prediction['needs_review'] and prediction['review_status'] == 'proposed'
    assert not any('correct_answer' in block for block in prediction['blocks'])


def test_table_span_integrity_detects_gaps_and_overlapping_cells():
    table = {'rows': 2, 'columns': 2, 'cells': [{'row': 0, 'column': 0, 'rowspan': 1, 'colspan': 2},
             {'row': 1, 'column': 0, 'rowspan': 1, 'colspan': 1}, {'row': 1, 'column': 1, 'rowspan': 1, 'colspan': 1}]}
    assert grid_integrity(table)
    table['cells'].append(copy.deepcopy(table['cells'][-1]))
    assert not grid_integrity(table)
    table['cells'] = table['cells'][:2]
    assert not grid_integrity(table)


def test_unmapped_font_does_not_generate_a_guessed_transcription():
    class Page:
        def get_fonts(self): return []
        def get_texttrace(self): return [{'font': 'unknown', 'bbox': [0, 0, 10, 10], 'chars': [(65533, 7)]}]
    result = embedded_font_candidates([Page()], 1)
    assert result[0]['status'] == 'unresolved' and result[0]['candidates'] == []


def test_ocr_without_installed_engine_is_explicitly_unavailable(monkeypatch):
    monkeypatch.setattr('experiments.recovery.ocr_capabilities', lambda: {'engine': None, 'languages': []})
    assert ocr_page('unused.pdf', 1, 'por', 5)['status'] == 'unavailable'


def test_human_time_is_never_inferred_and_requires_exact_content(tmp_path):
    assert human_timings(None, {})['median_seconds'] is None
    payload = {'records': [{'target_id': 'layout', 'content_sha256': 'a' * 64, 'method': 'geometry',
                            'reviewer': 'Revisor independente', 'seconds': 25, 'decision': 'correct',
                            'reason': 'A legenda pertence à figura seguinte.'}]}
    path = tmp_path / 'times.json'
    write_json(path, payload)
    assert human_timings(path, {'layout': 'a' * 64})['total_seconds'] == 25
    with pytest.raises(ValueError):
        human_timings(path, {'layout': 'b' * 64})
    payload['records'][0]['seconds'] = -1
    with pytest.raises(ValidationError):
        CorrectionLog.model_validate(payload)


def test_experiment_cli_rejects_writes_into_sources_and_invalid_configuration(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_experiments.py'), '--output', str(ROOT / 'data/datasets')], capture_output=True, text=True)
    assert result.returncode == 2 and 'tmp/' in result.stderr
    config = read_json(ROOT / 'experiments/config.json')
    config['classification']['test_fraction'] = .9
    with pytest.raises(ValueError):
        validate_config(config)
    with pytest.raises(ValueError):
        source_path('../fora.pdf', 'a' * 64)


def test_classification_cli_exports_reproducible_proposals_and_all_model_metrics(tmp_path):
    output = tmp_path / 'classification'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_experiments.py'), '--only', 'classification', '--output', str(output)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    report = read_json(output / 'classification-report.json')
    assert report['selection']['test_used_for_selection'] is False
    assert report['llm']['status'] == 'not_run'
    assert len(report['models']) == 5
    proposals = read_json(output / 'classification-proposals.json')
    assert len(proposals) == 89
    assert all(p['needs_review'] and p['review_status'] == 'proposed' and not p['labels']['skills'] for p in proposals)
    assert all(model['test']['latency']['p95_ms'] >= 0 for model in report['models'].values())
    assert read_json(output / 'run.json')['code_sha256']
    assert read_json(output / 'run.json')['status'] == 'complete'


def test_proposal_contracts_and_schema_never_assert_approval_or_skills():
    for model, filename in [(ThemeProposal, 'classification-proposal'), (LayoutProposal, 'layout-proposal'),
                            (ExternalPredictions, 'external-predictions')]:
        assert read_json(ROOT / f'docs/experimentos/{filename}.schema.json') == model.model_json_schema()
    from experiments.classification import proposal
    row = corpus()[0]
    row['split'] = 'test'
    # A taxonomia publicada é distinta do pequeno corpus sintético de treino.
    model = {'kind': 'keywords', 'labels': ['Geometria plana'], 'majority': 'Geometria plana',
             'keywords': {'Geometria plana': ['triangulo']}}
    result = proposal(row, model)
    result['review_status'] = 'approved'
    with pytest.raises(ValidationError):
        ThemeProposal.model_validate(result)
    result['review_status'] = 'proposed'
    result['labels']['skills'] = ['MT.H12']
    with pytest.raises(ValidationError):
        ThemeProposal.model_validate(result)


def test_encoding_offset_hypotheses_remain_proposals_with_no_source_specific_rules():
    text = 'O texto de uma pergunta e o seu contexto'
    class Page:
        def get_fonts(self): return []
        def get_texttrace(self):
            return [{'font': 'unknown', 'bbox': [0, 0, 400, 12],
                     'chars': [(65533, ord(c) - 29) for c in text]}]
    result = embedded_font_candidates([Page()], 1)[0]
    assert text in result['candidates'] and result['needs_review']
    assert any(row['offset'] == 29 for row in result['shift_hypotheses'])
