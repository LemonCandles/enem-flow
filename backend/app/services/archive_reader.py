"""Read-only archive access; extracted text cannot publish itself."""
from collections import Counter
from functools import lru_cache
import gzip
import json
from pathlib import Path

from ..core.config import ROOT


@lru_cache(maxsize=12)
def _read(path,mtime):
    p=Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())


def read(path,default):
    return _read(str(path),path.stat().st_mtime_ns) if path.exists() else default


def inventory(year=None,application=None):
    catalog=read(ROOT/'data/sources/catalogo/acervo.json',{'files':[]})
    coverage=read(ROOT/'data/bank/coverage.json',{})
    files=catalog['files']
    selected=[r for r in files if (year is None or r['year']==year) and (not application or r['application']==application)]
    return dict(years=sorted({r['year'] for r in files},reverse=True),applications=sorted({r['application'] for r in files if year is None or r['year']==year}),
                references=len(selected),downloaded=sum(r['status']=='downloaded' for r in selected),
                unavailable=[{k:r.get(k) for k in ('year','application','official_title','label','url','error')} for r in selected if r['status']=='error'],
                formats=dict(Counter(r['variant'] for r in selected if r['role']=='prova')),
                coverage=coverage,files=[{k:r.get(k) for k in ('id','year','application','day','booklet','variant','role','status','url','path','sha256','label')} for r in selected])


def questions(year,application=None,number=None,offset=0,limit=25):
    rows=read(ROOT/'data/bank/occurrences.json',[])
    selected=[r for r in rows if r['year']==year and (not application or r['application']==application) and (number is None or r['number']==number)]
    return dict(total=len(selected),offset=offset,limit=limit,items=selected[offset:offset+limit])


def detail(occurrence_id):
    rows=read(ROOT/'data/bank/occurrences.json',[])
    occurrence=next((r for r in rows if r['occurrence_id']==occurrence_id),None)
    if not occurrence:return None
    documents=read(ROOT/'data/bank/raw'/f'{occurrence["year"]}.json.gz',[])
    document=next((d for d in documents if d['source_id']==occurrence['source_id']),None)
    if not document:
        # Local resumable cache, before the deterministic bank has been packaged.
        path=ROOT/occurrence['path']
        if path.resolve().is_relative_to((ROOT/'data/derived/archive').resolve()):document=read(path,None)
    if not document:return None
    question=next((q for q in document['questions'] if q['occurrence_id']==occurrence_id),None)
    if not question:return None
    source=next((r for r in read(ROOT/'data/sources/catalogo/acervo.json',{'files':[]})['files'] if r['id']==occurrence['source_id']),{})
    matches=[{k:r[k] for k in ('occurrence_id','year','application','booklet','number')} for r in rows if r['canonical_id']==occurrence['canonical_id']]
    return {**question,'canonical_id':occurrence['canonical_id'],'source':source,'occurrences':matches,'source_issues':document['issues']}
