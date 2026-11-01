import copy
import json
from pathlib import Path

from sqlalchemy import func, select

from backend.app.installers.curated import classified
from backend.app.services.identity import signatures
from backend.app.models import CanonicalQuestion, QuestionVersion
from scripts.link_booklets import MIN_CONTAINMENT, MIN_MARGIN, pair, shingles

ROOT = Path(__file__).resolve().parents[2]


def test_booklet_links_cover_each_curated_item_once_per_color():
    links = json.loads((ROOT / 'data/catalog/occurrences-v1.json').read_text())
    manifest = json.loads((ROOT / 'data/catalog/manifest.json').read_text())
    assert links['catalog'] == manifest['version'] and links['pending'] == []
    questions = {q['question_id']: q for q in links['questions']}
    for entry, exam in zip(manifest['exams'], links['exams']):
        payload = classified(json.loads((ROOT / entry['path']).read_text()))
        assert exam['exam_id'] == payload.id and exam['source_sha256'] == payload.source.sha256
        booklets = {b['booklet']: b for b in exam['booklets']}
        assert len(booklets) == 4 and all(b['linked'] == len(payload.questions) and b['pending'] == 0 for b in booklets.values())
        assert booklets[exam['booklets'][0]['booklet']]['source_sha256'] == payload.source.sha256
        numbers = {q.content.number for q in payload.questions}
        per_booklet = {name: [] for name in booklets}
        for question in payload.questions:
            content = question.content.model_dump()
            row = questions[question.question_id]
            digest, _ = signatures(content)
            assert row['canonical_id'] == 'enem-' + digest[:32]
            assert sorted(o['booklet'] for o in row['occurrences']) == sorted(booklets)
            for occurrence in row['occurrences']:
                per_booklet[occurrence['booklet']].append(occurrence['number'])
                assert occurrence['source_sha256'] == booklets[occurrence['booklet']]['source_sha256']
                assert occurrence['answer'] == (None if content['annulled'] else content['correct_answer'])
                assert occurrence['text_containment'] >= MIN_CONTAINMENT and occurrence['margin'] >= MIN_MARGIN
                assert occurrence['figures'] in ('sem imagens raster', 'equivalentes') or occurrence['figures'].startswith('conferidas visualmente: ')
                if occurrence['source_sha256'] == payload.source.sha256:
                    assert occurrence['number'] == content['number']
        # Each color is a permutation of the same numbers: no item is linked twice.
        assert all(sorted(found) == sorted(numbers) for found in per_booklet.values())


def test_pairing_requires_containment_margin_and_a_single_owner():
    text = 'Um recipiente contém água a vinte graus e recebe calor constante durante dez minutos de experimento'
    other = 'Uma pesquisa mediu o tempo de leitura de estudantes em três escolas públicas diferentes do país'
    assert pair({91: shingles(text)}, {120: shingles('QUESTÃO 120 ' + text), 121: shingles(other)})[91][::3] == (120, None)
    weak = pair({91: shingles(text)}, {120: shingles(other)})[91]
    assert weak[3].startswith('Texto corresponde')
    ambiguous = pair({91: shingles(text)}, {120: shingles(text), 121: shingles(text)})[91]
    assert ambiguous[3].startswith('Folga')
    contested = pair({91: shingles(text), 92: shingles(text + ' adicional')}, {120: shingles(text + ' adicional'), 121: shingles(other)})
    assert all(contested[n][3].startswith('Questão 120 disputada') for n in (91, 92))


def test_import_of_a_linked_color_reuses_identity_and_checks_its_answer_key(admin, exam_payload, database, monkeypatch):
    assert admin.post('/admin/imports', json=exam_payload).status_code == 201
    with database() as db:
        original = {n: db.get(QuestionVersion, f'teste-q{n}:1').canonical_id for n in (1, 2, 3)}
    color = copy.deepcopy(exam_payload)
    color.update(id='outra-cor-vinculada', booklet='Amarelo')
    color['source'] = dict(color['source'], sha256='c' * 64, answer_key_sha256='d' * 64)
    order = {1: 115, 2: 101, 3: 130}
    for q in color['questions']:
        n = q['content']['number']
        q['question_id'] = f'amarelo-q{order[n]}'
        q['content']['number'] = order[n]
        # The other PDF yields slightly different text, so the signature alone would not match.
        q['content']['statement'] += ' (caderno amarelo)'
    links = {('c' * 64, order[n]): (original[n], answer) for n, answer in ((1, 'B'), (2, 'C'), (3, None))}
    monkeypatch.setattr('backend.app.services.identity.booklet_links', lambda: links)

    wrong = copy.deepcopy(color)
    wrong['id'] = 'gabarito-divergente'
    for q in wrong['questions']:
        q['question_id'] = 'divergente-' + q['question_id']
    wrong['questions'][0]['content']['correct_answer'] = 'A'
    response = admin.post('/admin/imports', json=wrong)
    assert response.status_code == 409 and 'vínculo entre cores' in response.json()['detail']

    assert admin.post('/admin/imports', json=color).status_code == 201
    with database() as db:
        assert db.scalar(select(func.count()).select_from(CanonicalQuestion)) == 3
        for n, number in order.items():
            assert db.get(QuestionVersion, f'amarelo-q{number}:1').canonical_id == original[n]
