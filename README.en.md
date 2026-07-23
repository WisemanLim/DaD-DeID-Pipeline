# DaD DeID Pipeline

> [🇰🇷 한국어](README.md) | 🇬🇧 English

> Scaffolded by `wise-dev-standard / bio-rag-research` (multi-domain: ict-saas[J] base + healthcare[Q] · finance[K] · manufacturing[C])

A pipeline that de-identifies **PII + domain-specific confidential information** (trade secrets, BOM, process values) during document parsing/OCR/embedding (PDF, DOCX, PPTX, handwritten images), driven by policy. Source: [.docs/PRD.v2.md](.docs/PRD.v2.md)

## Tech stack

| Layer | Stack |
|---|---|
| Portal (dashboard + E2E pipeline UI) | Next.js 15 + React 19 + TS — `/` KPI cards · `/pipeline` upload→de-id→index→search (`apps/portal`) |
| BFF (authn/authz/audit) | NestJS 11 (`apps/bff`) |
| **Detect + policy + transform** | FastAPI + uv + Presidio + spaCy (`services/deid`) |
| Separated indexing + retrieval | FastAPI + LangChain + Langfuse (`services/rag`) |
| OCR/reindex worker | Go (`services/worker`, optional) |
| Shared schema | Rule-bundle / DeidPolicy JSON Schema, KSIC map (`packages/shared`) |
| DB | local=SQLite / dev+=PostgreSQL+pgvector (↔ Qdrant adapter) + Redis |
| Observability | Langfuse + OpenTelemetry |
| Policy engine | builtin → OPA/Cedar (env switch) |

## Prerequisites

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node 22 + pnpm 9
- Go 1.23 (worker)
- Docker + Docker Compose
- **Tesseract OCR** 5.x + langdata(kor) — `brew install tesseract tesseract-lang` (for OCR path)
- spaCy models (ko/en) auto-install on deid `uv sync` via pyproject URL pins

## Quick start

```bash
make up                 # infra only (postgres+pgvector, redis, minio)
(cd services/deid && uv sync) && (cd services/rag && uv sync)
make run                # honcho: deid:8001 + rag:8002 (python core, stable)
curl localhost:8001/health   # {"status":"ok","service":"deid","env":"local"}
curl localhost:8002/health   # {"status":"ok","service":"rag","vector_backend":"sqlite"}

pnpm install            # portal/bff deps (root workspace)
make run-web            # portal:3000 + bff:3001 (host)

make dev                # full stack via compose --profile app
make test               # pnpm -r test + uv run pytest (+ make ragas)

# --- Standard per-environment run (pm2, recommended) ---
make local-all          # compose infra (postgres+redis) + pm2 (deid/rag/portal/bff)
make local-ps           # pm2 ls + compose ps
make local-logs         # follow pm2 logs
make local-stop         # pm2 delete + compose down
# dev/staging/prod follow the same pattern: make dev-all, make staging-stop, make prod-ps ...
```

> **Why run vs run-web:** honcho is all-or-nothing — if one process exits it SIGTERMs the rest.
> Only the self-contained, always-listening Python services (deid/rag) go in `make run`;
> pnpm workspace apps (portal/bff) are split into `make run-web`. honcho runs via `uvx` (no root venv needed).
> `make run`(+`run-web`) still works for quick local dev, but **`make <env>-all` (pm2) is the standard**
> for unified per-environment startup (`ecosystem.config.cjs`, 4 apps: deid/rag/portal/bff).
> `bff`'s Nest scaffolding (health endpoint) is done — auth/authz/audit logic is still pending.

## make targets

| Target | Description |
|---|---|
| `up` / `down` | start/clean infra datastores |
| `dev` | full stack (compose `app` profile) |
| `run` | python core deid+rag via honcho/uvx (Procfile.dev) |
| `run-web` | portal+bff on host (pnpm workspace) |
| `<env>-all` (`local`/`dev`/`staging`/`prod`) | compose infra (postgres+redis) + pm2 `startOrRestart` (deid/rag/portal/bff). staging/prod run `pnpm build` first, then production mode |
| `<env>-stop` | pm2 delete (deid/rag/portal/bff) + compose down |
| `<env>-logs` / `<env>-infra-logs` | pm2 logs / compose (postgres+redis) logs |
| `<env>-ps` | pm2 ls + compose ps |
| `<env>-compose-all` | app services (deid/rag/worker) only, via docker compose (legacy) |
| `test` / `ragas` | Vitest+pytest / RAG groundedness eval |
| `build` | build app images |
| `deploy` | helm upgrade / argocd sync (prod=K8s) |

## Environment variables

