import copy

import pytest
from sqlalchemy import select, func

from backend.app.installers.audited import apply_audited, content_hash
from backend.app.installers.generated import publish_generated
from backend.app.models import CanonicalQuestion, Exam, QuestionVersion, Review, ExamRun, User
from backend.app.preparation import blocking_issues, prepare_exam
from backend.app.services.identity import signatures


def install(tmp_path, exam_payload, database):
    prepared, _ = prepare_exam(exam_payload)
    (tmp_path / 'exam.json').write_text(prepared.model_dump_json())
    with database.begin() as db:
        assert publish_generated(db, tmp_path)['published'] == 1
        exam = db.get(Exam, exam_payload['id'])
        old = db.get(QuestionVersion, exam.items[0])
        content = copy.deepcopy(old.content)
        content['correct_answer'] = 'A'
        plan = {
            'schema_version': '1.0',
            'audit_sha256': 'a' * 64,
            'changes': [
                {
                    'exam_id': exam.id,
                    'question_id': old.question_id,
                    'previous_version': old.id,
                    'previous_sha256': content_hash(old.content),
                    'source_sha256': exam.source['sha256'],
                    'answer_key_sha256': exam.source['answer_key_sha256'],
                    'content': content,
                    'reason': 'Gabarito conferido na coluna correta da fonte oficial.',
                    'evidence': {'page': 2, 'extractors_agree': True},
                }
            ],
        }
    return plan


def test_source_checked_revision_is_idempotent_and_preserves_old_snapshots(tmp_path, exam_payload, database):
    plan = install(tmp_path, exam_payload, database)
    with database.begin() as db:
        old = db.get(QuestionVersion, 'teste-q1:1')
        snapshot = copy.deepcopy(old.content)
        user = User(name='Teste', email='snapshot@invalid.local', password_hash='unused', role='student')
        db.add(user)
        db.flush()
        run = ExamRun(
            user_id=user.id,
            exam_id=exam_payload['id'],
            start_key='audit-snapshot',
            exam_info={},
            items=[{'id': old.id, 'content': snapshot}],
            answers={old.id: 'B'},
            finished_at=123,
            result={'correct': 1},
            started_at=100,
        )
        db.add(run)
        db.flush()
        run_id = run.id
        assert apply_audited(db, plan)['changed'] == 1
        assert apply_audited(db, plan)['changed'] == 0
    with database() as db:
        exam = db.get(Exam, exam_payload['id'])
        new = db.get(QuestionVersion, exam.items[0])
        assert new.version == 2 and new.content['correct_answer'] == 'A'
        assert db.get(QuestionVersion, 'teste-q1:1').content == snapshot
        run = db.get(ExamRun, run_id)
        assert (
            run.items[0]['content'] == snapshot and run.result == {'correct': 1} and run.answers == {'teste-q1:1': 'B'}
        )
        assert db.get(CanonicalQuestion, new.canonical_id).answer_signature == signatures(new.content)[1]
        assert exam.source['automatic_archive']['review_status'] == 'pending'
        assert db.scalar(select(func.count()).select_from(Review).where(Review.target_id == new.id)) == 1


@pytest.mark.parametrize('conflict', ['source', 'version', 'manual_draft', 'withdrawn', 'labels', 'reviewed'])
def test_revision_refuses_stale_sources_and_manual_changes(tmp_path, exam_payload, database, conflict):
    plan = install(tmp_path, exam_payload, database)
    with database.begin() as db:
        exam = db.get(Exam, exam_payload['id'])
        old = db.get(QuestionVersion, exam.items[0])
        if conflict == 'source':
            plan['changes'][0]['source_sha256'] = 'd' * 64
        if conflict == 'version':
            plan['changes'][0]['previous_sha256'] = 'e' * 64
        if conflict == 'manual_draft':
            db.add(
                QuestionVersion(
                    id='teste-q1:2',
                    question_id=old.question_id,
                    canonical_id=old.canonical_id,
                    version=2,
                    content=old.content,
                    status='draft',
                )
            )
            db.flush()
        if conflict == 'withdrawn':
            old.status = 'withdrawn'
        if conflict == 'labels':
            plan['changes'][0]['content']['labels']['themes'] = []
        if conflict == 'reviewed':
            exam.source = {
                **exam.source,
                'automatic_archive': {**exam.source['automatic_archive'], 'review_status': 'reviewed'},
            }
        with pytest.raises(ValueError):
            apply_audited(db, plan)
        assert exam.items[0] == 'teste-q1:1'


def test_missing_options_and_control_glyphs_cannot_hide_behind_a_cached_report(exam_payload):
    prepared, _ = prepare_exam(exam_payload)
    c = prepared.questions[0].content.model_dump()
    c['alternatives'][0]['text'] = 'Alternativa não extraída; conferir original.'
    c['alternatives'][1]['text'] = 'Fórmula \x01 perdida'
    codes = {i['code'] for i in blocking_issues(c)}
    assert {'missing_alternative', 'control_character'} <= codes


