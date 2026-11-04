"""Finalization events shared by exams and diagnostics."""

import copy

from ..models import LearningEvent


def record_learning_events(db, origin, mode):
    for position, item in enumerate(origin.items, 1):
        content = item['content']
        answer = origin.answers.get(item['id'])
        db.add(
            LearningEvent(
                user_id=origin.user_id,
                run_id=origin.id if mode == 'exam' else None,
                session_id=origin.id if mode == 'diagnostic' else None,
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
                    'help_used': False,
                    'labels': copy.deepcopy(content['labels']),
                },
            )
        )
