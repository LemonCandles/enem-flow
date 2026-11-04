"""Confere todo o catálogo instalado com PDFs, dois extratores de gabarito e correção isolada."""

import _bootstrap  # noqa: F401
import argparse
from pathlib import Path

from experiments.archive_audit import run

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'enem-flow.db')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-sources', action='store_true')
    parser.add_argument('--scoring', action='store_true')
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Reutiliza relatórios somente após conferir versões, fontes, recursos e recortes.',
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'tmp') or output == ROOT / 'tmp':
        parser.error('Use uma saída específica em tmp/.')
    run(args.database, output, args.render_sources, args.scoring, args.resume)


if __name__ == '__main__':
    main()
