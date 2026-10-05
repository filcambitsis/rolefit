import data from "./demo-data.json";

export type Evidence = {
  id: string;
  quote: string;
  start: number;
  end: number;
  section: string;
  skills: string[];
};
export type Requirement = {
  id: string;
  text: string;
  skill: string | null;
  required: boolean;
  status: string;
  tier: string;
  note?: string | null;
  evidence: Evidence | null;
};
export type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  countries: string[];
  family: string;
  career_level: string;
  employment: string;
  workplace: string;
  provider: string;
  url: string;
  score: number | null;
  requirements: Requirement[];
  description?: string;
  first_seen: string;
};
export type Preferences = {
  families: string[];
  employment: string[];
  workplace: string;
  career_levels: string[];
  search: string;
};
export const families = data.families;
export const careerLevels = [
  ["junior", "Junior / graduate"],
  ["mid", "Mid-level"],
  ["senior", "Senior"],
  ["lead", "Lead / management"],
  ["unknown", "Not specified"],
];
export function matchesCareerLevel(
  job: Pick<Job, "career_level" | "employment">,
  levels: string[],
): boolean {
  return (
    !levels.length ||
    job.employment === "internship" ||
    levels.includes(job.career_level)
  );
}
export const defaults: Preferences = {
  families: [],
  employment: ["full-time", "part-time", "internship", "unknown"],
  workplace: "any",
  career_levels: [],
  search: "",
};
// Fill in missing fields and drop role families that no longer exist,
// so preferences saved by an older version still work.
export function cleanPreferences(saved: Partial<Preferences>): Preferences {
  return {
    ...defaults,
    employment: saved.employment ?? defaults.employment,
    workplace: saved.workplace ?? defaults.workplace,
    career_levels: (saved.career_levels ?? []).filter((level) =>
      careerLevels.some(([value]) => value === level),
    ),
    search: saved.search ?? defaults.search,
    families: [
      ...new Set(
        (saved.families ?? [])
          .map((f) =>
            ["AI Consultant", "AI Solutions & Implementation"].includes(f)
              ? "AI Consulting & Solutions"
              : f,
          )
          .filter((f) => families.includes(f)),
      ),
    ],
  };
}

export const demoEvidence: Evidence[] = data.evidence;
export const demoJobs: Job[] = data.jobs;
