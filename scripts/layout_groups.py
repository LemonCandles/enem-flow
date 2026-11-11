#!/usr/bin/env python3
"""Agrupa as questões das provas pelo layout, de forma determinística (`pdf-geometry-v4`).

Para cada questão: renderiza as regiões como uma imagem (150 dpi), tipa os blocos pela
geometria e tipografia do PDF, calcula a assinatura estrutural e verifica as invariantes
dos dois canais (vetorial e raster). Questões com a mesma assinatura formam um grupo.

Saídas em `tmp/layout/<execução>/`: a imagem e a sobreposição de cada questão,
`questions.json`, `groups.json` e `index.html` (folha de contato por assinatura). Com
`--reference` ou `--catalog`, rotula cada questão com um tipo de layout (automático se elegível,
senão pela decisão manual registrada em `--decisions`), grava `tipos.html` (folha por tipo, com as
decisões manuais em destaque) e os arquivos pedidos: a referência por questão e o catálogo dos
tipos. Os dois são determinísticos: regerar sem mudança dá os mesmos bytes.

    .venv/bin/python scripts/layout_groups.py                       # provas do perfil local
    .venv/bin/python scripts/layout_groups.py data/derived/exams/x.json --output tmp/layout/x
    .venv/bin/python scripts/layout_groups.py --output tmp/layout/v3 \
        --catalog data/catalog/layout-types.json --reference data/datasets/layout-types-reference-v1.json
"""

import _bootstrap  # noqa: F401
import argparse
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path
import time

import pymupdf

from backend.app.services.presentation import content_fingerprint
from ingestion.archive import local_source
from ingestion.layout import reference
from ingestion.layout.analysis import ADAPTER, UNSUPPORTED, analyze, overlay
from ingestion.layout.render import furniture, save_png

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / 'data/datasets/layout-types-decisions-v1.json'


def profile_exams():
    """Provas do perfil local: as revisadas do catálogo e as automáticas geradas."""
    profile = json.loads((ROOT / 'data/catalog/profiles.json').read_text())['local']
    curated = {
        json.loads((ROOT / entry['path']).read_text())['id']: ROOT / entry['path']
        for entry in json.loads((ROOT / 'data/catalog/manifest.json').read_text())['exams']
    }
    paths = [curated[i] for i in profile.get('reviewed', []) if i in curated]
    paths += [ROOT / 'data/derived/exams' / f'{i}.json' for i in profile.get('automatic', [])]
    return paths


def eligible(issues):
    return not any(i.get('severity') == 'error' for i in issues)


def figure_attributes(blocks, regions):
    """Largura de cada figura em relação à região da questão e o alinhamento horizontal nela."""
    result = []
    for block in blocks:
        if block['type'] != 'image':
            continue
        x0, _, x1, _ = block['bbox']
        candidates = [r['bbox'] for r in regions if r['page'] == block['page']]
        left, _, right, _ = max(candidates, key=lambda r: min(r[2], x1) - max(r[0], x0))
        width = max(1e-6, right - left)
        margin_left, margin_right = x0 - left, right - x1
        alignment = (
            'centro'
            if abs(margin_left - margin_right) <= 0.1 * width
            else 'esquerda'
            if margin_left < margin_right
            else 'direita'
        )
        result.append(
            {'alternative': block['alternative'], 'width_ratio': round((x1 - x0) / width, 3), 'alignment': alignment}
        )
    return result


def support_group(source_hash, regions):
    """Texto de apoio compartilhado: a mesma região impressa vale para todas as questões que a citam."""
    shared = [{'page': r['page'], 'bbox': r['bbox']} for r in regions if r.get('shared_for')]
    if not shared:
        return None
    return 'apoio-' + hashlib.sha256(json.dumps([source_hash, shared], sort_keys=True).encode()).hexdigest()[:16]


def content_form(content):
    """`imagem-unica` quando o JSON publica a questão inteira como uma figura, sem texto próprio."""
    blocks = content.get('blocks') or []
    return 'imagem-unica' if blocks and all(b['type'] == 'image' for b in blocks) else 'estruturado'


