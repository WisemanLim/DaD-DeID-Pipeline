# impl/18 — 포털 E2E 파이프라인 UI (PRD §1 한 줄 요약 / §3 ⓖ) 시험 시나리오

기존 portal(:3000)은 대시보드 전용. PRD §1 한 줄 요약 전 과정(업로드→파싱/OCR→검출→정책
변환→분리 인덱싱→검색)을 웹에서 직접 실행하도록 UI + Next.js 서버 라우트(deid/rag 프록시)를 추가.
작성자 표기도 Wiseman.Lim 으로 정정.

## 케이스

| # | 케이스 | 명령/행위 | 기대 |
|---|---|---|---|
| 1 | 작성자 정정 | `grep 작성자 .docs/PRD.md .docs/PRD.v2.md` | 둘 다 `Wiseman.Lim` |
| 2 | 단위 테스트(payload 매퍼) | `vitest run` (portal) | metrics 3 + pipeline 4 = 7 pass |
| 3 | 프로덕션 빌드/타입체크 | `next build` | 성공, `/pipeline`·`/api/process`·`/api/search` 라우트 생성 |
| 4 | 파이프라인 페이지 서빙 | `curl :3000/pipeline` | 200 |
| 5 | E2E 텍스트(제조 영업비밀) | `POST /api/process` text, manufacturing-chemical, 주민+카드+촉매비율 | doc_level=TRADE_SECRET, 검출 4건, transform_action=RANGE_BUCKET+REMOVE+TOKENIZE, 청크 rag 인덱싱 |
| 6 | PUBLIC 문단 | `POST /api/process` 공개 문단 | doc_level=PUBLIC, namespace=PUBLIC, export_blocked=false |
| 7 | 외부반출 게이트 | `POST /api/search external=true` | RESTRICTED/TRADE_SECRET 청크 차단(export_blocked_count≥1) |
| 8 | CORS 회피 | 브라우저→`/api/*`(서버)→deid/rag | deid/rag 직접 호출 없음(서버 프록시) |
