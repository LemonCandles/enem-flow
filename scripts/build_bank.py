#!/usr/bin/env python3
"""Indexa questões de todos os PDFs baixados, sem aprovar a extração automática.

Os JSONs derivados mantêm texto, geometria e ocorrências. A identidade estrita
agrupa transcrições iguais; semelhança nunca equivale a aprovação ou gabarito.
"""

import _bootstrap  # noqa: F401
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path

from ingestion.archive import CATALOG, sha, write_json
from ingestion.bank import OUTPUT, VERSION, extract

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / 'data/bank'


def build(workers=2):
    catalog = json.loads(CATALOG.read_text())
    originals = [
        r
        for r in catalog['files']
        if r['role'] == 'prova' and r['status'] == 'downloaded' and r['path'].endswith(('.pdf', '.txt'))
    ]
    # Repeated identical links in the HTML are one source occurrence.
    originals = list({r['path']: r for r in originals}.values())
    sources = []
    canonical = {}
    occurrences = []
    raw = defaultdict(list)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extract, r): r for r in originals}
        for future in as_completed(futures):
            result = future.result()
            r = futures[future]
            raw[r['year']].append(result)
            sources.append({k: v for k, v in result.items() if k != 'questions'})
            for q in result['questions']:
                key = q['canonical_id']
                canonical.setdefault(
                    key, dict(id=key, identity_sha256=q['identity_sha256'], method=q['identity_method'], occurrences=[])
                )['occurrences'].append(q['occurrence_id'])
                occurrences.append(
                    {k: v for k, v in q.items() if k not in ('text', 'regions', 'issues')}
                    | dict(
                        source_id=r['id'],
                        year=r['year'],
                        application=r['application'],
                        day=r['day'],
                        booklet=r['booklet'],
                        path=str((OUTPUT / str(r['year']) / (r['id'] + '.json')).relative_to(ROOT)),
                    )
                )
            if len(sources) % 20 == 0:
                print(f'{len(sources)}/{len(originals)} PDFs indexados', flush=True)
    sources.sort(key=lambda r: (r['year'], r['source_path']))
    occurrences.sort(key=lambda r: (r['year'], r['source_id'], r['number'], r['occurrence_id']))
    from scripts.link_curated_bank import link

    canonical, published_links = link(sources, occurrences, canonical)
    for row in canonical.values():
        row['occurrences'].sort()
    # Deterministic compressed JSON preserves the complete text bank in Git,
    # without committing gigabytes of recoverable PDF binaries or cache files.
    raw_files = []
    for year, documents in sorted(raw.items()):
        target = BANK / 'raw' / f'{year}.json.gz'
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            sorted(documents, key=lambda r: r['source_id']), ensure_ascii=False, separators=(',', ':')
        ).encode()
        target.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
        raw_files.append(dict(year=year, path=str(target.relative_to(ROOT)), sha256=sha(target)))
    summary = dict(
        adapter=VERSION,
        years=sorted({r['year'] for r in sources}),
        pdfs=sum(r['source_path'].endswith('.pdf') for r in sources),
        txts=sum(r['source_path'].endswith('.txt') for r in sources),
        occurrences=len(occurrences),
        canonical_questions=len(canonical),
        duplicate_occurrences=len(occurrences) - len(canonical),
        sources_with_issues=sum(bool(r['issues']) for r in sources),
        published_by_this_command=0,
        raw_files=raw_files,
        by_year=[
            dict(
                year=y, pdfs=sum(r['year'] == y for r in sources), occurrences=sum(r['year'] == y for r in occurrences)
            )
            for y in sorted({r['year'] for r in sources})
        ],
    )
    write_json(BANK / 'coverage.json', summary)
    write_json(BANK / 'published-links.json', published_links)
    write_json(BANK / 'sources.json', sources)
    write_json(BANK / 'canonical.json', sorted(canonical.values(), key=lambda r: r['id']))
    write_json(BANK / 'occurrences.json', occurrences)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    build(parser.parse_args().workers)
