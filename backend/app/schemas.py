import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Schema):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_address(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Informe um e-mail válido.")
        return value.casefold()


class Register(Login):
    name: str = Field(min_length=2, max_length=80)


class Preferences(Schema):
    name: str = Field(min_length=2, max_length=80)
    target_course: str = Field(default="", max_length=120)
    daily_goal: int = Field(default=10, ge=1, le=100)


class ResetPassword(Schema):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=10, max_length=128)


class Source(Schema):
    url: str = Field(max_length=1000, pattern=r"^https://")
    answer_key_url: str = Field(max_length=1000, pattern=r"^https://")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    answer_key_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    publisher: str = Field(max_length=100)
    notes: str = Field(default="", max_length=3000)


class Asset(Schema):
    path: str = Field(pattern=r"^/assets/[a-zA-Z0-9_./-]+\.(png|jpg|webp)$")
    alt: str = Field(min_length=5, max_length=3000)

    @field_validator("path")
    @classmethod
    def safe_path(cls, value):
        if ".." in value or "//" in value:
            raise ValueError("Caminho de imagem inválido.")
        return value


class Alternative(Schema):
    letter: Literal["A", "B", "C", "D", "E"]
    text: str = Field(default="", max_length=10000)
    image: Asset | None = None


class ParagraphBlock(Schema):
    type: Literal["paragraph"]
    text: str = Field(min_length=1, max_length=30000)


class ImageBlock(Schema):
    type: Literal["image"]
    asset: Asset


class MathBlock(Schema):
    type: Literal["math"]
    tex: str = Field(min_length=1, max_length=8000)


class TableBlock(Schema):
    type: Literal["table"]
    headers: list[str] = Field(min_length=1, max_length=12)
    rows: list[list[str]] = Field(min_length=1, max_length=100)
    caption: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def rectangular(self):
        if any(len(row) != len(self.headers) for row in self.rows):
            raise ValueError("Todas as linhas precisam corresponder às colunas da tabela.")
        if any(len(cell) > 3000 for row in self.rows for cell in row):
            raise ValueError("Célula de tabela longa demais.")
        return self


ContentBlock = Annotated[ParagraphBlock | ImageBlock | MathBlock | TableBlock, Field(discriminator="type")]


class Labels(Schema):
    discipline: str | None = Field(default=None, max_length=100)
    themes: list[str] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=20)
    taxonomy_version: str = Field(default="manual-v1", max_length=80)
    provenance: str = Field(default="Revisão manual", max_length=200)


class QuestionContent(Schema):
    number: int = Field(ge=1, le=1000)
    area: Literal["Matemática", "Ciências da Natureza", "Ciências Humanas", "Linguagens"]
    statement: str = Field(min_length=5, max_length=30000)
    blocks: list[ContentBlock] = Field(default_factory=list, max_length=100)
    images: list[Asset] = Field(default_factory=list, max_length=20)
    alternatives: list[Alternative] = Field(min_length=5, max_length=5)
    correct_answer: Literal["A", "B", "C", "D", "E"] | None
    annulled: bool = False
    labels: Labels = Field(default_factory=Labels)
    page: int = Field(ge=1)
    # Fallback to the approved original region preserves complex spatial semantics.
    original_layout: bool = False
    layout: dict | None = None

    @model_validator(mode="after")
    def consistent(self):
        if [a.letter for a in self.alternatives] != list("ABCDE"):
            raise ValueError("As alternativas devem seguir a ordem A a E.")
        if self.annulled != (self.correct_answer is None):
            raise ValueError("Uma questão anulada não tem gabarito; as demais precisam de gabarito.")
        if any(not a.text and not a.image for a in self.alternatives) and not (self.original_layout and self.images):
            raise ValueError("Alternativas vazias exigem uma representação original.")
        if any(len(v) > 150 for v in self.labels.themes + self.labels.skills):
            raise ValueError("Rótulo longo demais.")
        return self


class ImportQuestion(Schema):
    question_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    content: QuestionContent


class ExamImport(Schema):
    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    title: str = Field(min_length=5, max_length=160)
    year: int = Field(ge=1998, le=2100)
    application: str = Field(min_length=2, max_length=80)
    booklet: str = Field(min_length=2, max_length=80)
    day: int = Field(ge=1, le=2)
    kind: Literal["complete", "section", "collection"]
    expected_items: int = Field(ge=1, le=200)
    duration_minutes: int = Field(ge=1, le=600)
    source: Source
    questions: list[ImportQuestion] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_items(self):
        if len({q.question_id for q in self.questions}) != len(self.questions):
            raise ValueError("Questão canônica duplicada.")
        if len({q.content.number for q in self.questions}) != len(self.questions):
            raise ValueError("Numeração duplicada.")
        if len(self.questions) > self.expected_items:
            raise ValueError("Há mais itens que o total declarado.")
        return self


class StartRun(Schema):
    exam_id: str = Field(max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=80)


class Answer(Schema):
    choice: Literal["A", "B", "C", "D", "E"] | None


class ReviewRequest(Schema):
    action: Literal["approve", "reject", "withdraw", "publish"]
    reason: str = Field(min_length=10, max_length=2000)


class EditQuestion(Schema):
    content: QuestionContent
    reason: str = Field(min_length=10, max_length=2000)
