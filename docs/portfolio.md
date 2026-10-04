# Presenting RoleFit

## A 90-second walkthrough

1. Run `make demo` and introduce the problem: a job list is more useful when you can inspect why each role appears.
2. Show role discovery and the requirement-coverage explanation.
3. Open a role. Point to an exact CV passage and a “Not verified in your CV” item.
4. Save a role, visit Saved roles, then show country and role preferences.
5. Explain that the real backend parses PDF/DOCX/TXT and ingests public employer job boards. The displayed demo data is fictional.
6. Finish with the tradeoff: transparent, inexpensive rules instead of an unvalidated learned ranking model. Mention the three-CV checks and limitations.

## CV bullet

Built RoleFit, a full-stack CV-to-job matching app using FastAPI, Next.js and SQLAlchemy, integrating three public job-board providers and explainable requirement coverage linked to exact CV passages.

## Interview points

- Why BM25 is only a tiebreaker: keyword similarity should not override explicit requirement coverage.
- Why an unknown score is different from zero: extraction failure is not evidence of a poor candidate.
- Why no verified match is not a missing skill: CVs are incomplete descriptions.
- How the system protects data: discarded original files, user-scoped records, deletion paths, ignored private data and localhost-only development access.
- How validation changed the code: missed qualification headings, unrelated date ranges counted as relevant experience, ambiguous aliases, and mobile overflow.
- What remains deliberately simple: degree/experience requirements need manual review; no proficiency or hiring-probability claim.

## Media

- [Desktop screenshot](images/desktop.png)
- [Evidence screenshot](images/evidence.png)
- [Mobile screenshot](images/mobile.png)
- [Two-screen demo GIF](images/demo.gif)

All media uses the fictional sample workspace. The GIF is a slideshow of real app screens, not a recording of the full flow.
