"""Curation of tutor material: proposals written by curators or drafted by the provider, then reviewed."""

from fastapi import APIRouter
from sqlalchemy import select

from ... import models as m
from ...core.config import tutor_settings
from ...dependencies import AdminUser, SessionDep
from ...schemas.tutor import MaterialLevels, MaterialReview
from ...services import tutor
from ...services.content import public_question
from ...services.errors import NotFound

router = APIRouter(prefix='/tutor', tags=['curadoria'])


@router.get('/status')
def provider_status():
    """Whether the provider is configured; never returns the key."""
    settings = tutor_settings()
    return {
        'enabled': settings.enabled,
        'missing': settings.missing,
        'model': settings.model or None,
        'base_url': settings.base_url,
        'timeout_seconds': settings.timeout_seconds,
        'max_output_tokens': settings.max_output_tokens,
        'daily_limit': settings.daily_limit,
        'max_cost_usd': settings.max_cost_usd,
    }


@router.get('/exams/{exam_id}')
def exam_items(exam_id: str, db: SessionDep):
    exam = db.get(m.Exam, exam_id)
    if exam is None or exam.status != 'published':
        raise NotFound('Prova publicada não encontrada.')
    rows = []
    for key in exam.items:
        question = db.get(m.QuestionVersion, key)
        rows.append(
            {
                'id': question.id,
                'number': question.content['number'],
                'area': question.content['area'],
                'material': tutor.material_status(db, question),
            }
        )
    return {'exam': {'id': exam.id, 'title': exam.title}, 'items': rows}


@router.get('/questions/{version_id}')
def question_materials(version_id: str, db: SessionDep):
    question = tutor.question_or_404(db, version_id)
    item = {
        'id': question.id,
        'question_id': question.question_id,
        'canonical_id': question.canonical_id,
        'version': question.version,
        'content': question.content,
    }
    return {'question': public_question(item, finished=True), 'materials': tutor.materials_of(db, question)}


@router.post('/questions/{version_id}/materials', status_code=201)
def write_material(version_id: str, payload: MaterialLevels, user: AdminUser, db: SessionDep):
    question = tutor.question_or_404(db, version_id)
    material = tutor.add_material(db, question, payload.model_dump(), user.id)
    return tutor.material_data(material, material.content_sha256)


@router.post('/questions/{version_id}/draft', status_code=201)
def draft(version_id: str, user: AdminUser, db: SessionDep):
    question = tutor.question_or_404(db, version_id)
    material = tutor.draft_material(db, question, user.id)
    return tutor.material_data(material, material.content_sha256)


@router.post('/materials/{material_id}/review')
def review(material_id: str, payload: MaterialReview, user: AdminUser, db: SessionDep):
    material = tutor.review_material(db, material_id, payload.action, payload.reason, user.id)
    current = db.scalar(
        select(m.QuestionVersion)
        .where(m.QuestionVersion.question_id == material.question_id)
        .order_by(m.QuestionVersion.version.desc())
        .limit(1)
    )
    return tutor.material_data(material, tutor.material_fingerprint(current.content) if current else None)
