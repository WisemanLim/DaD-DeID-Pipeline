import { Controller, Get } from "@nestjs/common";

@Controller()
export class AppController {
  @Get("health")
  health() {
    return { status: "ok", service: "bff", env: process.env.APP_ENV ?? "local" };
  }
}
