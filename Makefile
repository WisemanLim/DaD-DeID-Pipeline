.PHONY: dev test ragas build deploy up down run run-web stop restart logs ps
ENV ?= local

COMPOSE := docker compose
PM2     := pnpm exec pm2

# --- 인프라(datastore)만 기동 / infra only ---
up:      ; docker compose up -d
down:    ; docker compose --profile app down --remove-orphans

# --- 전체 스택 / full stack ---
# pnpm 워크스페이스 앱(portal/bff)은 호스트 실행 권장(아래 run). 자체완결 py/go 서비스만 컨테이너.
dev:     ; docker compose --profile app up

# --- local 멀티프로세스 (honcho via uvx) / host direct-mode ---
# uvx = uv tool run: ephemeral env, 루트 venv 불필요. honcho 가 Procfile 명령들을 spawn.
run:     ; uvx honcho -f Procfile.dev start
run-web: ; pnpm -r --parallel dev               # portal/bff (호스트, node 워크스페이스) — 스텁 완성 후
stop:    ; @echo "honcho 는 포그라운드. Ctrl-C 로 종료 / honcho is foreground; Ctrl-C to stop"
restart: ; @echo "stop 후 make run / stop then re-run"
logs:    ; @echo "honcho 통합 로그는 포그라운드 출력 / honcho streams combined logs in foreground"
ps:      ; uvx honcho -f Procfile.dev check

# --- test / build / deploy ---
test:    ; pnpm -r test && uv run pytest
ragas:   ; uv run pytest -m ragas               # RAG groundedness/recall/MRR
build:   ; docker compose --profile app build
deploy:  ; @echo "helm upgrade / argocd sync (prod=K8s+Helm+Argo)"

# ==== 환경별 표준 실행 (pm2) — 참고: AITech-VLM-receipt Makefile 패턴 이식 ====
#
# 구동 방식: 인프라(postgres/redis)는 docker compose 로 선행 구동하고,
# 서비스(deid/rag uvicorn, portal/bff)는 pm2 로 구동한다.
#
# 사용법:
#   make local-all     # local: compose 인프라 기동 → pm2 로 deid/rag/portal/bff 기동
#   make local-stop     # local: pm2 서비스 중지 → compose 인프라 중지
#   make local-logs     # pm2 로그 팔로우 (인프라 로그는 make local-infra-logs)
#   dev / staging / prod 도 동일한 패턴 (make dev-all, make staging-stop, ...)
#
# 참고:
#   - staging/prod 는 portal 을 빌드(next build)하고 bff 를 빌드(nest build)한 뒤 프로덕션 모드로 서빙한다.
#   - 전체 스택을 컨테이너로만(app 서비스=deid/rag/worker) 띄우려면: make <env>-compose-all.

ENVS := local dev staging prod

define compose_cmd
$(COMPOSE) --env-file .env.$(1)
endef

define ENV_RULES
$(1)-all:
	$(call compose_cmd,$(1)) up -d postgres redis
	@if [ "$(1)" = "staging" ] || [ "$(1)" = "prod" ]; then \
		cd apps/portal && pnpm build; \
		cd ../bff && pnpm build; \
	fi
	APP_ENV=$(1) $(PM2) startOrRestart ecosystem.config.cjs

$(1)-stop:
	-$(PM2) delete deid rag portal bff 2>/dev/null || true
	$(call compose_cmd,$(1)) down

$(1)-logs:
	$(PM2) logs

$(1)-infra-logs:
	$(call compose_cmd,$(1)) logs -f postgres redis

$(1)-ps:
	$(PM2) ls
	$(call compose_cmd,$(1)) ps

# 기존 방식 — app 프로파일 서비스(deid/rag/worker)만 컨테이너로 기동
$(1)-compose-all:
	$(call compose_cmd,$(1)) --profile app up -d --build

.PHONY: $(1)-all $(1)-stop $(1)-logs $(1)-infra-logs $(1)-ps $(1)-compose-all
endef

$(foreach e,$(ENVS),$(eval $(call ENV_RULES,$(e))))

help-env:
	@echo "make {local|dev|staging|prod}-{all|stop|logs|ps}  — compose 인프라 + pm2 서비스 기동/중지/로그/상태"
	@echo "make <env>-infra-logs                              — postgres/redis 인프라 로그"
	@echo "make <env>-compose-all                             — app 서비스(deid/rag/worker)를 docker compose 로만 기동"

.PHONY: help-env
