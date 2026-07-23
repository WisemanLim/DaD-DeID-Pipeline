# dev-env 검증 결과 / result

- 실행일: 2026-06-09
- 판정: **PASS**

| # | 케이스 | 결과 |
|---|---|---|
| 1 | `make up` (postgres+pgvector, redis, minio) | PASS — 3 컨테이너 healthy |
| 2 | `uv sync` (services/deid, services/rag) | PASS — deid 73pkg / rag 112pkg |
| 3 | `make run` (uvx honcho) | PASS — deid:8001 / rag:8002 기동·유지 |
| 4 | `curl :8001/health` | PASS — `{"status":"ok","service":"deid","env":"local"}` |
| 5 | `curl :8002/health` | PASS — `{"status":"ok","service":"rag","vector_backend":"sqlite"}` |

메모:
- bff 스텁(nest 미완)이 honcho all-or-nothing 으로 전체 종료시킨 이슈 → Procfile.dev 에서 python 코어만 두고 portal/bff 는 `make run-web` 분리로 해결.
- `make run` honcho 가 루트 venv 없어 실패 → `uvx honcho` 로 변경.
