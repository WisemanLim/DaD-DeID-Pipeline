# impl/16 — pm2 기반 환경별 실행 표준 (Makefile) 시험 결과

- 실행일: 2026-07-23
- 판정: **PASS**

| # | 케이스 | 결과 |
|---|---|---|
| 1 | `make -n local-all` | PASS — 3줄 dry-run 정상 |
| 2 | `make local-all` | PASS — postgres/redis healthy, deid/rag/portal online (restart=0) |
| 3 | `curl :8001/health` | PASS — `{"status":"ok","service":"deid","env":"local"}` |
| 4 | `curl :8002/health` | PASS — `{"status":"ok","service":"rag","vector_backend":"sqlite"}` |
| 5 | `curl :3000` | PASS — 200 |
| 6 | `make local-ps` | PASS — pm2 ls(3앱 online) + `docker compose ps` |
| 7 | `make local-stop` | PASS — 대상 3앱만 delete, compose down, 기존 무관 pm2 프로세스(CoreSight-G-api/fe) 영향 없음 |

## 발견 이슈 및 조치

1. **`services/{deid,rag}/.venv` 경로 손상**(선행 발견, 이번 구현과 무관한 기존 이슈):
   프로젝트가 과거 `.../tmp/De-Identification-PI-DSI` 경로에서 현재 위치로 이동되면서
   venv 내 스크립트 shebang 이 구 경로를 가리켜 `uv run uvicorn` 이
   `Failed to spawn: uvicorn (No such file or directory)` 로 실패.
   조치: `rm -rf services/{deid,rag}/.venv && uv sync` 로 venv 재생성(shebang 정상화, PASS 재확인).
2. **`apps/bff` nest 스캐폴딩 미완**: `tsconfig.json`/`nest-cli.json` 부재로 `nest start --watch` 즉시 에러,
   pm2 크래시 루프 발생. 조치: `ecosystem.config.cjs`/`Makefile` 에서 bff 를 주석 처리로 제외
   (완료 후 재활성화 지점 코드 주석에 명시). Procfile.dev 의 기존 관례(portal/bff 는 `make run-web` 분리)와 일치.

## 생성/수정 파일
- `.docs/PRD.v2.md` — §9 실행/프로세스 관리 표준 추가, 변경 이력 기록.
- `ecosystem.config.cjs` — 신규. deid/rag/portal pm2 앱 정의(bff 는 주석 처리).
- `Makefile` — `<env>-all/-stop/-logs/-infra-logs/-ps/-compose-all`(env∈local/dev/staging/prod) 타겟 추가, `help-env` 추가.
- `test/impl/16/{scenario,result}.md` — 본 시험.
