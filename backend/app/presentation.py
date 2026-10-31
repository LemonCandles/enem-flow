"""A presentation adapter for unchanged legacy snapshots of the bundled JSON.

This never changes assessment data, version identifiers, choices or results. A
legacy item can use the native view only when its exact transcription hash matches.
"""
import hashlib
import json
from functools import lru_cache

from .db import ROOT


@lru_cache(maxsize=1)
def native_bundle():
    path = ROOT / "data/enem-2024-dia2-azul.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text())
    return {q['question_id']: q['content'] for q in payload['questions']}


def readable_content(question_id, content):
    if not content.get('original_layout'):
        return content
    native = native_bundle().get(question_id)
    if not native or not native.get('blocks'):
        return content
    signature = hashlib.sha256(content['statement'].encode()).hexdigest()
    if native.get('layout', {}).get('legacy_text_sha256') != signature:
        return content
    return {**content, **{field: native[field] for field in ('statement', 'blocks', 'images', 'alternatives', 'original_layout')}}
