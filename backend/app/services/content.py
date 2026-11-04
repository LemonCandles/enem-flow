"""Content contracts, publication gates, and immutable versions."""

from .errors import Conflict, InvalidContent, NotFound
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import ROOT
from ..models import Exam, QuestionVersion
from ..schemas import ExamImport
from .presentation import readable_content
from ..preparation import blocking_issues
from .identity import identify


def iter_assets(content: dict):
    """Every figure a question shows: loose images, alternatives and blocks."""
    yield from content.get("images", [])
    yield from (a["image"] for a in content["alternatives"] if a.get("image"))
    yield from (block["asset"] for block in content.get("blocks", []) if block["type"] == "image")


def validate_assets(content: dict):
    root = (ROOT / "data/assets").resolve()
    for asset in iter_assets(content):
        path = (ROOT / "data" / asset["path"].lstrip("/")).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise InvalidContent(f"Imagem ausente: {asset['path']}")


def import_exam(db: Session, payload: ExamImport):
    if db.get(Exam, payload.id):
        raise Conflict("Esta prova já foi importada. Use a edição versionada.")
    items, canonical_ids = [], set()
    for question in payload.questions:
        content = question.content.model_dump()
        validate_assets(content)
        canonical_id = identify(db, content, (payload.source.sha256, question.content.number))
        if canonical_id in canonical_ids:
            raise Conflict("A prova contém duas ocorrências da mesma questão canônica.")
        canonical_ids.add(canonical_id)
        version_id = f"{question.question_id}:1"
        previous = db.get(QuestionVersion, version_id)
        if previous and previous.content != content:
            raise Conflict("Questão canônica existente com conteúdo diferente.")
        if not previous:
            db.add(
                QuestionVersion(
                    id=version_id,
                    question_id=question.question_id,
                    canonical_id=canonical_id,
                    version=1,
                    content=content,
                )
            )
        elif previous.canonical_id is None:
            previous.canonical_id = canonical_id
        items.append(version_id)
    exam = Exam(**payload.model_dump(exclude={"questions", "schema_version"}), items=items, status="draft")
    db.add(exam)
    db.flush()
    return exam


def exam_summary(db: Session, exam: Exam):
    # Only area and status are needed; loading every full content made large catalogs slow.
    rows = (
        db.execute(
            select(QuestionVersion.id, QuestionVersion.status, QuestionVersion.content["area"].as_string()).where(
                QuestionVersion.id.in_(exam.items)
            )
        ).all()
        if exam.items
        else []
    )
    found = {key: (status, area) for key, status, area in rows}
    automatic = exam.source.get('automatic_archive', {})
    quality = {
        "origin": "automatic" if automatic else "reviewed",
        "review_status": automatic.get('review_status', 'reviewed'),
        "blocking_issues": automatic.get('blocking_issues', 0),
    }
    return {
        "id": exam.id,
        "title": exam.title,
        "year": exam.year,
        "application": exam.application,
        "booklet": exam.booklet,
        "day": exam.day,
        "kind": exam.kind,
        "expected_items": exam.expected_items,
        "item_count": len(exam.items),
        "duration_minutes": exam.duration_minutes,
        "status": exam.status,
        "areas": sorted({found[key][1] for key in exam.items if key in found}),
        "approved_items": sum(found[key][0] == "approved" for key in exam.items if key in found),
        "source": exam.source,
        "content_quality": quality,
    }


def visible_exam(db: Session, exam_id: str):
    exam = db.get(Exam, exam_id)
    if not exam or exam.status != "published":
        raise NotFound("Prova não encontrada ou ainda em revisão.")
    return exam


def public_exam_summary(db: Session, exam: Exam):
    data = exam_summary(db, exam)
    data["source"] = {key: exam.source[key] for key in ("url", "sha256", "publisher", "notes")}
    return data


def public_question(item: dict, finished: bool):
    # Build an explicit allowlist: never serialize the answer key or opaque layout metadata.
    content = readable_content(item['question_id'], item["content"])
    out = {
        key: content[key]
        for key in ("number", "area", "statement", "images", "alternatives", "labels", "page", "original_layout")
    }
    out['blocks'] = content.get('blocks', [])
    out['preparation_errors'] = len(blocking_issues(content))
    out.update(
        id=item["id"],
        question_id=item["question_id"],
        canonical_id=item.get('canonical_id') or item['question_id'],
        version=item["version"],
    )
    if finished:
        out.update(correct_answer=content["correct_answer"], annulled=content["annulled"])
    return out
