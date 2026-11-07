"""Geometry-based PDF adapter. No exam year or question number is special-cased."""

from .text import (
    SUB,
    SUP,
    SUSPECT,
    align_option_lines,
    diagnostic,
    garbled,
    lines,
    literal,
    mark_bare_options,
    textual_table,
    watermark,
)
from .regions import (
    LANGUAGE,
    auto_columns,
    discover_regions,
    language_key,
    margin_headings,
    section_break,
    shared_numbers,
)
from .answer_key import answer_key_rows
from .figures import alternative_graphics, graphics
from .exam import extract_exam, extract_question, from_manifest

__all__ = [
    'LANGUAGE',
    'SUB',
    'SUP',
    'SUSPECT',
    'align_option_lines',
    'alternative_graphics',
    'answer_key_rows',
    'auto_columns',
    'diagnostic',
    'discover_regions',
    'extract_exam',
    'extract_question',
    'from_manifest',
    'garbled',
    'graphics',
    'language_key',
    'lines',
    'literal',
    'margin_headings',
    'mark_bare_options',
    'section_break',
    'shared_numbers',
    'textual_table',
    'watermark',
]