`.env.{local,dev,staging,prod}` — `ENV`, `DATABASE_URL`, `REDIS_URL`, `VECTOR_BACKEND` (sqlite/pgvector/qdrant), `DEID_API_BASE`, `RAG_API_BASE`, `POLICY_ENGINE`, `VAULT_URL`, `LANGFUSE_*`. prod holds keys only (inject via Secret Manager/Vault/KMS).

## Directory layout

```
apps/portal      Governance dashboard (Next.js)
apps/bff         Authn/authz/audit (NestJS)
services/deid    Detect + policy engine + transform (FastAPI) ← PRD core
services/rag     Separated indexing + retrieval (FastAPI + LangChain)
services/worker  OCR/reindex worker (Go, optional)
packages/shared  Rule-bundle / DeidPolicy schema, KSIC map
test/            Testing standard (dev-env + impl/<Nth>)
```

## Implementation status

### deid core (Epic 0/1/2) — `services/deid`

**Rule-bundle loader + detection (regex+Luhn) + policy engine + transformer** slice. Detection = regex+Luhn only (seed `classifier` rules deferred to NER).

| Component | Path | Role |
|---|---|---|
| Rule loader | `app/detect/rules.py` | load seed (`global`+`privacy` 46 regex + industry), KSIC section→subdomain registry, sort by priority |
| Detector | `app/detect/{detector,ner,dictionary,composite}.py` | regex+Luhn + **spaCy NER** (person/loc/org) + **lexicon** (trade secrets) merged |
| Classifier judge | `app/detect/{embedder,classifier_judge}.py` | seed classifier rules via embedding-margin judgment → `/guard?ml=true` |
| LLM judge | `app/detect/llm_judge.py` | Claude (claude-opus-4-8) precise judgment → `/guard?ml=true&llm=true` (needs ANTHROPIC_API_KEY; no-op otherwise) |
| Policy engine | `app/policy/engine.py` | (category,subCategory)→deid action, sensitivity & export gate |
| Transformer | `app/transform/transformer.py` | REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH + TokenVault |
| Pipeline | `app/pipeline.py` | chunk → per-chunk de-id → ChunkMetadata (rag /index contract) |
| Observability | `app/observability.py` | Langfuse-compatible trace (PRD §7 tags+spans) + KPI metrics (PRD §5) |
| OCR | `app/ocr.py` | Tesseract adapter (image/handwriting→text), low-confidence re-check flag → `/process-image` |
| Guardrail | `app/guardrail.py` | runtime I/O block/refuse/warn/disclaimer (Epic 7) → `/guard` |
| Parsers | `app/parsers.py` · `app/external_parsers.py` | GROBID/Tika (when set) → pypdf·python-docx fallback → `/process-document` |
| Langfuse sink | `app/langfuse_sink.py` | sends trace when LANGFUSE_HOST set, no-op otherwise |

### Separated indexing (Epic 4) — `services/rag`

**Sensitivity namespace separation + tenant (project_id) isolation + export gate**. Embedding = offline placeholder (token Jaccard) — PRD: retrieval tuning is out of scope.

| Component | Path | Role |
|---|---|---|
| VectorStore | `app/index/{store,pgvector_store,qdrant_store,weaviate_store}.py` | namespace=sensitivity, project_id isolation, export block. in-memory ↔ **pgvector** ↔ **qdrant** ↔ **weaviate** (VECTOR_BACKEND) |
| Embedder | `app/index/embedder.py` | sentence-transformers (multilingual MiniLM) + hash fallback (EMBED_BACKEND) |
| Chunk meta | `app/index/schema.py` | `ChunkMetadata` (industry_code·sensitivity·lineage·`export_blocked()`) |

### Ports

| Service | URL | Port | API docs | Note |
|---|---|---|---|---|
| deid | http://localhost:8001 | 8001 | `/docs` | detect+policy+transform (implemented) |
| rag | http://localhost:8002 | 8002 | `/docs` | separated indexing+search gate (implemented) |
| bff | http://localhost:3001 | 3001 | — | `GET /health` only, auth/authz/audit pending |
| portal | http://localhost:3000 | 3000 | — | `/` dashboard · `/pipeline` E2E pipeline UI |
| postgres+pgvector | localhost:5432 | 5432 | — | `make up` |
| redis / minio | 6379 / 9000·9001 | — | — | `make up` |

### Portal E2E pipeline (`/pipeline`, PRD §1 one-liner)

Run the whole flow in the browser: **pick industry (KSIC) → input (text / PDF·DOCX·TXT / handwriting image) → detection + policy transform (per-chunk sensitivity, transform_action, rules) → sensitivity-namespaced indexing → search (external-export gate toggle)**. The browser only calls Next.js server routes (CORS-free); the server proxies deid/rag.

