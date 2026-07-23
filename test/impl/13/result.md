# test/impl/13 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (deid 49/49 · rag 14/14[pgvector 포함] · portal 3/3 · ruff clean)

```
external_parsers: 5 passed
전체: deid 49 + rag 14 + portal 3 = 66 PASS
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_tika_noop_when_unset | PASS |
| S2 | test_grobid_noop_when_unset | PASS |
| S3 | test_tika_unreachable_returns_none | PASS (graceful) |
| S4 | test_parse_document_falls_back_to_local | PASS |
| S5 | test_parse_document_tika_fallback_on_unreachable | PASS |

## 구현
- `app/external_parsers.py` — `tika_extract`(PUT /tika), `grobid_extract`(POST /api/processFulltextDocument, TEI 태그제거). stdlib urllib, 8s 타임아웃, 미설정/실패 None
- `parsers.parse_document` — 라우팅: 과학PDF→GROBID→Tika→로컬(pypdf/docx)→평문, 항상 graceful 폴백

## 수정 이력
- 없음.

## 한계 / 잔여
- 실 Tika/GROBID 서버 연동 테스트는 컨테이너 필요(운영 배포 시). 오프라인은 폴백 경로 검증.
- TEI 본문 추출은 태그 제거(경량) — 구조적 섹션 분리는 후속.
