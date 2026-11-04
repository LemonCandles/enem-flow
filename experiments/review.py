"""Relatório local com coordenadas sobre o original e cronômetro explícito."""

import html
import json

import pymupdf as fitz

from .common import ROOT, digest, read_json, source_path


def render_review(config, output):
    reference = read_json(ROOT / config['reference'])
    proposals = {row['id']: row for row in read_json(output / 'layout-proposals.json')}
    method = read_json(output / 'layout-report.json')['selection']['method']
    assets = output / 'review-assets'
    assets.mkdir(exist_ok=True)
    sections, targets = [], {}
    for example in reference['examples']:
        key = example['id']
        targets[key] = digest(example)
        images = []
        with fitz.open(source_path(example['source_path'], example['source_sha256'])) as doc:
            for ri, region in enumerate(example['regions']):
                clip = fitz.Rect(region['bbox'])
                name = f'{key}-{ri}.png'
                doc[region['page'] - 1].get_pixmap(matrix=fitz.Matrix(1.7, 1.7), clip=clip).save(assets / name)
                overlays = []
                for kind, blocks in [('reference', example['blocks']), ('proposal', proposals[key]['blocks'])]:
                    for block in blocks:
                        if block['page'] != region['page'] or not clip.contains(
                            fitz.Point(block['bbox'][0] + 0.1, block['bbox'][1] + 0.1)
                        ):
                            continue
                        box = fitz.Rect(block['bbox']) & clip
                        style = f'left:{100 * (box.x0 - clip.x0) / clip.width:.3f}%;top:{100 * (box.y0 - clip.y0) / clip.height:.3f}%;width:{100 * box.width / clip.width:.3f}%;height:{100 * box.height / clip.height:.3f}%'
                        label = f'{block["order"]} {block["type"]}' + (
                            f' [{block["alternative"]}]' if block['alternative'] else ''
                        )
                        overlays.append(
                            f'<div class="box {kind}" style="{style}" title="{html.escape(label)}"><span>{html.escape(label)}</span></div>'
                        )
                images.append(
                    f'<div class="page"><img alt="Original, {html.escape(key)}, página {region["page"]}" src="review-assets/{name}">{"".join(overlays)}</div>'
                )
        sections.append(
            f'<article id="{key}"><h2>{html.escape(key)} · {html.escape(example["split"])}</h2><p>{html.escape(example["pattern"])}</p><div class="pages">{"".join(images)}</div><p class="status" aria-live="polite"></p><button class="start" data-id="{key}">Iniciar revisão</button> <select aria-label="Decisão"><option value="accept">Aceitar proposta</option><option value="correct">Exige correção</option><option value="reject">Rejeitar proposta</option></select><label>Justificativa / correções<textarea minlength="10"></textarea></label><button class="record" data-id="{key}">Registrar tempo e decisão</button></article>'
        )
    payload = json.dumps({'targets': targets, 'method': method}).replace('<', '\\u003c')
    document = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Enem Flow · revisão dos experimentos</title>
<style>body{font:16px system-ui;background:#f6f5f0;color:#242424;max-width:1300px;margin:auto;padding:24px}article{border-top:1px solid #888;padding:24px 0}.pages{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}.page{position:relative;width:min(100%,560px);background:white}.page img{display:block;width:100%}.box{position:absolute;box-sizing:border-box;border:2px solid #007568;pointer-events:none}.box span{font:10px system-ui;position:absolute;top:0;background:#fff;color:#242424}.proposal{border-color:#b33327}.proposal span{right:0}.hide-reference .reference,.hide-proposal .proposal{display:none}textarea{display:block;width:100%;min-height:70px}label{display:block;margin:10px 0}button,select,input{font:inherit;padding:8px}button{cursor:pointer}header{position:sticky;top:0;background:#f6f5f0;padding:12px;z-index:2;border-bottom:1px solid #888}.status{min-height:24px}</style>
<header><h1>Revisão técnica de layout</h1><p>Verde: referência assistida. Vermelho: proposta. Nenhuma decisão publica conteúdo.</p><label>Identificação do revisor <input id="reviewer" minlength="2" required></label><label><input type="checkbox" checked id="reference"> Referência</label><label><input type="checkbox" checked id="proposal"> Proposta</label><button id="export">Exportar tempos e decisões</button><p id="notice" role="status">O cronômetro começa apenas ao clicar em Iniciar revisão. Registros ficam nesta página até exportar.</p></header>
<main>SECTIONS</main><script>const data=PAYLOAD,starts={},records=[];
for(const kind of ['reference','proposal'])document.getElementById(kind).onchange=e=>document.body.classList.toggle('hide-'+kind,!e.target.checked);
document.querySelectorAll('.start').forEach(button=>button.onclick=()=>{starts[button.dataset.id]=performance.now();button.closest('article').querySelector('.status').textContent='Revisão iniciada.';});
document.querySelectorAll('.record').forEach(button=>button.onclick=()=>{const id=button.dataset.id,article=button.closest('article'),reviewer=document.getElementById('reviewer').value.trim(),reason=article.querySelector('textarea').value.trim();if(starts[id]===undefined||reviewer.length<2||reason.length<10){article.querySelector('.status').textContent='Inicie a revisão, identifique o revisor e escreva uma justificativa com pelo menos 10 caracteres.';return;}const record={target_id:id,content_sha256:data.targets[id],method:data.method,reviewer,seconds:(performance.now()-starts[id])/1000,decision:article.querySelector('select').value,reason};const previous=records.findIndex(r=>r.target_id===id);if(previous>=0)records.splice(previous,1);records.push(record);delete starts[id];article.querySelector('.status').textContent='Tempo e decisão registrados; exporte antes de fechar.';});
document.getElementById('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:'1.0',records},null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='correction-times.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};</script></html>'''
    (output / 'review.html').write_text(document.replace('SECTIONS', ''.join(sections)).replace('PAYLOAD', payload))
