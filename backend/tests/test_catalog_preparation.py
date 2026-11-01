import copy
from pathlib import Path

from backend.app.catalog import classified, install_catalog
from backend.app.content import import_exam
from backend.app.models import QuestionVersion
from backend.app.schemas import ExamImport

ROOT=Path(__file__).resolve().parents[2]


def test_classified_preparation_stays_idempotent_and_upgrades_previous_profile(database):
    from backend.app.preparation import prepare_exam
    base=ExamImport.model_validate_json((ROOT/'data/catalog/enem-2023-matematica-azul.json').read_text())
    previous=classified(base,refresh_preparation_audit=False)
    with database.begin() as db:
        exam=import_exam(db,previous)
        old_contents={key:copy.deepcopy(db.get(QuestionVersion,key).content) for key in exam.items}
    with database.begin() as db:
        assert install_catalog(db,publish=True)['new_versions']==45
        assert all(db.get(QuestionVersion,key).content==content for key,content in old_contents.items())
    desired=classified(base)
    prepared,report=prepare_exam(desired)
    assert prepared.model_dump()==desired.model_dump()
    assert report['errors']==0


def test_catalog_can_publish_a_previous_install_and_stays_idempotent(database):
    from sqlalchemy import func, select
    from backend.app.models import Exam, Review
    with database.begin() as db:
        install_catalog(db,publish=False)
        versions={e.id:list(e.items) for e in db.scalars(select(Exam))}
    with database.begin() as db:
        assert install_catalog(db,publish=True)['new_versions']==0
        assert all(e.status=='published' and e.items==versions[e.id] for e in db.scalars(select(Exam)))
        count=db.scalar(select(func.count()).select_from(Review))
    with database.begin() as db:
        install_catalog(db,publish=True)
        assert db.scalar(select(func.count()).select_from(Review))==count


def test_catalog_publication_respects_manual_decisions(database, admin):
    from sqlalchemy import select
    from backend.app.models import Exam
    with database.begin() as db:install_catalog(db,publish=True)
    exams=admin.get('/admin/exams').json()
    withdrawn=exams[0]['id'];rejected=exams[1]['id']
    assert admin.post('/admin/reviews/'+withdrawn,json=dict(action='withdraw',reason='Retirada manual a preservar no bootstrap')).status_code==200
    key=admin.get('/admin/exams/'+rejected).json()['items'][0]['id']
    assert admin.post('/admin/reviews/'+key,json=dict(action='reject',reason='Rejeição manual a preservar no bootstrap')).status_code==200
    with database.begin() as db:
        install_catalog(db,publish=True)
        assert db.get(Exam,withdrawn).status=='withdrawn'
        assert db.get(Exam,rejected).status=='in_review'
        assert db.get(QuestionVersion,key).status=='in_review'


def test_catalog_does_not_publish_an_unchanged_pending_manual_edit(database, admin):
    from backend.app.models import Exam
    with database.begin() as db:install_catalog(db,publish=True)
    exam=admin.get('/admin/exams').json()[0]
    item=admin.get('/admin/exams/'+exam['id']).json()['items'][0]
    assert admin.put('/admin/questions/'+item['id'],json=dict(content=item['content'],reason='Edição manual pendente de conferência')).status_code==200
    with database.begin() as db:
        install_catalog(db,publish=True)
        current=db.get(Exam,exam['id'])
        assert current.status=='in_review'
        assert db.get(QuestionVersion,current.items[0]).status=='draft'


def test_catalog_upgrade_keeps_a_previous_rejection_pending(database):
    from backend.app.models import Exam
    base=ExamImport.model_validate_json((ROOT/'data/enem-2024-dia2-azul.json').read_text())
    with database.begin() as db:
        exam=import_exam(db,base);exam.status='in_review'
        db.get(QuestionVersion,exam.items[0]).status='in_review'
    for _ in range(2):
        with database.begin() as db:
            install_catalog(db,publish=True)
            exam=db.get(Exam,base.id)
            assert exam.status=='in_review'
            assert db.get(QuestionVersion,exam.items[0]).status=='in_review'
