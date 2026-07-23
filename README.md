# DaD DeID Pipeline

> 🇰🇷 한국어 | [🇬🇧 English](README.en.md)

> 생성: `wise-dev-standard / bio-rag-research` (다도메인: ict-saas[J] 베이스 + healthcare[Q]·finance[K]·manufacturing[C])

문서(PDF·DOCX·PPTX·손글씨 이미지)를 파싱·OCR·임베딩하는 과정에서 **개인정보(PII) + 업종 특화 비공개 정보**(영업비밀·BOM·공정값 등)를 정책 기반으로 비식별하는 파이프라인. 근거: [.docs/PRD.v2.md](.docs/PRD.v2.md)

## 기술 스택

| 레이어 | 스택 |
|---|---|
| 포털(대시보드 + E2E 파이프라인 UI) | Next.js 15 + React 19 + TS — `/` KPI 카드 · `/pipeline` 업로드→비식별→인덱싱→검색 (`apps/portal`) |
| BFF (인증·권한·감사) | NestJS 11 (`apps/bff`) |
| **검출+정책+변환** | FastAPI + uv + Presidio + spaCy (`services/deid`) |
| 분리 인덱싱+검색 | FastAPI + LangChain + Langfuse (`services/rag`) |
| OCR/재색인 워커 | Go (`services/worker`, 선택) |
| 공유 스키마 | 룰번들·DeidPolicy JSON Schema, KSIC 매핑 (`packages/shared`) |
| DB | local=SQLite / dev+=PostgreSQL+pgvector (↔ Qdrant 어댑터) + Redis |
| 관측성 | Langfuse + OpenTelemetry |
| 정책엔진 | builtin → OPA/Cedar (env 스위치) |

## 사전 요구사항

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node 22 + pnpm 9
- Go 1.23 (worker)
- Docker + Docker Compose
- **Tesseract OCR** 5.x + langdata(kor) — `brew install tesseract tesseract-lang` (OCR 경로용)
- spaCy 모델(ko/en)은 deid `uv sync` 시 pyproject URL 핀으로 자동 설치

## 빠른 시작

```bash
make up                 # 인프라(postgres+pgvector, redis, minio)만 기동
(cd services/deid && uv sync) && (cd services/rag && uv sync)
make run                # honcho: deid:8001 + rag:8002 (python 코어, 안정)
curl localhost:8001/health   # {"status":"ok","service":"deid","env":"local"}
curl localhost:8002/health   # {"status":"ok","service":"rag","vector_backend":"sqlite"}

pnpm install            # portal/bff 의존성 (루트 워크스페이스)
make run-web            # portal:3000 + bff:3001 (호스트)

make dev                # 또는 compose --profile app 으로 deid/rag/worker 컨테이너
make test               # pnpm -r test + uv run pytest (+ make ragas)

# --- 환경별 표준 실행 (pm2, 권장) ---
make local-all          # compose 인프라(postgres+redis) + pm2(deid/rag/portal/bff) 기동
make local-ps           # pm2 ls + compose ps
make local-logs         # pm2 로그 팔로우
make local-stop         # pm2 delete + compose down
# dev/staging/prod 도 동일 패턴: make dev-all, make staging-stop, make prod-ps ...
```

> **run vs run-web 분리 이유:** honcho 는 all-or-nothing — 한 프로세스가 종료하면 전체에 SIGTERM.
> 항상 listen 하는 자체완결 python 서비스(deid/rag)만 `make run` 기본에 두고,
> pnpm 워크스페이스 앱(portal/bff)은 `make run-web` 으로 분리한다. honcho 는 `uvx` 로 실행(루트 venv 불필요).
> 로컬 빠른 개발엔 `make run`(+`run-web`)도 유지되지만, **환경별(local/dev/staging/prod) 통합 기동은
> `make <env>-all`(pm2) 이 표준**이다(`ecosystem.config.cjs`, deid/rag/portal/bff 4앱).
> `bff`는 nest 스캐폴딩(health 엔드포인트) 완료 상태 — 인증/권한/감사 로직은 다음 단계 구현 예정.

## make 타겟

