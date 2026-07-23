# test/impl/11 — 실 임베딩 + Qdrant 어댑터 시나리오

대상: rag `app/index/embedder.py`(sentence-transformers + 해시 폴백), `app/index/qdrant_store.py`(로컬 in-memory).
러너: `cd services/rag && uv run pytest tests/test_qdrant.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | get_embedder() | embed("…") | dim 차원 벡터, dim>0 (실모델 또는 폴백) |
| S2 | HashEmbedder | embed 2회 | 결정적 동일, dim=64 |
| S3 | PUBLIC+RESTRICTED upsert | namespaces | 민감도별 분리 |
| S4 | external 검색 | query | RESTRICTED 차단(blocked≥1), PUBLIC만 |
| S5 | projA·projB | query projA | 크로스테넌트 누출 0 |

## 도메인 compliance 매핑
- Qdrant 백엔드도 namespace 분리·외부반출 게이트·테넌트 격리 유지 (query filter)
- 실 임베딩(paraphrase-multilingual-MiniLM) 적용, 모델 미가용 시 해시 폴백 (graceful)
- VECTOR_BACKEND: in-memory / pgvector / **qdrant** 스위치, 동일 VectorStore 추상화
