"""Curation of layout proposals: submit, compare with the published blocks and the source, review."""

from fastapi import APIRouter

from ... import models as m
from ...dependencies import AdminUser, SessionDep
from ...schemas.layout import LayoutProposalImport, LayoutReview
from ...services import layout
from ...services.errors import NotFound

router = APIRouter(prefix='/layout', tags=['curadoria'])


@router.post('/proposals', status_code=201)
def submit(payload: LayoutProposalImport, user: AdminUser, db: SessionDep):
    """A refused conversion is stored as `invalid` with its reasons; nothing published changes."""
    proposal = layout.submit(db, payload.model_dump(mode='json'), user.id)
    return layout.proposal_data(proposal, db.get(m.QuestionVersion, proposal.question_version_id))


@router.get('/questions/{version_id}')
def for_question(version_id: str, db: SessionDep):
    version = db.get(m.QuestionVersion, version_id)
    if version is None:
        raise NotFound('Versão da questão não encontrada.')
    exam = layout.source_of(db, version)
    return {
        'published': version.content,
        'source_url': exam.source.get('url') if exam else None,
        'page': version.content['page'],
        'proposals': [layout.proposal_data(p) for p in layout.proposals_for(db, version_id)],
    }


@router.post('/proposals/{proposal_id}/review')
def review(proposal_id: str, payload: LayoutReview, user: AdminUser, db: SessionDep):
    proposal = layout.review(db, proposal_id, payload.action, payload.reason, payload.compared_with_source, user.id)
    return layout.proposal_data(proposal)
