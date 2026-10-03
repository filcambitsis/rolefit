# Persona fixtures

These eight synthetic draft fixtures exercise the software only. They are **not** the hand-authored real-CV-based evaluation personas required by the plan. No synthetic grades are supplied. The freeze command rejects `origin: synthetic-draft`.

Replace their content with eight independently human-authored, anonymized CVs, including the owner's contact-redacted real CV. Set origin to human-authored only when true. Keep the deliberately off-target profile, one profile with no skills section, non-native English, and a two-column parser fixture. Preserve IDs once labels exist. Broad preferences must leave at least 100 eligible jobs per persona. Load each with `rolefit load-persona data/personas/<id>.json` and run `rolefit embed` before freezing.
