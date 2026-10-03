# RoleFit

Evidence-grounded job matching for AI and data roles. Upload a CV, choose preferences, and inspect the CV passage behind each matched requirement. The project includes a Next.js frontend, FastAPI backend, job ingestion, and a ranking evaluation pipeline.

**Status:** the application currently uses an untrained evidence-coverage score. The research hypothesis has not been evaluated: human-authored personas, human labels, a reviewed ESCO vocabulary, and quality audits are still required. Included persona drafts and the demo snapshot are explicitly synthetic and must not be reported as research results.

## Project layout

| Folder | Purpose |
| --- | --- |
| `api/` | FastAPI application, authentication, CV parsing, ingestion, and database migrations |
| `web/` | Next.js frontend |
| `ml/` | Embeddings, retrieval baselines, and ranking evaluation |
| `data/` | Source configuration, vocabulary, demo fixtures, and annotation inputs |
| `tests/` | Automated correctness and isolation tests |
| `scripts/` | Annotation, data preparation, and maintenance tools |
| `docs/` | Experiment protocol, grading rubric, retention policy, and future work |
| `.github/` | Continuous integration |

Root configuration files support Python packaging, database migrations, Docker, and common development commands. `.env.example` files contain configuration examples, not real credentials.

## Run locally

Requires Python 3.12+ and Node.js 22+.

```sh
make setup
```

Then run each command in a separate terminal:

```sh
make run-api
make run-web
```

The frontend opens at `http://127.0.0.1:3000`; the API is on port `8000`. These commands enable local development authentication. For a fresh database, run `make crawl` to collect job postings. Without an API URL configured, the frontend offers a clearly labelled sample workspace.

`make up` is the Docker Compose alternative with PostgreSQL and pgvector. Production requires Supabase configuration, development authentication disabled, and deployment configuration for the chosen host.

## Development commands

- `make check` — Python lint/tests, frontend types/lint, and production build.
- `make crawl` — collect and reconcile public job postings.
- `make extract` — deterministic preview requirement extraction.
- `make label` — start the human annotation tool after preparing a frozen snapshot.
- `make evaluate` — evaluate a completed human-labelled snapshot; refuses incomplete research inputs.

Local embeddings require `.venv/bin/pip install -e '.[ml]'`, followed by `.venv/bin/rolefit embed`. Structured model extraction requires the LLM settings in `.env.example`; use `.venv/bin/rolefit extract --llm` to enable it explicitly.

## Local files

`.venv/`, `node_modules/`, and `rolefit.egg-info/` support installed dependencies. `work/` contains the local database, model downloads, and scratch files. These are ignored by Git and hidden in the VS Code Explorer by the workspace settings; they remain accessible on disk. Disposable test and build caches regenerate when needed.

Do not delete `work/` just to tidy the folder: it contains collected data. Never commit real CVs, credentials, or local databases.

## Documentation

- [Pre-registered experiment](docs/preregistration.md)
- [Human grading rubric](docs/rubric.md)
- [Persona fixture notes](data/personas/README.md)
- [Retention policy](docs/retention.md)
- [Future work](docs/later.md)

MIT licensed.
