"""Produz correções rastreáveis a partir da auditoria das fontes, sem publicar."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.archive_repairs import run

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,default=ROOT/'enem-flow.db')
    p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--retry-failed',action='store_true',help='Retoma apenas provas sem relatório completo, conferindo as versões de todos os candidatos preservados.')
    args=p.parse_args()
    if not args.output.resolve().is_relative_to(ROOT/'tmp'):p.error('Saída deve ficar em tmp/.')
    run(args.database,args.audit,args.output,args.workers,args.retry_failed)
