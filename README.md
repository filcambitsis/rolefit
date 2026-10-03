# RoleFit

Job matching for AI, machine learning and data roles that shows its working.

Upload a CV, choose your preferences, and RoleFit ranks current public job postings. For each job, it shows
which requirements your CV supports, with the exact CV passage behind each one, and which requirements it
could not verify.

## How matching works

1. **CV parsing.** Text is read from a PDF, DOCX or TXT file and split into passages (one per line), grouped
   by section (experience, education, projects, skills, languages).
2. **Job requirements.** Each posting's requirement lines are extracted and tagged with skills from a small,
   hand-reviewed vocabulary (`data/skills.json`), as required or preferred.
3. **Evidence check.** A requirement counts as met only when a CV passage supports it, and that passage must
   be an exact substring of your CV. Years of experience and degree level are checked with simple rules.
   Anything else is shown as not verified. That does not mean you lack the skill, only that the CV didn't show it.
4. **Ranking.** Jobs are sorted by **requirement coverage** (85% weight on required, 15% on preferred
   requirements). Ties are broken by BM25 text similarity between the CV and the posting.

The score measures how many of a posting's requirements the CV visibly supports. It is **not** a hiring
probability or a validated suitability rating.

## Status

- Works locally end to end: CV upload, preferences, ranked matches, evidence, save/skip, application links.
- Jobs come from public Greenhouse, Lever and Ashby boards (`data/seeds.json`).
- Matching has not been formally benchmarked. Manual testing with real CVs is in progress.
- Production sign-in (Supabase) is prepared but not deployed. Local runs use a development user.

The project began as a formal ranking study, which was dropped in favour of this smaller scope. See
[docs/archive](docs/archive/README.md).

## Project layout

| Folder | Purpose |
| --- | --- |
| `api/` | FastAPI backend: CV parsing, job collection, matching, authentication, database migrations |
| `web/` | Next.js frontend |
| `data/` | Job board list, skills vocabulary, fictional sample CV |
| `scripts/` | Smoke test and scheduled crawl helper |
| `tests/` | Automated tests |
| `docs/` | Data retention notes, future ideas, archived research plan |

## Run locally

Requires Python 3.12+ and Node.js 22+.

```sh
make setup
```

Then run each command in its own terminal:

```sh
make run-api   # API on http://127.0.0.1:8000
make run-web   # app on http://127.0.0.1:3000
```

If port 3000 is busy, run the frontend on another port and allow it in the API:

```sh
CORS_ORIGINS='["http://127.0.0.1:3002"]' make run-api
cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npx next dev --hostname 127.0.0.1 --port 3002
```

These commands use a local development user (`DEV_AUTH=true`). Never expose that setup publicly. Without an
API URL, the frontend opens a clearly labelled sample workspace with fictional companies.

## Commands

- `make crawl`: fetch and update job postings.
- `make extract`: extract requirements for all eligible jobs.
- `make check`: Python lint and tests, frontend type checks, lint and production build.
- `.venv/bin/python scripts/smoke_api.py`: run the main flow against a running local API using the
  fictional sample CV.
- `.venv/bin/alembic upgrade head`: apply database migrations.

Optional: set the `LLM_*` settings in `.env` and run `.venv/bin/rolefit extract --llm` for model-based
requirement extraction. This path has not been validated, and CV text would be sent to that provider.

## Privacy

Uploaded files are parsed and discarded. CV text and evidence stay in the local database until you replace or
delete the CV. Real CVs, databases and credentials are kept out of Git. See [docs/retention.md](docs/retention.md).

MIT licensed.
