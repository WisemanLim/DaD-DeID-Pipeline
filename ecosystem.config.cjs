// pm2 ecosystem — 환경별(local/dev/staging/prod) 서비스 프로세스 통합 관리.
// 호출: APP_ENV=<env> pnpm exec pm2 startOrRestart ecosystem.config.cjs (Makefile <env>-all 에서 실행)
// 인프라(postgres/redis)는 docker compose 담당, 여기는 host-native 프로세스(deid/rag/portal/bff)만 관리.
const APP_ENV = process.env.APP_ENV || "local";
const isProdLike = APP_ENV === "staging" || APP_ENV === "prod";

module.exports = {
  apps: [
    {
      name: "deid",
      cwd: "./services/deid",
      script: "uv",
      args: `run uvicorn app.main:app --host 0.0.0.0 --port 8001${isProdLike ? "" : " --reload"}`,
      interpreter: "none",
      env: { ENV: APP_ENV },
    },
    {
      name: "rag",
      cwd: "./services/rag",
      script: "uv",
      args: `run uvicorn app.main:app --host 0.0.0.0 --port 8002${isProdLike ? "" : " --reload"}`,
      interpreter: "none",
      env: { ENV: APP_ENV },
    },
    {
      name: "bff",
      cwd: "./apps/bff",
      script: isProdLike ? "dist/main.js" : "node_modules/.bin/nest",
      args: isProdLike ? "" : "start --watch",
      interpreter: isProdLike ? "node" : "none",
      env: { NODE_ENV: isProdLike ? "production" : "development", APP_ENV, PORT: 3001 },
    },
    {
      name: "portal",
      cwd: "./apps/portal",
      script: "node_modules/.bin/next",
      args: isProdLike ? "start -p 3000" : "dev -p 3000",
      interpreter: "none",
      env: { NODE_ENV: isProdLike ? "production" : "development", APP_ENV },
    },
  ],
};