| 타겟 | 설명 |
|---|---|
| `up` / `down` | 인프라 datastore 기동/정리 |
| `dev` | 전체 스택 (compose `app` 프로파일) |
| `run` | honcho(uvx)로 python 코어 deid+rag 기동 (Procfile.dev) |
| `run-web` | portal+bff 호스트 기동 (pnpm 워크스페이스) |
| `<env>-all` (`local`/`dev`/`staging`/`prod`) | compose 인프라(postgres+redis) 기동 + pm2 `startOrRestart`(deid/rag/portal/bff). staging/prod 는 `pnpm build` 후 프로덕션 모드로 기동 |
| `<env>-stop` | pm2 delete(deid/rag/portal/bff) + compose down |
| `<env>-logs` / `<env>-infra-logs` | pm2 로그 / compose(postgres+redis) 로그 |
| `<env>-ps` | pm2 ls + compose ps |
| `<env>-compose-all` | app 서비스(deid/rag/worker)만 docker compose 로 기동(기존 방식) |
| `test` / `ragas` | Vitest+pytest / RAG groundedness eval |
| `build` | app 이미지 빌드 |
| `deploy` | helm upgrade / argocd sync (prod=K8s) |

## 환경 변수

`.env.{local,dev,staging,prod}` — `ENV`·`DATABASE_URL`·`REDIS_URL`·`VECTOR_BACKEND`(sqlite/pgvector/qdrant)·`DEID_API_BASE`·`RAG_API_BASE`·`POLICY_ENGINE`·`VAULT_URL`·`LANGFUSE_*`. prod 는 키 목록만(Secret Manager/Vault/KMS 주입).

## 디렉터리 구조

```
apps/portal      거버넌스 대시보드 (Next.js)
apps/bff         인증·권한·감사 (NestJS)
services/deid    검출+정책엔진+변환 (FastAPI) ← PRD 핵심
services/rag     분리 인덱싱·검색 (FastAPI + LangChain)
services/worker  OCR/재색인 워커 (Go, 선택)
packages/shared  룰번들·DeidPolicy 스키마, KSIC 매핑
test/            시험 표준 (dev-env + impl/<Nth>)
```

## 구현 현황

### deid 코어 (Epic 0/1/2) — `services/deid`

**룰번들 로더 + 검출(regex+Luhn) + 정책엔진 + 변환기** 슬라이스. 검출=정규식+Luhn 만(seed 의 `classifier` 룰은 NER 후속).

| 컴포넌트 | 위치 | 역할 |
|---|---|---|
| 룰 로더 | `app/detect/rules.py` | seed(`global`+`privacy` 46 regex + 업종) 적재, KSIC 섹션→서브도메인 레지스트리, priority 정렬 |
| 검출기 | `app/detect/{detector,ner,dictionary,composite}.py` | regex+Luhn + **spaCy NER**(인명/지명/기관) + **용어사전**(영업비밀) 병합 |
| classifier 판정 | `app/detect/{embedder,classifier_judge}.py` | seed classifier 룰 임베딩 margin 판정 → `/guard?ml=true` |
| LLM judge | `app/detect/llm_judge.py` | Claude(claude-opus-4-8) 정밀 판정 → `/guard?ml=true&llm=true` (ANTHROPIC_API_KEY 필요, 없으면 no-op) |
| 정책엔진 | `app/policy/engine.py` | (category,subCategory)→deid 액션, 민감도·export 차단 |
| 변환기 | `app/transform/transformer.py` | REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH + TokenVault |
| 파이프라인 | `app/pipeline.py` | 청킹 → 청크별 비식별 → ChunkMetadata 산출 (rag /index 계약) |
| 관측 | `app/observability.py` | Langfuse 호환 trace(PRD §7 태그+span) + KPI 메트릭(PRD §5) |
| OCR | `app/ocr.py` | Tesseract 어댑터(이미지/손글씨→텍스트), 신뢰도 임계 재검 플래그 → `/process-image` |
| 가드레일 | `app/guardrail.py` | 런타임 I/O block/refuse/warn/disclaimer (Epic 7) → `/guard` |
| 파서 | `app/parsers.py` · `app/external_parsers.py` | GROBID/Tika(설정 시) → pypdf·python-docx 폴백 → `/process-document` |
| Langfuse sink | `app/langfuse_sink.py` | LANGFUSE_HOST 설정 시 trace 전송, 미설정 no-op |

### 분리 인덱싱 (Epic 4) — `services/rag`

**민감도별 namespace 분리 + 테넌트(project_id) 격리 + 외부반출 게이트**. 임베딩은 오프라인 placeholder(토큰 Jaccard) — PRD: 검색 정확도 튜닝 Out of scope.

