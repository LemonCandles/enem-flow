"""Versioned editorial vocabulary; official skills are a separate namespace."""
from functools import lru_cache
import json

from ..core.config import ROOT


@lru_cache(maxsize=1)
def taxonomy():
    return json.loads((ROOT/'data/taxonomy/enem-content-v1.json').read_text())


def validate_labels(labels,area=None):
    if labels['taxonomy_version']!='enem-content-v1':return
    discipline=next((d for d in taxonomy()['disciplines'] if d['name']==labels['discipline']),None)
    if not discipline or (area and discipline['area']!=area):
        raise ValueError('Disciplina incompatível com a área na taxonomia enem-content-v1.')
    if not labels['themes'] or any(t not in discipline['themes'] for t in labels['themes']):
        raise ValueError('Tema ausente ou fora da disciplina na taxonomia enem-content-v1.')
    if len(set(labels['themes']))!=len(labels['themes']):raise ValueError('Tema duplicado.')
    if labels['skills']:
        official=json.loads((ROOT/'data/taxonomy/enem-official-math.json').read_text())
        valid={s['id'] for s in official['skills']}
        if discipline['name']!='Matemática' or any(s not in valid for s in labels['skills']):raise ValueError('Habilidade deve usar identificador oficial com área, como MT.H12.')
