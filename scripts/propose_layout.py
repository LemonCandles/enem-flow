#!/usr/bin/env python3
"""Gera uma proposta de layout para uma versão instalada, no contrato aceito pela curadoria.

Usa a localização geométrica de `experiments/layout.py` nas regiões já registradas na
extração da questão, recorta as figuras em `data/assets/<prova>/layout/` e grava o JSON.
A proposta não altera nada: envie o arquivo em Curadoria → Layout proposto, compare com o
caderno original e aprove ou rejeite. Fórmulas detectadas viram texto, pois a geometria não
as reconstrói em LaTeX; transcreva-as antes de enviar, se for o caso.

    .venv/bin/python scripts/propose_layout.py enem-2025-regular-dia2-caderno-7-azul-q160:2 \
        --output tmp/layout/q160.json
"""

import _bootstrap  # noqa: F401
import argparse
import hashlib
import json
from pathlib import Path
import re

import pymupdf

from backend.app.core.db import SessionLocal
from backend.app.models import QuestionVersion
from backend.app.services.layout import source_of
from backend.app.services.layout_adapter import version_fingerprint
from experiments.layout import assemble, extract_candidates
from ingestion.archive import local_source
from ingestion.exam_pdf.text import LIST_BULLET

ROOT = Path(__file__).resolve().parents[1]
BULLET = re.compile(LIST_BULLET.pattern.removeprefix('^'))


def source_pdf(url, sha256):
    path = local_source(url, sha256)
    if path is None:
        raise SystemExit('PDF original ausente ou com hash diferente; sincronize o acervo antes de propor.')
    return path


def propose(version_id):
    with SessionLocal() as db:
        version = db.get(QuestionVersion, version_id)
        if version is None:
            raise SystemExit(f'Versão não encontrada: {version_id}')
        exam = source_of(db, version)
        if exam is None:
            raise SystemExit('A versão não pertence a nenhuma prova instalada.')
        content, source = version.content, exam.source
        exam_id = exam.id
    pdf = source_pdf(source['url'], source['sha256'])
    with pymupdf.open(pdf) as doc:
        # Column regions may reach a little past the page edge; the extractor works inside the page.
        regions = [
            {'page': r['page'], 'bbox': list(pymupdf.Rect(r['bbox']) & doc[r['page'] - 1].rect)}
            for r in (content.get('layout') or {}).get('blocks', [])
        ]
    if not regions:
        raise SystemExit('A questão não tem regiões de extração registradas.')
    candidates, tables = extract_candidates(pdf, regions, enhanced=True)
    assembled = assemble(candidates, 'geometry')
    target = ROOT / 'data/assets' / exam_id / 'layout'
    target.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf) as doc:
        for block in assembled['blocks']:
            # Same cleanup as the extractor: list numbers lose bullets without a character map.
            block['text'] = BULLET.sub(r'\1 ', block['text'])
            if block['type'] == 'math':
                block['type'] = 'paragraph'
            if block['type'] != 'image':
                continue
            pixmap = doc[block['page'] - 1].get_pixmap(clip=pymupdf.Rect(block['bbox']), dpi=200)
            data = pixmap.tobytes('png')
            name = hashlib.sha256(data).hexdigest()[:16] + '.png'
            (target / name).write_bytes(data)
            block['asset'] = f'/assets/{exam_id}/layout/{name}'
    return {
        'schema_version': '1.0',
        'question_version': version_id,
        'source_sha256': source['sha256'],
        'content_sha256': version_fingerprint(content),
        'regions': regions,
        'blocks': assembled['blocks'],
        'links': assembled['links'],
        'table_structures': tables,
        'origin': {'method': 'geometry', 'script': 'propose_layout.py', 'experiment': 'data-ai-v1'},
        'review_status': 'proposed',
        'needs_review': True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('version', help='Identificador da versão, como prova-q12:1')
    parser.add_argument('--output', type=Path, help='Arquivo de saída; sem ele, imprime o JSON.')
    args = parser.parse_args()
    text = json.dumps(propose(args.version), ensure_ascii=False, indent=1)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')
        print(f'Proposta gravada em {args.output}')
    else:
        print(text)


if __name__ == '__main__':
    main()
