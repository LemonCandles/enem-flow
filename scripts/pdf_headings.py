"""Cabeçalhos compartilhados pela indexação e pela preparação nativa de PDFs."""
import re

QUESTION_WORD = r'Q\s*U\s*E\s*S\s*T\s*[ÃA]\s*O'
HEADING = re.compile(r'^\s*' + QUESTION_WORD + r'\s*(\d(?:\s*\d){0,2})\b', re.I)


def heading_number(match):
    return int(re.sub(r'\s+', '', match[1]))
