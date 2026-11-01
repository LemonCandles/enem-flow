"""Conservative identity across occurrences; numbering/order stay in each version."""
from functools import lru_cache
import hashlib
import json
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import select

from .db import ROOT
from .models import CanonicalQuestion


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC',text)).strip()


def signatures(content,assets_root=None):
    root=assets_root or ROOT/'data/assets'
    def asset(image):
        if not image:return None
        p=(root/image['path'].removeprefix('/assets/')).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('Figura ausente na identificação canônica.')
        return hashlib.sha256(p.read_bytes()).hexdigest()
    def digest(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    blocks=[]
    for b in content.get('blocks',[]):
        if b['type']=='paragraph' and b.get('role')=='credit':continue
        if b['type']=='paragraph':blocks.append(['text',normalized(b['text'])])
        elif b['type']=='math':blocks.append(['math',normalized(b['tex'])])
        elif b['type']=='image':blocks.append(['image',asset(b['asset']),normalized(b.get('caption','')),b.get('equations',[])])
        elif b['type']=='table':blocks.append(['table',[normalized(x) for x in b['headers']],[[normalized(x) for x in row] for row in b['rows']]])
    if not blocks:blocks=[['text',normalized(content['statement'])]]
    choices={a['letter']:digest([normalized(a['text']),asset(a.get('image'))]) for a in content['alternatives']}
    signature=digest(dict(area=content['area'],blocks=blocks,images=[asset(i) for i in content.get('images',[])],choices=sorted(choices.values())))
    return signature,choices.get(content['correct_answer'])


@lru_cache(maxsize=1)
def booklet_links():
    """(SHA-256 da fonte, número) -> (identidade, gabarito oficial) das cores vinculadas."""
    path=ROOT/'data/catalog/occurrences-v1.json'
    if not path.is_file():return {}
    data=json.loads(path.read_text())
    return {(o['source_sha256'],o['number']):(q['canonical_id'],o['answer']) for q in data['questions'] for o in q['occurrences']}


def identify(db,content,occurrence=None):
    """Resolve a identidade canônica; `occurrence` é (SHA-256 da fonte, número da questão)."""
    signature,answer=signatures(content)
    same_content=db.scalar(select(CanonicalQuestion).where(CanonicalQuestion.signature==signature))
    linked=booklet_links().get(occurrence) if occurrence else None
    if linked:
        canonical_id,official=linked
        if official!=(None if content['annulled'] else content['correct_answer']):
            raise HTTPException(409,'O gabarito difere do registrado para esta ocorrência no vínculo entre cores. Confira a fonte.')
        if same_content and same_content.id!=canonical_id:
            raise HTTPException(409,'O conteúdo já tem outra identidade canônica; revise o vínculo entre cores antes de importar.')
        identity=db.get(CanonicalQuestion,canonical_id)
        if identity:return identity.id
        identity=CanonicalQuestion(id=canonical_id,signature=signature,answer_signature=answer)
        db.add(identity);db.flush()
        return identity.id
    identity=same_content or db.get(CanonicalQuestion,'enem-'+signature[:32])
    if identity:
        if identity.answer_signature and answer and identity.answer_signature!=answer:
            raise HTTPException(409,'O mesmo conteúdo tem gabaritos conflitantes entre ocorrências. Confira a fonte antes de unir.')
        if not identity.answer_signature and answer:identity.answer_signature=answer
        return identity.id
    identity=CanonicalQuestion(id='enem-'+signature[:32],signature=signature,answer_signature=answer)
    db.add(identity);db.flush()
    return identity.id


def validate_revision_identity(db, content, canonical_id):
    """A revision keeps its identity, but cannot take another item's signature."""
    signature, _ = signatures(content)
    existing = db.scalar(select(CanonicalQuestion).where(CanonicalQuestion.signature == signature))
    if existing and existing.id != canonical_id:
        raise HTTPException(409, 'O conteúdo pertence a outra questão canônica. Revise a duplicata antes de salvar.')


def validate_exam_identities(items):
    """Check both stable identities and current content, including edited versions."""
    identities, content_signatures = set(), set()
    for canonical_id, content in items:
        signature, _ = signatures(content)
        if signature in content_signatures or (canonical_id and canonical_id in identities):
            raise HTTPException(409, 'A prova contém questões duplicadas por conteúdo ou identidade canônica.')
        content_signatures.add(signature)
        if canonical_id: identities.add(canonical_id)
