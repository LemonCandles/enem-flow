"""Owned fixed diagnostic sessions; feedback is available only at finish."""

import secrets
import time
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ..dependencies import CurrentUser, SessionDep
from ..models import DiagnosticSession, Exam
from ..schemas import Answer
from ..schemas.diagnostics import StartDiagnostic
from ..services.content import public_question
from ..services.diagnostics import eligible_items, identity, select_items, user_origins
from ..services.learning import record_learning_events
from ..services.scoring import score

router = APIRouter(tags=['diagnóstico'])


def owned_session(db, session_id, user_id, lock=False):
    if lock:
        found = db.execute(
            update(DiagnosticSession)
            .where(DiagnosticSession.id == session_id, DiagnosticSession.user_id == user_id)
            .values(started_at=DiagnosticSession.started_at)
        ).rowcount
        if not found:
            raise HTTPException(404, 'Diagnóstico não encontrado.')
    session = db.scalar(
        select(DiagnosticSession)
        .where(DiagnosticSession.id == session_id, DiagnosticSession.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if session is None:
        raise HTTPException(404, 'Diagnóstico não encontrado.')
    return session


def session_data(session, include_items=True):
    result = {
        k: getattr(session, k)
        for k in (
            'id',
            'objective',
            'area',
            'available_minutes',
            'selection',
            'answers',
            'started_at',
            'finished_at',
            'result',
        )
    }
    result['answered'] = sum(v is not None for v in session.answers.values())
    if include_items:
        result['items'] = [
            dict(public_question(i, session.finished_at is not None), source_url=i['source_url']) for i in session.items
        ]
    return result


@router.get('/diagnostic-options')
def options(user: CurrentUser, db: SessionDep):
    areas = defaultdict(Counter)
    pool = eligible_items(db)
    for item in pool:
        areas[item['content']['area']].update(set(item['content']['labels']['themes']))
    return {
        'areas': [
            {
                'area': area,
                'eligible_items': sum(1 for i in pool if i['content']['area'] == area),
                'themes': dict(sorted(themes.items())),
            }
            for area, themes in sorted(areas.items())
        ]
    }


def check_parameters(session, payload):
    if (session.objective, session.area, session.available_minutes) != (
        payload.objective,
        payload.area,
        payload.available_minutes,
    ):
        raise HTTPException(409, 'Esta chave já foi usada para outro diagnóstico.')
    return session_data(session)


@router.post('/sessions', status_code=201)
def start(payload: StartDiagnostic, user: CurrentUser, db: SessionDep):
    previous = db.scalar(
        select(DiagnosticSession).where(
            DiagnosticSession.user_id == user.id, DiagnosticSession.start_key == payload.idempotency_key
        )
    )
    if previous:
        return check_parameters(previous, payload)
    pool = [i for i in eligible_items(db) if i['content']['area'] == payload.area]
    if not pool:
        raise HTTPException(422, 'Não há questões elegíveis com temas publicados nesta área.')
    seen = {identity(i) for origin in user_origins(db, user.id) for i in origin.items}
    items, selection = select_items(pool, seen, payload.available_minutes, secrets.token_hex(16))
    # Each snapshot retains its original source, since a session can mix exams.
    sources = {}
    for exam in db.scalars(select(Exam).where(Exam.status == 'published').order_by(Exam.id)):
        for key in exam.items:
            sources.setdefault(key, exam.source['url'])
    items = [dict(i, source_url=sources[i['id']]) for i in items]
    session = DiagnosticSession(
        user_id=user.id,
        start_key=payload.idempotency_key,
        objective=payload.objective,
        area=payload.area,
        available_minutes=payload.available_minutes,
        selection=selection,
        items=items,
        answers={},
    )
    db.add(session)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        previous = db.scalar(
            select(DiagnosticSession).where(
                DiagnosticSession.user_id == user.id, DiagnosticSession.start_key == payload.idempotency_key
            )
        )
        if previous is None:
            raise
        return check_parameters(previous, payload)
    return session_data(session)


@router.get('/me/sessions')
def history(user: CurrentUser, db: SessionDep):
    return [
        session_data(s, False)
        for s in db.scalars(
            select(DiagnosticSession)
            .where(DiagnosticSession.user_id == user.id)
            .order_by(DiagnosticSession.started_at.desc())
        )
    ]


@router.get('/sessions/{session_id}')
def get_session(session_id: str, user: CurrentUser, db: SessionDep):
    return session_data(owned_session(db, session_id, user.id))


@router.put('/sessions/{session_id}/answers/{item_id}')
def answer(session_id: str, item_id: str, payload: Answer, user: CurrentUser, db: SessionDep):
    session = owned_session(db, session_id, user.id, lock=True)
    if session.finished_at is not None:
        raise HTTPException(409, 'Este diagnóstico já foi finalizado e não aceita alterações.')
    if item_id not in {i['id'] for i in session.items}:
        raise HTTPException(404, 'Questão não pertence a este diagnóstico.')
    session.answers = {**session.answers, item_id: payload.choice}
    return {'answers': session.answers, 'saved_at': time.time()}


@router.post('/sessions/{session_id}/finish')
def finish(session_id: str, user: CurrentUser, db: SessionDep):
    session = owned_session(db, session_id, user.id, lock=True)
    if session.finished_at is None:
        session.finished_at = time.time()
        session.result = score(session.items, session.answers)
        record_learning_events(db, session, 'diagnostic')
        db.flush()
    return session_data(session)
