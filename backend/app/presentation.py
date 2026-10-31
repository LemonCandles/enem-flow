"""A presentation adapter for unchanged earlier snapshots of the bundled JSON.

This never changes assessment data, version identifiers, choices or results. A
snapshot can use the reviewed view only when its complete content hash matches.
"""
import hashlib
import json
from functools import lru_cache

from .db import ROOT
from .schemas import QuestionContent


ASSESSMENT_FIELDS = ('number', 'area', 'correct_answer', 'annulled', 'labels', 'page')


def content_fingerprint(content):
    normalized = QuestionContent.model_validate(content).model_dump()
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def previous_fingerprints():
    versions = {}
    sources = [ROOT / 'data/derived/baselines/enem-2024-dia2-azul-extraction.json',
               ROOT / 'data/derived/baselines/enem-2024-dia2-azul-native-v1.json']
    for path in sources:
        if not path.is_file(): continue
        for question in json.loads(path.read_text())['questions']:
            versions.setdefault(question['question_id'], set()).add(content_fingerprint(question['content']))
    return versions


def is_previous_bundled_content(question_id, content):
    return content_fingerprint(content) in previous_fingerprints().get(question_id, set())


@lru_cache(maxsize=1)
def native_bundle():
    path = ROOT / "data/enem-2024-dia2-azul.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text())
    return {q['question_id']: q['content'] for q in payload['questions']}


def readable_content(question_id, content):
    native = native_bundle().get(question_id)
    if not native or not native.get('blocks'):
        return content
    normalized = QuestionContent.model_validate(content).model_dump()
    desired = QuestionContent.model_validate(native).model_dump()
    if normalized == desired or any(normalized[key] != desired[key] for key in ASSESSMENT_FIELDS):
        return content
    if not is_previous_bundled_content(question_id, content):
        return content
    return {**content, **{field: native[field] for field in ('statement', 'blocks', 'images', 'alternatives', 'original_layout')}}
