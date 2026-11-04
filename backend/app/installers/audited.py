"""Apply source-checked archive corrections as immutable, traceable versions."""

from collections import defaultdict
import hashlib
import json

from sqlalchemy import func, select

from ..models import CanonicalQuestion, Exam, QuestionVersion, Review
from ..preparation import blocking_issues
from ..schemas import QuestionContent
from ..services.content import publish_exam, validate_assets
from ..services.identity import signatures, validate_revision_identity
from .bundled import bundled_reviewer


def content_hash(content):
    content = QuestionContent.model_validate(content).model_dump()
    return hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def apply_audited(db, plan):
    """Caller owns transaction; a stale plan or a newer manual draft aborts it."""
    if plan.get('schema_version') != '1.0' or not plan.get('audit_sha256'):
        raise ValueError('Plano de auditoria sem versão ou evidência.')
    if plan.get('failures'):
        raise ValueError('A geração do plano contém falhas; conclua a análise antes de aplicar.')
    checked, seen = [], set()
    exams = {}
    for row in plan['changes']:
        pair = row['exam_id'], row['question_id']
        if pair in seen:
            raise ValueError('Correção duplicada no plano.')
        seen.add(pair)
        exam = exams.setdefault(row['exam_id'], db.get(Exam, row['exam_id']))
        if (
            not exam
            or exam.status != 'published'
            or exam.source.get('automatic_archive', {}).get('review_status') != 'pending'
        ):
            raise ValueError('Este instalador só atualiza o acervo automático publicado e pendente.')
        if (
            exam.source['sha256'] != row['source_sha256']
            or exam.source['answer_key_sha256'] != row['answer_key_sha256']
        ):
            raise ValueError('A fonte da prova mudou desde a auditoria.')
        current = next(
            (
                db.get(QuestionVersion, key)
                for key in exam.items
                if db.get(QuestionVersion, key).question_id == row['question_id']
            ),
            None,
        )
        desired = QuestionContent.model_validate(row['content']).model_dump()
        if current is None:
            raise ValueError('Questão ausente da prova.')
        if content_hash(current.content) == content_hash(desired):
            continue
        if current.id != row['previous_version'] or content_hash(current.content) != row['previous_sha256']:
            raise ValueError('A versão atual diverge da versão auditada.')
        latest = db.scalar(
            select(func.max(QuestionVersion.version)).where(QuestionVersion.question_id == current.question_id)
        )
        if current.status != 'approved' or latest != current.version:
            raise ValueError('Há edição ou decisão posterior à versão publicada; revise manualmente.')
        if any(current.content[field] != desired[field] for field in ('number', 'area', 'labels', 'page')):
            raise ValueError('Correção técnica não pode alterar identidade, área, rótulos ou página.')
        if len(row.get('reason', '')) < 20 or not row.get('evidence'):
            raise ValueError('Toda correção exige motivo e evidência.')
        validate_assets(desired)
        validate_revision_identity(db, desired, current.canonical_id)
        checked.append((exam, current, desired, row))
    # A changed canonical answer must agree with every active occurrence,
    # including the English/Spanish booklets that share common questions.
    replacements = {old.id: desired for _, old, desired, _ in checked}
    affected = {old.canonical_id for _, old, _, _ in checked}
    identities = defaultdict(set)
    for exam in db.scalars(select(Exam).where(Exam.status == 'published')):
        for key in exam.items:
            q = db.get(QuestionVersion, key)
            if q.canonical_id in affected:
                identities[q.canonical_id].add(signatures(replacements.get(key, q.content)))
    for canonical_id, values in identities.items():
        if len(values) != 1:
            declared = {r['canonical_id'] for r in plan.get('canonical_review_required', [])}
            changes_answer = any(
                old.canonical_id == canonical_id
                and (old.content['correct_answer'], old.content['annulled'])
                != (desired['correct_answer'], desired['annulled'])
                for _, old, desired, _ in checked
            )
            if canonical_id not in declared or changes_answer:
                raise ValueError(f'Ocorrências ativas divergentes para {canonical_id}; corrija-as no mesmo plano.')
    ambiguous = {key for key, values in identities.items() if len(values) > 1}
    if not checked:
        return {'changed': 0, 'exams': 0, 'versions': []}
    reviewer = bundled_reviewer(db)
    versions = []
    for exam, old, desired, row in checked:
        number = old.version + 1
        new = QuestionVersion(
            id=f'{old.question_id}:{number}',
            question_id=old.question_id,
            canonical_id=old.canonical_id,
            version=number,
            content=desired,
            status='approved',
        )
        db.add(new)
        reason = json.dumps(
            {
                'reason': row['reason'],
                'audit_sha256': plan['audit_sha256'],
                'before': row['previous_sha256'],
                'after': content_hash(desired),
                'evidence': row['evidence'],
                'canonical_review_required': old.canonical_id in ambiguous,
            },
            ensure_ascii=False,
        )
        if len(reason) > 2000:
            raise ValueError('Evidência de revisão excede o limite do registro.')
        db.add(Review(user_id=reviewer.id, target_id=new.id, action='approve', reason=reason))
        exam.items = [new.id if key == old.id else key for key in exam.items]
        versions.append(new.id)
    db.flush()
    for canonical_id, values in identities.items():
        if canonical_id in ambiguous:
            continue  # Preserve the existing link; never merge or guess a new identity.
        identity = db.get(CanonicalQuestion, canonical_id)
        identity.signature, identity.answer_signature = next(iter(values))
    db.flush()
    touched = {exam.id for exam, _, _, _ in checked}
    for key in touched:
        exam = exams[key]
        pending = sum(len(blocking_issues(db.get(QuestionVersion, item).content)) for item in exam.items)
        exam.source = {
            **exam.source,
            'automatic_archive': {**exam.source['automatic_archive'], 'blocking_issues': pending},
            'technical_audit': {
                'sha256': plan['audit_sha256'],
                'independent_pedagogical_review': False,
                'canonical_review_required': sorted(
                    {db.get(QuestionVersion, item).canonical_id for item in exam.items} & ambiguous
                ),
            },
        }
        publish_exam(
            db,
            exam,
            reviewer.id,
            'Correções técnicas rastreadas pela auditoria integral; revisão independente continua pendente.',
            allow_pending=True,
        )
    metadata_updates = 0
    for exam in db.scalars(select(Exam).where(Exam.status == 'published')):
        automatic = exam.source.get('automatic_archive', {})
        if automatic.get('review_status') != 'pending' or exam.id in touched:
            continue
        pending = sum(len(blocking_issues(db.get(QuestionVersion, item).content)) for item in exam.items)
        related = sorted({db.get(QuestionVersion, item).canonical_id for item in exam.items} & ambiguous)
        if automatic.get('blocking_issues') != pending or related:
            exam.source = {
                **exam.source,
                'automatic_archive': {**automatic, 'blocking_issues': pending},
                **(
                    {
                        'technical_audit': {
                            'sha256': plan['audit_sha256'],
                            'independent_pedagogical_review': False,
                            'canonical_review_required': related,
                        }
                    }
                    if related
                    else {}
                ),
            }
            db.add(
                Review(
                    user_id=reviewer.id,
                    target_id=exam.id,
                    action='audit',
                    reason='Contagem de pendências atualizada pela validação do conteúdo exibido; sem alterar versões ou aprovação. Auditoria '
                    + plan['audit_sha256'],
                )
            )
            metadata_updates += 1
    return {
        'changed': len(versions),
        'exams': len(touched),
        'versions': versions,
        'quality_metadata_updated': metadata_updates,
        'canonical_identities_requiring_review': len(ambiguous),
    }
