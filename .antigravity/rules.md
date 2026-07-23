# 개발환경 표준 (Wise Dev Standard) — DaD DeID Pipeline

> Antigravity 전용 규칙 — 루트 `AGENTS.md` 미러. Claude Code / Cursor 와 동일 표준.

## 현재 프로젝트 기본 스택 (profile: bio-rag-research)

문서 비식별 파이프라인 모노레포 (PRD `.docs/PRD.v2.md`). 역할 분리형:

| 서비스 | 스택 | 역할 |
|---|---|---|
| `services/deid` | Python+FastAPI+uv | 검출(regex+Luhn+NER+dictionary+classifier/LLM judge)+정책+변환+OCR+가드레일. :8001 |
| `services/rag` | Python+FastAPI+LangChain | 민감도 namespace 분리 인덱싱+검색 게이트. VectorStore in-memory↔pgvector↔qdrant↔weaviate. :8002 |
| `services/worker` | Go | OCR/재색인 워커(선택) |
| `apps/portal` | Next.js 15+React 19+TS | 거버넌스 KPI 대시보드 |
| `apps/bff` | NestJS 11 | 인증·권한·감사 BFF |
| `packages/shared` | JSON Schema | 룰번들·DeidPolicy 스키마, KSIC 매핑 |

실행: `make up`(인프라)/`make run`(uvx honcho deid+rag)/`make run-web`(portal+bff)/`make dev`(compose --profile app).

## 핵심 규칙
- 언어 우선순위: Node/TS · Python · Rust · Go · C/C++. 본 프로젝트 핵심=Python.
- 패키지매니저: uv(python) + pnpm(node). DB: local SQLite / dev+ PostgreSQL+pgvector + Redis.
- 시험: `test/dev-env/` + `test/impl/<Nth>/`, 사이클(시나리오→진행→수정·재시험→결과). 러너 pytest+Ragas+Vitest.
- 시크릿 하드코딩 금지 → Vault/Secret Manager/KMS, 환경변수(ANTHROPIC_API_KEY 등).
- 외부 서버 연동은 항상 graceful 폴백(미가용 시 in-memory/pypdf/no-op).
- LLM 연동: 공식 anthropic SDK + claude-opus-4-8.

## 업종/업태(도메인) 표준 — 다도메인 (COMPLIANCE.md 준수)
베이스라인 `ict-saas`(J) + 오버레이 `healthcare`(Q)·`finance`(K)·`manufacturing`(C), 후속 `govtech`(O)·`media-gaming`(R). 규제 충돌 시 강한 쪽 우선.
- 한국 규제(1순위): PIPA(§23·가명정보)·ISMS-P·CSAP / 보건의료데이터 가이드라인(2024-12)·의료법 / 전자금융감독규정(2025-02)·신용정보법·마이데이터 / 중대재해처벌법·산업안전보건법.
- 국제: SOC2·ISO27001·GDPR / HIPAA·GDPR Art.9 / PCI-DSS 4.0.1 / EU REACH·CE·IEC 62443.
- **데이터 등급(규제대상): PHI·개인신용정보·카드·영업비밀 — 비-프로덕션 실데이터 반입 금지(합성/비식별만).**
- 인프라 델타: 멀티테넌트 RLS(크로스테넌트 누출 0)·vault 격리·PAN Luhn→토큰화·OT/IT 분리·민감 원문↔검색 저장소 분리·외부 LLM 반출 게이트(RESTRICTED/TRADE_SECRET 차단).

## 도메인(연구/RAG)
출처 병기·ACL 필터·비식별화·감사로그·재현성(모델/청커/프롬프트 버전 고정)·하이브리드 검색(BM25+벡터). 고위험 응답 human-in-the-loop.

---
_생성: wise-dev-standard. 갱신: `/wise-dev-standard:standardize`._
