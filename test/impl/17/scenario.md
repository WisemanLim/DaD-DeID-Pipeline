# impl/17 — bff NestJS 스캐폴딩 완료 시험 시나리오

`apps/bff` 는 `console.log` 스텁뿐(NestFactory 미호출, tsconfig/nest-cli.json 부재)이라
`nest build`/`nest start` 자체가 불가했다(impl/16 결과 §발견 이슈 2). 이번 차수 범위:
최소 동작 NestJS 앱(health 엔드포인트, :3001)으로 완성해 pm2 환경별 실행에 재편입.
**OIDC/RBAC/ABAC/감사로그 등 실제 인증·권한·감사 로직은 이번 범위 밖**(PRD 다음 단계로 이관).

## 케이스

| # | 케이스 | 명령 | 기대 |
|---|---|---|---|
| 1 | 타입체크/빌드 | `nest build` | 에러 없이 `dist/main.js` 생성 |
| 2 | 프로덕션 모드 기동 | `PORT=3099 node dist/main.js` + `curl :3099/health` | `{"status":"ok","service":"bff","env":"local"}` |
| 3 | dev watch 기동 | `nest start` + `curl :3098/health` | 동일 응답, 정상 종료(SIGTERM) |
| 4 | pm2 통합(local) | `make local-all` | deid/rag/portal/bff 4앱 모두 online, restart=0 |
| 5 | bff 헬스체크(pm2) | `curl :3001/health` | `{"status":"ok","service":"bff","env":"local"}` |
| 6 | 중지 | `make local-stop` | pm2 delete(deid/rag/portal/bff) + compose down |
