"""Install source-curated lots and labels through immutable, guarded versions."""
import copy
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from ..core.config import ROOT
from ..services.content import import_exam, publish_exam, validate_assets
from ..models import Exam, QuestionVersion, Review
from ..schemas import ExamImport, QuestionContent
from ..services.presentation import content_fingerprint, is_previous_bundled_content
from ..services.identity import identify
from .bundled import bundled_reviewer
from ..preparation import fingerprint as preparation_fingerprint


def classified(payload, *, refresh_preparation_audit=True):
    """Labels apply only to the exact reviewed content and declared source."""
    data=copy.deepcopy(payload.model_dump() if isinstance(payload,ExamImport) else payload)
    records=json.loads((ROOT/'data/classification/annotations-v1.json').read_text())
    annotations={a['question_id']:a for a in records['annotations']}
    for q in data['questions']:
        a=annotations.get(q['question_id'])
        if not a or a['source_sha256']!=data['source']['sha256'] or a['content_sha256']!=content_fingerprint(q['content']):
            raise ValueError(f'Anotação não corresponde à versão e fonte de {q["question_id"]}.')
        if a['status']!='curated':raise ValueError('Anotação sem curadoria não pode ser instalada como lote revisado.')
        q['content']['labels']=dict(discipline=a['discipline'],themes=a['themes'],skills=[],taxonomy_version=a['taxonomy_version'],provenance='reference-v1: curadoria técnica assistida; segunda revisão independente pendente.')
        q['content']['layout']={**(q['content'].get('layout') or {}),'classification':dict(version=records['version'],status=a['status'],independent_review=False,evidence=a['evidence'],rationale=a['rationale'],skill_candidates=a['skill_candidates'])}
        preparation=q['content']['layout'].get('preparation')
        if preparation and refresh_preparation_audit:
            # Labels change the full-content fingerprint, although source-reviewed
            # prose/formulas did not change. Retain the original audit and link
            # the classified output so import does not reinterpret it again.
            q['content']['layout']['classification']['source_preparation_output_sha256']=preparation['output_sha256']
            preparation['output_sha256']=preparation_fingerprint(q['content'])
    return ExamImport.model_validate(data)


def install_catalog(db,publish=False):
    manifest=json.loads((ROOT/'data/catalog/manifest.json').read_text())
    reviewer=bundled_reviewer(db)
    stats=dict(imported_exams=0,new_versions=0,canonical_questions=0)
    for entry in manifest['exams']:
        path=(ROOT/entry['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Caminho do catálogo fora do projeto.')
        base=ExamImport.model_validate_json(path.read_text());desired=classified(base)
        previous_profile=classified(base,refresh_preparation_audit=False)
        exam=db.get(Exam,desired.id);changed=False
        was_withdrawn=bool(exam and exam.status=='withdrawn')
        previous_items=[db.get(QuestionVersion,key) for key in exam.items] if exam else []
        previous_drafts=[q.id for q in previous_items if q.status=='draft']
        held_for_review=(any(q.status=='in_review' for q in previous_items) or bool(previous_drafts and
                         db.scalar(select(Review.id).where(Review.target_id.in_(previous_drafts),Review.action=='edit').limit(1))))
        if not exam:
            exam=import_exam(db,desired);stats['imported_exams']+=1;changed=True
        else:
            if len(exam.items)!=len(desired.questions):raise HTTPException(409,'Lote existente foi reorganizado; exige revisão manual.')
            new_keys=[]
            for key,original,target,previous_target in zip(exam.items,base.questions,desired.questions,previous_profile.questions):
                old=db.get(QuestionVersion,key);wanted=target.content.model_dump()
                if old.question_id!=target.question_id:raise HTTPException(409,'Ordem do lote existente foi alterada.')
                validate_assets(wanted)
                if QuestionContent.model_validate(old.content).model_dump()==wanted:
                    if old.canonical_id is None:old.canonical_id=identify(db,wanted,(desired.source.sha256,target.content.number))
                    new_keys.append(old.id);continue
                trusted=content_fingerprint(old.content)==content_fingerprint(original.content.model_dump())
                trusted=trusted or content_fingerprint(old.content)==content_fingerprint(previous_target.content.model_dump())
                if base.id=='enem-2024-dia2-azul':trusted=trusted or is_previous_bundled_content(old.question_id,old.content)
                if not trusted:raise HTTPException(409,f'{old.question_id} tem edição própria; nenhuma substituição automática permitida.')
                # Source curation changes labels/presentation, never assessment.
                if any(old.content[k]!=wanted[k] for k in ('number','area','page','correct_answer','annulled')):
                    raise HTTPException(409,'Mudança de avaliação exige revisão manual.')
                latest=db.scalar(select(func.max(QuestionVersion.version)).where(QuestionVersion.question_id==old.question_id))
                canonical_id=old.canonical_id or identify(db,wanted,(desired.source.sha256,target.content.number))
                new=QuestionVersion(id=f'{old.question_id}:{latest+1}',question_id=old.question_id,canonical_id=canonical_id,version=latest+1,content=wanted,status='draft')
                db.add(new);new_keys.append(new.id);stats['new_versions']+=1;changed=True
            db.flush();exam.items=new_keys
        # Backfill identity only; do not rewrite old content or run snapshots.
        for q,key in zip(desired.questions,exam.items):
            current=db.get(QuestionVersion,key)
            canonical_id=current.canonical_id or identify(db,q.content.model_dump(),(desired.source.sha256,q.content.number))
            for previous in db.scalars(select(QuestionVersion).where(QuestionVersion.question_id==q.question_id,QuestionVersion.canonical_id.is_(None))):
                previous.canonical_id=canonical_id
        # Explicit publication also handles a previous install without publication.
        # Repeated runs never override a human rejection, pending edit or withdrawal.
        pending=[db.get(QuestionVersion,key) for key in exam.items]
        if changed and held_for_review:
            for question in pending:
                if question.status=='draft':question.status='in_review'
        can_publish=(publish and not was_withdrawn and not held_for_review and (changed or
                     (exam.status in {'draft','in_review'} and all(q.status in {'draft','approved'} for q in pending))))
        if changed or can_publish:
            reason=f'{manifest["version"]}: lote conferido com a fonte e taxonomia reference-v1; habilidades apenas propostas e revisão independente pendente.'
            if can_publish:
                for key in exam.items:
                    db.get(QuestionVersion,key).status='approved'
                    db.add(Review(user_id=reviewer.id,target_id=key,action='approve',reason=reason))
                publish_exam(db,exam,reviewer.id,reason)
            else:exam.status='withdrawn' if was_withdrawn else 'in_review'
    from ..models import CanonicalQuestion
    stats['canonical_questions']=db.scalar(select(func.count()).select_from(CanonicalQuestion))
    return stats
