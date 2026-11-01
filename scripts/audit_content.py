"""Audit the active booklet against its declared source and official answer key."""
import hashlib
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.content import validate_assets
from backend.app.schemas import ExamImport


def audit(path=None):
    import pymupdf
    payload = ExamImport.model_validate_json((path or ROOT/'data/enem-2024-dia2-azul.json').read_text())
    catalog=json.loads((ROOT/'data/sources/catalogo/acervo.json').read_text())
    def locate(url,digest):
        matches=[ROOT/'data/sources'/r['path'] for r in catalog['files'] if r['url']==url and r.get('sha256')==digest]
        existing=next((p for p in matches if p.is_file()),None)
        if not existing:raise ValueError(f'Fonte declarada não encontrada no catálogo local: {url}')
        return existing
    source=locate(payload.source.url,payload.source.sha256)
    key=locate(payload.source.answer_key_url,payload.source.answer_key_sha256)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == payload.source.sha256
    assert hashlib.sha256(key.read_bytes()).hexdigest() == payload.source.answer_key_sha256
    with pymupdf.open(key) as doc:
        text = '\n'.join(p.get_text() for p in doc)
    answers = {int(n): None if a.upper().startswith('ANULAD') else a.upper() for n,a in re.findall(r'\b(\d{1,3})\s+(ANULAD[AO]|[ABCDE])\b',text,re.I)}
    numbers={q.content.number for q in payload.questions}
    assert numbers <= set(answers)
    if payload.kind=='complete':assert set(answers)==numbers
    assert len(payload.questions) == payload.expected_items
    figures = tables = math = 0
    for q in payload.questions:
        c=q.content
        assert c.correct_answer == answers[c.number], c.number
        assert c.annulled == (answers[c.number] is None), c.number
        assert not c.original_layout and c.blocks and not c.images, c.number
        assert [a.letter for a in c.alternatives] == list('ABCDE')
        validate_assets(c.model_dump())
        figures += sum(b.type == 'image' for b in c.blocks)
        tables += sum(b.type == 'table' for b in c.blocks)
        math += sum(b.type == 'math' for b in c.blocks)
        for b in c.blocks:
            if b.type == 'image':
                assert b.asset.alt.strip()
                with pymupdf.open(ROOT/'data'/b.asset.path.lstrip('/')) as image:
                    assert image[0].rect.width > 0
    return {'questions':len(payload.questions),'valid_answers':sum(a is not None for a in answers.values()),
            'annulled':[n for n,a in answers.items() if a is None], 'figures':figures,'tables':tables,'math_blocks':math,
            'source_hashes':'verified','answer_key':'verified','assets':'verified','review':'technical_integrity_only'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--exam',type=Path)
    print(json.dumps(audit(parser.parse_args().exam),ensure_ascii=False,indent=2))
