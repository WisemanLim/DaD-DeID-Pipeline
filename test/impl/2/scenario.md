# test/impl/2 — 분리 인덱싱 (Epic 4) 시나리오

대상: `services/rag` VectorStore(민감도 namespace 분리) + 테넌트 격리 + 외부반출 게이트.
러너: `cd services/rag && uv run pytest`.

## 시나리오

| # | Given | When | Then (수용 기준) |
|---|---|---|---|
| S1 | PUBLIC/RESTRICTED/TRADE_SECRET 청크 | `/index` ×3 | namespace 3개로 분리 (`{PUBLIC:1,RESTRICTED:1,TRADE_SECRET:1}`) |
| S2 | RESTRICTED 청크 | `/search external=false` | 내부검색은 민감 청크 반환, blocked=0 |
| S3 | RESTRICTED+TRADE_SECRET+PUBLIC | `/search external=true` | 민감 2건 차단, PUBLIC만 반환, `export_blocked_count=2` |
| S4 | proj-A·proj-B 동일내용 청크 | `/search project_id=proj-A` | proj-A 1건만 (크로스테넌트 누출 0) |
| S5 | 동일 chunk_id 2회 upsert | namespaces | 1건만 (멱등) |
| S6 | TRADE_SECRET 청크 | `/index` | `export_blocked=true` |

## 도메인 compliance 매핑 (COMPLIANCE.md)
- 의료(Q)/제조(C): S3 — RESTRICTED/TRADE_SECRET 외부 LLM 반출 차단
- ict-saas(J): S4 — 크로스테넌트 데이터 누출 차단(RLS 등가)
