"""문서 파서 + Langfuse sink 시험 (impl/10)."""
import base64
import io

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.langfuse_sink import emit
from app.main import app
from app.observability import Trace
from app.parsers import parse_docx, parse_document

client = TestClient(app)


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_docx():
    out = parse_docx(_docx_bytes("환자 900101-1234567 진료기록"))
    assert "900101-1234567" in out


def test_parse_document_txt_dispatch():
    out = parse_document("안녕 010-1234-5678".encode(), "text/plain")
    assert "010-1234-5678" in out


def test_process_document_docx_deidentifies():
    """DOCX → 파싱 → 비식별 (RRN 제거)."""
    b64 = base64.b64encode(_docx_bytes("환자 900101-1234567")).decode()
    r = client.post("/process-document", json={
        "file_base64": b64,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "document_id": "docX", "industry_code": "healthcare-clinical", "project_id": "p",
    })
    assert r.status_code == 200
    joined = " ".join(c["text"] for c in r.json()["chunks"])
    assert "900101-1234567" not in joined


def test_pdf_writer_empty_ok():
    """pypdf 가용성 + 빈 PDF 파싱 무오류."""
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    w.write(buf)
    out = parse_document(buf.getvalue(), "application/pdf")
    assert isinstance(out, str)


def test_langfuse_sink_noop_offline():
    """LANGFUSE_HOST 미설정 → no-op(False), 예외 없음."""
    assert emit(Trace(tags={"industry_code": "Q"})) is False
