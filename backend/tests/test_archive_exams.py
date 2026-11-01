import copy
import json

import pytest
from fastapi import HTTPException

from backend.app.archive_exams import publish_generated
from backend.app.models import Exam, QuestionVersion
from backend.app.bundled_content import bundled_reviewer
from backend.app.content import exam_summary, public_question, publish_exam
from backend.app.preparation import blocking_issues, prepare_exam
from scripts.build_archive_exams import areas, booklet_label, exam_id
from scripts.exam_pdf import answer_key_rows

KEY = 'QUESTÃO\nGABARITO\nINGLÊS\nESPANHOL\n1\nC\nC\n2\nA\nD\n3\nAnulado\nB\n6\nE\nCIÊNCIAS HUMANAS\nE SUAS TECNOLOGIAS\n7\nB\n'


def test_answer_key_reads_the_declared_language_column():
    assert answer_key_rows(KEY, 'Inglês') == {1: 'C', 2: 'A', 3: None, 6: 'E', 7: 'B'}
    assert answer_key_rows(KEY, 'espanhol') == {1: 'C', 2: 'D', 3: 'B', 6: 'E', 7: 'B'}
    with pytest.raises(ValueError, match='declare "language"'):
        answer_key_rows(KEY)
    # Non-breaking spaces between number and letters do not hide the second column.
    assert answer_key_rows('INGLÊS\xa0\nESPANHOL\xa0\n91\xa0\nA\xa0\nD\xa0\n', 'espanhol') == {91: 'D'}


def test_generated_exam_metadata_follows_the_period_of_the_exam():
    assert [a['area'] for a in areas(2009, 1)] == ['Ciências da Natureza', 'Ciências Humanas']
    assert [a['area'] for a in areas(2016, 1)] == ['Ciências Humanas', 'Ciências da Natureza']
    assert [(a['first'], a['area']) for a in areas(2016, 2)] == [(91, 'Linguagens'), (136, 'Matemática')]
    assert [a['area'] for a in areas(2017, 1)] == ['Linguagens', 'Ciências Humanas']
    assert areas(2022, 2)[1] == dict(first=136, last=180, area='Matemática', discipline='Matemática')
    assert booklet_label('caderno-1-azul-ingles') == 'Caderno 1 · Azul · Inglês'
    assert exam_id(2022, 'digital', 1, 'caderno-1-azul-ingles', 'ingles') == 'enem-2022-digital-dia1-caderno-1-azul-ingles'
    assert exam_id(2022, 'regular', 1, 'caderno-1-azul', 'espanhol') == 'enem-2022-regular-dia1-caderno-1-azul-espanhol'


def write(directory, payload):
    prepared, _ = prepare_exam(payload)
    (directory / f'{payload["id"]}.json').write_text(json.dumps(prepared.model_dump(), ensure_ascii=False))
    return prepared


def test_generated_exams_are_published_without_curation_and_only_once(tmp_path, exam_payload, database):
    pending = copy.deepcopy(exam_payload)
    pending['id'] = 'acervo-com-pendencia'
    for q in pending['questions']:
        q['question_id'] = 'acervo-' + q['question_id']
    pending['questions'][0]['content']['statement'] = 'Valor de $x^2 sem fechamento.'
    prepared = write(tmp_path, pending)
    assert blocking_issues(prepared.questions[0].content.model_dump())
    duplicated = copy.deepcopy(exam_payload)
    duplicated.update(id='acervo-duplicado', expected_items=2)
    duplicated['questions'] = [copy.deepcopy(duplicated['questions'][0]) for _ in range(2)]
    for i, q in enumerate(duplicated['questions']):
        q['question_id'] = f'duplicado-q{i}'
        q['content']['number'] = i + 1
    write(tmp_path, duplicated)
    (tmp_path / 'resumo.json').write_text('[]')
    (tmp_path / 'arquivo-invalido.json').write_text('{')

    with database.begin() as db:
        result = publish_generated(db, tmp_path)
    assert result['published'] == 1 and result['existing'] == 0
    assert [f['id'] for f in result['failed']] == ['acervo-duplicado','arquivo-invalido']
    with database() as db:
        exam = db.get(Exam, 'acervo-com-pendencia')
        assert exam.status == 'published'
        assert all(db.get(QuestionVersion, key).status == 'approved' for key in exam.items)
        assert exam_summary(db,exam)['content_quality']==dict(origin='automatic',review_status='pending',blocking_issues=1)
        question = db.get(QuestionVersion, exam.items[0])
        visible = public_question(dict(id=question.id, question_id=question.question_id, version=1, content=question.content), False)
        assert visible['preparation_errors'] == 1
        assert 'correct_answer' not in visible
        reviewer = bundled_reviewer(db)
        with pytest.raises(HTTPException, match='pendências bloqueantes'):
            publish_exam(db, exam, reviewer.id, 'Conferência manual')
        assert db.get(Exam, 'acervo-duplicado') is None
    with database.begin() as db:
        again = publish_generated(db, tmp_path)
    assert again['published'] == 0 and again['existing'] == 1


def test_legacy_automatic_metadata_preserves_versions_and_manual_review(tmp_path, exam_payload, database):
    write(tmp_path, exam_payload)
    with database.begin() as db:
        assert publish_generated(db, tmp_path)['published'] == 1
        exam = db.get(Exam, exam_payload['id'])
        items = list(exam.items)
        content = [copy.deepcopy(db.get(QuestionVersion, key).content) for key in items]
        exam.source = {k: v for k, v in exam.source.items() if k != 'automatic_archive'}
        reviewer = bundled_reviewer(db)
        with pytest.raises(HTTPException, match='origem e o estado de revisão'):
            publish_exam(db, exam, reviewer.id, 'Origem não registrada', allow_pending=True)
    with database.begin() as db:
        assert publish_generated(db, tmp_path)['existing'] == 1
        exam = db.get(Exam, exam_payload['id'])
        assert exam.items == items
        assert [db.get(QuestionVersion, key).content for key in items] == content
        assert exam_summary(db, exam)['content_quality']['review_status'] == 'pending'
        reviewer = bundled_reviewer(db)
        publish_exam(db, exam, reviewer.id, 'Conferência manual concluída')
        assert exam_summary(db, exam)['content_quality'] == dict(origin='automatic', review_status='reviewed', blocking_issues=0)
    with database.begin() as db:
        publish_generated(db, tmp_path)
        assert exam_summary(db, db.get(Exam, exam_payload['id']))['content_quality']['review_status'] == 'reviewed'
