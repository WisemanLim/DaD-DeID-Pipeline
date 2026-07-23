# test/impl/10 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (deid 40/40 · rag 9/9[pgvector 통합 포함] · ruff clean)

```
deid: 40 passed   (기존 35 + parsers 5)
rag:   9 passed   (기존 7 + pgvector 2; postgres make up 상태)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_parse_docx | PASS |
| S2 | test_parse_document_txt_dispatch | PASS |
| S3 | test_process_document_docx_deidentifies | PASS (RRN 제거) |
| S4 | test_pdf_writer_empty_ok | PASS |
| S5 | test_langfuse_sink_noop_offline | PASS |
| S6 | test_hash_embedding_deterministic | PASS |
| S7 | test_pgvector_namespace_and_gate | PASS (postgres 가용) |

## 구현
- `services/deid/app/parsers.py` — pypdf/python-docx → 텍스트, content_type 디스패치. deid `POST /process-document`
- `services/deid/app/langfuse_sink.py` — LANGFUSE_HOST 설정 시 trace 전송, 미설정/실패 no-op(파이프라인 비차단). /process 에 결선
- `services/rag/app/index/pgvector_store.py` — pgvector 백엔드(결정적 해시 임베딩 64d, cosine `<=>`), namespace=민감도, project_id 격리, 외부반출 WHERE 게이트
- rag main: `VECTOR_BACKEND=pgvector` → PgVectorStore, 연결 실패 시 in-memory 폴백

## 수정 이력
- **FAIL→PASS**: `embedding <=> %s` 에 `operator does not exist: vector <=> double precision[]` → 쿼리 파라미터 `%s::vector` 캐스트 추가 후 통과.

## 한계 / 잔여
- 해시 임베딩은 placeholder(검색 정확도 튜닝 Out-of-scope). 실 임베딩 모델 연동 시 동일 인터페이스 교체.
- Qdrant/Weaviate 어댑터는 동일 VectorStore 추상화로 후속.
- Langfuse 라이브 전송은 LANGFUSE_HOST+키 설정 시에만(오프라인 검증은 no-op 경로).
- Tika/GROBID(대용량·과학문서)는 후속 — 현재 pypdf/python-docx 경량 경로.
