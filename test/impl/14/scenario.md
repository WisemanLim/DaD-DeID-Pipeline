# test/impl/14 — 서버 컨테이너 통합 + pgvector dim 동적 시나리오

대상: `docker-compose.override.yml`(tika/grobid/qdrant/langfuse), `.env.dev` 결선, rag `pgvector_store` dim 동적+마이그레이션.
러너: `docker compose config` + `cd services/rag && uv run pytest`(postgres make up).

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | override 전 profile | `docker compose config --services` | deid/rag/worker/postgres/redis/minio/qdrant/tika/grobid/langfuse (10) |
| S2 | hash 백엔드(64d) | PgVectorStore | 테이블 dim=64 |
| S3 | 64d 테이블 존재 + 실모델(384d) | PgVectorStore 재생성 | dim 64→384 마이그레이션, 데이터 비움 |
| S4 | rag 전체 | pytest | 14 PASS (pgvector 실모델 dim) |

## 설계 메모
- 서버는 compose **profile** 로 opt-in: `--profile vector`(qdrant) `--profile parse`(tika·grobid) `--profile obs`(langfuse)
- 코드/폴백 완비 → 서버 미기동도 동작(in-memory·pypdf·no-op sink)
- pgvector dim = embedder.dim 동적(hash 64 / 실모델 384). dim 변경 시 dev 재생성(prod=Alembic)
