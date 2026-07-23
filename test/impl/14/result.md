# test/impl/14 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (compose config 유효 · rag 14/14 · ruff clean)

| # | 케이스 | 결과 |
|---|---|---|
| S1 | compose 10 서비스 | PASS (deid/rag/worker/postgres/redis/minio/qdrant/tika/grobid/langfuse) |
| S2 | hash dim=64 | PASS |
| S3 | dim 64→384 마이그레이션 | PASS (`[rag] pgvector dim 64→384 마이그레이션`, rows 1→0) |
| S4 | rag 전체 | PASS (14 passed, 실모델 dim 384) |

## 구현
- `docker-compose.override.yml` — tika(`--profile parse`)·grobid(`--profile parse`)·langfuse(`--profile obs`) 추가. qdrant/minio 기존
- `.env.dev` — TIKA_URL/GROBID_URL/LANGFUSE_* /EMBED_BACKEND 결선(주석 기본, 서버 기동 시 활성)
- `pgvector_store` — 공유 embedder 사용(dim 동적), `_migrate_dim()`: 기존 컬럼 dim ≠ embedder.dim 시 dev 재생성

## 수정 이력
- 없음.

## 운영 안내
- 전체 기동: `docker compose --profile app --profile vector --profile parse --profile obs up`
- 서버 미기동도 동작: qdrant→in-memory, tika/grobid→pypdf, langfuse→no-op sink (폴백 완비)

## 한계 / 잔여
- Langfuse self-host 는 clickhouse 등 추가 필요(dev 단순화 — SDK 호환 엔드포인트만). 운영은 Langfuse Cloud 권장.
- prod dim 마이그레이션은 Alembic(현재 dev 재생성). 기존 인덱스 보존 마이그레이션 후속.
