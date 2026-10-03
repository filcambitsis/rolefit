.PHONY: setup check run-api run-web crawl extract evaluate label up
setup:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'
	cd web && npm ci
	mkdir -p work
	.venv/bin/alembic upgrade head
check:
	.venv/bin/ruff check api ml scripts tests
	.venv/bin/pytest -q
	cd web && npm run typecheck && npm run lint && npm run build
run-api:
	DEV_AUTH=true .venv/bin/uvicorn rolefit.main:app --host 127.0.0.1 --port 8000
run-web:
	cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev
crawl:
	.venv/bin/rolefit crawl
extract:
	.venv/bin/rolefit extract
evaluate:
	.venv/bin/rolefit evaluate
label:
	.venv/bin/python scripts/label.py
up:
	docker compose up --build
