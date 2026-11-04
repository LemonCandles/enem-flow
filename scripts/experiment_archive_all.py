"""Aplica métodos da etapa 3 a todas as questões publicadas; não publica propostas."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.archive_full import inventory, run

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, default=ROOT / 'enem-flow.db')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument(
        '--model',
        type=Path,
        help='classification-model.json de uma execução completa, junto dos relatórios/modelo de layout.',
    )
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--inventory-only', action='store_true')
    p.add_argument('--skip-inventory', action='store_true')
    p.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retoma falhas e preserva resultados completos com versões e modelo idênticos, registrando a proveniência anterior.',
    )
    args = p.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'tmp'):
        p.error('Saída deve ficar em tmp/.')
    if not args.inventory_only and args.model is None:
        p.error('--model é obrigatório para aplicar os métodos selecionados.')
    if args.inventory_only and args.skip_inventory:
        p.error('Escolha uma operação de inventário.')
    if not args.skip_inventory:
        inventory(args.output)
    if not args.inventory_only:
        run(args.database, args.output, args.model, args.workers, args.retry_failed)
