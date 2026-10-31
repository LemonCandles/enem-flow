"""Prepare any exam JSON/PDF as native draft content plus a review report."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.preparation import prepare_exam


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input',type=Path,help='JSON no contrato de prova, nativo ou com regiões page/bbox')
    source.add_argument('--manifest',type=Path,help='Metadados, áreas e configuração de layout para um PDF novo')
    parser.add_argument('--pdf',type=Path,help='PDF associado; obrigatório com --manifest')
    parser.add_argument('--answer-key',type=Path,help='PDF do gabarito (ou answers no manifesto com hash da fonte)')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--assets-root',type=Path,default=ROOT/'data/assets')
    parser.add_argument('--force',action='store_true',help='Substituir JSON/relatório de saída existentes')
    parser.add_argument('--strict',action='store_true',help='Retornar código 2 quando houver qualquer aviso de revisão')
    args=parser.parse_args()
    report_path=args.report or args.output.with_suffix('.report.json')
    sources=[p.resolve() for p in [args.input,args.manifest,args.pdf,args.answer_key] if p]
    for path in [args.output,report_path]:
        if path.suffix.lower()!='.json' or path.resolve() in sources: parser.error('Saídas devem ser JSON e não podem substituir entradas.')
        if path.exists() and not args.force: parser.error(f'{path} já existe; escolha outra saída ou use --force.')
    if args.output.resolve()==report_path.resolve(): parser.error('Prova e relatório precisam de caminhos diferentes.')
    try:
        data=json.loads((args.input or args.manifest).read_text())
        if args.manifest:
            if not args.pdf: parser.error('--manifest exige --pdf')
            from scripts.exam_pdf import from_manifest
            data=from_manifest(data,args.pdf,args.answer_key)
        # Validate identifiers/paths before producing any figure assets.
        from backend.app.schemas import ExamImport
        data=ExamImport.model_validate(data).model_dump()
        if args.pdf:
            from scripts.exam_pdf import extract_exam
            data=extract_exam(data,args.pdf,args.assets_root)
        prepared,report=prepare_exam(data)
        # Use the same KaTeX validator as CI, with the actual output path.
        import subprocess
        validator=ROOT/'frontend/scripts/validate-latex.cjs'
        checked=subprocess.run(['node',str(validator),'--stdin'],input=prepared.model_dump_json(),capture_output=True,text=True)
        if checked.returncode: raise ValueError('Validação LaTeX falhou: '+checked.stderr.strip())
        report['latex_validation']=checked.stdout.strip()
        missing=[]
        for q in prepared.questions:
            c=q.content.model_dump()
            assets=c['images']+[a['image'] for a in c['alternatives'] if a.get('image')]+[b['asset'] for b in c['blocks'] if b['type']=='image']
            for asset in assets:
                target=(args.assets_root/asset['path'].removeprefix('/assets/')).resolve()
                if not target.is_relative_to(args.assets_root.resolve()) or not target.is_file():
                    missing.append({'question_id':q.question_id,'path':asset['path']})
        report['missing_assets']=missing
        report['errors']+=len(missing)
        for path,value in [(args.output,prepared.model_dump()),(report_path,report)]:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(f"{len(prepared.questions)} questões; {report['changes']} operações; {report['warnings']} avisos; {report['errors']} pendências bloqueantes. Rascunho: {args.output}. Relatório: {report_path}.")
        return 2 if report['errors'] or (args.strict and report['warnings']) else 0
    except (ValueError,OSError,KeyError) as error:
        parser.exit(2,f'Preparação interrompida: {error}\n')


if __name__=='__main__': raise SystemExit(main())
