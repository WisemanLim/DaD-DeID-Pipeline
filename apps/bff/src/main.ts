// DaD DeID Pipeline BFF — 인증/권한/감사 분리.
// 남은 구현(PRD 다음 단계): OIDC SSO + RBAC/ABAC, 감사로그(인덱싱/조회/다운로드), 멀티테넌트 RLS 컨텍스트.
import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3001);
}

bootstrap();
