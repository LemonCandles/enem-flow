"""Versioned, reproducible coverage selection, independent of student estimates."""
import copy
import random
from collections import Counter

from sqlalchemy import select

from ..models import DiagnosticSession, Exam, ExamRun, QuestionVersion
from ..preparation import blocking_issues

SELECTOR_VERSION = 'diagnostic-coverage-v1'


def identity(item):
    return item.get('canonical_id') or item['question_id']


def eligible_items(db):
    keys = set()
    for items in db.scalars(select(Exam.items).where(Exam.status == 'published')):
        keys.update(items)
    latest = {}
    # Chunk to stay below SQL parameter limits even with the full archive.
    keys = sorted(keys)
    for offset in range(0, len(keys), 400):
        for q in db.scalars(select(QuestionVersion).where(QuestionVersion.id.in_(keys[offset:offset + 400]),
                                                       QuestionVersion.status == 'approved')):
            c = q.content
            if c['annulled'] or not c['correct_answer'] or not c['labels']['themes'] or blocking_issues(c):
                continue
            key = q.canonical_id or q.question_id
            old = latest.get(key)
            if old is None or (q.created_at, q.id) > (old.created_at, old.id):
                latest[key] = q
    return [{'id': q.id, 'question_id': q.question_id, 'canonical_id': q.canonical_id,
             'version': q.version, 'content': copy.deepcopy(q.content)} for q in sorted(latest.values(), key=lambda q: q.id)]


def user_origins(db, user_id):
    return [*db.scalars(select(ExamRun).where(ExamRun.user_id == user_id)),
            *db.scalars(select(DiagnosticSession).where(DiagnosticSession.user_id == user_id))]


def select_items(pool, seen, minutes, seed):
    rng = random.Random(seed)
    remaining = sorted(pool, key=lambda i: i['id'])
    rng.shuffle(remaining)
    counts = Counter({t: 0 for i in remaining for t in set(i['content']['labels']['themes'])})
    selected = []
    for _ in range(min(20, minutes // 3, len(remaining))):
        # Coverage first; unseen identities break ties before the seeded order.
        item = min(remaining, key=lambda i: (min(counts[t] for t in i['content']['labels']['themes']),
                                            identity(i) in seen))
        selected.append(item)
        counts.update(set(item['content']['labels']['themes']))
        remaining.remove(item)
    return selected, {'version': SELECTOR_VERSION, 'seed': seed, 'requested_items': min(20, minutes // 3),
                      'selected_items': len(selected), 'eligible_items': len(pool),
                      'themes': dict(sorted(counts.items())),
                      'repeated_items': [i['id'] for i in selected if identity(i) in seen]}
