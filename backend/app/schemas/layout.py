"""Layout proposals received by curation: the experimental contract plus the target question version."""

from typing import Literal

from pydantic import Field

from .base import Schema


class LayoutRegion(Schema):
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]


class LayoutBlockIn(LayoutRegion):
    id: str = Field(min_length=1, max_length=40)
    type: Literal['paragraph', 'credit', 'caption', 'math', 'image', 'table', 'alternative']
    text: str = Field(default='', max_length=30000)
    order: int = Field(ge=0)
    group: str = Field(default='stem', max_length=40)
    alternative: Literal['A', 'B', 'C', 'D', 'E'] | None = None
    # Image blocks point to a cropped figure already stored under data/assets.
    asset: str | None = Field(default=None, max_length=300)
    alt: str = Field(default='', max_length=1000)


class LayoutLinkIn(Schema):
    source: str
    target: str
    relation: Literal['caption_of', 'credit_of']


class LayoutProposalImport(Schema):
    schema_version: Literal['1.0']
    question_version: str = Field(min_length=3, max_length=100)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    content_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    regions: list[LayoutRegion] = Field(min_length=1, max_length=20)
    blocks: list[LayoutBlockIn] = Field(min_length=1, max_length=200)
    links: list[LayoutLinkIn] = Field(default_factory=list, max_length=100)
    table_structures: list[dict] = Field(default_factory=list, max_length=20)
    origin: dict[str, str] = Field(default_factory=dict)
    review_status: Literal['proposed']
    needs_review: Literal[True]


class LayoutReview(Schema):
    action: Literal['approve', 'reject']
    reason: str = Field(min_length=10, max_length=2000)
    compared_with_source: bool = False
