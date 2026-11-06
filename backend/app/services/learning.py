"""Finalization events shared by exams and diagnostics."""

import copy

from sqlalchemy import select

from ..models import HelpEvent, LearningEvent


def help_snapshot(db, session_id):
    """Delivered help per item of a practice, frozen into its learning events."""
    snapshot = {}
    for event in db.scalars(
        select(HelpEvent)
        .where(HelpEvent.session_id == session_id, HelpEvent.outcome == 'delivered')
        .order_by(HelpEvent.delivered_at)
    ):
        row = snapshot.setdefault(event.item_id, {'levels': [], 'events': [], 'modes': []})
        row['levels'].append(event.level)
        row['events'].append(event.id)
        row['modes'].append(event.mode)
    return snapshot


def recommendation_context(item):
    recommendation = item.get('recommendation')
    if not recommendation:
        return {}
    return {'policy_version': recommendation['policy_version'], 'recommendation': recommendation['function']}


def record_learning_events(db, origin, mode):
    # Only practice offers help; the server derives it from the delivered events.
    assisted = help_snapshot(db, origin.id) if mode == 'practice' else {}
    for position, item in enumerate(origin.items, 1):
        content = item['content']
        answer = origin.answers.get(item['id'])
        db.add(
            LearningEvent(
                user_id=origin.user_id,
                run_id=origin.id if mode == 'exam' else None,
                session_id=origin.id if mode != 'exam' else None,
                item_id=item['id'],
                position=position,
                answer=answer,
                correct=None if content['annulled'] else answer == content['correct_answer'],
                created_at=origin.finished_at,
                context={
                    'schema_version': '2.0',
                    'content_version': item['version'],
                    'canonical_id': item.get('canonical_id') or item['question_id'],
                    'area': content['area'],
                    'mode': mode,
                    'help_used': item['id'] in assisted,
                    **({'help': assisted[item['id']]} if item['id'] in assisted else {}),
                    'labels': copy.deepcopy(content['labels']),
                    **recommendation_context(item),
                },
            )
        )