| 컴포넌트 | 위치 | 역할 |
|---|---|---|
| VectorStore | `app/index/{store,pgvector_store,qdrant_store,weaviate_store}.py` | namespace=민감도, project_id 격리, 외부반출 차단. in-memory ↔ **pgvector** ↔ **qdrant** ↔ **weaviate**(VECTOR_BACKEND) |
| 임베딩 | `app/index/embedder.py` | sentence-transformers(다국어 MiniLM) + 해시 폴백 (EMBED_BACKEND) |
| 청크 메타 | `app/index/schema.py` | `ChunkMetadata` (industry_code·sensitivity·lineage·`export_blocked()`) |

### 접속/포트

| 서비스 | URL | 포트 | API 문서 | 비고 |
|---|---|---|---|---|
| deid | http://localhost:8001 | 8001 | `/docs` | 검출+정책+변환 (구현) |
| rag | http://localhost:8002 | 8002 | `/docs` | 분리 인덱싱+검색 게이트 (구현) |
| bff | http://localhost:3001 | 3001 | — | `GET /health` 만 구현, 인증/권한/감사는 다음 단계 |
| portal | http://localhost:3000 | 3000 | — | `/` 대시보드 · `/pipeline` E2E 파이프라인 UI |
| postgres+pgvector | localhost:5432 | 5432 | — | `make up` |
| redis / minio | 6379 / 9000·9001 | — | — | `make up` |

### 포털 E2E 파이프라인 (`/pipeline`, PRD §1 한 줄 요약)

웹에서 전 과정 실행: **업종(KSIC) 선택 → 입력(텍스트/PDF·DOCX·TXT/손글씨 이미지) → 검출·정책 변환(청크별 민감도·transform_action·룰) → 민감도별 분리 인덱싱 → 검색(외부반출 게이트 토글)**. 브라우저는 Next.js 서버 라우트만 호출(CORS 회피), 서버가 deid/rag 를 프록시.

```bash
# POST /api/process — 업로드/텍스트 → deid 처리 + rag 인덱싱 (서버 프록시)
curl -s -X POST localhost:3000/api/process -H 'content-type: application/json' \
  -d '{"mode":"text","document_id":"d1","industry_code":"manufacturing-chemical","project_id":"portal","text":"환자 900101-1234567, 카드 4242 4242 4242 4242, 촉매비율 17.3%"}'
# → {"process":{"doc_sensitivity_level":"TRADE_SECRET","chunk_count":1,"chunks":[...]},"indexed":[{"namespace":"TRADE_SECRET","export_blocked":true}]}

# POST /api/search — rag 검색 (external=true 시 RESTRICTED/TRADE_SECRET 청크 차단)
curl -s -X POST localhost:3000/api/search -H 'content-type: application/json' \
  -d '{"query":"촉매","project_id":"portal","external":true}'
# → {"hits":[...],"export_blocked_count":1,"external":true}
```

### API 예시 — bff

```bash
# GET /health — 현재 구현된 유일한 엔드포인트(인증/권한/감사는 다음 단계)
curl -s localhost:3001/health
# {"status":"ok","service":"bff","env":"local"}
```

### API 예시 — deid

```bash
# POST /deid — 텍스트 비식별
curl -s -X POST localhost:8001/deid -H 'content-type: application/json' \
  -d '{"text":"환자 900101-1234567, 카드 4242 4242 4242 4242, 메일 a@b.com","industry_code":"healthcare-clinical"}'
```
```json
{
  "sensitivity_level": "RESTRICTED", "export_blocked": true,
  "detections": [
    {"rule_id":"PRIV_ID_KR_IN_001","category":"pii","sub_category":"national_id_kr","action":"REMOVE","sensitivity":"RESTRICTED"},
    {"rule_id":"PRIV_FIN_CARD_001","category":"financial","sub_category":"card_pan","action":"TOKENIZE","sensitivity":"RESTRICTED"},
    {"rule_id":"PRIV_CONTACT_KR_IN_002","category":"pii","sub_category":"email","action":"MASK","sensitivity":"INTERNAL"}
  ],
  "transformed_text": "환자 [REMOVED], 카드 ⟨TOK:9219e0affa⟩, 메일 *@*.***",
  "stats": {"entities_detected_total": 3, "transform_rate_avg": 1.0, "vault_entries": 1}
}
```
```bash
# GET /rules — 적재 룰 요약 (regex 검출가능 수 + unsupported 패턴타입)
curl -s "localhost:8001/rules?industry_code=manufacturing-chemical"
# {"total":213,"detectable_regex":13,"unsupported_pattern_types":["classifier"]}
```

### API 예시 — deid→rag 결선 (PRD 핵심 플로우)

