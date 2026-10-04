# Portfolio validation

Checked locally on 3–4 October 2026. This documents engineering verification, not scientific validation of candidate suitability.

## Three private CVs

Three user-provided, text-based PDFs (one, two and one pages) parsed successfully. Exact source-offset checks passed for all extracted passages. Real CV files, names, contact details and quotes are not included in this document or public fixtures.

AI-assisted inspection covered five jobs for each profile, including high-coverage results, less relevant roles and a posting with no extracted requirements. Selection was exploratory rather than random. It found:

- Missing qualification headings inflated coverage by omitting constraints.
- A standalone employment date range incorrectly satisfied specialised work experience.
- A ReAct agent mention could be confused with the React framework.
- Newly added skills were absent from old stored evidence.
- Skills listed in a CV did not establish seniority, proficiency or the full conditions of a compound requirement.

Fixes add section boundaries, preserve unverified constraints, refresh saved evidence, distinguish ReAct, and leave degree and experience constraints for manual review. The UI now states the limits of skill mentions, flags senior titles and limited extraction, and shows no score when extraction produces no requirements.

Some mismatches remain: alternatives, compound requirements, incomplete vocabulary and uncommon job headings. This is why the product reports requirement coverage rather than suitability. A user's own review of relevance remains valuable; no independent human-rating study has been performed.

## Automated checks

Run `make check` to repeat:
- Python lint and 45 regression tests.
- Frontend scoring-contract and demo-employment checks.
- TypeScript checks, ESLint and production build.

Tests include required-only/preferred-only/empty scoring, consistent rounding, exact evidence, forged-span rejection, user isolation, bad uploads, CV replacement/deletion, legacy cache cleanup, stale CV extraction, negation, skill aliases, retired preferences, crawler failure handling and local-development authentication restrictions.

SQLite migrations were verified on a fresh database and applied to the existing database after a local backup, and `alembic check` reported no pending schema differences. PostgreSQL migrations are covered by the repository CI workflow; no new remote CI run is claimed until these changes are pushed.

## Public job data

The refreshed corpus contained 245 eligible jobs from the configured public boards during this check. Counts change with time. Three old endpoints (Lever Netflix, Lever Welocalize and Ashby Anthropic) returned 404s and had no open stored jobs; they were removed from the active seed list. The remaining sources refreshed without failures.

Six application URLs, two per provider, returned HTTP 200. This is a spot check, not a guarantee that every posting remains open. Failed boards preserve existing jobs; partial failures are reported and return a nonzero exit code.

## Browser checks

- Demo discovery, evidence detail, save/unsave, skip/restore, preferences and empty results.
- Connected upload of the fictional CV, preferences, matching, details and save/skip.
- No-requirements job displays N/A and an explanation.
- Backend unavailable state displays a clear retry message.
- Desktop at 1440 px and mobile at 390 px.
- Fixed mobile horizontal overflow; measured document width matches viewport width.
- Hidden mobile navigation no longer exposes off-screen controls.
- Screenshots contain only fictional demo content.

Default local startup uses frontend 3002 and API 8000 with matching CORS settings and polling enabled for macOS file-watcher limits.

## Release boundary

Ready for a local portfolio demonstration after the documented checks pass. Public hosting, production authentication, backup-retention operations and a remote CI result are separate from these local checks.

## Netherlands-only update (5 October 2026)

The API enforces Netherlands availability for matches, job details and saving. Legacy country preferences are ignored, and old foreign bookmarks are hidden. Tests cover foreign/unknown remote locations and multi-location Dutch jobs. The source list now contains Eye Security, DataSnipper, IMC and TomTom (Lever EU). Refresh yielded 11 eligible listings, all with extracted requirements after adding missing section-heading variants. Desktop (1440px) and mobile (390px) layouts, evidence, simplified preferences, saving and shortlist navigation were checked; screenshots were refreshed.
