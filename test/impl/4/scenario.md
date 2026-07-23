# test/impl/4 — 거버넌스 관측 (Epic 6) 시나리오

대상: deid `app/observability.py`(Langfuse 호환 trace + KPI 메트릭) + `/process` trace + `/metrics`, rag `/metrics`.
러너: `cd services/deid && uv run pytest` + `cd services/rag && uv run pytest`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | MetricsRegistry detected=transformed=4 | snapshot | transform_rate_avg=1.0, 빈 레지스트리=0.0(0분모 가드) |
| S2 | TraceRecorder span | span 기록 | tags 보존, span name·metadata·duration 기록 |
| S3 | RRN 문서 `/process` | trace 검사 | PRD §7 태그(industry·document·policy) + span {deid.detect, deid.transform} |
| S4 | `/process` 호출 | `/metrics` | documents_processed_total +1, entities_detected_total≥1, transform_rate_avg 존재 |
| S5 | rag external 검색 차단 | `/metrics` | llm_sensitive_block_total≥1, chunks_indexed_total≥1 |

## 도메인 compliance 매핑 (PRD §5 운영지표)
- entities_detected_total / transform_rate_avg — 검출·변환율
- **llm_sensitive_block_total** — RESTRICTED/TRADE_SECRET 외부반출 차단 건수 (의료/제조/금융)
- documents_processed_total — 처리량(OTel 메트릭 대응)
