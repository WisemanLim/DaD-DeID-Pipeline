# test/impl/15 — LLM judge(Claude) + Weaviate 어댑터 시나리오

대상: deid `app/detect/llm_judge.py`(Claude 정밀 판정) + `/guard?llm=true`, rag `app/index/weaviate_store.py`.
러너: deid `uv run pytest tests/test_llm_judge.py` + rag `uv run pytest tests/test_weaviate.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | ANTHROPIC_API_KEY 없음 | llm_judge.judge | available=False (no-op) |
| S2 | `/guard ml=true llm=true`, 키 없음 | POST | ML 결과 유지(차단), 예외 없음(폴백) |
| S3 | chunk_id | weaviate `_uuid` | 결정적 UUID(36자) |
| S4 | VECTOR_BACKEND=weaviate, 서버 미가용 | store 생성 | in-memory 폴백(예외 없음) |
| S5 | Weaviate 서버 가용(skip 가능) | external 검색 | RESTRICTED 차단, PUBLIC만 |

## 설계 메모
- LLM judge = classifier ML 매치를 Claude(claude-opus-4-8)로 정밀 확인 → 오탐 제거. 공식 anthropic SDK, 구조화 출력(json_schema), best-effort(키 없으면 ML 유지)
- Weaviate = weaviate-client v4, WEAVIATE_URL. 동일 VectorStore 추상화(namespace·격리·게이트). 서버 미가용 시 폴백
- 외부 서버(Claude API/Weaviate) 의존 → 오프라인은 no-op/skip 경로 검증, 실연동은 키/서버 설정 시
