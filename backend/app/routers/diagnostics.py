"""Owned fixed diagnostic sessions; feedback is available only at finish."""

import secrets
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..dependencies import CurrentUser, SessionDep
from ..models import DiagnosticSession, Exam
from ..schemas import Answer
from ..schemas.diagnostics import StartDiagnostic
from ..services import attempts
from ..services.attempts import DIAGNOSTIC
from ..services.content import public_question
from ..services.diagnostics import eligible_items, identity, select_items, user_origins

router = APIRouter(tags=['diagnóstico'])


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


@router.post('/sessions', status_code=201)
def start(payload: StartDiagnostic, user: CurrentUser, db: SessionDep):
    def build():
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
        return DiagnosticSession(
            user_id=user.id,
            start_key=payload.idempotency_key,
            objective=payload.objective,
            area=payload.area,
            available_minutes=payload.available_minutes,
            selection=selection,
            items=[dict(i, source_url=sources[i['id']]) for i in items],
            answers={},
        )

    def same_request(session):
        requested = (payload.objective, payload.area, payload.available_minutes)
        return (session.objective, session.area, session.available_minutes) == requested

    return session_data(attempts.start(db, DIAGNOSTIC, user.id, payload.idempotency_key, same_request, build))


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
    return session_data(attempts.owned(db, DIAGNOSTIC, session_id, user.id))


@router.put('/sessions/{session_id}/answers/{item_id}')
def answer(session_id: str, item_id: str, payload: Answer, user: CurrentUser, db: SessionDep):
    return attempts.save_answer(db, DIAGNOSTIC, session_id, item_id, payload.choice, user.id)


@router.post('/sessions/{session_id}/finish')
def finish(session_id: str, user: CurrentUser, db: SessionDep):
    return session_data(attempts.finish(db, DIAGNOSTIC, session_id, user.id))
