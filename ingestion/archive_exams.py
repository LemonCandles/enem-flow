"""Metadata of an archive exam and a first look at its PDF, shared by generation and trials."""

import re

import pymupdf

from ingestion.exam_pdf import LANGUAGE, garbled, language_key, lines
from ingestion.pdf_headings import HEADING


APPLICATIONS = {
    'regular': 'Regular',
    'reaplicacao-ppl': 'Reaplicação/PPL',
    'digital': 'Digital',
    'reaplicacao': 'Reaplicação',
    'segunda-aplicacao': '2ª aplicação',
    'terceira-aplicacao': '3ª aplicação',
    'belem-ananindeua-marituba': 'Belém, Ananindeua e Marituba',
}
LANGUAGES = {'ingles': 'Inglês', 'espanhol': 'Espanhol'}


def areas(year, day):
    """Metadados da época; em 2009, Natureza precedia Humanas no primeiro dia."""
    names = (
        (('Linguagens', 'Ciências Humanas'), ('Ciências da Natureza', 'Matemática'))
        if year >= 2017
        else (('Ciências Humanas', 'Ciências da Natureza'), ('Linguagens', 'Matemática'))
    )
    if year == 2009:
        # Caderno azul de 2009, página 2: Natureza, questões 1–45.
        names = (('Ciências da Natureza', 'Ciências Humanas'), ('Linguagens', 'Matemática'))
    first = 1 if day == 1 else 91
    result = [
        dict(first=first, last=first + 44, area=names[day - 1][0]),
        dict(first=first + 45, last=first + 89, area=names[day - 1][1]),
    ]
    for area in result:
        if area['area'] == 'Matemática':
            area['discipline'] = 'Matemática'
    return result


def duration(year, day):
    if year >= 2017:
        return 330 if day == 1 else 300
    return 270 if day == 1 else 330


def booklet_label(booklet):
    match = re.match(r'caderno-(\d+)-(.+)', booklet)
    if not match:
        return booklet
    return f'Caderno {match[1]} · ' + ' · '.join(LANGUAGES.get(part, part.capitalize()) for part in match[2].split('-'))


def exam_id(year, application, day, booklet, language):
    suffix = f'-{language}' if language and not booklet.endswith(language) else ''
    return f'enem-{year}-{application}-dia{day}-{booklet}{suffix}'


def scan(pdf):
    """Margem superior, última página com questões, línguas oferecidas e linhas ilegíveis."""
    tops, last, offered, total, broken = [], 1, set(), 0, 0
    with pymupdf.open(pdf) as doc:
        height = doc[min(1, len(doc) - 1)].rect.height
        for number, page in enumerate(doc, start=1):
            for line in lines(page, page.rect):
                total += 1
                broken += garbled(line['text'])
                if HEADING.match(line['text']):
                    last = number
                    if number > 1:
                        tops.append(line['bbox'][1])
                elif match := LANGUAGE.match(line['text']):
                    offered.add(language_key(match[3]))
                    if number > 1:
                        tops.append(line['bbox'][1])
    return dict(
        top=max(30, min(tops) - 3) if tops else 55,
        last=last,
        height=height,
        offered=sorted(offered),
        garbled=broken / max(1, total),
    )
