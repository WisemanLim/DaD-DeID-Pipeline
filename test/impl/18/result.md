# impl/18 — 포털 E2E 파이프라인 UI 시험 결과

- 실행일: 2026-07-23
- 판정: **PASS**

| # | 케이스 | 결과 |
|---|---|---|
| 1 | 작성자 정정 | PASS — PRD.md·PRD.v2.md 모두 `Wiseman.Lim` |
| 2 | `vitest run` | PASS — 7 tests (metrics 3 + pipeline 4) |
| 3 | `next build` | PASS — `/pipeline`(ƒ)·`/api/process`·`/api/search` 라우트 생성 |
| 4 | `curl :3000/pipeline` | PASS — 200 |
| 5 | E2E 텍스트(제조 영업비밀) | PASS — doc_level=TRADE_SECRET, 검출 4건(PRIV_ID_KR_IN_001·PRIV_KR_055·DICT_catalyst_ratio_secret·DICT_process_param_secret), transform=RANGE_BUCKET+REMOVE+TOKENIZE, 인덱싱 완료 |
| 6 | PUBLIC 문단 | PASS — doc_level=PUBLIC, namespace=PUBLIC, export_blocked=false |
| 7 | 외부반출 게이트 | PASS — external=true 시 export_blocked_count=1 (민감 청크 차단) |
| 8 | CORS 회피 | PASS — 브라우저는 `/api/process`·`/api/search`(Next 서버 라우트)만 호출, 서버에서 deid/rag 프록시 |

## 메모
- deid 첫 호출 `deid.detect` 스팬 ~19.5s (spaCy NER + torch/sentence-transformers 콜드 로드). 이후 호출은 수백 ms. → README 트러블슈팅 기록.
- 내부 검색에서 비식별 용어("촉매")는 변환 치환(⟨RANGE_BUCKET⟩)돼 매칭 0건 — 의도된 비식별 동작.
- 이미지(OCR) 경로는 UI/서버 라우트/`deid /process-image` 배선 완료. 실제 OCR 은 tesseract 바이너리 설치 시 동작(미설치 시 deid 측 폴백).

## 범위 밖(다음 단계)
- 검색 임베딩 품질 튜닝(PRD Out of Scope), 업로드 인증/권한(bff 연동), 대용량 파일 스트리밍.

## 생성/수정 파일
- `.docs/PRD.md`, `.docs/PRD.v2.md` — 작성자 정정, §3 ⓖ 추가, 변경 이력.
- `apps/portal/lib/pipeline.ts` — deid/rag 프록시 + payload 매퍼.
- `apps/portal/app/api/process/route.ts`, `apps/portal/app/api/search/route.ts` — 서버 라우트.
- `apps/portal/app/pipeline/page.tsx`, `apps/portal/app/pipeline/PipelineClient.tsx` — UI.
- `apps/portal/app/page.tsx` — 대시보드↔파이프라인 내비 링크.
- `apps/portal/lib/pipeline.test.ts` — 단위 테스트.
- `test/impl/18/{scenario,result}.md`.
