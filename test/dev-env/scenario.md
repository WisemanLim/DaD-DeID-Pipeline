# dev-env 검증 시나리오 / env verification

표준 환경이 동작하는지 1회 검증. 구현(`test/impl/<Nth>/`) 전에 통과해야 함.

## 사전 / prerequisites
- [ ] `uv` 설치 (Python 3.12)
- [ ] `pnpm` 9 + Node 22
- [ ] `go` 1.23 (worker 사용 시)
- [ ] Docker + Docker Compose

## 케이스 / cases

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | `make up` | postgres(pgvector)+redis 기동, healthcheck pass |
| 2 | `psql $DATABASE_URL -c '\dx'` | `vector` 확장 존재 |
| 3 | `uv sync` (services/deid, services/rag) | 의존성 설치 성공 |
| 4 | `make run` (honcho) | deid:8001 / rag:8002 / portal:3000 / bff 기동 |
| 5 | `curl localhost:8001/health` | `{"status":"ok","service":"deid"}` |
| 6 | `curl localhost:8002/health` | `{"status":"ok","service":"rag","vector_backend":"sqlite"}` |
| 7 | `make test` | pnpm/pytest 그린 (스텁 통과) |
| 8 | `make dev` (compose --profile app) | deid/rag/worker 컨테이너 빌드·기동 |

## 결과 / result
- 실행일:
- 통과/실패:
- 로그: `logs/`
