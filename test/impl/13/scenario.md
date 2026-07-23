# test/impl/13 — Tika/GROBID 외부 파서 어댑터 시나리오

대상: deid `app/external_parsers.py`(Tika/GROBID HTTP) + `parsers.parse_document` 폴백 결선.
러너: `cd services/deid && uv run pytest tests/test_external_parsers.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | TIKA_URL 미설정 | tika_extract | None |
| S2 | GROBID_URL 미설정 | grobid_extract | None |
| S3 | TIKA_URL 설정+미가용 | tika_extract | None (graceful, 예외 없음) |
| S4 | 외부 미설정 + DOCX | parse_document | python-docx 폴백, RRN 추출 |
| S5 | TIKA_URL 미가용 + TXT | parse_document | 폴백 평문 디코드 |

## 설계 메모
- 라우팅: 과학 PDF → GROBID 우선 → Tika → 로컬(pypdf/docx) → 평문
- 서버 미설정/미가용 시 항상 graceful 폴백 (8s 타임아웃, 예외 삼킴)
- 엔진 자체개발 안 함(PRD Out-of-scope) — HTTP 어댑터만, 실 Tika/GROBID 컨테이너는 운영 배포 시
