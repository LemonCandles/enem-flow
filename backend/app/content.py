"""Content contracts, publication gates, and immutable versions."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .db import ROOT
from .models import Exam, QuestionVersion, Review
from .schemas import ExamImport
from .presentation import readable_content
from .preparation import blocking_issues


def validate_assets(content: dict):
    assets = list(content.get("images", []))
    assets.extend(a["image"] for a in content["alternatives"] if a.get("image"))
    assets.extend(block["asset"] for block in content.get("blocks", []) if block["type"] == "image")
    root = (ROOT / "data/assets").resolve()
    for asset in assets:
        path = (ROOT / "data" / asset["path"].lstrip("/")).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(422, f"Imagem ausente: {asset['path']}")


def import_exam(db: Session, payload: ExamImport):
    if db.get(Exam, payload.id):
        raise HTTPException(409, "Esta prova já foi importada. Use a edição versionada.")
    items = []
    for question in payload.questions:
        content = question.content.model_dump()
        validate_assets(content)
        version_id = f"{question.question_id}:1"
        previous = db.get(QuestionVersion, version_id)
        if previous and previous.content != content:
            raise HTTPException(409, "Questão canônica existente com conteúdo diferente.")
        if not previous:
            db.add(QuestionVersion(id=version_id, question_id=question.question_id, version=1, content=content))
        items.append(version_id)
    exam = Exam(**payload.model_dump(exclude={"questions", "schema_version"}), items=items, status="draft")
    db.add(exam)
    db.flush()
    return exam


def exam_summary(db: Session, exam: Exam):
    questions = [db.get(QuestionVersion, key) for key in exam.items]
    return {"id": exam.id, "title": exam.title, "year": exam.year,
            "application": exam.application, "booklet": exam.booklet, "day": exam.day,
            "kind": exam.kind, "expected_items": exam.expected_items, "item_count": len(exam.items),
            "duration_minutes": exam.duration_minutes, "status": exam.status,
            "areas": sorted({q.content["area"] for q in questions}),
            "approved_items": sum(q.status == "approved" for q in questions),
            "source": exam.source}


def publish_exam(db: Session, exam: Exam, user_id: str, reason: str):
    if len(exam.items) != exam.expected_items:
        raise HTTPException(409, "A prova está incompleta para o total declarado.")
    for key in exam.items:
        question = db.get(QuestionVersion, key)
        if not question or question.status != "approved":
            raise HTTPException(409, "Todas as versões precisam de aprovação antes da publicação.")
        if blocking_issues(question.content):
            raise HTTPException(409, "Há pendências bloqueantes de preparação. Corrija e revise as versões antes de publicar.")
        validate_assets(question.content)
    exam.status = "published"
    db.add(Review(user_id=user_id, target_id=exam.id, action="publish", reason=reason))


def public_question(item: dict, finished: bool):
    # Build an explicit allowlist: never serialize the answer key or opaque layout metadata.
    content = readable_content(item['question_id'], item["content"])
    out = {key: content[key] for key in ("number", "area", "statement", "images", "alternatives", "labels", "page", "original_layout")}
    out['blocks'] = content.get('blocks', [])
    out.update(id=item["id"], question_id=item["question_id"], version=item["version"])
    if finished:
        out.update(correct_answer=content["correct_answer"], annulled=content["annulled"])
    return out
