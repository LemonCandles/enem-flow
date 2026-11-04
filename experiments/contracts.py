"""Contratos experimentais separados do conteúdo publicável e dos rótulos aprovados."""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class CorrectionTiming(Contract):
    target_id: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    method: str = Field(min_length=1)
    reviewer: str = Field(min_length=2)
    seconds: float = Field(gt=0, le=86400)
    decision: Literal['accept', 'correct', 'reject']
    reason: str = Field(min_length=10)


class CorrectionLog(Contract):
    schema_version: Literal['1.0'] = '1.0'
    records: list[CorrectionTiming]


class ExternalPrediction(Contract):
    question_id: str
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    theme: str
    evidence: str = Field(min_length=1, max_length=1000)
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)
    repeat_themes: list[str] = Field(min_length=2)


class ExternalPredictions(Contract):
    schema_version: Literal['1.0'] = '1.0'
    model: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    training_groups: list[str]
    data_policy: str = Field(min_length=10)
    records: list[ExternalPrediction]


class ProposedLabels(Contract):
    discipline: Literal['Matemática']
    themes: list[
        Literal[
            'Estatística',
            'Geometria espacial',
            'Geometria plana',
            'Grandezas e medidas',
            'Gráficos e coordenadas',
            'Números e proporcionalidade',
            'Probabilidade e combinatória',
            'Álgebra e funções',
        ]
    ] = Field(min_length=1, max_length=1)
    skills: list[str] = Field(max_length=0)


class ThemeOrigin(Contract):
    experiment: Literal['data-ai-v1']
    model: str
    model_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class ThemeProposal(Contract):
    schema_version: Literal['1.0']
    question_id: str
    canonical_id: str
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    taxonomy_version: Literal['enem-content-v1']
    labels: ProposedLabels
    origin: ThemeOrigin
    evidence: str = Field(min_length=1, max_length=1000)
    margin: float = Field(ge=0)
    margin_is_probability: Literal[False]
    review_status: Literal['proposed']
    needs_review: Literal[True]
    independent_review: Literal[False]
    evaluation_split: Literal['train', 'development', 'test', 'unlabeled_archive']
    review_reasons: list[str] = Field(min_length=1)


BLOCK_TYPES = ['paragraph', 'credit', 'caption', 'math', 'image', 'table', 'alternative']


class Region(Contract):
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]

    @field_validator('bbox')
    @classmethod
    def rectangle(cls, box):
        if not all(math.isfinite(n) for n in box) or box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError('Caixa PDF inválida.')
        return box


class LayoutBlock(Region):
    id: str = Field(min_length=1)
    type: Literal['paragraph', 'credit', 'caption', 'math', 'image', 'table', 'alternative']
    text: str = ''
    order: int = Field(ge=0)
    group: str = 'stem'
    alternative: Literal['A', 'B', 'C', 'D', 'E'] | None = None


class LayoutLink(Contract):
    source: str
    target: str
    relation: Literal['caption_of', 'credit_of']


class LayoutExample(Contract):
    id: str
    split_group: str
    split: Literal['train', 'development', 'test']
    pattern: str
    difficult: bool
    source_path: str
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    regions: list[Region] = Field(min_length=1)
    blocks: list[LayoutBlock] = Field(min_length=1)
    links: list[LayoutLink]
    annotation: str = Field(min_length=10)
    review_status: Literal['technical_annotation'] = 'technical_annotation'
    independent_review: Literal[False] = False

    @model_validator(mode='after')
    def coherent(self):
        ids = {b.id for b in self.blocks}
        if len(ids) != len(self.blocks) or sorted(b.order for b in self.blocks) != list(range(len(self.blocks))):
            raise ValueError('Identificadores e ordem dos blocos precisam ser únicos.')
        for b in self.blocks:
            if not any(
                r.page == b.page
                and r.bbox[0] <= b.bbox[0] + 2
                and r.bbox[1] <= b.bbox[1] + 2
                and r.bbox[2] >= b.bbox[2] - 2
                and r.bbox[3] >= b.bbox[3] - 2
                for r in self.regions
            ):
                raise ValueError('Bloco fora da região anotada.')
        types = {b.id: b.type for b in self.blocks}
        if any(
            link.source not in ids
            or types.get(link.target) != 'image'
            or types.get(link.source) != link.relation.removesuffix('_of')
            for link in self.links
        ):
            raise ValueError('Vínculo de figura inválido.')
        return self


class LayoutReference(Contract):
    schema_version: Literal['1.0'] = '1.0'
    version: Literal['layout-reference-v1'] = 'layout-reference-v1'
    coordinate_system: Literal['PDF points; top-left origin; page rotation applied']
    annotation_policy: str
    examples: list[LayoutExample]

    @model_validator(mode='after')
    def separated(self):
        groups, pages = {}, {}
        if len({x.id for x in self.examples}) != len(self.examples):
            raise ValueError('Exemplo repetido.')
        for example in self.examples:
            if groups.setdefault(example.split_group, example.split) != example.split:
                raise ValueError('Identidade presente em mais de uma partição.')
            for page in {r.page for r in example.regions}:
                key = (example.source_sha256, page)
                if pages.setdefault(key, example.split) != example.split:
                    raise ValueError('Página presente em mais de uma partição de layout.')
        return self


class LayoutProposal(Contract):
    schema_version: Literal['1.0']
    id: str
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    regions: list[Region] = Field(min_length=1)
    blocks: list[LayoutBlock]
    links: list[LayoutLink]
    origin: dict[str, str]
    table_structures: list[dict]
    review_status: Literal['proposed']
    needs_review: Literal[True]
