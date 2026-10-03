# Archived research plan

RoleFit started as a formal ranking study. The plan was eight candidate personas, 250–350 human-graded
candidate–job pairs, BM25, dense and hybrid baselines, and a logistic-regression ranker evaluated with nDCG@10.

That study was **not carried out**. The project scope changed to a dependable portfolio application,
tested manually with a handful of real CVs. No human labels were collected and no ranking results exist.

These files are kept for context only:

- `preregistration.md`: the original experiment protocol.
- `rubric.md`: the grading rubric the study would have used.
- `verified-build.json`: a record of the September 2026 crawl and build checks.

The experimental code (`ml/`, labelling and audit scripts, synthetic persona drafts) was removed and is
still available in Git history before the "Simplify scope" commit.
