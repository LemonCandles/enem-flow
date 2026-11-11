#!/usr/bin/env python3
"""Inventário e espelho retomável do acervo público do Inep (sem URLs inventadas)."""

import _bootstrap  # noqa: F401
import argparse
import json
from pathlib import Path
import ssl

from ingestion import archive
from ingestion.archive import CATALOG, SOURCE_ROOT, download, inventory, sha, summary, sync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'sync', 'audit', 'reference'])
    parser.add_argument(
        '--refresh', action='store_true', help='Reconsultar páginas; nunca sobrescrever PDFs divergentes.'
    )
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=4)
    parser.add_argument('--years', type=int, nargs='+')
    parser.add_argument(
        '--ca-file', type=Path, help='Intermediário TLS validado; mantém os certificados de confiança do sistema.'
    )
    args = parser.parse_args()
    if args.ca_file:
        # `fetch` lê o contexto do módulo ingestion.archive; um global deste script não teria efeito.
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=str(args.ca_file))
        archive.TLS_CONTEXT = context
    catalog = inventory(args.refresh) if args.command == 'inventory' else json.loads(CATALOG.read_text())
    if args.command == 'reference':
        # The official matrix is a local, recoverable original; its immutable
        # manifest and structured definitions remain versioned.
        source = json.loads((SOURCE_ROOT / 'referencias/manifesto.json').read_text())
        result = download(source, {})
        print(
            json.dumps(
                {key: result.get(key) for key in ('path', 'status', 'sha256', 'bytes', 'error')}, ensure_ascii=False
            )
        )
        if result['status'] != 'downloaded':
            raise SystemExit(2)
    elif args.command == 'sync':
        sync(catalog, args.workers, args.years)
        if any(r['status'] == 'error' for r in catalog['files'] if not args.years or r['year'] in args.years):
            raise SystemExit(2)
    elif args.command == 'audit':
        problems = []
        for r in catalog['files']:
            p = SOURCE_ROOT / r['path']
            if r['status'] != 'downloaded' or not p.is_file() or sha(p) != r.get('sha256'):
                problems.append(r['path'])
        print(json.dumps({'summary': summary(catalog), 'problems': problems}, ensure_ascii=False, indent=2))
        if problems:
            raise SystemExit(2)
    else:
        print(json.dumps(summary(catalog), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
