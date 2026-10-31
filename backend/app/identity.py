"""Conservative identity across occurrences; numbering/order stay in each version."""
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


def identify(db,content):
    signature,answer=signatures(content)
    identity=db.scalar(select(CanonicalQuestion).where(CanonicalQuestion.signature==signature))
    if identity:
        if identity.answer_signature and answer and identity.answer_signature!=answer:
            raise HTTPException(409,'O mesmo conteúdo tem gabaritos conflitantes entre ocorrências. Confira a fonte antes de unir.')
        if not identity.answer_signature and answer:identity.answer_signature=answer
        return identity.id
    identity=CanonicalQuestion(id='enem-'+signature[:32],signature=signature,answer_signature=answer)
    db.add(identity);db.flush()
    return identity.id