```bash
# 1) POST /process — 문서 청킹 + 청크별 비식별 → ChunkMetadata
curl -s -X POST localhost:8001/process -H 'content-type: application/json' \
  -d '{"text":"회사 공개 소개.\n\n환자 900101-1234567, 카드 4242 4242 4242 4242.","document_id":"docA","industry_code":"healthcare-clinical","project_id":"proj-A","owner":"u1"}'
# → {"doc_sensitivity_level":"RESTRICTED","chunk_count":2,"chunks":[{text, metadata:{chunk_id,sensitivity_level,transform_action,lineage,...}}, ...]}

# 2) 각 청크를 rag /index 로 인덱싱 (metadata 계약 그대로) → 3) /search external 게이트
```
결선 실측(E2E): `docA#0`→PUBLIC, `docA#1`→RESTRICTED(blocked). external 검색 시 RESTRICTED 차단, internal 전건. → [test/impl/3/](test/impl/3/)

### API 예시 — rag (분리 인덱싱)

```bash
# POST /index — 비식별된 청크 인덱싱 (민감도 namespace 분리)
curl -s -X POST localhost:8002/index -H 'content-type: application/json' -d '{
  "text":"환자 차트 혈압",
  "metadata":{"document_id":"d1","chunk_id":"c2","industry_code":"Q","sensitivity_level":"RESTRICTED",
    "transform_action":"MASK","lineage":{},"source_uri":"s3://x","domain":"healthcare-clinical",
    "project_id":"proj-A","owner":"u1","version":"1"}}'
# {"indexed":"c2","namespace":"RESTRICTED","export_blocked":true}

# POST /search external=true — 외부반출 컨텍스트 → 민감 청크 차단
curl -s -X POST localhost:8002/search -H 'content-type: application/json' \
  -d '{"query":"혈압","project_id":"proj-A","external":true}'
# {"hits":[{"chunk_id":"c1","sensitivity_level":"PUBLIC",...}],"export_blocked_count":1,"external":true}
```

## 테스트

```bash
cd services/deid && uv run pytest        # 11 케이스 (검출/정책/변환 + 파이프라인 + 도메인 compliance)
cd services/rag  && uv run pytest        # 6 케이스 (namespace 분리/게이트/테넌트 격리)
```
- impl/1 (deid): [test/impl/1/](test/impl/1/) — 의료 직접식별자0 · 금융 PAN 토큰화 · 제조 절대값 미보존
- impl/2 (rag): [test/impl/2/](test/impl/2/) — 외부반출 차단 · 크로스테넌트 누출 0
- impl/3 (결선): [test/impl/3/](test/impl/3/) — deid /process → rag /index → search 게이트 E2E
- impl/4 (관측): [test/impl/4/](test/impl/4/) — trace(§7) + KPI 메트릭(§5, llm_sensitive_block_total)
- impl/5 (NER/dict): [test/impl/5/](test/impl/5/) — spaCy NER + 영업비밀 용어사전 + 복합 병합
- impl/6 (OCR): [test/impl/6/](test/impl/6/) — Tesseract 이미지 OCR → 비식별 (RRN 제거)
- impl/7 (도메인): [test/impl/7/](test/impl/7/) — privacy seed + KSIC 섹션 레지스트리 + 5도메인
- impl/8 (대시보드): [test/impl/8/](test/impl/8/) — portal /metrics KPI (vitest + next build)
- impl/9 (가드레일): [test/impl/9/](test/impl/9/) — Epic 7 I/O block/refuse (/guard)
- impl/10 (파서/pgvector): [test/impl/10/](test/impl/10/) — PDF/DOCX 파싱 + pgvector 게이트 + Langfuse sink
- impl/11 (임베딩/Qdrant): [test/impl/11/](test/impl/11/) — 실 임베딩 + Qdrant 게이트·격리
- impl/12 (classifier 판정): [test/impl/12/](test/impl/12/) — 임베딩 margin 의도 판정 (/guard?ml)
- impl/13 (외부 파서): [test/impl/13/](test/impl/13/) — Tika/GROBID 어댑터 + 폴백
- impl/14 (서버통합): [test/impl/14/](test/impl/14/) — compose 10서비스 + pgvector dim 마이그레이션
- impl/15 (LLM judge/Weaviate): [test/impl/15/](test/impl/15/) — Claude 정밀 판정 + Weaviate 어댑터
- impl/16 (pm2 실행표준): [test/impl/16/](test/impl/16/) — `make <env>-all` compose 인프라 + pm2 서비스
- impl/17 (bff nest): [test/impl/17/](test/impl/17/) — NestJS 스캐폴딩 완료(`/health`, :3001) + pm2 4앱
- impl/18 (포털 파이프라인): [test/impl/18/](test/impl/18/) — `/pipeline` E2E UI + `/api/process`·`/api/search` 서버 프록시
- dev-env 검증: [test/dev-env/result.md](test/dev-env/result.md) (PASS)
- 합계: **deid 51 + rag 16 + portal 3 = 70 케이스 PASS** (+pgvector·weaviate 통합은 서버 가용 시)

