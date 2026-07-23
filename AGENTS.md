# 개발환경 표준 (Wise Dev Standard) — DaD DeID Pipeline

> 이 파일은 Claude Code / Cursor / Antigravity 가 공통으로 읽는 프로젝트 표준이다.
> AI 코딩 도구는 코드·CI·인프라 생성 시 아래 표준을 기본값으로 준수한다.
> 생성: `wise-dev-standard / bio-rag-research` (다도메인). 갱신: `/wise-dev-standard:standardize`.

## 현재 프로젝트 기본 스택 (profile: bio-rag-research)

문서 비식별 파이프라인 모노레포 (PRD `.docs/PRD.v2.md`). 역할 분리형:

| 서비스 | 스택 | 역할 |
|---|---|---|
| `services/deid` | **Python + FastAPI + uv** | 검출(regex+Luhn+spaCy NER+dictionary+classifier judge+LLM judge) + 정책엔진 + 변환 + OCR + 가드레일 + 파이프라인. 포트 8001 |
| `services/rag` | Python + FastAPI + LangChain | 민감도 namespace 분리 인덱싱 + 검색 게이트. VectorStore: in-memory↔pgvector↔qdrant↔weaviate. 포트 8002 |
| `services/worker` | Go | OCR/대량 재색인 워커(선택) |
| `apps/portal` | Next.js 15 + React 19 + TS | 거버넌스 KPI 대시보드 (host dev) |
| `apps/bff` | NestJS 11 | 인증·권한·감사 BFF (host dev) |
| `packages/shared` | JSON Schema | 룰번들·DeidPolicy 스키마, KSIC 매핑 |

- 패키지매니저: **uv**(python) + **pnpm**(node). 실행: `make up`(인프라) / `make run`(uvx honcho deid+rag) / `make run-web`(portal+bff) / `make dev`(compose --profile app).
- DB: local=SQLite / dev+=PostgreSQL+pgvector + Redis. 임베딩: sentence-transformers(다국어 MiniLM) + 해시 폴백.
- 관측: Langfuse 호환 trace + KPI 메트릭(`/metrics`). 외부 서버(Tika/GROBID/Qdrant/Langfuse/Weaviate/Claude API)는 설정 시 사용, 미가용 시 폴백/no-op.

## 우선순위 언어
Node/TypeScript · Python · Rust · Go · C/C++ (동점이면 이 순서).
- Python: 데이터/ML/분석/ETL API, RAG (uv + uvicorn + FastAPI) ← **본 프로젝트 핵심**
- Node/TS: 프론트, BFF/API Gateway · Go: 고처리량 워커 · Rust: 메모리안전 코어

## 패키지 매니저
- Python: **uv** (pyproject.toml + uv.lock) · Node: **pnpm** (monorepo workspaces)
- Go: go modules · Rust: cargo · 금지: forever, yarn/bun 승인제

## 레이어 표준
- Frontend: Next.js(App Router) + React + TS + Tailwind, Vitest + Playwright
- Backend: NestJS / FastAPI / Gin / Axum (ORM: Prisma/SQLAlchemy/GORM/SQLx)
- Database: PostgreSQL(신규 기본) + Redis, local/test 만 SQLite, 벡터=pgvector/Qdrant/Weaviate
- Ops: GitHub Actions, Docker + Compose, K8s + Helm, Argo CD/Flux, SonarQube + Sentry

## 환경 (local / dev / staging / prod)
| 환경 | DB | compose | 핵심 |
|---|---|---|---|
| local | SQLite | 보통 X | 빠른 반복, 외부 의존 최소 |
| dev | PostgreSQL+pgvector | O | 공유 DB + Redis + (profile) minio/qdrant/tika/grobid/langfuse |
| staging | PostgreSQL | O | prod 동등 구성 검증 |
| prod | PostgreSQL | (K8s) | Helm + GitOps, 규제 데이터 분리 VPC |

## 시험 / Testing (표준)
프로젝트 루트 `test/` 에 저장. `test/dev-env/`(환경검증 1회) + `test/impl/<Nth>/`(구현마다).
사이클: 시나리오 작성 → 진행 → 오류 시 수정·재시험 → 결과 작성. 각 차수에 scenario.md·result.md·logs/.
러너: pytest(deid/rag) + Ragas(RAG) + Vitest(portal). 현재 70 케이스 PASS.

## 코드 생성 정책 (AI 도구용)
1. 데이터/ML/비식별 API → FastAPI(uv). 대시보드 → Next.js. BFF → NestJS. 워커 → Go.
2. 신규 DB → PostgreSQL + Redis. 로컬/테스트만 SQLite. 벡터는 VectorStore 추상화로 백엔드 스위치.
3. CI 는 GitHub Actions, K8s 배포는 Helm + GitOps.
4. **시크릿 코드/`.env` 하드코딩 금지** — Vault/Secret Manager/KMS 주입. ANTHROPIC_API_KEY 등 환경변수.
5. 외부 서버 연동은 항상 graceful 폴백(미가용 시 in-memory/pypdf/no-op).

## 업종/업태(도메인) 표준 — 다도메인 (COMPLIANCE.md 준수)

DaD DeID Pipeline 는 **다도메인 문서 비식별 파이프라인**. 베이스라인 `ict-saas`(KSIC J) + 오버레이 합집합
`healthcare`(Q)·`finance`(K)·`manufacturing`(C), 후속 `govtech`(O)·`media-gaming`(R).
**규제 충돌 시 더 강한 쪽 우선.** 상세는 루트 `COMPLIANCE.md`·`SECURITY.md`.

- **한국 규제(1순위):** PIPA(§23 민감정보·가명정보 특례)·정보통신망법·ISMS-P·CSAP / 의료: 보건의료데이터 가이드라인(2024-12)·의료법 / 금융: 전자금융감독규정(2025-02)·신용정보법·마이데이터 / 제조: 중대재해처벌법·산업안전보건법·OT 데이터 주권
- **국제:** SOC2·ISO27001·GDPR / HIPAA·GDPR Art.9 / PCI-DSS 4.0.1 / EU REACH·CE·IEC 62443
- **데이터 등급(규제대상):** PHI·개인신용정보·카드데이터·영업비밀 — **비-프로덕션(dev/staging/test) 실데이터 반입 금지** (합성/비식별만)
- **인프라 델타:** 멀티테넌트 RLS 격리(크로스테넌트 누출 0)·가명키/recipe token vault 격리·PAN Luhn→토큰화(PCI scope 축소)·OT/IT 분리·민감 원문↔검색 저장소 분리·외부 LLM 반출 게이트(RESTRICTED/TRADE_SECRET 차단)

## 도메인(연구/RAG) 확장 시
출처 병기 · 권한(ACL) 필터 · 비식별화 · 감사로그 · 재현성(모델/청커/프롬프트 버전 고정) ·
하이브리드 검색(BM25+벡터) 기본 전제. 고위험 응답은 human-in-the-loop. LLM 연동은 공식 anthropic SDK + claude-opus-4-8.

---
_생성: wise-dev-standard 플러그인. 갱신은 `/wise-dev-standard:standardize`._
