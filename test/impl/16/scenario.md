# impl/16 — pm2 기반 환경별 실행 표준 (Makefile) 시험 시나리오

참고 프로젝트(AITech-VLM-receipt) Makefile 의 `local-all`/`<env>-all` 패턴을
`ecosystem.config.cjs`(pm2) + `Makefile` 로 이식. 대상: `deid`(:8001), `rag`(:8002),
`portal`(:3000). `bff`는 nest 스캐폴딩 미완(tsconfig.json/nest-cli.json 없음)으로
이번 차수 범위 제외(주석 처리, README 트러블슈팅에 기록).

## 케이스

| # | 케이스 | 명령 | 기대 |
|---|---|---|---|
| 1 | Makefile 문법 | `make -n local-all` | dry-run 에러 없이 3단계 명령 출력 |
| 2 | 인프라+서비스 기동 | `make local-all` | postgres/redis healthy, pm2 apps(deid/rag/portal) online |
| 3 | deid 헬스체크 | `curl :8001/health` | `{"status":"ok",...}` |
| 4 | rag 헬스체크 | `curl :8002/health` | `{"status":"ok",...}` |
| 5 | portal 응답 | `curl -o /dev/null -w '%{http_code}' :3000` | 200 |
| 6 | 상태 조회 | `make local-ps` | pm2 ls + compose ps 출력, 대상 3앱 online/restart=0 |
| 7 | 중지 | `make local-stop` | pm2 delete(deid/rag/portal) + compose down, 기존 무관 pm2 프로세스(CoreSight-*) 영향 없음 |
