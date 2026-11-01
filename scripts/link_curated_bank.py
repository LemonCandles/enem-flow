"""Vincula ocorrências do acervo às identidades do catálogo conferido."""
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.catalog import classified
from backend.app.identity import signatures


def link(sources,occurrences,canonical):
    by_sha=defaultdict(set)
    for source in sources:by_sha[source['source_sha256']].add(source['source_id'])
    by_source_number=defaultdict(list)
    for row in occurrences:by_source_number[(row['source_id'],row['number'])].append(row)
    manifest=json.loads((ROOT/'data/catalog/manifest.json').read_text());aliases={};links=[]
    linked=ROOT/'data/catalog/occurrences-v1.json'
    booklets={q['question_id']:[(o['source_sha256'],o['number']) for o in q['occurrences']] for q in (json.loads(linked.read_text())['questions'] if linked.is_file() else [])}
    approved={}
    for entry in manifest['exams']:
        payload=classified(json.loads((ROOT/entry['path']).read_text()))
        for q in payload.questions:
            digest,_=signatures(q.content.model_dump());target='enem-'+digest[:32];approved[target]=digest
            # Same item in the other colors, when the booklet links were verified.
            places=booklets.get(q.question_id) or [(payload.source.sha256,q.content.number)]
            matches=[row for sha,number in places for sid in by_sha[sha] for row in by_source_number[(sid,number)]]
            for row in matches:
                old=row['canonical_id']
                if old in aliases and aliases[old]!=target:raise ValueError('Identidade de extração conflita com duas questões curadas; reveja o agrupamento.')
                aliases[old]=target
            links.append(dict(question_id=q.question_id,canonical_id=target,source_sha256=payload.source.sha256,number=q.content.number,occurrences=[r['occurrence_id'] for r in matches]))
    grouped={}
    for row in occurrences:
        old=row['canonical_id'];target=aliases.get(old,old)
        row['extraction_identity_id']=old;row['canonical_id']=target
        grouped.setdefault(target,dict(id=target,identity_sha256=approved.get(target,canonical[old]['identity_sha256']),method='source-curated-v1' if target in approved else canonical[old]['method'],status='curated' if target in approved else 'extracted_unreviewed',occurrences=[]))['occurrences'].append(row['occurrence_id'])
    for row in grouped.values():row['occurrences'].sort()
    return grouped,links
