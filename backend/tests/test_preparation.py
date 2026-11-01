import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models import Exam, QuestionVersion
from backend.app.preparation import prepare_content, prepare_exam
from backend.app.preparation.notation import normalize
from backend.app.schemas import QuestionContent

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('raw,expected', [
    ('Íons Mg²⁺ e H⁺ em H₂O.', r'Íons $\ce{Mg^2+}$ e $\ce{H^+}$ em $\ce{H2O}$.'),
    ('íon (H⁺).', r'íon ($\ce{H^+}$).'),
    ('22 L/mol e 0,78 g/mL', r'$22\,\mathrm{L/mol}$ e $0{,}78\,\mathrm{g/mL}$'),
    ('4,0 × 10⁵ e M₂', r'$4{,}0\times10^{5}$ e $M_{2}$'),
    ('R$ 10,00 em 3/4/2024. NO título de CO autores.', 'R$ 10,00 em 3/4/2024. NO título de CO autores.'),
    ('Dólar (US$) 39 000, A$ 40 000 e C$ 41 000.', 'Dólar (US$) 39 000, A$ 40 000 e C$ 41 000.'),
    (r'Já $\ce{CO2}$ e \(f_0\) e $$x^2$$.', r'Já $\ce{CO2}$ e \(f_0\) e $$x^2$$.'),
    ('Na Química, as fórmulas. No texto de revisão. As moléculas.', 'Na Química, as fórmulas. No texto de revisão. As moléculas.'),
    ('Frequências fᵣ e f₀, 10⁻³ e 70%.', r'Frequências $f_{r}$ e $f_{0}$, $10^{-3}$ e $70\%$.'),
    ('Os elétrons (e⁻) dos íons.', r'Os elétrons ($\ce{e-}$) dos íons.'),
])
def test_notation_is_conservative_and_idempotent(raw, expected):
    actual, issues = normalize(raw)
    assert actual == expected and not issues
    assert normalize(actual)[0] == actual


@pytest.mark.parametrize('raw,code', [
    ('Íon Mg2+', 'ambiguous_charge'),
    ('H2O (I) -> H+ (aq) + OH- (aq)', 'ambiguous_liquid_state'),
    ('4,0 × 105 toneladas', 'ambiguous_exponent'),
    ('Ca(?) -> Na', 'unreadable_reaction'),
])
def test_ambiguous_notation_is_reported_without_guessing(raw, code):
    result, issues = normalize(raw)
    if code == 'ambiguous_liquid_state':
        assert '(I)' in result and '(l)' not in result
    else: assert result == raw
    assert code in [i[0] for i in issues]


@pytest.mark.parametrize('text', [r'Fórmula $x^{2$', r'Fórmula $x + 2', r'Fórmula \(x+2'])
def test_broken_latex_blocks_approval_preparation(exam_payload, text):
    content=exam_payload['questions'][0]['content']
    content['statement']=text
    actual=prepare_content(content)
    assert any(i['code']=='invalid_latex' and i['severity']=='error' for i in actual['layout']['preparation']['issues'])


def figure():
    return {'type':'image','asset':{'path':'/assets/fixture.png','alt':'Esquema científico com duas câmaras.'}}


