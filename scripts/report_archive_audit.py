"""Reúne evidências e uma fila visual local, sem confundir triagem e aprovação."""

import _bootstrap  # noqa: F401
import argparse
from collections import Counter
from pathlib import Path

from experiments.common import file_digest, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def load_visual_review(path):
    if not path:
        return {}
    data = read_json(path)
    if (
        data.get('schema_version') != '1.0'
        or data.get('independent_review') is not False
        or data.get('human_seconds') is not None
    ):
        raise ValueError(
            'Inspeção assistida deve declarar versão, ausência de independência e tempo humano não medido.'
        )
    records = {}
    for row in data['records']:
        if row['version_id'] in records or not row.get('evidence_files') or not row.get('findings'):
            raise ValueError('Inspeção duplicada ou sem evidência/achados.')
        for name, expected in row['evidence_files'].items():
            resource = (ROOT / name).resolve()
            if not resource.is_relative_to(ROOT) or file_digest(resource) != expected:
                raise ValueError('Os arquivos da inspeção visual mudaram.')
        if any(not f['code'].startswith('visual_') or not f.get('detail') for f in row['findings']):
            raise ValueError('Achado visual sem código próprio ou descrição.')
        records[row['version_id']] = row
    return records


def visual_item_findings(records, exam, source, item):
    row = records.get(item['id'])
    if not row:
        return []
    if (row['exam'], row['content_sha256'], row['source_sha256']) != (
        exam,
        item['content_sha256'],
        source['source_sha256'],
    ):
        raise ValueError('A inspeção visual pertence a outra fonte ou versão de conteúdo.')
    return row['findings']


