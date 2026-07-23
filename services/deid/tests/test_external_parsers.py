"""외부 파서(Tika/GROBID) 어댑터 + 폴백 시험 (impl/13)."""
import io

from docx import Document

from app.external_parsers import grobid_extract, tika_extract
from app.parsers import parse_document


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_tika_noop_when_unset(monkeypatch):
    monkeypatch.delenv("TIKA_URL", raising=False)
    assert tika_extract(b"data") is None


def test_grobid_noop_when_unset(monkeypatch):
    monkeypatch.delenv("GROBID_URL", raising=False)
    assert grobid_extract(b"data") is None


def test_tika_unreachable_returns_none(monkeypatch):
    """설정됐으나 서버 미가용 → None(graceful, 예외 없음)."""
    monkeypatch.setenv("TIKA_URL", "http://127.0.0.1:59999")
    assert tika_extract(b"data") is None


def test_parse_document_falls_back_to_local(monkeypatch):
    """외부 서버 미설정 → 로컬 python-docx 폴백."""
    monkeypatch.delenv("TIKA_URL", raising=False)
    monkeypatch.delenv("GROBID_URL", raising=False)
    out = parse_document(_docx_bytes("환자 900101-1234567"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "900101-1234567" in out


def test_parse_document_tika_fallback_on_unreachable(monkeypatch):
    """TIKA_URL 설정+미가용 → 폴백 동작(평문)."""
    monkeypatch.setenv("TIKA_URL", "http://127.0.0.1:59999")
    out = parse_document("hello 010-1234-5678".encode(), "text/plain")
    assert "010-1234-5678" in out