def test_association_works_for_unseen_numbers_and_preserves_assessment(exam_payload):
    source = exam_payload['questions'][0]['content']
    source['number'] = 37
    source['statement'] = 'A figura apresenta reações químicas. Qual é a reação global?'
    source['blocks'] = [
        {'type':'paragraph','text':'A figura apresenta reações químicas.','role':'body'},
        figure(),
        {'type':'paragraph','text':'H₂O (l) → H⁺ (aq) + OH⁻ (aq)'},
        {'type':'paragraph','text':'Figura 2 — Célula experimental.'},
        {'type':'paragraph','text':'SILVA, A. Estudo da célula.'},
        {'type':'paragraph','text':'Disponível em: https://example.org. Acesso em: 2025.'},
        {'type':'paragraph','text':'Qual é a reação global?','role':'body'},
    ]
    source['alternatives'][0]['text']='CO₂ e O₂.'
    saved = copy.deepcopy(source)
    prepared = prepare_content(source)
    image = next(b for b in prepared['blocks'] if b['type']=='image')
    assert image['caption']=='Figura 2 — Célula experimental.'
    assert 'SILVA' in image['credit'] and len(image['equations'])==1
    assert r'\ce{H^+ (aq)}' in image['equations'][0]
    assert r'\ce{CO2}' in prepared['alternatives'][0]['text']
    assert source == saved
    normalized = QuestionContent.model_validate(source).model_dump()
    assert all(prepared[k]==normalized[k] for k in ['number','correct_answer','annulled','labels','page','area'])
    assert prepare_content(prepared)==prepared
    source['number']=88
    assert prepare_content(source)['blocks']==prepared['blocks']


def test_declared_body_reference_is_not_moved_to_figure(exam_payload):
    source=exam_payload['questions'][0]['content']
    source['blocks']=[{'type':'paragraph','text':'Fonte: texto de apoio.','role':'body'},figure()]
    actual=prepare_content(source)
    assert actual['blocks'][0]['text']=='Fonte: texto de apoio.'
    assert actual['blocks'][1]['credit']==''


def test_preview_and_import_share_preparation_and_draft_status(admin, exam_payload, database):
    exam_payload['questions'][0]['content']['statement']='Considere a molécula H₂O e o íon Mg²⁺.'
    preview=admin.post('/admin/imports/prepare',json=exam_payload)
    assert preview.status_code==200
    with database() as db: assert db.scalar(select(Exam)) is None
    imported=admin.post('/admin/imports',json=exam_payload)
    assert imported.status_code==201 and imported.json()['status']=='draft'
    with database() as db:
        actual=db.get(QuestionVersion,'teste-q1:1')
        assert actual.status=='draft'
        assert actual.content==preview.json()['exam']['questions'][0]['content']
        assert r'\ce{Mg^2+}' in actual.content['statement']


def test_unpositioned_images_block_approval_and_publication(admin, exam_payload):
    # An existing resource still blocks approval when its position is missing.
    fig=figure()
    source=json.loads((ROOT/'data/enem-2024-dia2-azul.json').read_text())
    fig['asset']=next(b['asset'] for b in source['questions'][0]['content']['blocks'] if b['type']=='image')
    c=exam_payload['questions'][0]['content']
    c['images']=[fig['asset']]
    assert admin.post('/admin/imports',json=exam_payload).status_code==201
    assert admin.post('/admin/reviews/teste-q1:1',json={'action':'approve','reason':'Conferência sem resolver a posição'}).status_code==409
    assert admin.post('/admin/reviews/prova-teste',json={'action':'publish','reason':'Tentar publicar antes de corrigir'}).status_code==409
    # Correcting placement creates a new draft; it does not modify the old one.
    c['images']=[];c['blocks']=[{'type':'paragraph','text':c['statement']},fig]
    assert admin.put('/admin/questions/teste-q1:1',json={'content':c,'reason':'Posicionar a figura conforme a fonte'}).status_code==200
    assert admin.post('/admin/reviews/teste-q1:2',json={'action':'approve','reason':'Posição e descrição conferidas na fonte'}).status_code==200


def test_edit_reports_conversion_limits_without_creating_a_version(admin, exam_payload, database):
    assert admin.post('/admin/imports',json=exam_payload).status_code==201
    content=exam_payload['questions'][0]['content']
    content['blocks']=[{'type':'paragraph','text':'Texto de apoio.\nAcesso em: 2025.'} for _ in range(100)]
    response=admin.put('/admin/questions/teste-q1:1',json={'content':content,'reason':'Conferência de um conteúdo extenso'})
    assert response.status_code==422
    with database() as db: assert db.get(QuestionVersion,'teste-q1:2') is None