@pytest.mark.parametrize('change_answer', [False, True])
def test_existing_canonical_links_require_explicit_adjudication_and_cannot_hide_key_conflicts(
    tmp_path, exam_payload, database, change_answer
):
    plan = install(tmp_path, exam_payload, database)
    other = copy.deepcopy(exam_payload)
    other['id'] = 'outra-ocorrencia'
    for q in other['questions']:
        q['question_id'] = 'outra-' + q['question_id']
    prepared, _ = prepare_exam(other)
    (tmp_path / 'other.json').write_text(prepared.model_dump_json())
    with database.begin() as db:
        assert publish_generated(db, tmp_path)['published'] == 1
        old = db.get(QuestionVersion, 'teste-q1:1')
        identity = db.get(CanonicalQuestion, old.canonical_id)
        original = identity.signature, identity.answer_signature
        desired = plan['changes'][0]['content']
        if not change_answer:
            desired['correct_answer'] = old.content['correct_answer']
            desired['blocks'][0]['text'] += ' Trecho recuperado da fonte.'
            desired['statement'] = desired['blocks'][0]['text']
        with pytest.raises(ValueError, match='divergentes'):
            apply_audited(db, plan)
        plan['canonical_review_required'] = [{'canonical_id': old.canonical_id}]
        if change_answer:
            with pytest.raises(ValueError, match='divergentes'):
                apply_audited(db, plan)
        else:
            result = apply_audited(db, plan)
            assert result['canonical_identities_requiring_review'] == 1
            assert (identity.signature, identity.answer_signature) == original
            assert db.get(Exam, other['id']).source['technical_audit']['canonical_review_required'] == [identity.id]


def test_resuming_audit_rechecks_versions_sources_assets_and_crops(tmp_path, exam_payload, monkeypatch):
    from experiments import archive_audit as audit, common
    from backend.app.schemas import QuestionContent
    import hashlib

    monkeypatch.setattr(common, 'ROOT', tmp_path)
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    for name in ['source.pdf', 'key.pdf']:
        (tmp_path / name).write_bytes(name.encode())
    asset = tmp_path / 'data/assets/figure.png'
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b'original asset')
    source_hash = hashlib.sha256(b'source.pdf').hexdigest()
    key_hash = hashlib.sha256(b'key.pdf').hexdigest()
    content = QuestionContent.model_validate(exam_payload['questions'][0]['content']).model_dump()
    exam = {
        'source': {'sha256': source_hash, 'answer_key_sha256': key_hash},
        'items': [{'id': 'q:1', 'content': content}],
    }
    row = {
        'id': 'q:1',
        'content_sha256': common.digest(content),
        'source_figures_pixel_checked': 0,
        'findings': [],
        'source_images': ['original.png'],
    }
    cached = {
        'source_sha256': source_hash,
        'answer_key_sha256': key_hash,
        'source_path': 'source.pdf',
        'answer_key_path': 'key.pdf',
        'items': [row],
        'assets': {'/assets/figure.png': {'sha256': common.file_digest(asset)}},
    }
    path = tmp_path / 'report.json'
    common.write_json(path, cached)
    assert audit.reusable_report(exam, path, [], tmp_path, False) == cached
    assert audit.reusable_report(exam, path, [], tmp_path, True) is None
    asset.write_bytes(b'changed asset')
    assert audit.reusable_report(exam, path, [], tmp_path, False) is None
    asset.write_bytes(b'original asset')
    exam['items'][0]['content']['statement'] = 'Texto alterado depois da auditoria.'
    assert audit.reusable_report(exam, path, [], tmp_path, False) is None


@pytest.mark.parametrize('changed', ['source', 'content', 'exam', 'asset'])
def test_assisted_visual_findings_cannot_follow_stale_content_or_evidence(tmp_path, monkeypatch, changed):
    from scripts import report_archive_audit as reports
    from experiments.common import file_digest, write_json

    monkeypatch.setattr(reports, 'ROOT', tmp_path)
    asset = tmp_path / 'capture.jpg'
    asset.write_bytes(b'inspected capture')
    row = {
        'version_id': 'q:2',
        'exam': 'exam',
        'content_sha256': 'content',
        'source_sha256': 'source',
        'evidence_files': {'capture.jpg': file_digest(asset)},
        'findings': [{'code': 'visual_footer', 'detail': 'Rodapé anexado à alternativa.'}],
    }
    path = tmp_path / 'review.json'
    write_json(path, {'schema_version': '1.0', 'independent_review': False, 'human_seconds': None, 'records': [row]})
    records = reports.load_visual_review(path)
    source = {'source_sha256': 'source'}
    item = {'id': 'q:2', 'content_sha256': 'content'}
    assert reports.visual_item_findings(records, 'exam', source, item) == row['findings']
    assert reports.visual_item_findings(records, 'exam', source, {'id': 'other'}) == []
    if changed == 'asset':
        asset.write_bytes(b'replaced capture')
        with pytest.raises(ValueError, match='arquivos'):
            reports.load_visual_review(path)
    else:
        if changed == 'source':
            source['source_sha256'] = 'new-source'
        if changed == 'content':
            item['content_sha256'] = 'new-content'
        with pytest.raises(ValueError, match='outra fonte ou versão'):
            reports.visual_item_findings(records, 'other' if changed == 'exam' else 'exam', source, item)
