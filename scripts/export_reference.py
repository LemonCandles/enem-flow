"""Exporta referência temática com grupos canônicos e hashes imutáveis."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.installers.curated import classified
from backend.app.services.identity import signatures
from backend.app.services.presentation import content_fingerprint


def build():
    manifest=json.loads((ROOT/'data/catalog/manifest.json').read_text());items=[];ids=set()
    for entry in manifest['exams']:
        payload=classified(json.loads((ROOT/entry['path']).read_text()))
        for q in payload.questions:
            c=q.content.model_dump()
            if c['area']!='Matemática' or c['annulled']:continue
            signature,_=signatures(c);key='enem-'+signature[:32]
            if key in ids:raise ValueError('Duplicata canônica no conjunto de referência.')
            ids.add(key)
            items.append(dict(canonical_id=key,split_group=key,question_id=q.question_id,exam_id=payload.id,
                number=c['number'],page=c['page'],source_sha256=payload.source.sha256,
                content_sha256=content_fingerprint(c),discipline=c['labels']['discipline'],themes=c['labels']['themes'],
                taxonomy_version=c['labels']['taxonomy_version'],review_status='technical_curation',independent_review=False))
    result=dict(version='adaptive-math-reference-v1',purpose='Referência exploratória de temas; não é benchmark pedagógico independente ou calibração TRI.',
                taxonomy_version='enem-content-v1',eligible_items=len(items),
                excluded=[dict(question_id='enem-2023-dia2-azul-q164',reason='Anulada no gabarito oficial.')],
                split_policy='Separar desenvolvimento/teste por split_group após segunda anotação e adjudicação. Nenhum split de avaliação foi declarado aqui.',
                theme_counts=dict(sorted(Counter(t for item in items for t in item['themes']).items())),items=items)
    return result


if __name__=='__main__':
    target=ROOT/'data/datasets/adaptive-math-reference-v1.json';target.parent.mkdir(exist_ok=True)
    data=build();target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'{data["eligible_items"]} questões únicas em {len(data["theme_counts"])} temas; nenhuma habilidade proposta publicada como rótulo.')
