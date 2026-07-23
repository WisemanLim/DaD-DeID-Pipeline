# test/impl/8 — 거버넌스 대시보드 (Epic 6 ⓕ) 시나리오

대상: `apps/portal` Next 대시보드 — deid/rag `/metrics` 소비 KPI 카드.
러너: `pnpm --filter portal test` (vitest) + `pnpm --filter portal build` (Next 컴파일/타입).

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | deid+rag 메트릭 객체 | formatKpis | 6개 KPI 카드, 값 정규화(12, 100%, 5, 7) |
| S2 | 빈 메트릭 | formatKpis | 0 / 0% 기본값, 6개 유지 |
| S3 | KPI 배열 | source 태그 | deid/rag 출처 구분 |
| S4 | Next App Router 페이지 | `next build` | 컴파일·타입체크 성공, `/` 라우트 생성 |

## 도메인 compliance 매핑 (PRD §5 / §3 ⓕ)
- 대시보드 KPI = entities_detected_total·transform_rate_avg·documents_processed_total·restricted_chunks_total(deid) + llm_sensitive_block_total·chunks_indexed_total(rag)
- 거버넌스/보안 담당자용 변환율·차단율 모니터링(PRD 타깃 사용자)
