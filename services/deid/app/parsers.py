"""문서 파서 (PRD Out-of-scope 엔진 활용) — PDF/DOCX/TXT → 텍스트.

PRD: 파서 엔진 자체개발 안 함(Tika/Unstructured/GROBID). 여기선 경량 pypdf/python-docx 어댑터.
추출 텍스트는 /process 파이프라인에 그대로 투입(동일 비식별). 문단 경계는 \\n\\n 로 정규화.
"""
from __future__ import annotations

import io


def parse_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "").strip() for p in reader.pages]
    return "\n\n".join(p for p in pages if p)


def parse_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paras)


def parse_document(data: bytes, content_type: str) -> str:
    """외부 파서(GROBID/Tika, 설정 시) 우선 → 실패 시 pypdf/python-docx/평문 폴백."""
    from app.external_parsers import grobid_extract, tika_extract

    ct = (content_type or "").lower()
    is_pdf = "pdf" in ct
    # 과학 PDF = GROBID 우선
    if is_pdf:
        out = grobid_extract(data)
        if out:
            return out
    # 범용 = Tika
    out = tika_extract(data)
    if out:
        return out
    # --- 로컬 폴백 ---
    if is_pdf:
        return parse_pdf(data)
    if "word" in ct or "docx" in ct or "officedocument" in ct:
        return parse_docx(data)
    return data.decode("utf-8", errors="replace")
