"""Where each question is on the page: columns, headings and language sections."""

import re
import unicodedata

import pymupdf as fitz

from ingestion.pdf_headings import HEADING, heading_number
from .text import lines

LANGUAGE = re.compile(r'^Quest[õo]es\s+de\s+(\d+)\s+a\s+(\d+)\s*\(\s*op[çc][ãa]o\s*:?\s*([^)]+?)\s*\)', re.I)


def language_key(name):
    """'Inglês' -> 'ingles': the key a manifest uses to choose a language option."""
    return ''.join(c for c in unicodedata.normalize('NFKD', name.strip().lower()) if not unicodedata.combining(c))


def shared_numbers(text):
    """Explicit shared passages; never infer targets from a topic or proximity."""
    match = re.match(
        r'^(?:textos?|figura|tabela|grafico|informacoes|dados)\b.*?\bpara\s+(?:as?\s+)?questoes(?:\s+de)?\s+(\d{1,3})\s+(e|a|[-–])\s+(\d{1,3})\b',
        language_key(text),
    )
    if not match:
        return None
    first, last = int(match[1]), int(match[3])
    if not 0 < first < last <= first + 10:
        return None
    return [first, last] if match[2] == 'e' else list(range(first, last + 1))


def section_break(text):
    return language_key(text).strip() in {'proposta de redacao', 'instrucoes para a redacao'}


def auto_columns(source_lines, width):
    wide = sum(l['bbox'][2] - l['bbox'][0] > width * 0.65 for l in source_lines)
    crossing = sum(
        l['bbox'][0] < width / 2 - 12 and l['bbox'][2] > width / 2 + 12 and len(l['text']) > 25 for l in source_lines
    )
    heading_columns = {l['bbox'][0] >= width / 2 for l in source_lines if HEADING.match(l['text'])}
    return (
        [[0, width]]
        if wide >= 2 or crossing >= 3 and len(heading_columns) <= 1
        else [[0, width / 2], [width / 2, width]]
    )


def discover_regions(doc, config, languages=None):
    """Discover question boundaries in one/two columns; overrides describe layout.

    Foreign-language options are printed sections ("Questões de 01 a 05 (opção
    inglês)") that reuse the same numbers. Only the option declared in
    `language` is kept; `languages` receives number -> language for those items.
    """
    layout = config.get('layout', {})
    chosen = language_key(config['language']) if config.get('language') else None
    regions, current, section, offered = {}, None, None, set()
    shared = []
    start, end = layout.get('pages', [1, len(doc)])
    if not (1 <= start <= end <= len(doc)):
        raise ValueError('Intervalo de páginas inválido.')
    for pn in range(start, end + 1):
        page = doc[pn - 1]
        options = {**layout, **layout.get('page_overrides', {}).get(str(pn), {})}
        top, bottom = options.get('top', 55), options.get('bottom', page.rect.height - 48)
        all_lines = lines(page, fitz.Rect(0, top, page.rect.width, bottom))
        columns = options.get('columns', 'auto')
        if columns == 'auto':
            columns = auto_columns(all_lines, page.rect.width)
        if not isinstance(columns, list) or not columns:
            raise ValueError('columns deve ser auto ou uma lista de intervalos [x0, x1].')
        for x0, x1 in columns:
            events = []
            for l in all_lines:
                if not x0 <= l['bbox'][0] < x1:
                    continue
                if m := HEADING.match(l['text']):
                    events.append((l['bbox'][1], 'question', heading_number(m)))
                elif m := LANGUAGE.match(l['text']):
                    events.append((l['bbox'][1], 'language', (int(m[1]), int(m[2]), language_key(m[3]))))
                elif targets := shared_numbers(l['text']):
                    events.append((l['bbox'][1], 'shared', targets))
                elif section_break(l['text']):
                    events.append((l['bbox'][1], 'break', None))
            cursor = top
            for y, kind, value in sorted(events):
                if current is not None and y > cursor + 3:
                    clip = fitz.Rect(x0, cursor, x1, y - 1)
                    if page.get_text(clip=clip).strip():
                        regions[current].append({'page': pn, 'bbox': list(clip)})
                current, cursor = None, y
                if kind == 'break':
                    continue
                if kind == 'language':
                    section = value
                    offered.add(value[2])
                    continue
                if kind == 'shared':
                    if section and section[2] != chosen and section[0] <= value[0] <= section[1]:
                        continue
                    current = ('shared', len(shared))
                    shared.append((current, value))
                    regions[current] = []
                    continue
                number = value
                if section and not section[0] <= number <= section[1]:
                    section = None
                if section:
                    if not chosen:
                        raise ValueError(
                            f'Questões {section[0]}–{section[1]} têm opções de língua estrangeira: declare "language" no manifesto ({", ".join(sorted(offered))}).'
                        )
                    if section[2] != chosen:
                        continue
                    if languages is not None:
                        languages[number] = chosen
                if number in regions:
                    raise ValueError(f'Cabeçalho duplicado {number}: confira idioma, páginas e colunas no manifesto.')
                regions[number] = []
                current = number
            if current is not None and bottom > cursor:
                clip = fitz.Rect(x0, cursor, x1, bottom)
                if page.get_text(clip=clip).strip():
                    regions[current].append({'page': pn, 'bbox': list(clip)})
    if chosen and chosen not in offered:
        raise ValueError(
            f'Língua "{config["language"]}" não encontrada nas opções do caderno ({", ".join(sorted(offered)) or "nenhuma"}).'
        )
    for key, targets in shared:
        pieces = regions.pop(key)
        if not pieces or any(number not in regions for number in targets):
            raise ValueError(f'Texto compartilhado sem todas as questões {targets}; confira as margens e a língua.')
        for number in targets:
            regions[number] = [{**piece, 'shared_for': targets} for piece in pieces] + regions[number]
    return regions


def margin_headings(doc, config, numbers):
    """Headings of missing questions printed above `top` or below `bottom`."""
    layout = config.get('layout', {})
    start, end = layout.get('pages', [1, len(doc)])
    found = []
    for pn in range(start, end + 1):
        page = doc[pn - 1]
        options = {**layout, **layout.get('page_overrides', {}).get(str(pn), {})}
        top, bottom = options.get('top', 55), options.get('bottom', page.rect.height - 48)
        for line in lines(page, page.rect):
            m = HEADING.match(line['text'])
            if m and heading_number(m) in numbers and not top <= line['bbox'][1] < bottom:
                found.append(f'{heading_number(m)} (página {pn}, y={line["bbox"][1]:.0f})')
    return found[:8]
