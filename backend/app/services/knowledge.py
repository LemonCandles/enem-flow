"""Deterministic student state, reconstructed from finalized events and snapshots."""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from ..models import DiagnosticSession, LearningEvent
from .diagnostics import eligible_items, identity, user_origins

ESTIMATOR = {
    'version': 'beta-first-independent-v1',
    'prior_alpha': 1,
    'prior_beta': 1,
    'minimum_evidence': 5,
    'recent_limit': 20,
    'independence': 'first_answer_without_help_per_canonical_identity',
}


def groups_for(area, labels):
    namespace = (area, labels.get('discipline'), labels.get('taxonomy_version', 'manual-v1'))
    return [('theme', *namespace, theme) for theme in sorted(set(labels.get('themes', [])))] + [
        ('skill', area, None, 'official-enem', skill) for skill in sorted(set(labels.get('skills', [])))
    ]


def new_group(key):
    kind, area, discipline, taxonomy, name = key
    return {
        'kind': kind,
        'area': area,
        'discipline': discipline,
        'taxonomy_version': taxonomy,
        'name': name,
        'attempts': 0,
        'correct': 0,
        'independent_attempts': 0,
        'independent_correct': 0,
        'assisted_attempts': 0,
        'assisted_correct': 0,
        'unknown_help_attempts': 0,
        'repeated_attempts': 0,
        'unanswered': 0,
        'annulled': 0,
        'last_practice': None,
        'recent': [],
        '_seen': set(),
        '_answered': set(),
    }


@dataclass(frozen=True)
class EventFacts:
    canonical: str
    labels: dict
    area: str
    help_used: bool | None


def read_event(event, item):
    """Events 1.0 lack some fields, which come from the snapshot; absent help stays unknown."""
    context = event.context
    return EventFacts(
        canonical=context.get('canonical_id') or identity(item),
        labels=context.get('labels', item['content']['labels']),
        area=context.get('area', item['content']['area']),
        help_used=context.get('help_used'),
    )


def finished_events(db, user_id, origin_map):
    """Events of finished attempts, in the order the evidence was produced."""
    snapshots = {key: {i['id']: i for i in o.items} for key, o in origin_map.items()}
    events = []
    for e in db.scalars(select(LearningEvent).where(LearningEvent.user_id == user_id)):
        mode = 'exam' if e.run_id is not None else 'diagnostic'
        origin_key = (mode, e.run_id or e.session_id)
        origin = origin_map.get(origin_key)
        if origin is None or origin.finished_at is None:
            continue
        item = snapshots[origin_key].get(e.item_id)
        if item is not None:
            events.append((origin.finished_at, mode, origin.id, e.position, e.id, e, item))
    events.sort(key=lambda row: row[:5])
    return events


def count_answer(row, event, facts, finished, mode, origin_id, *, repeated, independent):
    if event.correct is None:
        row['annulled'] += 1
        return
    if event.answer is None:
        row['unanswered'] += 1
        return
    row['attempts'] += 1
    row['correct'] += int(event.correct)
    row['_answered'].add(facts.canonical)
    row['repeated_attempts'] += int(repeated)
    if independent:
        row['independent_attempts'] += 1
        row['independent_correct'] += int(event.correct)
    if facts.help_used is True:
        row['assisted_attempts'] += 1
        row['assisted_correct'] += int(event.correct)
    elif facts.help_used is not False:
        row['unknown_help_attempts'] += 1
    row['last_practice'] = finished
    row['recent'].append(
        {
            'date': finished,
            'origin_id': origin_id,
            'mode': mode,
            'item_id': event.item_id,
            'canonical_id': facts.canonical,
            'correct': event.correct,
            'help_used': facts.help_used,
            'independent': independent,
            'repeated': bool(repeated),
        }
    )
    row['recent'] = row['recent'][-ESTIMATOR['recent_limit'] :]


def reconstruct(db, user_id):
    origins = user_origins(db, user_id)
    origin_map = {('diagnostic' if isinstance(o, DiagnosticSession) else 'exam', o.id): o for o in origins}
    rows = {}

    def group(key):
        if key not in rows:
            rows[key] = new_group(key)
        return rows[key]

    # Include available dimensions with zero evidence, plus historical dimensions.
    for item in eligible_items(db):
        for key in groups_for(item['content']['area'], item['content']['labels']):
            group(key)
    for origin in origins:
        for item in origin.items:
            for key in groups_for(item['content']['area'], item['content']['labels']):
                group(key)['_seen'].add(identity(item))

    independent_seen, answered_seen = set(), set()
    for finished, mode, origin_id, _, _, event, item in finished_events(db, user_id, origin_map):
        facts = read_event(event, item)
        valid = event.correct is not None and event.answer is not None
        repeated = valid and facts.canonical in answered_seen
        independent = valid and facts.help_used is False and facts.canonical not in independent_seen
        for key in groups_for(facts.area, facts.labels):
            count_answer(
                group(key), event, facts, finished, mode, origin_id, repeated=repeated, independent=independent
            )
        if independent:
            independent_seen.add(facts.canonical)
        if valid:
            answered_seen.add(facts.canonical)
    result = defaultdict(list)
    for key in sorted(rows, key=lambda k: tuple(v or '' for v in k)):
        row = rows[key]
        n, correct = row['independent_attempts'], row['independent_correct']
        row.update(
            alpha=1 + correct,
            beta=1 + n - correct,
            estimate=(1 + correct) / (2 + n) if n else None,
            evidence_status='none' if not n else 'low' if n < 5 else 'available',
            seen_items=len(row.pop('_seen')),
            distinct_answered_items=len(row.pop('_answered')),
        )
        result[row.pop('kind')].append(row)
    return {'estimator': ESTIMATOR, 'themes': result['theme'], 'skills': result['skill']}
