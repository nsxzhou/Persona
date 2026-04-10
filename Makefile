SHELL := /bin/bash

.PHONY: dev db api worker web status stop stop-api stop-worker stop-web logs

ROOT_DIR := $(CURDIR)
API_DIR := $(ROOT_DIR)/api
WEB_DIR := $(ROOT_DIR)/web
RUN_DIR := $(ROOT_DIR)/.run
API_LOG := $(RUN_DIR)/api.log
WORKER_LOG := $(RUN_DIR)/worker.log
WEB_LOG := $(RUN_DIR)/web.log
API_PORT := 8000
WEB_PORT := 3000

dev: db api worker web status

db:
	@echo "检查数据库容器状态..."
	@if docker compose ps --status running --services | grep -q '^postgres$$'; then \
		echo "Postgres 已运行，跳过启动"; \
	else \
		echo "Postgres 未运行，正在启动..."; \
		docker compose up -d postgres; \
	fi

api:
	@mkdir -p "$(RUN_DIR)"
	@echo "检查后端服务状态..."
	@if lsof -iTCP:$(API_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "后端已在 $(API_PORT) 端口运行，跳过启动"; \
	else \
		echo "后端未运行，正在启动..."; \
		if [ ! -f "$(API_DIR)/.env" ] && [ -f "$(API_DIR)/.env.example" ]; then cp "$(API_DIR)/.env.example" "$(API_DIR)/.env"; fi; \
		cd "$(API_DIR)" && uv sync; \
		cd "$(API_DIR)" && uv run alembic upgrade head; \
		cd "$(API_DIR)" && nohup uv run uvicorn app.main:app --reload --port $(API_PORT) >"$(API_LOG)" 2>&1 & \
		for i in $$(seq 1 20); do \
			if lsof -iTCP:$(API_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then break; fi; \
			sleep 1; \
		done; \
		if lsof -iTCP:$(API_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "后端启动完成，日志: $(API_LOG)"; \
		else \
			echo "后端启动失败，请检查日志: $(API_LOG)"; \
			exit 1; \
		fi; \
	fi

worker:
	@mkdir -p "$(RUN_DIR)"
	@echo "检查 StyleAnalysis Worker 状态..."
	@if pgrep -f 'python -m app.worker' >/dev/null 2>&1; then \
		echo "Worker 已运行，跳过启动"; \
	else \
		echo "Worker 未运行，正在启动..."; \
		cd "$(API_DIR)" && uv sync; \
		cd "$(API_DIR)" && nohup uv run python -m app.worker >"$(WORKER_LOG)" 2>&1 & \
		sleep 1; \
		if pgrep -f 'python -m app.worker' >/dev/null 2>&1; then \
			echo "Worker 启动完成，日志: $(WORKER_LOG)"; \
		else \
			echo "Worker 启动失败，请检查日志: $(WORKER_LOG)"; \
			exit 1; \
		fi; \
	fi

web:
	@mkdir -p "$(RUN_DIR)"
	@echo "检查前端服务状态..."
	@if lsof -iTCP:$(WEB_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "前端已在 $(WEB_PORT) 端口运行，跳过启动"; \
	else \
		echo "前端未运行，正在启动..."; \
		if [ ! -f "$(WEB_DIR)/.env.local" ] && [ -f "$(WEB_DIR)/.env.local.example" ]; then cp "$(WEB_DIR)/.env.local.example" "$(WEB_DIR)/.env.local"; fi; \
		cd "$(WEB_DIR)" && pnpm install; \
		cd "$(WEB_DIR)" && nohup pnpm dev --port $(WEB_PORT) >"$(WEB_LOG)" 2>&1 & \
		for i in $$(seq 1 20); do \
			if lsof -iTCP:$(WEB_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then break; fi; \
			sleep 1; \
		done; \
		if lsof -iTCP:$(WEB_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "前端启动完成，日志: $(WEB_LOG)"; \
		else \
			echo "前端启动失败，请检查日志: $(WEB_LOG)"; \
			exit 1; \
		fi; \
	fi

status:
	@echo "== 服务状态 =="
	@if docker compose ps --status running --services | grep -q '^postgres$$'; then \
		echo "数据库: running"; \
	else \
		echo "数据库: stopped"; \
	fi
	@if lsof -iTCP:$(API_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "后端($(API_PORT)): running"; \
	else \
		echo "后端($(API_PORT)): stopped"; \
	fi
	@if pgrep -f 'python -m app.worker' >/dev/null 2>&1; then \
		echo "Worker: running"; \
	else \
		echo "Worker: stopped"; \
	fi
	@if lsof -iTCP:$(WEB_PORT) -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "前端($(WEB_PORT)): running"; \
	else \
		echo "前端($(WEB_PORT)): stopped"; \
	fi

stop: stop-api stop-worker stop-web

stop-api:
	@if lsof -tiTCP:$(API_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		lsof -tiTCP:$(API_PORT) -sTCP:LISTEN | xargs kill; \
		echo "已停止后端"; \
	else \
		echo "后端未运行"; \
	fi

stop-worker:
	@if pgrep -f 'python -m app.worker' >/dev/null 2>&1; then \
		pgrep -f 'python -m app.worker' | xargs kill; \
		echo "已停止 Worker"; \
	else \
		echo "Worker 未运行"; \
	fi

stop-web:
	@if lsof -tiTCP:$(WEB_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		lsof -tiTCP:$(WEB_PORT) -sTCP:LISTEN | xargs kill; \
		echo "已停止前端"; \
	else \
		echo "前端未运行"; \
	fi

logs:
	@echo "后端日志: $(API_LOG)"
	@echo "Worker 日志: $(WORKER_LOG)"
	@echo "前端日志: $(WEB_LOG)"
