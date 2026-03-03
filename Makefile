.PHONY: sync format lint typecheck docstrings test demo web api web-lan web-ssl stop-web stop-api cert-dev build-index check

sync:
	uv sync --dev

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy voice_triage

docstrings:
	uv run interrogate --config pyproject.toml voice_triage

test:
	uv run pytest -q

demo:
	uv run voice_triage demo

web:
	uv run voice_triage web --host 127.0.0.1 --port 8000 --no-ssl

api:
	uv run voice_triage api --host 127.0.0.1 --port 8000 --no-ssl

web-lan:
	uv run voice_triage web --host 0.0.0.0 --port 8000 --no-ssl

web-ssl:
	uv run voice_triage web --host 0.0.0.0 --port 8443

stop-web:
	uv run voice_triage stop-web

stop-api:
	uv run voice_triage stop-api

cert-dev:
	powershell -ExecutionPolicy Bypass -File .\scripts\generate_dev_tls_cert.ps1 -Hosts localhost,127.0.0.1

build-index:
	uv run voice_triage build-index

check: lint typecheck docstrings test
