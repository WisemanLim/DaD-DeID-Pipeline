# test/impl/6 — OCR/이미지 경로 (Epic 3) 시나리오

대상: `app/ocr.py`(Tesseract 어댑터) + deid `POST /process-image` (OCR→비식별).
러너: `cd services/deid && uv run pytest tests/test_ocr.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | 설치된 tesseract langdata | `_available_lang()` | eng 또는 kor 포함 |
| S2 | RRN 텍스트 이미지 | `ocr_image()` | 텍스트 추출, mean_confidence>0 |
| S3 | RRN 이미지 base64 | `/process-image` | document_type=image/ocr, ocr_mean_confidence 반환, OCR 정확 시 RRN 제거+RESTRICTED |

## 도메인 compliance 매핑 (PRD 시나리오3)
- 손글씨/이미지 문서 OCR 후 동일 비식별(applies_to=OCR) — RRN 제거 검증
- 신뢰도 임계(<60) 미만 → low_confidence 플래그(손글씨 편차 재검 권고)
