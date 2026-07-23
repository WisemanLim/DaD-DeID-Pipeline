"""OCR 경로 시험 (Epic 3) — 이미지 → OCR → 비식별 (PRD §3 ⓓ / 시나리오3)."""
import base64
import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app
from app.ocr import _available_lang, ocr_image

client = TestClient(app)


def _text_image(text: str) -> bytes:
    """고대비 큰 텍스트 이미지 생성(OCR 신뢰도 확보)."""
    font = ImageFont.load_default(size=32)        # Pillow 10+ 스케일러블 기본폰트
    img = Image.new("RGB", (760, 90), "white")
    ImageDraw.Draw(img).text((12, 28), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_available_lang():
    assert "eng" in _available_lang() or "kor" in _available_lang()


def test_ocr_extracts_text():
    out = ocr_image(_text_image("ID 900101-1234567"))
    assert out.text.strip()
    assert out.mean_confidence > 0


def test_process_image_deidentifies_ocr_text():
    """이미지 OCR 산출물에도 비식별 적용 — RRN 제거 + document_type=image/ocr."""
    img_b64 = base64.b64encode(_text_image("ID 900101-1234567")).decode()
    r = client.post("/process-image", json={
        "image_base64": img_b64, "document_id": "imgA",
        "industry_code": "healthcare-clinical", "project_id": "proj-A",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["trace"]["tags"]["document_type"] == "image/ocr"
    assert "ocr_mean_confidence" in body
    # OCR 이 RRN 을 정확히 읽었다면 제거됐어야 함
    ocr_text = ocr_image(base64.b64decode(img_b64)).text
    if "900101-1234567" in ocr_text:
        joined = " ".join(c["text"] for c in body["chunks"])
        assert "900101-1234567" not in joined
        assert body["doc_sensitivity_level"] == "RESTRICTED"