```bash
# POST /api/process — upload/text → deid processing + rag indexing (server proxy)
curl -s -X POST localhost:3000/api/process -H 'content-type: application/json' \
  -d '{"mode":"text","document_id":"d1","industry_code":"manufacturing-chemical","project_id":"portal","text":"환자 900101-1234567, 카드 4242 4242 4242 4242, 촉매비율 17.3%"}'
# → {"process":{"doc_sensitivity_level":"TRADE_SECRET","chunk_count":1,"chunks":[...]},"indexed":[{"namespace":"TRADE_SECRET","export_blocked":true}]}

# POST /api/search — rag search (external=true blocks RESTRICTED/TRADE_SECRET chunks)
curl -s -X POST localhost:3000/api/search -H 'content-type: application/json' \
  -d '{"query":"촉매","project_id":"portal","external":true}'
# → {"hits":[...],"export_blocked_count":1,"external":true}
```

### API examples — bff

```bash
# GET /health — the only endpoint implemented so far (auth/authz/audit pending)
curl -s localhost:3001/health
# {"status":"ok","service":"bff","env":"local"}
```

### API examples — deid

```bash
# POST /deid — de-identify text
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
# GET /rules — loaded rule summary
curl -s "localhost:8001/rules?industry_code=manufacturing-chemical"
# {"total":213,"detectable_regex":13,"unsupported_pattern_types":["classifier"]}
```

### API examples — deid→rag pipeline (PRD core flow)

```bash
# 1) POST /process — chunk a document + de-identify each chunk → ChunkMetadata
curl -s -X POST localhost:8001/process -H 'content-type: application/json' \
  -d '{"text":"회사 공개 소개.\n\n환자 900101-1234567, 카드 4242 4242 4242 4242.","document_id":"docA","industry_code":"healthcare-clinical","project_id":"proj-A","owner":"u1"}'
# → {"doc_sensitivity_level":"RESTRICTED","chunk_count":2,"chunks":[{text, metadata:{chunk_id,sensitivity_level,transform_action,lineage,...}}, ...]}

# 2) feed each chunk to rag /index (metadata contract as-is) → 3) /search external gate
```
E2E observed: `docA#0`→PUBLIC, `docA#1`→RESTRICTED(blocked). external search blocks RESTRICTED, internal returns all. → [test/impl/3/](test/impl/3/)

### API examples — rag (separated indexing)

```bash
# POST /index — index a de-identified chunk (namespace by sensitivity)
curl -s -X POST localhost:8002/index -H 'content-type: application/json' -d '{
  "text":"환자 차트 혈압",
  "metadata":{"document_id":"d1","chunk_id":"c2","industry_code":"Q","sensitivity_level":"RESTRICTED",
    "transform_action":"MASK","lineage":{},"source_uri":"s3://x","domain":"healthcare-clinical",
    "project_id":"proj-A","owner":"u1","version":"1"}}'
# {"indexed":"c2","namespace":"RESTRICTED","export_blocked":true}

# POST /search external=true — external-export context → sensitive chunks blocked
curl -s -X POST localhost:8002/search -H 'content-type: application/json' \
  -d '{"query":"혈압","project_id":"proj-A","external":true}'
# {"hits":[{"chunk_id":"c1","sensitivity_level":"PUBLIC",...}],"export_blocked_count":1,"external":true}
```

## Tests

```bash
cd services/deid && uv run pytest        # 11 cases (detect/policy/transform + pipeline + domain compliance)
cd services/rag  && uv run pytest        # 6 cases (namespace split/gate/tenant isolation)
```
- impl/1 (deid): [test/impl/1/](test/impl/1/) — healthcare zero-direct-identifier · finance PAN tokenization · manufacturing absolute-value redaction
- impl/2 (rag): [test/impl/2/](test/impl/2/) — external-export blocked · zero cross-tenant leak
- impl/3 (pipeline): [test/impl/3/](test/impl/3/) — deid /process → rag /index → search gate E2E
- impl/4 (observability): [test/impl/4/](test/impl/4/) — trace(§7) + KPI metrics(§5, llm_sensitive_block_total)
- impl/5 (NER/dict): [test/impl/5/](test/impl/5/) — spaCy NER + trade-secret lexicon + composite merge
- impl/6 (OCR): [test/impl/6/](test/impl/6/) — Tesseract image OCR → de-id (RRN removed)
- impl/7 (domains): [test/impl/7/](test/impl/7/) — privacy seed + KSIC section registry + 5 domains
- impl/8 (dashboard): [test/impl/8/](test/impl/8/) — portal /metrics KPI (vitest + next build)
- impl/9 (guardrail): [test/impl/9/](test/impl/9/) — Epic 7 I/O block/refuse (/guard)
- impl/10 (parsers/pgvector): [test/impl/10/](test/impl/10/) — PDF/DOCX parsing + pgvector gate + Langfuse sink
- impl/11 (embeddings/Qdrant): [test/impl/11/](test/impl/11/) — real embeddings + Qdrant gate/isolation
- impl/12 (classifier judge): [test/impl/12/](test/impl/12/) — embedding-margin intent judgment (/guard?ml)
- impl/13 (external parsers): [test/impl/13/](test/impl/13/) — Tika/GROBID adapter + fallback
- impl/14 (server integration): [test/impl/14/](test/impl/14/) — compose 10 services + pgvector dim migration
- impl/15 (LLM judge/Weaviate): [test/impl/15/](test/impl/15/) — Claude precise judgment + Weaviate adapter
- impl/16 (pm2 run standard): [test/impl/16/](test/impl/16/) — `make <env>-all` compose infra + pm2 services
- impl/17 (bff nest): [test/impl/17/](test/impl/17/) — NestJS scaffolding done (`/health`, :3001) + pm2 4 apps
- impl/18 (portal pipeline): [test/impl/18/](test/impl/18/) — `/pipeline` E2E UI + `/api/process`·`/api/search` server proxy
- env verification: [test/dev-env/result.md](test/dev-env/result.md) (PASS)
- Total: **deid 51 + rag 16 + portal 3 = 70 cases PASS** (+pgvector·weaviate integration when servers up)

