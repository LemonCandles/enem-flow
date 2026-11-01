"""Reproduce the faithful original-region fallback for the bundled official exam.

Run from the repository root after obtaining the two source PDFs. Layout exceptions
are explicit and were checked against the original pages; extraction fails closed.
"""
import hashlib
import json
import re
from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul"
OUT = ROOT / "data/assets/enem-2024-dia2-azul"
PDF = SOURCES / "prova.pdf"
KEY = SOURCES / "gabarito.pdf"
FULL_WIDTH_PAGES = {15, 23, 26, 27, 28}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    key_text = "\n".join(p.get_text() for p in fitz.open(KEY))
    answers = {int(n): None if a == "Anulado" else a for n, a in re.findall(r"\b(\d{2,3})\s*\n\s*(Anulado|[ABCDE])\b", key_text)}
    assert set(answers) == set(range(91, 181)), "Gabarito incompleto ou inesperado"
    regions = {}
    current = None
    for page in list(doc)[1:31]:
        page_number = page.number + 1
        columns = [(31, 538)] if page_number in FULL_WIDTH_PAGES else [(31, 279), (289, 538)]
        blocks = page.get_text("blocks")
        for left, right in columns:
            headings = []
            for block in blocks:
                match = re.match(r"QUESTÃO\s+(\d+)", block[4])
                if match and left <= block[0] < right:
                    headings.append((block[1], int(match.group(1))))
            headings.sort()
            # The previous question can continue in the next column (113 and 155).
            top = 64
            for heading_index, (y, number) in enumerate(headings):
                if y > top + 5 and current is not None and (heading_index > 0 or y > 110):
                    clip = fitz.Rect(left, top, right, y - 3)
                    if page.get_text(clip=clip).strip():
                        regions[current].append((page_number, clip))
                if number in regions:
                    raise ValueError(f"Cabeçalho duplicado: {number}")
                regions[number] = []
                current, top = number, y - 1
            if current is not None:
                clip = fitz.Rect(left, top, right, 746)
                if page.get_text(clip=clip).strip():
                    regions[current].append((page_number, clip))
    assert set(regions) == set(answers), "Questões extraídas não correspondem ao gabarito"
    questions = []
    for number, pieces in sorted(regions.items()):
        images, texts, layout_blocks = [], [], []
        for index, (page_number, clip) in enumerate(pieces):
            page = doc[page_number - 1]
            text = page.get_text(clip=clip).strip()
            # No footer/watermark is allowed inside an item.
            assert "ENEM2024ENEM2024" not in text, (number, page_number)
            name = f"q{number}-{index + 1}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip)
            # Remove only trailing all-white scanlines; every original ink pixel is retained.
            samples, bottom = pix.samples, pix.height
            white_row = b"\xff" * pix.stride
            while bottom > 1 and samples[(bottom - 1) * pix.stride:bottom * pix.stride] == white_row:
                bottom -= 1
            clip.y1 = min(clip.y1, clip.y0 + bottom / 2.5 + 4)
            page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip).save(OUT / name)
            images.append({"path": f"/assets/enem-2024-dia2-azul/{name}",
                           "alt": f"Questão {number}, trecho {index + 1} do original oficial, página {page_number}. Inclui os textos, as figuras e as alternativas na disposição original."})
            texts.append(text)
            layout_blocks.append({"id": f"q{number}-region-{index + 1}", "type": "original_region",
                                  "page": page_number, "bbox": list(clip), "reading_order": index,
                                  "coordinate_system": "PDF points, top-left origin"})
        statement = "\n\n".join(texts)
        area = "Ciências da Natureza" if number < 136 else "Matemática"
        questions.append({"question_id": f"enem-2024-regular-q{number}", "content": {
            "number": number, "area": area, "statement": statement, "images": images,
            "alternatives": [{"letter": letter, "text": f"Alternativa {letter} do enunciado original"} for letter in "ABCDE"],
            "correct_answer": answers[number], "annulled": answers[number] is None,
            "labels": {"discipline": "Matemática" if number >= 136 else None, "themes": [], "skills": [],
                       "taxonomy_version": "manual-v1", "provenance": "Área e disciplina de Matemática identificadas pelo caderno oficial. Temas e habilidades aguardam revisão."},
            "page": pieces[0][0], "original_layout": True,
            "layout": {"schema_version": "1.0", "blocks": layout_blocks, "review_status": "original_fallback"}
        }})
    data = {"schema_version": "1.0", "id": "enem-2024-dia2-azul", "title": "ENEM 2024 · 2º dia",
            "year": 2024, "application": "Regular", "booklet": "Caderno 7 · Azul", "day": 2,
            "kind": "complete", "expected_items": 90, "duration_minutes": 300,
            "source": {"url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D2_CD7.pdf",
                       "answer_key_url": "https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D2_CD7.pdf",
                       "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
                       "answer_key_sha256": hashlib.sha256(KEY.read_bytes()).hexdigest(), "publisher": "Inep",
                       "notes": "Caderno completo do segundo dia (90 questões). Questão 129 anulada no gabarito oficial. Apresentação por recortes do original para preservar fórmulas e figuras. Temas e habilidades ainda não classificados. Produto independente, sem vínculo com o Inep."},
            "questions": questions}
    (ROOT / "data/enem-2024-dia2-azul.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    expected_files = {Path(image["path"]).name for q in questions for image in q["content"]["images"]}
    for generated in OUT.glob("q*-*.png"):
        if generated.name not in expected_files:
            generated.unlink()
    print(f"Geradas {len(questions)} questões, {sum(len(q['content']['images']) for q in questions)} recortes; 1 anulada.")


if __name__ == "__main__":
    main()
