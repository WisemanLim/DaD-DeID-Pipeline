# impl/17 — bff NestJS 스캐폴딩 완료 시험 결과

- 실행일: 2026-07-23
- 판정: **PASS**

| # | 케이스 | 결과 |
|---|---|---|
| 1 | `nest build` | PASS — `dist/main.js` 생성 |
| 2 | `PORT=3099 node dist/main.js` + health | PASS — `{"status":"ok","service":"bff","env":"local"}` |
| 3 | `nest start`(watch) + health | PASS — 동일 응답, 정상 종료 |
| 4 | `make local-all` | PASS — deid/rag/portal/bff 4앱 online, restart=0 |
| 5 | `curl :3001/health` | PASS — `{"status":"ok","service":"bff","env":"local"}` |
| 6 | `make local-stop` | PASS — pm2 delete 4앱 + compose down |

## 구현 범위
- `apps/bff/nest-cli.json`, `tsconfig.json`, `tsconfig.build.json` 신규.
- `apps/bff/src/app.module.ts`, `app.controller.ts`(`GET /health`) 신규.
- `apps/bff/src/main.ts` — `NestFactory.create` 로 교체(기존 `console.log` 스텁 제거), `PORT` env(기본 3001).
- devDependency 추가(`apps/bff/package.json`): `@types/node`, `@types/express`, `ts-jest`, `@nestjs/testing`(사용자 승인 후 `pnpm --filter bff add -D` 설치).
- `ecosystem.config.cjs` — bff 주석 해제(pm2 관리 대상 재편입), `Makefile` `<env>-stop` pm2 delete 목록·`<env>-all` staging/prod build 스텝에 bff 복원.

## 범위 밖(다음 단계 — PRD 기록됨)
- OIDC SSO, RBAC/ABAC, 감사로그(인덱싱/조회/다운로드), 멀티테넌트 RLS 컨텍스트 — AppController 스텁 주석에만 명시, 실제 로직 미구현.

## 생성/수정 파일
- `apps/bff/{nest-cli.json,tsconfig.json,tsconfig.build.json,src/app.module.ts,src/app.controller.ts,src/main.ts,package.json}`
- `ecosystem.config.cjs`, `Makefile`
- `.docs/PRD.v2.md` — 변경 이력 추가(§4.5)
- `test/impl/17/{scenario,result}.md`