Metrics: `GET localhost:8001/metrics` (deid: entities_detected_total·transform_rate_avg·documents_processed_total) · `GET localhost:8002/metrics` (rag: llm_sensitive_block_total·chunks_indexed_total).

## Troubleshooting

- **First deid request takes ~20s**: spaCy NER + torch/sentence-transformers cold load; subsequent calls are sub-second. The first "Run de-id" on portal `/pipeline` is the same.
- **`uv run uvicorn` → `Failed to spawn: uvicorn`**: after moving the project dir, venv shebangs point at the old path → `rm -rf services/{deid,rag}/.venv && uv sync`.
- **Portal `/pipeline` 502 / "deid failed"**: deid(:8001)/rag(:8002) not running. Check `make local-all` or `make run`. Portal connects via `DEID_API_BASE`/`RAG_API_BASE` (server-side).
- **Handwriting image OCR does nothing**: `tesseract` binary not installed; `/process-image` works once installed.

## Standard / multi-IDE

- [AGENTS.md](AGENTS.md) — shared dev standard for Claude Code · Cursor · Antigravity (stack·domain·compliance)
- `.cursor/rules/wise-dev-standard.mdc` (alwaysApply) · `.antigravity/rules.md` — per-IDE mirrors

## Compliance / Security

- [COMPLIANCE.md](COMPLIANCE.md) — multi-domain regulations (PIPA, HIPAA, PCI-DSS, e-finance supervision, IEC 62443) & data classes
- [SECURITY.md](SECURITY.md) — security standards, export gate, index metadata
- ⚠️ Regulated data (PHI, personal credit info, trade secrets) **must not enter non-production** — synthetic/de-identified only

## Implementation status (PRD P0/P1 — all Epics complete)

- [x] Epic 0/1/2 — rule loader + detection (regex+Luhn) + policy + transform (impl/1)
- [x] Epic 4 — separated indexing + export gate + tenant isolation (impl/2)
- [x] deid→rag pipeline — /process chunk→de-id→ChunkMetadata→index (impl/3)
- [x] Epic 6 — Langfuse-compatible trace + KPI metrics (impl/4)
- [x] Epic 1 complete — spaCy NER + dictionary detectors merged (impl/5)
- [x] Epic 3 — OCR/image path (Tesseract, /process-image, applies_to=OCR) (impl/6)
- [x] Epic 5 — domain overlays (privacy seed + KSIC section registry + 5 domains) (impl/7)
- [x] Epic 6 ⓕ — portal governance dashboard (Next, /metrics KPI) (impl/8)

### P2
- [x] Epic 7 — runtime guardrails (I/O block/refuse/warn/disclaimer, `/guard`) (impl/9)
- [x] pgvector adapter + PDF/DOCX parsers (`/process-document`) + Langfuse sink (impl/10)
- [x] real embeddings (sentence-transformers) + Qdrant adapter (impl/11)
- [x] classifier-rule ML judgment (embedding margin, /guard?ml=true) (impl/12)
- [x] Tika/GROBID external parser adapter (pypdf/docx fallback) (impl/13)
- [x] server container integration (Tika/GROBID/Qdrant/Langfuse compose) + dynamic pgvector dim (impl/14)
- [x] LLM judge (Claude /guard?llm=true) + Weaviate adapter (impl/15)
- [x] `/wise-dev-standard:standardize` — AGENTS.md + .cursor/rules + .antigravity (multi-IDE standard)
- External server/key integration (Claude API·Weaviate·Tika·GROBID·Langfuse) is deploy-time — code/fallback/skip all in place
