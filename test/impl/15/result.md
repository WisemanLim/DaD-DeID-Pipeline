# test/impl/15 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (deid 51/51 · rag 16/16 +1 skip[weaviate, 서버 없음] · portal 3/3 · ruff clean)

```
llm_judge: 2 passed
weaviate: 2 passed, 1 skipped
전체: deid 51 + rag 16 + portal 3 = 70 PASS (+1 skip)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_llm_judge_noop_without_key | PASS |
| S2 | test_guard_llm_flag_graceful | PASS |
| S3 | test_uuid_deterministic | PASS |
| S4 | test_backend_switch_falls_back | PASS |
| S5 | test_weaviate_external_gate | SKIP (서버 없음) |

## 구현
- `services/deid/app/detect/llm_judge.py` — Claude(claude-opus-4-8) 구조화 출력 판정, ANTHROPIC_API_KEY 없으면 available=False. `/guard?llm=true` 에서 ML 매치 룰을 정밀 확인(위반 아님이면 매치 제외)
- `services/rag/app/index/weaviate_store.py` — weaviate-client v4, WEAVIATE_URL, embedder BYO 벡터, namespace·테넌트·게이트. VECTOR_BACKEND=weaviate 스위치 + 미가용 폴백

## 수정 이력
- 없음.

## 한계 / 잔여
- LLM judge 실연동은 ANTHROPIC_API_KEY 필요(오프라인=no-op). 모델 claude-opus-4-8(LLM_JUDGE_MODEL override).
- Weaviate 실연동은 서버 필요(docker --profile vector 에 weaviate 추가 가능). grpc 포트 50051 고정 — 운영 시 환경별 조정.
- **코드 레벨 PRD 잔여 없음.** 남은 것은 외부 서버/키 연동(배포)과 `/wise-dev-standard:standardize`.
