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
  evidence: Evidence | null;
};
export type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  countries: string[];
  family: string;
  employment: string;
  employment_provenance: string;
  workplace: string;
  provider: string;
  url: string;
  score: number | null;
  required_coverage: number;
  requirements: Requirement[];
  description?: string;
  first_seen: string;
  state?: string;
  method: string;
};
export type Preferences = {
  families: string[];
  employment: string[];
  workplace: string;
  career_levels: string[];
  search: string;
};
export const families = [
  "AI Engineer",
  "ML Engineer",
  "Data Scientist",
  "Data Analyst",
  "Data Engineer",
  "Software Engineer",
  "AI Consultant",
  "Data Consultant",
  "Technology Consultant",
  "AI & Automation Specialist",
  "Solutions Engineer",
  "Product Analyst",
  "Business & Technology Analyst",
  "Product Owner",
];
export const careerLevels = [
  ["junior", "Junior / graduate"],
  ["mid", "Mid-level"],
  ["senior", "Senior"],
  ["lead", "Lead / management"],
  ["unknown", "Not specified"],
];
export function careerLevel(title: string, employment: string): string {
  if (employment === "internship" || /\bintern(?:ship)?\b/i.test(title))
    return "internship";
  if (/\b(?:lead|staff|principal|manager|head|director)\b/i.test(title))
    return "lead";
  if (/\b(?:senior|sr)\b/i.test(title)) return "senior";
  if (/\b(?:junior|jr|graduate|entry[ -]level)\b/i.test(title)) return "junior";
  if (/\b(?:mid[ -]level|medior|intermediate)\b/i.test(title)) return "mid";
  return "unknown";
}
export function matchesCareerLevel(
  job: Pick<Job, "title" | "employment">,
  levels: string[],
): boolean {
  return (
    !levels.length ||
    job.employment === "internship" ||
    levels.includes(careerLevel(job.title, job.employment))
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
    families: (saved.families ?? []).filter((f) => families.includes(f)),
  };
}
export const sampleCV = `Alex Morgan\nMachine Learning Engineer\n\nEXPERIENCE\nMachine Learning Engineer · Northstar Labs · Jan 2022 – Dec 2025\nBuilt Python services for document search and retrieval-augmented generation.\nTrained PyTorch models and deployed inference APIs with FastAPI and Docker.\nDesigned SQL reporting pipelines over a PostgreSQL warehouse.\nShipped production workloads on AWS with automated model monitoring.\nCollaborated with product teams to design experiments and evaluate model quality.\n\nEDUCATION\nMSc Computer Science · 2020 – 2022\n\nPROJECTS\nBuilt a semantic search tool using embeddings, vector databases and natural language processing.\nCreated interactive dashboards using Python, pandas and data visualization.\n\nLANGUAGES\nEnglish: fluent\n`;
export const skillTerms: Record<string, string[]> = {
  Python: ["python"],
  SQL: ["sql", "postgresql"],
  PyTorch: ["pytorch"],
  Docker: ["docker"],
  AWS: ["aws"],
  FastAPI: ["fastapi"],
  RAG: ["retrieval-augmented generation", "rag"],
  NLP: ["natural language processing", "nlp"],
  Embeddings: ["embeddings"],
  pandas: ["pandas"],
  "Data visualization": ["data visualization", "dashboards"],
  Kubernetes: ["kubernetes"],
  TensorFlow: ["tensorflow"],
  Spark: ["spark"],
  Tableau: ["tableau"],
  "A/B testing": ["a/b testing"],
  Statistics: ["statistics"],
  "Stakeholder management": ["stakeholder management"],
  Azure: ["azure"],
  "Computer vision": ["computer vision"],
};
export function parseEvidence(text: string): Evidence[] {
  const rows: Evidence[] = [];
  let offset = 0;
  for (const line of text.split("\n")) {
    const quote = line.trim();
    const start = offset + line.indexOf(quote);
    if (quote.length > 18)
      rows.push({
        id: `ev-${start}`,
        quote,
        start,
        end: start + quote.length,
        section: "CV evidence",
        skills: Object.entries(skillTerms)
          .filter(([, aliases]) =>
            aliases.some((a) =>
              new RegExp(
                `(^|[^a-z])${a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^a-z]|$)`,
                "i",
              ).test(quote),
            ),
          )
          .map(([skill]) => skill),
      });
    offset += line.length + 1;
  }
  return rows;
}
const templates = [
  [
    "Meridian",
    "AI Engineer, Search & Discovery",
    "Amsterdam, Netherlands",
    "NL",
    "AI Engineer",
    "hybrid",
    ["Python", "RAG", "FastAPI", "Docker"],
    ["Kubernetes", "Embeddings"],
  ],
  [
    "Arc",
    "Machine Learning Engineer",
    "Utrecht, Netherlands",
    "NL",
    "ML Engineer",
    "remote",
    ["Python", "PyTorch", "AWS", "Docker"],
    ["Spark", "SQL"],
  ],
  [
    "Layers",
    "Applied AI Engineer",
    "Rotterdam, Netherlands",
    "NL",
    "AI Engineer",
    "hybrid",
    ["Python", "NLP", "Embeddings"],
    ["TensorFlow", "Azure"],
  ],
  [
    "Forma",
    "Data Scientist, Product",
    "Amsterdam, Netherlands",
    "NL",
    "Data Scientist",
    "hybrid",
    ["Python", "SQL", "Statistics"],
    ["A/B testing", "pandas"],
  ],
  [
    "Orbit",
    "Data Analyst",
    "Eindhoven, Netherlands",
    "NL",
    "Data Analyst",
    "remote",
    ["SQL", "Data visualization", "pandas"],
    ["Tableau", "Python"],
  ],
  [
    "Parallel",
    "ML Platform Engineer",
    "Utrecht, Netherlands",
    "NL",
    "ML Engineer",
    "on-site",
    ["Python", "Docker", "Kubernetes", "AWS"],
    ["PyTorch", "Spark"],
  ],
  [
    "Aperture",
    "Computer Vision Engineer",
    "The Hague, Netherlands",
    "NL",
    "ML Engineer",
    "hybrid",
    ["Python", "PyTorch", "Computer vision"],
    ["Docker", "AWS"],
  ],
  [
    "Harbour",
    "Junior Software Engineer",
    "Rotterdam, Netherlands",
    "NL",
    "Software Engineer",
    "hybrid",
    ["Python", "SQL"],
    ["Docker"],
  ],
  [
    "Canal",
    "Senior Data Engineer",
    "Amsterdam, Netherlands",
    "NL",
    "Data Engineer",
    "remote",
    ["Python", "SQL", "AWS"],
    ["Spark"],
  ],
] as const;
export function demoJobs(evidence: Evidence[]): Job[] {
  return templates
    .map((t, i) => {
      const requirements: Requirement[] = [
        ...t[6].map((s) => ({ skill: s, required: true })),
        ...t[7].map((s) => ({ skill: s, required: false })),
      ].map((r, ri) => {
        const ev = evidence.find((e) => e.skills.includes(r.skill));
        return {
          id: `r-${i}-${ri}`,
          text: `Experience with ${r.skill}`,
          ...r,
          status: ev ? "met" : "not_verified",
          tier: ev ? "vocabulary" : "unverified",
          evidence: ev || null,
        };
      });
      const required = requirements.filter((r) => r.required);
      const coverage =
        required.filter((r) => r.status === "met").length / required.length;
      const score = requirementScore(requirements);
      return {
        id: `demo-${i}`,
        company: t[0],
        title: t[1],
        location: t[2],
        countries: [t[3]],
        family: t[4],
        employment: t[0] === "Aperture" ? "part-time" : "full-time",
        employment_provenance: "sample",
        workplace: t[5],
        provider: ["greenhouse", "lever", "ashby"][i % 3],
        url: "",
        score,
        required_coverage: coverage,
        requirements,
        first_seen: "2026-09-14",
        method: "Requirement coverage",
        description:
          "This illustrative role is part of the sample workspace. Requirements demonstrate how RoleFit connects a job to verified passages in a CV. Connect the backend to browse current postings from employers.",
      };
    })
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
}

// Match the API: absent requirement groups do not reduce the available score.
export function requirementScore(requirements: Requirement[]): number | null {
  if (!requirements.length) return null;
  let earned = 0,
    total = 0;
  for (const [required, weight] of [
    [true, 0.85],
    [false, 0.15],
  ] as const) {
    const group = requirements.filter((r) => r.required === required);
    if (group.length) {
      earned +=
        (weight * group.filter((r) => r.status === "met").length) /
        group.length;
      total += weight;
    }
  }
  return Math.round((100 * earned) / total);
}