def run(paths, output, assets_root, overlays=True):
    rows, seen = [], {}
    for path in paths:
        data = json.loads(Path(path).read_text())
        source = data['source']
        pdf = local_source(source['url'], source['sha256'])
        if pdf is None:
            raise SystemExit(f'{data["id"]}: PDF original ausente ou com hash diferente; sincronize o acervo.')
        with pymupdf.open(pdf) as doc:
            background = furniture(doc)
            for question in data['questions']:
                content = question['content']
                regions = content['layout']['blocks']
                key = (source['sha256'], json.dumps(regions, sort_keys=True))
                occurrence = {'exam': data['id'], 'number': content['number'], 'question_id': question['question_id']}
                if key in seen:
                    # The same printed question in another language edition of the booklet.
                    seen[key]['occurrences'].append(f'{data["id"]}#{content["number"]}')
                    seen[key]['occurrence_ids'].append(occurrence)
                    continue
                result = analyze(doc, content, data['id'], source['sha256'], assets_root, background)
                folder = output / data['id']
                folder.mkdir(parents=True, exist_ok=True)
                name = f'q{content["number"]:03d}'
                save_png(result['image'], folder / f'{name}.png')
                if overlays:
                    save_png(result['image'], folder / f'{name}-overlay.png', color=overlay(result))
                row = dict(
                    exam=data['id'],
                    number=content['number'],
                    question_id=question['question_id'],
                    signature=result['signature'],
                    eligible=eligible(result['issues']),
                    issues=[{k: i[k] for k in ('code', 'severity', 'message', 'location')} for i in result['issues']],
                    residual_for_humans=result['residual_for_humans'],
                    findings={k: len(v) for k, v in result['findings'].items()},
                    image=f'{data["id"]}/{name}.png',
                    overlay=f'{data["id"]}/{name}-overlay.png',
                    occurrences=[f'{data["id"]}#{content["number"]}'],
                    occurrence_ids=[occurrence],
                    source_sha256=source['sha256'],
                    content_sha256=content_fingerprint(content),
                    content_form=content_form(content),
                    support_group=support_group(source['sha256'], regions),
                    figures=figure_attributes(result['blocks'], regions),
                    adapter=ADAPTER,
                )
                seen[key] = row
                rows.append(row)
    return rows


def group(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['signature']].append(row)
    result = []
    for signature, members in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        unsupported = [message for token, message in UNSUPPORTED.items() if token in signature.split()]
        if '?' in signature or 'misto' in signature:
            unsupported.append('Alternativas sem estrutura A–E reconhecida.')
        result.append(
            dict(
                signature=signature,
                status='residual' if unsupported else 'supported',
                reasons=unsupported,
                questions=len(members),
                eligible=sum(m['eligible'] for m in members),
                members=[f'{m["exam"]}#{m["number"]}' for m in members],
            )
        )
    return result


def page(groups, rows, title):
    by_key = {f'{r["exam"]}#{r["number"]}': r for r in rows}
    parts = [
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{html.escape(title)}</title>',
        '<style>body{font:14px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}'
        'h2{font-size:15px;margin:28px 0 6px;font-family:ui-monospace,monospace}'
        '.grid{display:flex;flex-wrap:wrap;gap:10px}.q{width:220px;background:#fff;border:1px solid #ddd;padding:6px}'
        '.q img{width:100%;height:auto;display:block}.bad{border-color:#d33}.meta{font-size:12px;color:#555}'
        '.tag{display:inline-block;padding:1px 6px;border-radius:8px;font-size:12px;margin-left:6px}'
        '.supported{background:#dfd}.residual{background:#fdd}</style>',
        f'<h1>{html.escape(title)}</h1>',
        f'<p>{len(rows)} questões, {len(groups)} grupos, {sum(r["eligible"] for r in rows)} elegíveis à aprovação automática.</p>',
    ]
    for g in groups:
        parts.append(
            f'<h2>{html.escape(g["signature"])}<span class="tag {g["status"]}">{g["status"]}</span>'
            f'<span class="tag">{g["eligible"]}/{g["questions"]} elegíveis</span></h2>'
        )
        if g['reasons']:
            parts.append(f'<p class="meta">{html.escape(" ".join(g["reasons"]))}</p>')
        parts.append('<div class="grid">')
        for key in g['members']:
            r = by_key[key]
            codes = ', '.join(sorted({i['code'] for i in r['issues'] if i['severity'] == 'error'}))
            parts.append(
                f'<div class="q{"" if r["eligible"] else " bad"}"><a href="{r["overlay"]}">'
                f'<img loading="lazy" src="{r["image"]}" alt="{html.escape(key)}"></a>'
                f'<div class="meta">{html.escape(key)}{" · " + html.escape(codes) if codes else ""}</div></div>'
            )
        parts.append('</div>')
    return '\n'.join(parts)


