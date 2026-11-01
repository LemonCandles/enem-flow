import copy

import pytest

from backend.app.models import Exam, QuestionVersion


def test_edit_cannot_copy_another_canonical_question(published, admin, student, database):
    run=student.post('/exam-runs',json=dict(exam_id='prova-teste',idempotency_key='antes-da-duplicata')).json()
    c=admin.get('/admin/exams/prova-teste').json()['items'][0]['content']
    c['number']=2
    response=admin.put('/admin/questions/teste-q2:1',json=dict(content=c,reason='Cópia acidental de outra questão'))
    assert response.status_code==409
    with database() as db:
        assert db.get(QuestionVersion,'teste-q2:2') is None
        assert db.get(Exam,'prova-teste').status=='published'
    assert student.get('/exam-runs/'+run['id']).json()==run


def test_edit_also_rejects_copying_a_revised_signature(published, admin):
    c=admin.get('/admin/exams/prova-teste').json()['items'][0]['content']
    c['statement']='Texto revisado que ainda não é a assinatura original.'
    c['blocks']=[dict(type='paragraph',text=c['statement'],role='body')]
    assert admin.put('/admin/questions/teste-q1:1',json=dict(content=c,reason='Correção legítima do enunciado')).status_code==200
    c['number']=2
    response=admin.put('/admin/questions/teste-q2:1',json=dict(content=c,reason='Cópia de uma versão já corrigida'))
    assert response.status_code==409


@pytest.mark.parametrize('duplicate',['content','canonical'])
def test_publication_rejects_legacy_duplicates(published, admin, database, duplicate):
    with database.begin() as db:
        first=db.get(QuestionVersion,'teste-q1:1');second=db.get(QuestionVersion,'teste-q2:1')
        if duplicate=='content':
            c=copy.deepcopy(first.content);c['number']=2;second.content=c
        else: second.canonical_id=first.canonical_id
        db.get(Exam,'prova-teste').status='in_review'
    response=admin.post('/admin/reviews/prova-teste',json=dict(action='publish',reason='Verificar versões históricas duplicadas'))
    assert response.status_code==409


def test_revision_can_initialize_a_missing_legacy_identity(published, admin, database):
    with database.begin() as db:db.get(QuestionVersion,'teste-q1:1').canonical_id=None
    c=admin.get('/admin/exams/prova-teste').json()['items'][0]['content']
    response=admin.put('/admin/questions/teste-q1:1',json=dict(content=c,reason='Revisão legítima de uma identidade antiga'))
    assert response.status_code==200
    with database() as db:assert db.get(QuestionVersion,'teste-q1:2').canonical_id
