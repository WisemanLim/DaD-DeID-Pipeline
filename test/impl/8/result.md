# test/impl/8 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (portal vitest 3/3 · `next build` 성공)

```
portal vitest: 3 passed
next build:    ✓ Compiled / type-checked, Route / (ƒ dynamic) 생성
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | formatKpis 정규화 | PASS |
| S2 | 빈 메트릭 기본값 | PASS |
| S3 | source 태그 | PASS |
| S4 | next build 컴파일/타입 | PASS |

## 구현
- `apps/portal/lib/metrics.ts` — DeidMetrics/RagMetrics 타입, 순수 `formatKpis()`(6 KPI 정규화), `fetchKpis()`(deid/rag /metrics 병렬 fetch, NEXT_PUBLIC_*_API_BASE)
- `apps/portal/app/page.tsx` — 서버 컴포넌트 대시보드(KPI 카드 그리드, force-dynamic)
- `apps/portal/vitest.config.ts` + `lib/metrics.test.ts`

## 수정 이력
- **빌드 FAIL→PASS**: autocreated tsconfig 에 `@/*` paths 없어 `@/lib/metrics` 미해결.
  `baseUrl="."` + `paths {"@/*":["./*"]}` 추가 후 빌드 성공.

## 실행
- `make run-web` (portal:3000) — deid:8001·rag:8002 기동 시 실시간 KPI 표시.
- 환경: `NEXT_PUBLIC_DEID_API_BASE`·`NEXT_PUBLIC_RAG_API_BASE` (기본 localhost:8001/8002).

## 한계 / 잔여
- 카드 UI 만(차트·시계열 없음). Langfuse trace 뷰 임베드는 후속.