운영지표: `GET localhost:8001/metrics`(deid: entities_detected_total·transform_rate_avg·documents_processed_total) · `GET localhost:8002/metrics`(rag: llm_sensitive_block_total·chunks_indexed_total).

## 트러블슈팅

- **deid 첫 요청이 ~20초**: spaCy NER + torch/sentence-transformers 콜드 로드. 이후 호출은 수백 ms. 포털 `/pipeline` 첫 "비식별 실행"도 동일.
- **`uv run uvicorn` → `Failed to spawn: uvicorn`**: 프로젝트 경로 이동 후 venv shebang 이 구 경로를 가리킴 → `rm -rf services/{deid,rag}/.venv && uv sync` 로 재생성.
- **포털 `/pipeline` 502 / "deid 실패"**: deid(:8001)·rag(:8002) 미기동. `make local-all` 또는 `make run` 확인. 포털은 `DEID_API_BASE`/`RAG_API_BASE`(서버) 로 접속.
- **손글씨 이미지 OCR 무반응**: `tesseract` 바이너리 미설치. 설치 시 `/process-image` 정상 동작.

## 표준 / 멀티 IDE

- [AGENTS.md](AGENTS.md) — Claude Code · Cursor · Antigravity 공통 개발 표준 (스택·도메인·규제)
- `.cursor/rules/wise-dev-standard.mdc` (alwaysApply) · `.antigravity/rules.md` — IDE별 미러

## 규제 / 보안

- [COMPLIANCE.md](COMPLIANCE.md) — 다도메인 규제(PIPA·HIPAA·PCI-DSS·전자금융감독규정·IEC 62443 등)·데이터등급
- [SECURITY.md](SECURITY.md) — 보안 표준·외부반출 게이트·인덱스 메타데이터
- ⚠️ 규제대상 데이터(PHI·개인신용정보·영업비밀)는 **비-프로덕션 반입 금지** — 합성/비식별만

## 구현 현황 (PRD P0/P1 — 전 Epic 완료)

- [x] Epic 0/1/2 — 룰로더 + 검출(regex+Luhn) + 정책 + 변환 (impl/1)
- [x] Epic 4 — 분리 인덱싱 + 외부반출 게이트 + 테넌트 격리 (impl/2)
- [x] deid→rag 결선 — /process 청킹→비식별→ChunkMetadata→인덱싱 (impl/3)
- [x] Epic 6 — Langfuse 호환 trace + KPI 메트릭 (impl/4)
- [x] Epic 1 완성 — spaCy NER + dictionary 검출기 병합 (impl/5)
- [x] Epic 3 — OCR/이미지 경로 (Tesseract, /process-image, applies_to=OCR) (impl/6)
- [x] Epic 5 — 도메인 오버레이 (privacy seed + KSIC 섹션 레지스트리 + 5도메인) (impl/7)
- [x] Epic 6 ⓕ — portal 거버넌스 대시보드 (Next, /metrics KPI) (impl/8)

### P2
- [x] Epic 7 — 런타임 가드레일 (I/O block/refuse/warn/disclaimer, `/guard`) (impl/9)
- [x] pgvector 어댑터 + PDF/DOCX 파서(`/process-document`) + Langfuse sink (impl/10)
- [x] 실 임베딩(sentence-transformers) + Qdrant 어댑터 (impl/11)
- [x] classifier 룰 ML 판정 (임베딩 margin, /guard?ml=true) (impl/12)
- [x] Tika/GROBID 외부 파서 어댑터 (폴백 pypdf/docx) (impl/13)
- [x] 서버 컨테이너 통합(Tika/GROBID/Qdrant/Langfuse compose) + pgvector dim 동적 (impl/14)
- [x] LLM judge(Claude /guard?llm=true) + Weaviate 어댑터 (impl/15)
- [x] `/wise-dev-standard:standardize` — AGENTS.md + .cursor/rules + .antigravity (멀티 IDE 표준)
- 외부 서버/키 연동(Claude API·Weaviate·Tika·GROBID·Langfuse)은 배포 시점 — 코드/폴백/skip 완비
