.PHONY: setup dev test unit run-mcp run-dashboard fmt lint type build

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e .

dev:
	uvicorn apps.http_dashboard.main:app --reload --port 8766

test:
	pytest -q

unit:
	pytest tests -q

run-mcp:
	python -m apps.mcp_server

run-dashboard:
	python -m apps.http_dashboard.main

fmt:
	ruff check --fix .
	ruff format .

lint:
	ruff check .
	mypy .

type:
	mypy .

build:
	docker build -f infra/docker/Dockerfile.mcp -t prompt-go:mcp .
	docker build -f infra/docker/Dockerfile.dashboard -t prompt-go:dashboard .