def report(audit, experiments, initial=None, plan=None, figure_review=None, visual_review=None):
    manifest = read_json(audit / 'manifest.json')
    browser = read_json(audit / 'browser-report.json')
    scoring = read_json(audit / 'scoring-report.json')
    models = read_json(experiments / 'all-experiments-report.json')
    historical = read_json(experiments / 'historical-inventory.json')
    correction_plan = read_json(plan) if plan else {'changes': [], 'canonical_review_required': []}
    changes = correction_plan['changes']
    canonical_pending = {r['canonical_id'] for r in correction_plan.get('canonical_review_required', [])}
    visual_records = load_visual_review(visual_review)
    reviewed_figures = {}
    if figure_review:
        for row in read_json(figure_review)['records']:
            if (
                row['decision'] != 'equivalent_crop'
                or file_digest(ROOT / 'data' / row['asset'].lstrip('/')) != row['asset_sha256']
                or file_digest(row['expected_path']) != row['expected_sha256']
            ):
                raise ValueError('A revisão visual de figura não corresponde aos recursos atuais.')
            reviewed_figures[(row['version_id'], row['asset'], row['source_sha256'])] = row
    if not browser['complete'] or browser['errors'] or not models.get('complete', False) or scoring['failed']:
        raise ValueError('Conclua as verificações de navegador, experimentos e correção antes de consolidar.')
    if models['questions'] != manifest['questions'] or browser['questions'] != 2 * manifest['questions']:
        raise ValueError('A cobertura das evidências diverge do catálogo auditado.')
    changed = {r['question_id']: r for r in changes}
    rows = []
    counts = Counter()
    for entry in manifest['index']:
        source = read_json(audit / entry['source_report'])
        proposals = read_json(experiments / 'all-proposals' / f'{entry["id"]}.json')
        renders = {v: read_json(audit / 'browser' / v / f'{entry["id"]}.json') for v in ('desktop', 'mobile')}
        for item in source['items']:
            proposal = next(q for q in proposals['items'] if q['question_id'] == item['question_id'])
            render = {v: next(q for q in renders[v]['items'] if q['number'] == item['number']) for v in renders}
            if (
                proposal['version_id'] != item['id']
                or proposal['content_sha256'] != item['content_sha256']
                or any(r['id'] != item['id'] for r in render.values())
            ):
                raise ValueError('Uma evidência pertence a outra versão da questão.')
            acknowledged = [
                f
                for f in item['findings']
                if f['code'] == 'source_figure_pixel_mismatch'
                and (item['id'], f['asset'], source['source_sha256']) in reviewed_figures
            ]
            visual = visual_item_findings(visual_records, entry['id'], source, item)
            issues = sorted(
                {f['code'] for f in item['findings'] if f.get('severity') != 'info' and f not in acknowledged}
                | {f['code'] for f in item['preparation_issues']}
                | {f['code'] for r in render.values() for theme in ['light', 'dark'] for f in r[theme]['issues']}
                | {f['code'] for f in visual}
            )
            if proposal.get('geometry_failure'):
                issues.append('geometry_fallback')
            if item['canonical_id'] in canonical_pending:
                issues.append('canonical_identity_requires_review')
            counts.update(issues)
            row = {
                'exam': entry['id'],
                'number': item['number'],
                'version': item['id'],
                'question_id': item['question_id'],
                'official_answer': item['official_answer'],
                'annulled': item['annulled'],
                'key_matches': item['key_matches'],
                'page': item['page'],
                'issues': issues,
                'corrected': item['question_id'] in changed,
                'source_images': item.get('source_images', []),
                'screenshots': {v: render[v].get('screenshot') for v in render},
                'proposed_theme': proposal['classification'].get('labels', {}).get('themes', []),
                'proposed_blocks': len(proposal['layout']['blocks']),
                'content_sha256': item['content_sha256'],
            }
            row['figure_comparisons_acknowledged'] = len(acknowledged)
            row['assisted_visual_findings'] = visual
            rows.append(row)
    if set(visual_records) - {r['version'] for r in rows}:
        raise ValueError('Uma inspeção visual não pertence ao catálogo auditado.')
    summary = {
        'schema_version': '1.0',
        'sources': {k: v for k, v in manifest.items() if k != 'index'},
        'browser': browser,
        'scoring': {k: v for k, v in scoring.items() if k != 'results'},
        'experiments': {k: v for k, v in models.items() if k != 'exams_summary'},
        'historical_inventory': historical,
        'corrections': {
            'versions': len(changes),
            'exams': len({r['exam_id'] for r in changes}),
            'plan_sha256': file_digest(plan) if plan else None,
            'canonical_identities_requiring_review': len(canonical_pending),
        },
        'affected_questions_by_code': dict(counts),
        'questions_with_findings': sum(bool(r['issues']) for r in rows),
        'manual_semantic_review_complete': False,
        'independent_pedagogical_review': False,
        'figure_crop_review': {
            'records': len(reviewed_figures),
            'independent_review': False,
            'sha256': file_digest(figure_review) if figure_review else None,
        },
        'assisted_visual_review': {
            'records': len(visual_records),
            'independent_review': False,
            'human_seconds': None,
            'sha256': file_digest(visual_review) if visual_review else None,
        },
        'evidence_sha256': {
            str(p.name): file_digest(p)
            for p in [
                audit / 'manifest.json',
                audit / 'browser-report.json',
                audit / 'scoring-report.json',
                experiments / 'all-experiments-report.json',
            ]
        },
    }
    if initial:
        summary['before'] = {k: v for k, v in read_json(initial / 'manifest.json').items() if k != 'index'}
    write_json(audit / 'complete-report.json', summary)
    write_json(audit / 'review-index.json', rows)
    # Embed only escaped JSON, use textContent for all dynamic text. This works
    # via file:// too; original crops and screenshots are relative local assets.
    data = __import__('json').dumps(rows, ensure_ascii=False).replace('<', r'\u003c')
    html = (
        '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Conferência integral do acervo</title>
<style>body{font:16px system-ui;background:#f3f5f8;color:#172033;margin:0}header,main{max-width:1500px;margin:auto;padding:20px}header{position:sticky;top:0;background:#fff;z-index:1;border-bottom:1px solid #ccd3df}h1{font-size:24px;margin:0 0 10px}input,select,button{font:inherit;padding:8px;max-width:100%}.controls{display:flex;gap:12px;flex-wrap:wrap}#meta{margin:14px 0}#meta span{display:inline-block;margin:4px 12px 4px 0}.columns{display:grid;grid-template-columns:1fr 1fr .65fr;gap:16px;align-items:start}.column{background:#fff;padding:14px;border-radius:8px;min-width:0}img{display:block;width:100%;height:auto;margin:10px 0}.badge{background:#e5edf8;border-radius:6px;padding:4px}a{color:#145cb5}@media(max-width:800px){.columns{grid-template-columns:1fr}header{position:static}}</style>
<header><h1>Conferência integral do acervo</h1><p>Fontes, gabaritos e renderização automatizados. Propostas de IA e achados de triagem exigem revisão; esta fila não é uma aprovação pedagógica independente.</p><div class="controls"><input id="search" aria-label="Buscar prova, questão ou diagnóstico" placeholder="Ano, prova, questão, diagnóstico"><select id="filter" aria-label="Filtrar questões"><option value="all">Todas</option><option value="issues">Com achados</option><option value="corrected">Corrigidas</option><option value="key">Divergência de gabarito</option></select><button id="prev">Anterior</button><button id="next">Próxima</button><span id="position"></span></div><div id="meta"></div></header>
<main><div class="columns"><section class="column"><h2>Trecho original</h2><div id="original"></div></section><section class="column"><h2>Site · desktop</h2><div id="desktop"></div></section><section class="column"><h2>Site · celular</h2><div id="mobile"></div></section></div></main>
<script id="rows" type="application/json">'''
        + data
        + '''</script><script>
const rows=JSON.parse(document.getElementById('rows').textContent);let filtered=rows,index=0;const $=s=>document.getElementById(s);
function apply(){const text=$('search').value.toLowerCase(),mode=$('filter').value;filtered=rows.filter(r=>JSON.stringify([r.exam,r.number,r.issues]).toLowerCase().includes(text)&&(mode==='all'||mode==='issues'&&r.issues.length||mode==='corrected'&&r.corrected||mode==='key'&&!r.key_matches));index=0;render()}
function images(target,paths){$(target).replaceChildren();if(!paths.length){const p=document.createElement('p');p.textContent='Captura não armazenada. Consulte os resultados automatizados desta versão no índice JSON.';$(target).append(p)}for(const path of paths){const a=document.createElement('a');a.href=path;a.target='_blank';const img=document.createElement('img');img.src=path;img.alt=target==='original'?'Recorte da fonte oficial':'Captura da questão no site';a.append(img);$(target).append(a)}}
function render(){const r=filtered[index];$('position').textContent=`${filtered.length?index+1:0} / ${filtered.length}`;$('meta').replaceChildren();$('prev').disabled=index<=0;$('next').disabled=index>=filtered.length-1;if(!r){for(const v of ['original','desktop','mobile'])$(v).replaceChildren();return}for(const text of [r.exam,`Questão ${r.number} · página ${r.page}`,`Versão ${r.version}`,r.annulled?'Anulada':`Gabarito oficial ${r.official_answer}`,r.key_matches?'Gabarito coincide':'Gabarito divergente',r.corrected?'Correção presente nesta versão':'',r.issues.length?'Achados: '+r.issues.join(', '):'Sem achados automatizados',...r.assisted_visual_findings.map(f=>'Inspeção assistida: '+f.detail),r.proposed_theme.length?'Tema proposto: '+r.proposed_theme.join(', '):'Sem classificação temática aplicável']){if(!text)continue;const span=document.createElement('span');span.textContent=text;$('meta').append(span)}images('original',r.source_images);for(const v of ['desktop','mobile'])images(v,r.screenshots[v]?[r.screenshots[v]]:[])}
$('search').oninput=apply;$('filter').onchange=apply;$('prev').onclick=()=>{index--;render()};$('next').onclick=()=>{index++;render()};render();</script></html>'''
    )
    (audit / 'review.html').write_text(html)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--experiments', type=Path, required=True)
    p.add_argument('--initial', type=Path)
    p.add_argument('--plan', type=Path)
    p.add_argument(
        '--figure-review',
        type=Path,
        help='Decisões técnicas sobre recortes, vinculadas à versão/fonte/bytes; não aprovam a questão inteira.',
    )
    p.add_argument(
        '--visual-review',
        type=Path,
        help='Achados de inspeção assistida, vinculados a conteúdo, fonte e arquivos; não aprovam questões.',
    )
    a = p.parse_args()
    report(a.audit, a.experiments, a.initial, a.plan, a.figure_review, a.visual_review)