def type_page(items, rows, title):
    """Folha de contato por tipo; decisões manuais destacadas com a assinatura observada e a justificativa."""
    images = {r['question_id']: r for r in rows}
    grouped = defaultdict(list)
    for item in items:
        grouped[item['type']].append(item)
    manual = sum(item['provenance']['origin'] == 'manual' for item in items)
    parts = [
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{html.escape(title)}</title>',
        '<style>body{font:14px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}'
        'h2{font-size:15px;margin:28px 0 6px;font-family:ui-monospace,monospace}'
        '.grid{display:flex;flex-wrap:wrap;gap:10px}.q{width:220px;background:#fff;border:1px solid #ddd;padding:6px}'
        '.q img{width:100%;height:auto;display:block}.manual{border:2px solid #c60}.meta{font-size:12px;color:#555}'
        '.why{font-size:12px;color:#733;margin-top:4px}</style>',
        f'<h1>{html.escape(title)}</h1>',
        f'<p>{len(items)} questões, {len(grouped)} tipos, {manual} por decisão manual (borda laranja).</p>',
    ]
    for type_id, members in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        parts.append(f'<h2>{html.escape(type_id)} · {len(members)}</h2><div class="grid">')
        for item in members:
            row, provenance = images[item['question_id']], item['provenance']
            key = f'{item["exam"]}#{item["number"]}'
            note = ''
            if provenance['origin'] == 'manual':
                note = (
                    f'<div class="why">{html.escape(provenance["decision"])}: '
                    f'{html.escape(provenance["observed_signature"])} → {html.escape(item["signature"])}. '
                    f'{html.escape(provenance["justification"])}</div>'
                )
            parts.append(
                f'<div class="q{" manual" if note else ""}"><a href="{row["overlay"]}">'
                f'<img loading="lazy" src="{row["image"]}" alt="{html.escape(key)}"></a>'
                f'<div class="meta">{html.escape(key)} · {html.escape(item["signature"])}</div>{note}</div>'
            )
        parts.append('</div>')
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('exams', nargs='*', type=Path, help='JSON de provas com regiões; padrão: perfil local.')
    parser.add_argument('--output', type=Path, help='Pasta de saída; padrão: tmp/layout/<data-hora>.')
    parser.add_argument('--catalog', type=Path, help='Grava o catálogo dos tipos de layout (layout-types-v1).')
    parser.add_argument('--reference', type=Path, help='Grava a referência rotulada por questão.')
    parser.add_argument('--decisions', type=Path, default=DECISIONS, help='Decisões manuais versionadas.')
    args = parser.parse_args()
    paths = args.exams or profile_exams()
    output = args.output or ROOT / 'tmp/layout' / time.strftime('%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=True)
    rows = run(paths, output, output / 'assets')
    groups = group(rows)
    (output / 'questions.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n')
    (output / 'groups.json').write_text(json.dumps(groups, ensure_ascii=False, indent=1) + '\n')
    (output / 'index.html').write_text(page(groups, rows, f'Grupos de layout ({ADAPTER})'))
    eligible_count = sum(r['eligible'] for r in rows)
    print(f'{len(rows)} questões, {len(groups)} grupos, {eligible_count} elegíveis. Relatório: {output / "index.html"}')
    if args.catalog or args.reference:
        decisions = args.decisions.read_bytes()
        try:
            items = reference.label(rows, json.loads(decisions))
        except reference.LabelError as error:
            raise SystemExit(str(error)) from None
        sources = []
        for path in paths:
            data = json.loads(Path(path).read_text())
            sources.append(
                {
                    'exam': data['id'],
                    'path': str(Path(path).resolve().relative_to(ROOT)),
                    'url': data['source']['url'],
                    'sha256': data['source']['sha256'],
                }
            )
        if args.reference:
            labeled = reference.reference(items, sources, ADAPTER, hashlib.sha256(decisions).hexdigest())
            write(args.reference, labeled)
        if args.catalog:
            write(args.catalog, reference.catalog(items, ADAPTER))
        (output / 'tipos.html').write_text(type_page(items, rows, f'Tipos de layout ({ADAPTER})'))
        manual = sum(item['provenance']['origin'] == 'manual' for item in items)
        print(
            f'{len(items)} questões com tipo ({manual} por decisão manual), {len({i["type"] for i in items})} tipos. '
            f'Folha por tipo: {output / "tipos.html"}'
        )


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