def test_generic_cli_does_not_overwrite_sources_and_accepts_new_files(tmp_path, exam_payload):
    source=tmp_path/'nova-prova.json';target=tmp_path/'preparada.json'
    source.write_text(json.dumps(exam_payload))
    before=source.read_bytes()
    cmd=[sys.executable,str(ROOT/'scripts/prepare_exam.py'),'--input',str(source),'--output',str(target)]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(target.read_text())['questions'][0]['content']['layout']['preparation']['version']=='generic-v1'
    assert 'válidas' in json.loads(target.with_suffix('.report.json').read_text())['latex_validation']
    assert subprocess.run(cmd,capture_output=True).returncode==2
    assert source.read_bytes()==before


def test_pdf_adapter_uses_geometry_and_preserves_source(tmp_path):
    from scripts.exam_pdf import extract_exam
    source=ROOT/'data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf'
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    data=json.loads((ROOT/'data/derived/baselines/enem-2024-dia2-azul-extraction.json').read_text())
    data['questions']=data['questions'][:2];data['expected_items']=2;data['kind']='collection'
    result,report=prepare_exam(extract_exam(data,source,tmp_path/'assets'))
    assert len(result.questions)==2 and report['errors']==0
    assert all(not q.content.original_layout and not q.content.images for q in result.questions)
    first=result.questions[0].content
    image=next(b for b in first.blocks if b.type=='image')
    assert 'Momentum and Car safety' in image.credit or 'Momentum and Car safety' in image.caption
    assert 'shalom-education.com' in image.credit
    assert first.alternatives[1].text=='absorve a energia cinética do sistema.'
    assert list((tmp_path/'assets').rglob('*.png'))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before


def test_manifest_rejects_mismatched_key_and_discovers_columns():
    from scripts.exam_pdf import from_manifest
    base=json.loads((ROOT/'data/enem-2024-dia2-azul.json').read_text())
    manifest={k:v for k,v in base.items() if k not in ['questions','schema_version']}
    manifest.update(expected_items=3,kind='collection',layout={'pages':[2,2]},answers={'91':'B','92':'C','93':'E'},areas=[{'first':91,'last':93,'area':'Ciências da Natureza'}])
    actual=from_manifest(manifest,ROOT/'data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf')
    assert [q['content']['number'] for q in actual['questions']]==[91,92,93]
    manifest['answers'].pop('93')
    with pytest.raises(ValueError,match='não coincidem'): from_manifest(manifest,ROOT/'data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf')


def test_full_question_bitmap_is_not_used_as_a_figure(tmp_path, monkeypatch):
    from scripts.exam_pdf import extract_exam
    monkeypatch.setattr('scripts.exam_pdf.graphics', lambda page,clip:[clip])
    data=json.loads((ROOT/'data/derived/baselines/enem-2024-dia2-azul-extraction.json').read_text())
    data['questions']=data['questions'][:1];data['expected_items']=1;data['kind']='collection'
    result,report=prepare_exam(extract_exam(data,ROOT/'data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf',tmp_path))
    assert any(i['code']=='whole_region_image' and i['severity']=='error' for i in report['questions'][0]['issues'])
    assert not list(tmp_path.rglob('*.png'))


@pytest.mark.parametrize('source_number',[127,161,174])
def test_graphical_options_are_assigned_by_geometry_not_question_id(tmp_path, source_number):
    from scripts.exam_pdf import extract_exam
    data=json.loads((ROOT/'data/derived/baselines/enem-2024-dia2-azul-extraction.json').read_text())
    data['questions']=[q for q in data['questions'] if q['content']['number']==source_number]
    data['questions'][0]['content']['number']=37
    data['questions'][0]['question_id']='outra-prova-q37'
    data['expected_items']=1;data['kind']='collection'
    result,report=prepare_exam(extract_exam(data,ROOT/'data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf',tmp_path))
    assert all(a.image for a in result.questions[0].content.alternatives)
    assert not any(i['code']=='alternative_layout' for i in report['questions'][0]['issues'])
