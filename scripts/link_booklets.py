#!/usr/bin/env python3
"""Vincula as ocorrências das outras cores aos itens dos lotes conferidos.

As cores de uma mesma aplicação e dia trazem os mesmos itens em outra ordem.
Uma ocorrência só é vinculada quando o texto corresponde ao item conferido com
folga sobre o segundo candidato, o pareamento é único, o gabarito oficial da
cor coincide (inclusive anulação) e as figuras raster são equivalentes. O que
não cumpre esses critérios fica pendente, com o motivo.

Exige os PDFs das cores e seus gabaritos no espelho local (`archive_enem.py
sync`). O resultado, `data/catalog/occurrences-v1.json`, é versionado.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pymupdf
from backend.app.catalog import classified
from backend.app.identity import signatures
from scripts.archive_enem import CATALOG, SOURCE_ROOT, sha, write_json
from scripts.build_bank import extract

OUTPUT = ROOT / 'data/catalog/occurrences-v1.json'
VERSION = 'booklet-links-v1'
MIN_CONTAINMENT = 0.4
MIN_MARGIN = 0.3
MAX_FIGURE_DISTANCE = 8.0
SAME_EXAM = ('year', 'application', 'modality', 'day', 'variant', 'role', 'language')

# Conferências visuais explícitas para figuras reprocessadas pelo Inep em outra
# resolução, em que a comparação automática fica acima do limite.
VISUAL_CONFIRMED = {
    ('enem-2024-regular-q121', 'caderno-5-amarelo'): 'Mesma tirinha em quatro quadros; a imagem embutida no caderno amarelo tem outra resolução.',
    ('enem-2024-regular-q152', 'caderno-5-amarelo'): 'Mesmo gráfico de importações e exportações (jun. 2009 a jun. 2010); muda só a resolução.',
    ('enem-2024-regular-q167', 'caderno-5-amarelo'): 'Mesma ilustração dos celulares de 3 1/2 e 4 5/6 polegadas; muda só a resolução.',
}


def words(text):
    text = re.sub(r'\$[^$]*\$|\\\(.*?\\\)|\\\[.*?\\\]', ' ', text, flags=re.S)
    text = unicodedata.normalize('NFKD', text.lower())
    return re.findall(r'[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c)))


def shingles(text, size=3):
    tokens = words(text)
    return {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def curated_text(content):
    """Texto nativo do item; fórmulas em LaTeX ficam fora porque o PDF não as preserva."""
    parts = [content['statement']]
    for block in content.get('blocks', []):
        if block['type'] == 'paragraph':
            parts.append(block['text'])
        elif block['type'] == 'table':
            parts += block['headers'] + [cell for row in block['rows'] for cell in row]
    parts += [alternative['text'] for alternative in content['alternatives']]
    return ' '.join(parts)


def pair(curated, candidates):
    """Pareia cada item conferido ao candidato com maior contenção de trigramas.

    `curated` e `candidates` mapeiam número da questão para conjunto de
    trigramas. Retorna número conferido -> (número do candidato, contenção,
    folga sobre o segundo candidato, motivo de pendência ou None).
    """
    result = {}
    for number, mine in curated.items():
        scores = sorted(((len(mine & theirs) / max(1, len(mine)), other) for other, theirs in candidates.items()), reverse=True)
        best, other = scores[0] if scores else (0.0, None)
        margin = best - (scores[1][0] if len(scores) > 1 else 0.0)
        reason = None
        if best < MIN_CONTAINMENT:
            reason = f'Texto corresponde a {best:.0%} do item conferido; mínimo de {MIN_CONTAINMENT:.0%}.'
        elif margin < MIN_MARGIN:
            reason = f'Folga de {margin:.0%} sobre o segundo candidato; mínimo de {MIN_MARGIN:.0%}.'
        result[number] = (other, round(best, 3), round(margin, 3), reason)
    taken = {}
    for number, (other, *_rest, reason) in result.items():
        if reason is None:
            taken.setdefault(other, []).append(number)
    for other, numbers in taken.items():
        if len(numbers) > 1:
            for number in numbers:
                found, best, margin, _ = result[number]
                result[number] = (found, best, margin, f'Questão {other} disputada por {len(numbers)} itens conferidos.')
    return result


def official_answers(path):
    with pymupdf.open(path) as document:
        text = '\n'.join(page.get_text() for page in document)
    return {int(number): None if answer.upper().startswith('ANULAD') else answer.upper()
            for number, answer in re.findall(r'\b(\d{1,3})\s+(ANULAD[AO]|[ABCDE])\b', text, re.I)}


def thumbnail(page, box, grid=16):
    zoom = 64 / max(box.width, box.height)
    pixmap = page.get_pixmap(clip=box, matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
    width, height, samples, stride = pixmap.width, pixmap.height, pixmap.samples, pixmap.stride
    cells = []
    for gy in range(grid):
        for gx in range(grid):
            ys = range(gy * height // grid, max(gy * height // grid + 1, (gy + 1) * height // grid))
            xs = range(gx * width // grid, max(gx * width // grid + 1, (gx + 1) * width // grid))
            values = [samples[y * stride + x] for y in ys for x in xs if x < width and y < height]
            cells.append(sum(values) / len(values))
    return cells


def figures(path, occurrences):
    """Miniaturas em tons de cinza das imagens raster de cada ocorrência."""
    result = {}
    with pymupdf.open(path) as document:
        images = {}
        for occurrence in occurrences:
            found = []
            for region in occurrence['regions']:
                page = document[region['page'] - 1]
                area = pymupdf.Rect(region['bbox'])
                if region['page'] not in images:
                    images[region['page']] = page.get_image_info()
                for info in images[region['page']]:
                    box = pymupdf.Rect(info['bbox'])
                    if min(box.width, box.height) > 12 and (box & area).get_area() > 0.5 * box.get_area():
                        found.append((box.width / box.height, thumbnail(page, box)))
            result[occurrence['number']] = found
    return result


def figure_distance(mine, theirs):
    """Maior diferença média entre figuras pareadas; infinito se não equivalem."""
    if len(mine) != len(theirs):
        return float('inf')
    worst = 0.0
    for ratio, cells in mine:
        options = [sum(abs(a - b) for a, b in zip(cells, other)) / len(cells)
                   for other_ratio, other in theirs if abs(ratio - other_ratio) <= 0.05 * ratio]
        worst = max(worst, min(options, default=float('inf')))
    return worst


def records():
    files = json.loads(CATALOG.read_text())['files']
    return [r for r in files if r['status'] == 'downloaded']


def local(record):
    path = SOURCE_ROOT / record['path']
    if not path.is_file() or sha(path) != record['sha256']:
        raise SystemExit(f'Fonte ausente ou com hash divergente: {record["path"]}. Execute archive_enem.py sync.')
    return path


def answer_key(files, record):
    keys = [r for r in files if r['role'] == 'gabarito' and r['booklet'] == record['booklet']
            and all(r.get(k) == record.get(k) for k in ('year', 'application', 'modality', 'day', 'variant'))]
    if len(keys) != 1:
        raise SystemExit(f'Gabarito do {record["booklet"]} não identificado no catálogo.')
    return keys[0]


def link_exam(files, payload):
    own = [r for r in files if r['role'] == 'prova' and r['sha256'] == payload.source.sha256]
    if len(own) != 1:
        raise SystemExit(f'Fonte de {payload.id} não identificada no catálogo.')
    own = own[0]
    booklets = [own] + sorted((r for r in files if r['booklet'] != own['booklet'] and all(r.get(k) == own.get(k) for k in SAME_EXAM)),
                              key=lambda r: r['booklet'])
    numbers = [q.content.number for q in payload.questions]
    curated = {q.content.number: shingles(curated_text(q.content.model_dump())) for q in payload.questions}
    own_occurrences = extract(own)['questions']
    own_figures = figures(local(own), own_occurrences)
    links = {q.question_id: [] for q in payload.questions}
    pending, summary = [], []
    for booklet in booklets:
        key_record = answer_key(files, booklet)
        answers = official_answers(local(key_record))
        occurrences = [o for o in extract(booklet)['questions'] if min(numbers) <= o['number'] <= max(numbers) and not o.get('language')]
        candidates = {o['number']: shingles(o['text']) for o in occurrences}
        theirs = figures(local(booklet), occurrences)
        paired = pair(curated, candidates)
        linked = 0
        for question in payload.questions:
            content = question.content
            other, best, margin, reason = paired[content.number]
            expected = None if content.annulled else content.correct_answer
            official = answers.get(other, 'ausente') if other is not None else 'ausente'
            if reason is None and official != expected:
                reason = f'Gabarito oficial da questão {other} ({official or "anulada"}) difere do item conferido ({expected or "anulada"}).'
            figure_note = 'sem imagens raster'
            if reason is None and (own_figures[content.number] or theirs.get(other)):
                distance = figure_distance(own_figures[content.number], theirs.get(other, []))
                confirmed = VISUAL_CONFIRMED.get((question.question_id, booklet['booklet']))
                if distance <= MAX_FIGURE_DISTANCE:
                    figure_note = 'equivalentes'
                elif confirmed:
                    figure_note = f'conferidas visualmente: {confirmed}'
                else:
                    reason = 'Figuras raster diferem além do limite; confira visualmente antes de vincular.'
            if reason:
                pending.append(dict(question_id=question.question_id, booklet=booklet['booklet'], candidate=other, reason=reason))
                continue
            linked += 1
            links[question.question_id].append(dict(booklet=booklet['booklet'], source_sha256=booklet['sha256'], number=other,
                                                    answer=official, text_containment=best, margin=margin, figures=figure_note))
        summary.append(dict(booklet=booklet['booklet'], source_path=booklet['path'], source_sha256=booklet['sha256'],
                            answer_key_sha256=key_record['sha256'], linked=linked, pending=len(payload.questions) - linked))
    questions = []
    for question in payload.questions:
        digest, _ = signatures(question.content.model_dump())
        questions.append(dict(question_id=question.question_id, canonical_id='enem-' + digest[:32], occurrences=links[question.question_id]))
    return dict(exam_id=payload.id, source_sha256=own['sha256'], booklets=summary), questions, pending


def build():
    files = records()
    manifest = json.loads((ROOT / 'data/catalog/manifest.json').read_text())
    exams, questions, pending = [], [], []
    for entry in manifest['exams']:
        payload = classified(json.loads((ROOT / entry['path']).read_text()))
        exam, rows, missing = link_exam(files, payload)
        exams.append(exam)
        questions += rows
        pending += missing
    return dict(version=VERSION, catalog=manifest['version'],
                method='Cores da mesma aplicação e dia: contenção de trigramas do texto nativo, pareamento único, gabarito oficial de cada cor e figuras raster equivalentes.',
                criteria=dict(min_text_containment=MIN_CONTAINMENT, min_margin=MIN_MARGIN, max_figure_distance=MAX_FIGURE_DISTANCE),
                limits='Desenhos vetoriais não são comparados; a equivalência deles decorre do texto, do pareamento e do gabarito.',
                exams=exams, questions=questions, pending=pending)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Falha se o arquivo versionado diferir do resultado atual.')
    result = build()
    if parser.parse_args().check:
        current = json.loads(OUTPUT.read_text()) if OUTPUT.is_file() else None
        raise SystemExit(0 if current == result else f'{OUTPUT.relative_to(ROOT)} desatualizado; execute sem --check.')
    write_json(OUTPUT, result)
    linked = sum(len(q['occurrences']) for q in result['questions'])
    print(f'{linked} ocorrências vinculadas a {len(result["questions"])} itens; {len(result["pending"])} pendentes.')
