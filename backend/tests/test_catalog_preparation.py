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
