# test/impl/2 — 결과 / result

- 실행일: 2026-06-09
- 러너: `cd services/rag && uv run pytest -q`
- 판정: **PASS (6/6)** · ruff clean

```
6 passed, 1 warning in 0.10s
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_index_separates_namespaces | PASS |
| S2 | test_internal_search_returns_sensitive | PASS |
| S3 | test_external_search_blocks_sensitive | PASS (의료/제조: 외부반출 차단) |
| S4 | test_tenant_isolation_no_cross_leak | PASS (ict-saas: 크로스테넌트 0) |
| S5 | test_idempotent_upsert | PASS |
| S6 | test_export_blocked_flag | PASS |

## E2E (실서비스 curl)
```
POST /index (RESTRICTED "환자 차트 혈압") + (PUBLIC "공개 혈압 안내")
GET /namespaces → {"PUBLIC":1,"RESTRICTED":1}
POST /search {"query":"혈압","project_id":"proj-A","external":true}
→ hits=[PUBLIC c1], export_blocked_count=1   (RESTRICTED 차단)
```

## 수정 이력
- 없음 (최초 통과).

## 한계 / 잔여
- 임베딩 = 오프라인 결정적 placeholder(토큰 Jaccard). 실 임베딩(pgvector/Qdrant + 임베딩 모델)은 어댑터 교체.
  PRD: 검색 정확도 튜닝은 Out of scope → 핵심(namespace 분리·게이트·테넌트 격리)만 검증.
- store = in-memory. VECTOR_BACKEND=pgvector/qdrant 어댑터 구현은 후속.
- 다음: deid→rag 자동 파이프라인 결선, OCR 경로(Epic 3), Langfuse trace(Epic 6).
