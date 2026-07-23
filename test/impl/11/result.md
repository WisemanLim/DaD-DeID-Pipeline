# test/impl/11 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (rag 13/13 + 1 skip[pgvector, postgres down] · ruff clean)

```
qdrant/embedder: 5 passed (최초 모델 다운로드 104s, 이후 캐시 ~14s)
rag 전체: 13 passed, 1 skipped
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_embedder_loads | PASS (실모델 로드) |
| S2 | test_hash_embedder_deterministic | PASS |
| S3 | test_qdrant_namespace_separation | PASS |
| S4 | test_qdrant_external_gate | PASS |
| S5 | test_qdrant_tenant_isolation | PASS |

## 구현
- `app/index/embedder.py` — `get_embedder()`: sentence-transformers(paraphrase-multilingual-MiniLM-L12-v2) 우선, 미설치/오프라인 시 `HashEmbedder`(64d) 폴백. EMBED_MODEL/EMBED_BACKEND env
- `app/index/qdrant_store.py` — qdrant-client. QDRANT_URL 시 원격, 아니면 `:memory:`(오프라인). namespace=payload, project_id 격리, 외부반출 query filter(must_not)
- rag main: VECTOR_BACKEND `qdrant`→QdrantStore (실패 시 in-memory 폴백)

## 수정 이력
- FutureWarning `get_sentence_embedding_dimension` → `get_embedding_dimension` 우선 호출(하위호환 getattr)

## 한계 / 잔여
- pgvector 백엔드는 여전히 64d 해시(테이블 고정) — 실 임베딩 전환 시 dim 마이그레이션 필요. Qdrant 는 embedder.dim 동적.
- Weaviate 는 qdrant 분기로 매핑(별도 클라이언트 후속).
- 모델 최초 다운로드 ~분 소요(이후 HF 캐시).
