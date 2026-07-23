"""OCR 어댑터 (Epic 3) — 이미지/손글씨 → 텍스트 → 동일 비식별 적용.

PRD §3 ⓓ / 시나리오3: 이미지 문서 OCR 후 applies_to=OCR/IMAGE_CAPTION 룰 적용.
엔진 = Tesseract(pytesseract). 엔진 자체개발 안 함(PRD Out of scope) — 어댑터만.
lang 자동: kor 설치 시 'kor+eng', 아니면 'eng'. 신뢰도 임계 미만 토큰은 재검 플래그.
"""
from __future__ import annotations

import io
from functools import lru_cache


@lru_cache(maxsize=1)
def _available_lang() -> str:
    """설치된 traineddata 기준 OCR 언어 결정."""
    try:
        import pytesseract
        langs = set(pytesseract.get_languages(config=""))
    except Exception:  # noqa: BLE001
        return "eng"
    if "kor" in langs:
        return "kor+eng" if "eng" in langs else "kor"
    return "eng"


class OcrResult:
    def __init__(self, text: str, mean_confidence: float, low_confidence: bool):
        self.text = text
        self.mean_confidence = mean_confidence
        self.low_confidence = low_confidence


def ocr_image(image_bytes: bytes, conf_threshold: float = 60.0) -> OcrResult:
    """이미지 바이트 → OCR 텍스트 + 평균 신뢰도. 임계 미만이면 재검 플래그(손글씨 편차 대비)."""
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    lang = _available_lang()
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

    words, confs = [], []
    for word, conf in zip(data["text"], data["conf"], strict=False):
        if word.strip():
            words.append(word)
            try:
                c = float(conf)
            except (TypeError, ValueError):
                c = -1
            if c >= 0:
                confs.append(c)
    text = " ".join(words)
    mean_conf = round(sum(confs) / len(confs), 2) if confs else 0.0
    return OcrResult(text=text, mean_confidence=mean_conf, low_confidence=mean_conf < conf_threshold)
