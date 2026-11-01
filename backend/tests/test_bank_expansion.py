import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import func,select

from backend.app.installers.curated import classified, install_catalog
from backend.app.services.content import import_exam
from backend.app.services.identity import signatures
from backend.app.models import CanonicalQuestion,Exam,ExamRun,QuestionVersion,User
from backend.app.schemas import ExamImport
from backend.app.services.presentation import content_fingerprint
from scripts.archive_enem import metadata,parse_year

ROOT=Path(__file__).resolve().parents[2]


def test_archive_parser_preserves_applications_and_formats():
    catalog=json.loads((ROOT/'data/sources/catalogo/acervo.json').read_text())
    assert {p['year'] for p in catalog['pages']}==set(range(1998,2026))
    for page in catalog['pages']:
        path=ROOT/'data/sources'/page['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==page['sha256']
        parsed=parse_year(path.read_text(),page['year'],page['url'])
        expected=[r for r in catalog['files'] if r['year']==page['year']]
        assert [(r['id'],r['url'],r['path']) for r in parsed]==[(r['id'],r['url'],r['path']) for r in expected]
    paths={}
    for r in catalog['files']:
        assert r['url'].startswith('https://download.inep.gov.br/')
        assert r['path'].startswith(f'enem/{r["year"]}/{r["application"]}/') and '..' not in r['path']
        assert r['path'] not in paths or paths[r['path']]==r['url']
        paths[r['path']]=r['url']
    assert metadata(2025,'Aplicação BELÉM, ANANINDEUA E MARITUBA','1º Dia – Caderno 1 – Azul – Aplicação Regular','Prova')['application']=='belem-ananindeua-marituba'
    assert metadata(2020,'Aplicação digital','1º Dia – Caderno 1 – Azul – Inglês – Aplicação digital','Prova')['language']=='ingles'
    assert metadata(2025,'Reaplicação','2º Dia – Caderno 11 – Laranja (Braile e ledor)','Prova | Leitor de tela (NVDA)')['variant']=='nvda'


def test_canonical_identity_preserves_occurrence_number_order_and_answers(admin,student,exam_payload,database):
    assert admin.post('/admin/imports',json=exam_payload).status_code==201
    other=copy.deepcopy(exam_payload);other['id']='outra-cor'
    for q in other['questions']:
        q['question_id']='outra-'+q['question_id'];c=q['content'];c['number']+=100
        c['alternatives']=[dict(old,letter=new) for new,old in zip('ABCDE',reversed(c['alternatives']))]
        c['correct_answer']={'A':'E','B':'D','C':'C','D':'B','E':'A',None:None}[c['correct_answer']]
    assert admin.post('/admin/imports',json=other).status_code==201
    for payload in [exam_payload,other]:
        for q in payload['questions']:
            assert admin.post(f'/admin/reviews/{q["question_id"]}:1',json=dict(action='approve',reason='Conferência sintética da ocorrência')).status_code==200
        assert admin.post(f'/admin/reviews/{payload["id"]}',json=dict(action='publish',reason='Conferência do caderno sintético')).status_code==200
    with database() as db:
        assert db.scalar(select(func.count()).select_from(CanonicalQuestion))==3
        assert db.get(QuestionVersion,'teste-q1:1').canonical_id==db.get(QuestionVersion,'outra-teste-q1:1').canonical_id
    first=student.post('/exam-runs',json=dict(exam_id=exam_payload['id'],idempotency_key='origem-canonica')).json()
    second=student.post('/exam-runs',json=dict(exam_id=other['id'],idempotency_key='outra-cor-canonica')).json()
    assert first['items'][0]['canonical_id']==second['items'][0]['canonical_id']
    assert first['items'][0]['number']==1 and second['items'][0]['number']==101
    student.put(f'/exam-runs/{second["id"]}/answers/outra-teste-q1:1',json=dict(choice='D'))
    assert student.post(f'/exam-runs/{second["id"]}/finish').json()['result']['correct']==1


def test_canonical_duplicates_and_conflicting_keys_are_not_merged(admin,exam_payload):
    assert admin.post('/admin/imports',json=exam_payload).status_code==201
    conflict=copy.deepcopy(exam_payload);conflict['id']='conflito'
    for q in conflict['questions']:q['question_id']='conflito-'+q['question_id']
    conflict['questions'][0]['content']['correct_answer']='E'
    assert admin.post('/admin/imports',json=conflict).status_code==409
    duplicate=copy.deepcopy(exam_payload);duplicate['id']='duplicada';duplicate['expected_items']=4
    extra=copy.deepcopy(duplicate['questions'][0]);extra['question_id']='duplicada-extra';extra['content']['number']=4
    duplicate['questions'].append(extra)
    assert admin.post('/admin/imports',json=duplicate).status_code==409


def test_catalog_labels_create_versions_keep_snapshots_and_are_idempotent(database,admin):
    original=ExamImport.model_validate_json((ROOT/'data/enem-2024-dia2-azul.json').read_text())
    with database.begin() as db:
        exam=import_exam(db,original);user=db.scalar(select(User))
        snapshot=[dict(id=key,question_id=db.get(QuestionVersion,key).question_id,version=1,content=copy.deepcopy(db.get(QuestionVersion,key).content)) for key in exam.items]
        run=ExamRun(user_id=user.id,exam_id=exam.id,start_key='antes-dos-rotulos',exam_info={},items=snapshot,answers={snapshot[0]['id']:'B'})
        db.add(run);db.flush();run_id=run.id
    with database.begin() as db:
        stats=install_catalog(db,publish=True)
        assert stats['imported_exams']==1 and stats['new_versions']==90 and stats['canonical_questions']==135
    with database.begin() as db:
        assert install_catalog(db,publish=True)['new_versions']==0
        assert db.get(ExamRun,run_id).items==snapshot
        assert db.get(ExamRun,run_id).answers=={snapshot[0]['id']:'B'}
        exam=db.get(Exam,original.id);c=db.get(QuestionVersion,exam.items[0]).content
        assert c['labels']['discipline']=='Física' and c['labels']['themes']==['Mecânica']
        assert not c['labels']['skills']
        assert db.get(Exam,'enem-2023-matematica-azul').status=='published'
        c=copy.deepcopy(c);c['statement']+=' Edição própria a preservar.'
        db.get(QuestionVersion,exam.items[0]).content=c
    with pytest.raises(HTTPException,match='edição própria'):
        with database.begin() as db:install_catalog(db,publish=True)


def test_reference_has_eight_themes_and_no_annulled_or_canonical_duplicate():
    from scripts.export_reference import build
    data=json.loads((ROOT/'data/datasets/adaptive-math-reference-v1.json').read_text())
    assert build()==data
    assert data['eligible_items']==89 and len(data['theme_counts'])==8
    assert len({item['canonical_id'] for item in data['items']})==89
    assert not any(i['question_id']=='enem-2023-dia2-azul-q164' for i in data['items'])
    for path in ['data/enem-2024-dia2-azul.json','data/catalog/enem-2023-matematica-azul.json']:
        payload=json.loads((ROOT/path).read_text());prepared=classified(payload)
        for q,old in zip(prepared.questions,payload['questions']):
            content=q.content.model_dump();original=copy.deepcopy(content);original['labels']=old['content'].get('labels',{})
            assert content['correct_answer']==old['content']['correct_answer']
            if content['area']=='Matemática':assert len(content['layout']['classification']['skill_candidates'])==1
            assert not content['labels']['skills']
    invalid=classified(json.loads((ROOT/'data/enem-2024-dia2-azul.json').read_text())).model_dump()
    invalid['questions'][0]['content']['labels']['themes']=['Números e proporcionalidade']
    with pytest.raises(ValueError,match='fora da disciplina'):ExamImport.model_validate(invalid)


def test_2023_curated_lot_matches_source_and_is_reproducible():
    from scripts.review_2023_math import review
    from scripts.exam_pdf import lines
    import pymupdf as fitz
    before=json.loads((ROOT/'data/derived/baselines/enem-2023-matematica-auto-v1.json').read_text())
    actual=json.loads((ROOT/'data/catalog/enem-2023-matematica-azul.json').read_text())
    rebuilt,report=review(before,render=False)
    assert rebuilt==actual and report['errors']==report['warnings']==0
    pdf=ROOT/'data/sources/enem/2023/regular/impresso/dia-2/caderno-7-azul/prova.pdf'
    key=pdf.with_name('gabarito.pdf')
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==actual['source']['sha256']
    assert hashlib.sha256(key.read_bytes()).hexdigest()==actual['source']['answer_key_sha256']
    for q,old in zip(actual['questions'],before['questions']):
        assert q['content']['correct_answer']==old['content']['correct_answer']
        assert q['content']['annulled']==old['content']['annulled']
    with fitz.open(pdf) as doc:
        options=[l['option'] for l in lines(doc[15],fitz.Rect(0,490,283,580)) if l.get('option')]
    assert options==list('ABCDE')


def test_archive_requires_admin_and_returns_native_text(admin,student,monkeypatch,tmp_path):
    from backend.app.services import archive_reader as archive
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    source=dict(id='abc',year=1998,application='regular',url='https://download.inep.gov.br/original.pdf',path='enem/1998/prova.pdf')
    catalog=tmp_path/'data/sources/catalogo/acervo.json';catalog.parent.mkdir(parents=True);catalog.write_text(json.dumps(dict(files=[source|dict(status='downloaded',variant='padrao',role='prova') ])))
    rows=tmp_path/'data/bank/occurrences.json';rows.parent.mkdir(parents=True);occ=dict(occurrence_id='abc-q1-1',source_id='abc',year=1998,application='regular',booklet='amarelo',number=1,canonical_id='canonical-1');rows.write_text(json.dumps([occ]))
    raw=tmp_path/'data/bank/raw/1998.json.gz';raw.parent.mkdir();raw.write_bytes(gzip.compress(json.dumps([dict(source_id='abc',issues=[],questions=[occ|dict(text='Texto nativo ainda não revisado.',page=1)])]).encode()))
    assert student.get('/admin/archive').status_code==403
    assert admin.get('/admin/archive/questions?year=1998&limit=200').status_code==422
    assert admin.get('/admin/archive/questions?year=1998').json()['total']==1
    assert admin.get('/admin/archive/questions/abc-q1-1').json()['text']=='Texto nativo ainda não revisado.'
    assert admin.get('/admin/archive/questions/inexistente').status_code==404
