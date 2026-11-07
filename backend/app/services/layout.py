"""Layout proposals in curation: conversion on arrival, comparison and a reviewed draft on approval."""

import time

from sqlalchemy import select

from ..models import Exam, LayoutProposal, QuestionVersion, Review
from .errors import Conflict, InvalidContent, NotFound
from .layout_adapter import ADAPTER_VERSION, LayoutRejected, convert
from .revisions import revise_question


def source_of(db, version):
    """The source document of the exam that uses this version."""
    for exam in db.scalars(select(Exam).order_by(Exam.id)):
        if version.id in exam.items:
            return exam
    return None


def proposal_data(proposal, version=None):
    data = {
        'id': proposal.id,
        'question_version_id': proposal.question_version_id,
        'adapter_version': proposal.adapter_version,
        'status': proposal.status,
        'errors': proposal.errors,
        'comparison': proposal.comparison,
        'origin': proposal.proposal.get('origin', {}),
        'created_at': proposal.created_at,
        'reviewed_at': proposal.reviewed_at,
        'review_reason': proposal.review_reason,
        'result_version_id': proposal.result_version_id,
        'converted': proposal.converted,
    }
    if version is not None:
        data['published'] = version.content
    return data


def submit(db, payload, user_id):
    """Every proposal is stored: valid ones wait for review, refused ones keep their reasons."""
    version = db.get(QuestionVersion, payload['question_version'])
    if version is None:
        raise NotFound('Versão da questão não encontrada.')
    exam = source_of(db, version)
    proposal = LayoutProposal(
        question_version_id=version.id,
        adapter_version=ADAPTER_VERSION,
        proposal=payload,
        created_by=user_id,
        errors=[],
        comparison={},
    )
    try:
        if exam is None:
            raise LayoutRejected(['A versão não pertence a nenhuma prova; não há fonte para comparar.'])
        proposal.converted, proposal.comparison = convert(payload, version.content, exam.source['sha256'])
        proposal.status = 'proposal'
    except LayoutRejected as rejected:
        proposal.status, proposal.errors = 'invalid', rejected.errors
    db.add(proposal)
    db.flush()
    return proposal


def proposals_for(db, version_id):
    return list(
        db.scalars(
            select(LayoutProposal)
            .where(LayoutProposal.question_version_id == version_id)
            .order_by(LayoutProposal.created_at.desc())
        )
    )


def review(db, proposal_id, action, reason, compared, user_id):
    """Approval converts again against the current version and creates a draft through the edit path."""
    proposal = db.get(LayoutProposal, proposal_id)
    if proposal is None:
        raise NotFound('Proposta de layout não encontrada.')
    if proposal.status != 'proposal':
        raise Conflict('Somente propostas válidas e pendentes podem ser revisadas.')
    if action == 'approve':
        if not compared:
            raise InvalidContent('Compare a proposta com o caderno original antes de aprovar.')
        version = db.get(QuestionVersion, proposal.question_version_id)
        exam = source_of(db, version)
        try:
            content, _ = convert(proposal.proposal, version.content, exam.source['sha256'] if exam else '')
        except LayoutRejected as rejected:
            raise Conflict('A questão ou a fonte mudou desde a proposta: ' + '; '.join(rejected.errors))
        question = revise_question(
            db,
            version,
            content,
            user_id,
            f'{ADAPTER_VERSION}, comparado com o original: {reason}',
            action='layout',
        )
        proposal.status, proposal.result_version_id = 'approved', question.id
    elif action == 'reject':
        proposal.status = 'rejected'
    else:
        raise InvalidContent('Ação desconhecida.')
    proposal.reviewed_by, proposal.reviewed_at, proposal.review_reason = user_id, time.time(), reason
    db.add(Review(user_id=user_id, target_id=proposal.id, action=f'layout_{action}', reason=reason))
    db.flush()
    return proposal
