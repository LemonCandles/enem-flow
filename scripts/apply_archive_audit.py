"""Valida/aplica um plano de correções técnicas; sem --apply faz rollback integral."""

import _bootstrap  # noqa: F401
import argparse
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from backend.app.installers.audited import apply_audited
from experiments.common import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def sync_derived(database, plan):
    from collections import Counter, defaultdict
    from experiments.archive_audit import installed_exams
    from backend.app.installers.audited import content_hash
    from backend.app.preparation import blocking_issues
    from backend.app.schemas import QuestionContent
    from backend.app.services.presentation import content_fingerprint

    grouped = defaultdict(dict)
    for row in plan['changes']:
        grouped[row['exam_id']][row['question_id']] = row
    paths = []
    for exam_id, changes in grouped.items():
        path = ROOT / 'data/derived/exams' / f'{exam_id}.json'
        if not path.exists():
            continue
        data = read_json(path)
        for question in data['questions']:
            row = changes.get(question['question_id'])
            if row:
                current = content_hash(question['content'])
                if current not in {row['previous_sha256'], content_hash(row['content'])}:
                    raise ValueError('Cache derivado possui edição própria; não foi sobrescrito: ' + str(path))
                question['content'] = row['content']
        paths.append((path, data))
    # Validate every candidate cache before replacing any of them.
    for path, data in paths:
        write_json(path, data)
        rows = []
        for question in data['questions']:
            c = QuestionContent.model_validate(question['content']).model_dump()
            metadata = c['layout']['preparation']
            rows.append(
                {
                    'question_id': question['question_id'],
                    'number': c['number'],
                    **metadata,
                    'issues': [i for i in metadata['issues'] if i.get('severity') != 'error'] + blocking_issues(c),
                }
            )
        issues = Counter(i['severity'] for row in rows for i in row['issues'])
        write_json(
            path.with_suffix('.report.json'),
            {
                'version': 'generic-v1',
                'exam_id': data['id'],
                'questions': rows,
                'changes': sum(len(row['changes']) for row in rows),
                'errors': issues['error'],
                'warnings': issues['warning'],
            },
        )
    identities = {
        q['question_id']: {
            'canonical_id': q['canonical_id'],
            'content_sha256': content_fingerprint(q['content']),
            'source_sha256': exam['source']['sha256'],
        }
        for exam in installed_exams(database)
        for q in exam['items']
    }
    write_json(ROOT / 'data/derived/exams/identities.json', {'schema_version': '1.0', 'items': identities})
    from scripts.build_archive_exams import from_report

    summary = ROOT / 'data/derived/exams/resumo.json'
    if summary.exists():
        rows = read_json(summary)
        write_json(
            summary,
            [from_report(row['id']) if row['id'] in grouped and row.get('status') == 'gerada' else row for row in rows],
        )
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--database', type=Path, default=ROOT / 'enem-flow.db')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument(
        '--sync-derived',
        action='store_true',
        help='Após aplicar, sincroniza caches derivados e identidades estáveis; exige a base de uso.',
    )
    args = parser.parse_args()
    if args.sync_derived and not args.apply:
        parser.error('--sync-derived exige --apply.')
    if args.sync_derived and args.database.resolve() != ROOT / 'enem-flow.db':
        parser.error('Sincronize os caches somente depois de aplicar na base de uso.')
    if not args.database.is_file():
        parser.error('Banco inexistente.')
    engine = create_engine('sqlite:///' + str(args.database.resolve()))

    @event.listens_for(engine, 'connect')
    def configure(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    with Session(engine) as db:
        try:
            result = apply_audited(db, read_json(args.plan))
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise
    engine.dispose()
    result['applied'] = args.apply
    if args.sync_derived:
        result['derived_exams_updated'] = sync_derived(args.database, read_json(args.plan))
    write_json(args.plan.with_suffix('.applied.json' if args.apply else '.validated.json'), result)
    print({k: v for k, v in result.items() if k != 'versions'})


if __name__ == '__main__':
    main()
