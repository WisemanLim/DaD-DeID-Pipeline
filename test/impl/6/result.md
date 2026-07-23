# test/impl/6 — 결과 / result

- 실행일: 2026-06-09
- 판정: **PASS** (deid 22/22 · ruff clean · OCR 3/3)

```
22 passed   (기존 19 + OCR 3)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_available_lang | PASS |
| S2 | test_ocr_extracts_text | PASS (conf 91) |
| S3 | test_process_image_deidentifies_ocr_text | PASS (document_type=image/ocr) |

## 검증 (실측)
```
이미지 "ID 900101-1234567" → OCR text='ID 900101-1234567' conf=91.0 → RRN 정확 인식
→ /process-image → 산출물에 RRN 미잔존, doc_sensitivity=RESTRICTED
```
(RRN 제거 분기 실제 실행 확인 — OCR 정확도 충분)

## 구현
- `app/ocr.py` — Tesseract(pytesseract) 어댑터. lang 자동(kor 설치 시 kor+eng), 평균 신뢰도·low_confidence 플래그
- deid `POST /process-image` — base64 이미지 → OCR → pipeline.process(document_type=image/ocr)
- 의존성: pytesseract, pillow + 시스템 tesseract 5.5.2 + tesseract-lang(kor)

## 수정 이력
- 없음.

## 한계 / 잔여
- 손글씨 실인식 정확도는 Tesseract 한계(인쇄체 대비 낮음) — 신뢰도 임계 재검 플래그로 대응, 전용 손글씨 모델 후속.
- PDF/DOCX 파서(Tika/Unstructured/GROBID) 연동은 후속 — 현재 이미지(PNG/JPG) 경로만.
