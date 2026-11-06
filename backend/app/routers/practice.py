"""Adaptive practice: a fixed session chosen from the student's evidence, with its reasons."""

import copy
import secrets
import time
from collections import Counter

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..dependencies import CurrentUser, SessionDep
from ..models import DiagnosticSession, LearningEvent, RecommendationEvent
from ..schemas import Answer
from ..schemas.practice import StartPractice
from ..services import attempts
from ..services.adaptive import ADAPTIVE_V1, DEFAULT_POLICY, PolicyInput, filter_pool, recommend
from ..services.attempts import PRACTICE
from ..services.diagnostics import eligible_items, identity, session_data, source_urls, user_origins
from ..services.knowledge import reconstruct

router = APIRouter(tags=['prática adaptativa'])


def provisional_difficulty(db):
    """Observed success per item, across students; below the minimum it stays unknown."""
    counts = {}
    for correct, context in db.execute(
        select(LearningEvent.correct, LearningEvent.context).where(
            LearningEvent.correct.is_not(None), LearningEvent.answer.is_not(None)
        )
    ):
        key = context.get('canonical_id')
        if key and context.get('help_used') is False:
            row = counts.setdefault(key, [0, 0])
            row[0] += int(correct)
            row[1] += 1
    return {
        key: {'success_rate': (1 + hits) / (2 + total), 'responses': total}
        for key, (hits, total) in counts.items()
        if total >= ADAPTIVE_V1['difficulty_min_responses']
    }


def exposure_of(db, user_id):
    """How many attempts of this student showed each item, finished or not."""
    return Counter(identity(item) for origin in user_origins(db, user_id) for item in origin.items)


@router.get('/practice-options')
def options(user: CurrentUser, db: SessionDep, available_minutes: int = Query(15, ge=3, le=180)):
    pool = eligible_items(db)
    exposures = exposure_of(db, user.id)
    difficulty = provisional_difficulty(db)
    areas = []
    for area in sorted({i['content']['area'] for i in pool}):
        candidates = [i for i in pool if i['content']['area'] == area]
        allowed, _ = filter_pool(
            PolicyInput(candidates, {}, exposures, available_minutes, '', 0, difficulty), ADAPTIVE_V1
        )
        areas.append(
            dict(
                area=area,
                eligible_items=len(allowed),
                exhausted=not allowed,
                themes=dict(Counter(t for i in allowed for t in set(i['content']['labels']['themes']))),
            )
        )
    return {'areas': areas}


@router.post('/practice-sessions', status_code=201)
def start(payload: StartPractice, user: CurrentUser, db: SessionDep):
    entries, built = [], []

    def build():
        pool = [i for i in eligible_items(db) if i['content']['area'] == payload.area]
        if not pool:
            raise HTTPException(422, 'Não há questões elegíveis com temas publicados nesta área.')
        data = PolicyInput(
            pool=pool,
            state=reconstruct(db, user.id),
            exposures=exposure_of(db, user.id),
            minutes=payload.available_minutes,
            seed=secrets.token_hex(16),
            now=time.time(),
            difficulty=provisional_difficulty(db),
        )
        chosen, selection = recommend(data)
        if not chosen:
            raise HTTPException(422, 'Você já praticou as questões disponíveis nesta área o máximo de vezes previsto.')
        entries.extend(chosen)
        sources = source_urls(db)
        items = [
            {
                **copy.deepcopy(e['item']),
                'source_url': sources[e['item']['id']],
                'recommendation': {'function': e['function'], 'reason': e['reason'], 'policy_version': DEFAULT_POLICY},
            }
            for e in chosen
        ]
        session = DiagnosticSession(
            user_id=user.id,
            kind='practice',
            start_key=payload.idempotency_key,
            objective=payload.objective,
            area=payload.area,
            available_minutes=payload.available_minutes,
            selection=selection,
            items=items,
            answers={},
        )
        built.append(session)
        return session

    def same_request(session):
        requested = (payload.objective, payload.area, payload.available_minutes)
        return session.kind == 'practice' and (session.objective, session.area, session.available_minutes) == requested

    session = attempts.start(db, PRACTICE, user.id, payload.idempotency_key, same_request, build)
    # Only the attempt created here gets events: a repeated key or a lost race already has them.
    for entry in entries if built and session is built[0] else []:
        db.add(
            RecommendationEvent(
                user_id=user.id,
                session_id=session.id,
                position=entry['position'],
                item_id=entry['item']['id'],
                policy_version=DEFAULT_POLICY,
                function=entry['function'],
                reason=entry['reason'],
                components=entry['components'],
                candidates_total=entry['candidates_total'],
                candidates=entry['candidates'],
            )
        )
    return session_data(session)


@router.get('/practice-sessions/{session_id}')
def get_session(session_id: str, user: CurrentUser, db: SessionDep):
    return session_data(attempts.owned(db, PRACTICE, session_id, user.id))


@router.put('/practice-sessions/{session_id}/answers/{item_id}')
def answer(session_id: str, item_id: str, payload: Answer, user: CurrentUser, db: SessionDep):
    return attempts.save_answer(db, PRACTICE, session_id, item_id, payload.choice, user.id)


@router.post('/practice-sessions/{session_id}/finish')
def finish(session_id: str, user: CurrentUser, db: SessionDep):
    return session_data(attempts.finish(db, PRACTICE, session_id, user.id))


def event_data(event, include_candidates=False):
    data = {
        'session_id': event.session_id,
        'position': event.position,
        'item_id': event.item_id,
        'policy_version': event.policy_version,
        'function': event.function,
        'reason': event.reason,
        'components': event.components,
        'candidates_total': event.candidates_total,
        'created_at': event.created_at,
    }
    if include_candidates:
        data['candidates'] = event.candidates
    return data


@router.get('/practice-sessions/{session_id}/recommendations')
def session_recommendations(session_id: str, user: CurrentUser, db: SessionDep):
    """The full audit of a session: each choice, its priority and the candidates compared."""
    session = attempts.owned(db, PRACTICE, session_id, user.id)
    events = db.scalars(
        select(RecommendationEvent)
        .where(RecommendationEvent.session_id == session.id)
        .order_by(RecommendationEvent.position)
    )
    return {'selection': session.selection, 'recommendations': [event_data(e, True) for e in events]}


@router.get('/me/recommendations')
def my_recommendations(user: CurrentUser, db: SessionDep):
    events = db.scalars(
        select(RecommendationEvent)
        .where(RecommendationEvent.user_id == user.id)
        .order_by(RecommendationEvent.created_at, RecommendationEvent.position)
    )
    return [event_data(e) for e in events]
