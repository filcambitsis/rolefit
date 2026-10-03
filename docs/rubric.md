# Apply-worthiness rubric (frozen v1)

Question: **Based on this CV, is this a job this candidate should realistically spend time applying for?**

Judge only the supplied CV and posting. Respect hard filters. Do not infer unstated qualifications or sponsorship. Look for demonstrated work, not keyword counts. The CV may support skills implicitly; quote the supporting passage in your note. Do not look at model scores while grading.

| Grade | Meaning | Two examples |
|---|---|---|
| 0 | Not a realistic application | An analyst with no software experience for a staff ML infrastructure role; an unrelated retail profile for an advanced research scientist role. |
| 1 | Significant required gaps | A Python analyst lacking required production ML deployment; a new graduate for a role explicitly requiring five years of relevant experience. |
| 2 | Plausible application with manageable gaps | An ML engineer with relevant deployment projects but no preferred cloud tool; an experienced analyst who has used a comparable BI platform. |
| 3 | Strong realistic application | Required experience, core skills and responsibilities are directly supported; a closely aligned candidate missing only a clearly optional tool. |

A missing keyword alone does not imply a missing ability. Grade the realistic application, not confidence in receiving an offer. When uncertain between adjacent grades, select the lower grade and leave a short note. Never use an LLM to supply the human ground truth. Re-grade 30 random pairs later and report quadratic weighted kappa separately.
