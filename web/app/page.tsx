"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  BriefcaseBusiness,
  Check,
  ChevronDown,
  Compass,
  FileText,
  Loader2,
  LogOut,
  MapPin,
  Menu,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  cleanPreferences,
  matchesCareerLevel,
  careerLevels,
  defaults,
  demoJobs,
  Evidence,
  families,
  Job,
  parseEvidence,
  Preferences,
  sampleCV,
} from "../lib/demo";
import { demoMode, request, supabase } from "../lib/api";

type View = "matches" | "profile" | "preferences" | "saved";

function descriptionParagraphs(text: string): string[] {
  // Keep source line breaks, joining short fragments introduced by inline links.
  const paragraphs: string[] = [];
  for (const line of text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)) {
    const previous = paragraphs.at(-1);
    if (
      previous &&
      !/[.!?:]$/.test(previous) &&
      (line.length < 50 || previous.length < 5)
    ) {
      paragraphs[paragraphs.length - 1] += ` ${line}`;
    } else {
      paragraphs.push(line);
    }
  }
  // Some feeds supply a single long block; break it at sentence boundaries.
  return paragraphs.flatMap((paragraph) => {
    if (paragraph.length < 700) return [paragraph];
    const sentences = paragraph.split(/(?<=[.!?])\s+(?=[A-Z])/);
    const chunks: string[] = [];
    for (let i = 0; i < sentences.length; i += 3) {
      chunks.push(sentences.slice(i, i + 3).join(" "));
    }
    return chunks;
  });
}

function Score({
  score,
  large = false,
}: {
  score: number | null;
  large?: boolean;
}) {
  return (
    <div
      className={`score ${large ? "score-large" : ""}`}
      aria-label={
        score === null
          ? "Not enough requirements extracted"
          : `${score}% requirement coverage`
      }
    >
      <span>
        {score ?? "—"}
        <small>{score === null ? "N/A" : "%"}</small>
      </span>
    </div>
  );
}
function CompanyMark({
  company,
  index = 0,
}: {
  company: string;
  index?: number;
}) {
  return (
    <div className={`company-mark mark-${index % 5}`} aria-hidden="true">
      {company.slice(0, 1)}
    </div>
  );
}

export default function Home() {
  const [view, setView] = useState<View>("matches");
  const [prefs, setPrefs] = useState<Preferences>(defaults);
  const [evidence, setEvidence] = useState<Evidence[]>(
    demoMode ? parseEvidence(sampleCV) : [],
  );
  const [jobs, setJobs] = useState<Job[]>(
    demoMode ? demoJobs(parseEvidence(sampleCV)) : [],
  );
  const [cvName, setCvName] = useState(
    demoMode ? "Alex Morgan · Sample CV" : "No CV uploaded",
  );
  const [draft, setDraft] = useState("");
  const [selected, setSelected] = useState<Job | null>(null);
  const [saved, setSaved] = useState<string[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [email, setEmail] = useState("");
  const [needsAuth, setNeedsAuth] = useState(false);
  const [sort, setSort] = useState("score");
  const [visibleCount, setVisibleCount] = useState(20);
  const [tab, setTab] = useState("all");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  const load = useCallback(async () => {
    if (demoMode) return;
    try {
      const profile = await request<{
        cv: { filename: string } | null;
        evidence: Evidence[];
        preferences: Preferences;
        saved: string[];
        skipped: string[];
      }>("/me");
      setPrefs(cleanPreferences(profile.preferences));
      setSaved(profile.saved);
      setSkipped(profile.skipped);
      setEvidence(profile.evidence);
      setCvName(profile.cv?.filename || "No CV uploaded");
      setNeedsAuth(false);
      if (profile.cv) {
        const data = await request<{ jobs: Job[] }>("/matches", {
          method: "POST",
        });
        setJobs(data.jobs);
      } else setView("profile");
    } catch (e) {
      setError((e as Error).message);
      if (supabase) setNeedsAuth(true);
    }
  }, []);
  useEffect(() => {
    if (demoMode) {
      try {
        const data = JSON.parse(
          localStorage.getItem("rolefit-demo-preferences") || "{}",
        );
        if (data.saved) setSaved(data.saved);
        if (data.prefs) setPrefs(cleanPreferences(data.prefs));
      } catch {
        /* invalid local preferences are safely ignored */
      }
    } else void load();
    const sub = supabase?.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") void load();
    });
    return () => sub?.data.subscription.unsubscribe();
  }, [load]);
  useEffect(() => {
    if (notice) {
      const id = setTimeout(() => setNotice(""), 4000);
      return () => clearTimeout(id);
    }
  }, [notice]);
  useEffect(() => {
    if (!selected) return;
    previousFocus.current = document.activeElement as HTMLElement;
    modalRef.current?.focus();
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
      if (e.key === "Tab") {
        const items = modalRef.current?.querySelectorAll<HTMLElement>(
          'button, a[href], input, select, [tabindex="0"]',
        );
        if (!items?.length) return;
        const first = items[0],
          last = items[items.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === modalRef.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKey);
      previousFocus.current?.focus();
    };
  }, [selected]);
  function navigate(next: View) {
    setView(next);
    setMobileMenu(false);
    setError("");
  }
  async function refresh(nextPrefs = prefs, nextEvidence = evidence) {
    setBusy(true);
    setError("");
    try {
      if (demoMode) {
        setJobs(demoJobs(nextEvidence));
        localStorage.setItem(
          "rolefit-demo-preferences",
          JSON.stringify({ saved, prefs: nextPrefs }),
        );
      } else {
        await request("/preferences", {
          method: "PUT",
          body: JSON.stringify(nextPrefs),
        });
        const data = await request<{ jobs: Job[] }>("/matches", {
          method: "POST",
        });
        setJobs(data.jobs);
      }
      setNotice("Your matches are up to date");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function openJob(job: Job) {
    setSelected(job);
    if (!demoMode) {
      try {
        const detail = await request<Job>(`/jobs/${job.id}`);
        setSelected((current) =>
          current?.id === job.id ? { ...detail, method: job.method } : current,
        );
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }
  async function toggleSave(job: Job) {
    const next = saved.includes(job.id)
      ? saved.filter((id) => id !== job.id)
      : [...saved, job.id];
    try {
      if (!demoMode)
        await request(`/jobs/${job.id}/decision`, {
          method: "PUT",
          body: JSON.stringify({
            state: next.includes(job.id) ? "saved" : "none",
          }),
        });
      setSaved(next);
      if (demoMode)
        localStorage.setItem(
          "rolefit-demo-preferences",
          JSON.stringify({ saved: next, prefs }),
        );
      setNotice(
        next.includes(job.id)
          ? "Job added to your shortlist"
          : "Job removed from your shortlist",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function skip(job: Job) {
    try {
      if (!demoMode)
        await request(`/jobs/${job.id}/decision`, {
          method: "PUT",
          body: JSON.stringify({ state: "skipped" }),
        });
      setSkipped([...skipped, job.id]);
      setSaved(saved.filter((id) => id !== job.id));
      setSelected(null);
      setNotice("Job hidden from your matches");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function parseCV(file?: File, text?: string) {
    setError("");
    setBusy(true);
    try {
      if (demoMode) {
        if (file && !/\.(txt|md)$/i.test(file.name))
          throw new Error(
            "PDF and DOCX parsing requires the connected backend. In this sample workspace, paste CV text or upload a .txt file.",
          );
        const raw = text || (await file!.text());
        if (raw.trim().length < 50)
          throw new Error("Please add at least 50 characters of CV text.");
        const next = parseEvidence(raw);
        setEvidence(next);
        setJobs(demoJobs(next));
        setCvName(file?.name || "Your CV · this session");
      } else {
        const data = new FormData();
        data.append(
          "file",
          file || new File([text || ""], "cv.txt", { type: "text/plain" }),
        );
        const result = await request<{
          evidence: Evidence[];
          filename: string;
        }>("/cv", { method: "POST", body: data });
        setEvidence(result.evidence);
        setCvName(result.filename);
      }
      setDraft("");
      setView("preferences");
      setNotice("CV parsed. Your evidence is ready.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function deleteCV() {
    try {
      if (!demoMode) await request("/cv", { method: "DELETE" });
      setEvidence([]);
      setJobs([]);
      setCvName("No CV uploaded");
      setNotice("CV and extracted evidence deleted");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function togglePreference(
    key: "families" | "employment" | "career_levels",
    value: string,
  ) {
    setPrefs({
      ...prefs,
      [key]: prefs[key].includes(value)
        ? prefs[key].filter((v) => v !== value)
        : [...prefs[key], value],
    });
  }
  const filtered = jobs.filter(
    (j) =>
      !skipped.includes(j.id) &&
      (view !== "saved" || saved.includes(j.id)) &&
      (!prefs.families.length || prefs.families.includes(j.family)) &&
      j.countries.includes("NL") &&
      prefs.employment.includes(j.employment) &&
      (prefs.workplace === "any" || j.workplace === prefs.workplace) &&
      matchesCareerLevel(j, prefs.career_levels) &&
      (!prefs.search ||
        `${j.title} ${j.company}`
          .toLowerCase()
          .includes(prefs.search.toLowerCase())) &&
      (tab !== "strong" || (j.score !== null && j.score >= 80)),
  );
  filtered.sort((a, b) =>
    sort === "newest"
      ? b.first_seen.localeCompare(a.first_seen)
      : (b.score ?? -1) - (a.score ?? -1),
  );

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {mobileMenu && (
        <button
          aria-label="Close navigation"
          className="nav-backdrop"
          onClick={() => setMobileMenu(false)}
        />
      )}
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <button
          className="brand"
          onClick={() => navigate("matches")}
          aria-label="RoleFit home"
        >
          <span className="brand-icon">
            r<span>↗</span>
          </span>
          rolefit<span className="brand-period">.</span>
        </button>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={view === "matches" ? "active" : ""}
            onClick={() => navigate("matches")}
          >
            <Compass size={20} /> Find jobs{" "}
            <span className="nav-count">{jobs.length}</span>
          </button>
          <button
            className={view === "saved" ? "active" : ""}
            onClick={() => navigate("saved")}
          >
            <Bookmark size={20} /> Saved jobs{" "}
            {saved.length > 0 && (
              <span className="nav-count">{saved.length}</span>
            )}
          </button>
          <div className="nav-divider" />
          <button
            className={view === "profile" ? "active" : ""}
            onClick={() => navigate("profile")}
          >
            <FileText size={20} /> My CV{" "}
            <span className={`tiny-dot ${evidence.length ? "ready" : ""}`} />
          </button>
          <button
            className={view === "preferences" ? "active" : ""}
            onClick={() => navigate("preferences")}
          >
            <SlidersHorizontal size={20} /> Preferences
          </button>
        </nav>
        {supabase && !needsAuth && (
          <button
            className="text-button"
            onClick={async () => {
              await supabase!.auth.signOut();
              setNeedsAuth(true);
              setJobs([]);
              setEvidence([]);
              setSaved([]);
            }}
          >
            <LogOut size={17} /> Sign out
          </button>
        )}
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-toggle icon-button"
              aria-label="Open navigation"
              onClick={() => setMobileMenu(true)}
            >
              <Menu size={22} />
            </button>
            <strong>
              {
                {
                  matches: "Find jobs",
                  saved: "Saved jobs",
                  profile: "My CV",
                  preferences: "Preferences",
                }[view]
              }
            </strong>
          </div>
        </header>
        <main id="main">
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={17} />
              </button>
            </div>
          )}
          {needsAuth ? (
            <section className="auth-card">
              <span className="eyebrow">SIGN IN</span>
              <h1>Welcome to RoleFit.</h1>
              <p>
                Sign in to privately upload your CV and discover roles that fit
                your experience.
              </p>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  setBusy(true);
                  const result = await supabase!.auth.signInWithOtp({
                    email,
                    options: { emailRedirectTo: window.location.origin },
                  });
                  setBusy(false);
                  if (result.error) setError(result.error.message);
                  else setNotice("Check your email for your sign-in link.");
                }}
              >
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <button className="button primary" disabled={busy}>
                  {busy ? <Loader2 className="spin" size={18} /> : null}Send
                  sign-in link <ArrowRight size={17} />
                </button>
              </form>
            </section>
          ) : (
            <>
              {(view === "matches" || view === "saved") && (
                <>
                  <section className="page-heading">
                    <div>
                      <h1>
                        {view === "saved"
                          ? "Saved jobs"
                          : "Tech jobs in the Netherlands"}
                      </h1>
                      <p>
                        {view === "saved"
                          ? "Jobs you’ve saved to review or apply to."
                          : "Compare job requirements with your CV."}
                      </p>
                    </div>
                    <button
                      className="button primary"
                      disabled={busy || !evidence.length}
                      onClick={() => refresh()}
                    >
                      {busy ? (
                        <Loader2 size={17} className="spin" />
                      ) : (
                        <Sparkles size={17} />
                      )}
                      Refresh matches
                    </button>
                  </section>
                  <section className="workspace-grid">
                    <div className="results-column">
                      <div className="results-toolbar">
                        <div
                          className="tabs"
                          role="group"
                          aria-label="Match filter"
                        >
                          <button
                            className={tab === "all" ? "selected" : ""}
                            onClick={() => setTab("all")}
                          >
                            All matches
                          </button>
                          <button
                            className={tab === "strong" ? "selected" : ""}
                            onClick={() => setTab("strong")}
                          >
                            80%+ coverage
                          </button>
                        </div>
                        <label className="sort-label">
                          <ArrowDown size={14} />
                          <select
                            aria-label="Sort jobs"
                            value={sort}
                            onChange={(e) => setSort(e.target.value)}
                          >
                            <option value="score">Requirement coverage</option>
                            <option value="newest">Most recent</option>
                          </select>
                          <ChevronDown size={13} />
                        </label>
                      </div>
                      <div className="search-row">
                        <label className="search-box">
                          <Search size={18} />
                          <input
                            aria-label="Search roles or companies"
                            placeholder="Search roles or companies"
                            value={prefs.search}
                            onChange={(e) =>
                              setPrefs({ ...prefs, search: e.target.value })
                            }
                          />
                          {prefs.search && (
                            <button
                              aria-label="Clear search"
                              onClick={() => setPrefs({ ...prefs, search: "" })}
                            >
                              <X size={16} />
                            </button>
                          )}
                        </label>
                        <button
                          className="filter-button"
                          onClick={() => navigate("preferences")}
                        >
                          <SlidersHorizontal size={17} />
                          Filters
                        </button>
                      </div>
                      <div className="result-count">
                        <span>
                          {filtered.length}{" "}
                          {filtered.length === 1 ? "role" : "roles"} for you
                        </span>
                        <span>
                          <ShieldCheck size={13} />
                          Grounded in your CV
                        </span>
                      </div>
                      <div className="job-list">
                        {filtered.slice(0, visibleCount).map((job, i) => (
                          <article className="job-card" key={job.id}>
                            <div className="job-top">
                              <CompanyMark company={job.company} index={i} />
                              <div className="job-heading">
                                <div className="company-line">
                                  {job.company}
                                  <span>·</span>
                                  <span>
                                    {demoMode ? "Sample role" : job.provider}
                                  </span>
                                </div>
                                <button
                                  className="job-title"
                                  onClick={() => openJob(job)}
                                >
                                  {job.title}
                                </button>
                              </div>
                              <button
                                className={`save-button ${saved.includes(job.id) ? "is-saved" : ""}`}
                                aria-label={`${saved.includes(job.id) ? "Unsave" : "Save"} ${job.title}`}
                                aria-pressed={saved.includes(job.id)}
                                onClick={() => toggleSave(job)}
                              >
                                <Bookmark
                                  size={20}
                                  fill={
                                    saved.includes(job.id)
                                      ? "currentColor"
                                      : "none"
                                  }
                                />
                              </button>
                            </div>
                            <div className="job-meta">
                              <span>
                                <MapPin size={14} />
                                {job.location}
                              </span>
                              <span>
                                <BriefcaseBusiness size={14} />
                                {job.employment === "unknown"
                                  ? "Employment not specified"
                                  : job.employment}
                              </span>
                              {job.workplace && job.workplace !== "unknown" && (
                                <span className="workplace-tag">
                                  {job.workplace}
                                </span>
                              )}
                            </div>
                            <div className="job-skills">
                              {job.requirements
                                .filter((r) => r.skill)
                                .slice(0, 4)
                                .map((r) => (
                                  <span
                                    key={r.id}
                                    className={
                                      r.status === "met" ? "matched-skill" : ""
                                    }
                                  >
                                    {r.status === "met" && <Check size={12} />}{" "}
                                    {r.skill}
                                  </span>
                                ))}
                            </div>
                            <div className="job-footer">
                              <div className="fit-summary">
                                <Score score={job.score} />
                                <div>
                                  <strong>
                                    {job.score === null
                                      ? "Not enough requirements extracted"
                                      : "Requirement coverage"}
                                  </strong>
                                  <span>
                                    {
                                      job.requirements.filter(
                                        (r) => r.status === "met" && r.required,
                                      ).length
                                    }{" "}
                                    of{" "}
                                    {
                                      job.requirements.filter((r) => r.required)
                                        .length
                                    }{" "}
                                    required items supported
                                  </span>
                                  <span>
                                    {(job.requirements.length < 5 ||
                                      job.requirements.filter((r) => r.required)
                                        .length < 3) &&
                                    job.score !== null
                                      ? "Limited extraction · review the full posting"
                                      : "Skill mentions do not establish proficiency"}
                                  </span>
                                  {/senior|staff|principal|director|head of|lead /i.test(
                                    job.title,
                                  ) && (
                                    <span>
                                      Senior role · check experience
                                      requirements
                                    </span>
                                  )}
                                </div>
                              </div>
                              <button
                                className="text-button"
                                onClick={() => openJob(job)}
                              >
                                View evidence <ArrowUpRight size={17} />
                              </button>
                            </div>
                          </article>
                        ))}
                      </div>
                      {filtered.length > visibleCount && (
                        <button
                          className="button secondary full-width"
                          onClick={() => setVisibleCount(visibleCount + 20)}
                        >
                          Show more roles · {filtered.length - visibleCount}{" "}
                          remaining <ArrowDown size={16} />
                        </button>
                      )}
                      {!filtered.length && (
                        <div className="empty-state">
                          <Compass size={38} />
                          <h2>
                            {view === "saved"
                              ? "No saved jobs yet."
                              : evidence.length
                                ? tab === "strong"
                                  ? "No matches at 80% or above."
                                  : "No roles match these filters."
                                : "Upload a CV to get started."}
                          </h2>
                          <p>
                            {view === "saved"
                              ? "Save a role to keep it within reach."
                              : evidence.length
                                ? tab === "strong"
                                  ? "Try all matches to see jobs with lower coverage."
                                  : "Try fewer filters or clear your search."
                                : "Add your CV to turn your experience into job matches."}
                          </p>
                          <button
                            className="button primary"
                            onClick={() => {
                              if (
                                view !== "saved" &&
                                evidence.length &&
                                tab === "strong"
                              ) {
                                setTab("all");
                                return;
                              }
                              navigate(
                                view === "saved"
                                  ? "matches"
                                  : evidence.length
                                    ? "preferences"
                                    : "profile",
                              );
                            }}
                          >
                            {view === "saved"
                              ? "Find jobs"
                              : evidence.length
                                ? tab === "strong"
                                  ? "Show all matches"
                                  : "Edit preferences"
                                : "Add your CV"}
                            <ArrowRight size={16} />
                          </button>
                          {skipped.length > 0 && (
                            <button
                              className="text-button"
                              onClick={async () => {
                                if (!demoMode)
                                  await Promise.all(
                                    skipped.map((id) =>
                                      request(`/jobs/${id}/decision`, {
                                        method: "PUT",
                                        body: JSON.stringify({ state: "none" }),
                                      }),
                                    ),
                                  );
                                setSkipped([]);
                              }}
                            >
                              Restore hidden roles
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </section>
                </>
              )}
              {view === "profile" && (
                <>
                  <section className="page-heading">
                    <div>
                      <h1>My CV</h1>
                      <p>
                        Upload your CV and review the text used for matching.
                      </p>
                    </div>
                    {evidence.length > 0 && (
                      <button
                        className="button secondary"
                        onClick={() => navigate("preferences")}
                      >
                        Set preferences <ArrowRight size={17} />
                      </button>
                    )}
                  </section>
                  <div className="form-grid">
                    <section className="panel upload-panel">
                      <h2>Upload or replace your CV</h2>
                      <p>
                        Use a text-based PDF, Word document, or plain text CV.
                      </p>
                      <button
                        disabled={busy}
                        className={`dropzone ${drag ? "dragging" : ""}`}
                        onDragOver={(e) => {
                          e.preventDefault();
                          setDrag(true);
                        }}
                        onDragLeave={() => setDrag(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setDrag(false);
                          const file = e.dataTransfer.files[0];
                          if (file) void parseCV(file);
                        }}
                        onClick={() => fileRef.current?.click()}
                      >
                        <span className="upload-icon">
                          {busy ? (
                            <Loader2 size={26} className="spin" />
                          ) : (
                            <Upload size={26} />
                          )}
                        </span>
                        <strong>
                          {busy ? "Reading your CV…" : "Drop your CV here"}
                        </strong>
                        <span>
                          or <b>browse files</b>
                        </span>
                        <small>
                          {demoMode
                            ? "Demo: .txt · PDF & DOCX with connected backend"
                            : "PDF, DOCX, TXT · Maximum 5 MB"}
                        </small>
                      </button>
                      <input
                        ref={fileRef}
                        type="file"
                        accept={demoMode ? ".txt,.md" : ".pdf,.docx,.txt"}
                        className="sr-only"
                        onChange={(e) => {
                          if (e.target.files?.[0])
                            void parseCV(e.target.files[0]);
                          e.target.value = "";
                        }}
                      />
                      <div className="or-divider">
                        <span />
                        or paste your CV
                        <span />
                      </div>
                      <label htmlFor="cv-text" className="sr-only">
                        CV text
                      </label>
                      <textarea
                        id="cv-text"
                        placeholder="Paste your experience, projects, education, and skills…"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={7}
                      />
                      <button
                        className="button primary full-width"
                        disabled={busy || draft.trim().length < 50}
                        onClick={() => parseCV(undefined, draft)}
                      >
                        Use this CV <ArrowRight size={17} />
                      </button>
                      <div className="privacy-note">
                        <ShieldCheck size={16} />
                        <p>
                          {demoMode
                            ? "Pasted CV text stays in memory for this demo session. It is not saved to browser storage."
                            : "Original files are discarded after parsing. You can delete retained text and evidence at any time."}
                        </p>
                      </div>
                    </section>
                    <section className="panel evidence-panel">
                      <div className="evidence-heading">
                        <h2>Current CV</h2>
                        {evidence.length > 0 && (
                          <button
                            className="text-button danger"
                            onClick={deleteCV}
                          >
                            Delete CV
                          </button>
                        )}
                      </div>
                      <p>{evidence.length ? cvName : "No CV uploaded."}</p>
                      {!evidence.length && (
                        <div className="evidence-placeholder">
                          <FileText size={35} />
                          <p>Upload your CV to start finding jobs.</p>
                        </div>
                      )}
                      {evidence.length > 0 && (
                        <details className="cv-preview">
                          <summary>
                            Review extracted CV text ({evidence.length}{" "}
                            passages)
                          </summary>
                          <p>
                            Check that your CV was read correctly. These are
                            copied passages, not independently verified claims.
                            Matching quotes also appear in each job’s details.
                          </p>
                          <div className="evidence-list">
                            {evidence.map((ev) => (
                              <p key={ev.id}>{ev.quote}</p>
                            ))}
                          </div>
                        </details>
                      )}
                    </section>
                  </div>
                </>
              )}
              {view === "preferences" && (
                <>
                  <section className="page-heading">
                    <div>
                      <h1>Job preferences</h1>
                      <p>
                        Choose the roles and employment types you want to see.
                      </p>
                    </div>
                  </section>
                  <div className="preferences-layout">
                    <section className="panel preferences-panel">
                      <div className="preference-section">
                        <h2>Role types</h2>
                        <p>
                          Select role types, or leave all unselected to include
                          every type.
                        </p>
                        <div className="role-options">
                          {families.map((f) => (
                            <button
                              key={f}
                              className={
                                prefs.families.includes(f) ? "chosen" : ""
                              }
                              aria-pressed={prefs.families.includes(f)}
                              onClick={() => togglePreference("families", f)}
                            >
                              <strong>{f}</strong>
                              <span className="checkbox">
                                {prefs.families.includes(f) && (
                                  <Check size={13} />
                                )}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="preference-section">
                        <h2>Career level</h2>
                        <p>
                          Estimated from job titles. Leave all unselected to
                          include every level. “Not specified” includes titles
                          without a clear level. Internships are controlled
                          separately under employment type.
                        </p>
                        <div className="choice-chips">
                          {careerLevels.map(([value, label]) => (
                            <button
                              key={value}
                              className={
                                prefs.career_levels.includes(value)
                                  ? "chosen"
                                  : ""
                              }
                              aria-pressed={prefs.career_levels.includes(value)}
                              onClick={() =>
                                togglePreference("career_levels", value)
                              }
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="preference-section">
                        <h2>Employment and workplace</h2>
                        <label>Employment type</label>
                        <div className="choice-chips">
                          {[
                            "full-time",
                            "part-time",
                            "internship",
                            "unknown",
                          ].map((type) => (
                            <button
                              key={type}
                              className={
                                prefs.employment.includes(type) ? "chosen" : ""
                              }
                              aria-pressed={prefs.employment.includes(type)}
                              onClick={() =>
                                togglePreference("employment", type)
                              }
                            >
                              {prefs.employment.includes(type) && (
                                <Check size={14} />
                              )}{" "}
                              {type === "unknown" ? "Not specified" : type}
                            </button>
                          ))}
                        </div>
                        <label htmlFor="workplace">Work arrangement</label>
                        <select
                          id="workplace"
                          value={prefs.workplace}
                          onChange={(e) =>
                            setPrefs({ ...prefs, workplace: e.target.value })
                          }
                        >
                          {["any", "remote", "hybrid", "on-site"].map((w) => (
                            <option key={w} value={w}>
                              {w === "any" ? "Open to anything" : w}
                            </option>
                          ))}
                        </select>
                        <p>
                          Only jobs with the selected arrangement are shown.
                          Choose “Open to anything” to include unspecified
                          arrangements.
                        </p>
                      </div>
                      <div className="form-footer">
                        <button
                          className="text-button"
                          onClick={() => setPrefs(defaults)}
                        >
                          Reset preferences
                        </button>
                        <button
                          className="button primary"
                          disabled={
                            busy || !prefs.employment.length || !evidence.length
                          }
                          onClick={async () => {
                            await refresh();
                            setView("matches");
                          }}
                        >
                          {busy ? (
                            <Loader2 size={17} className="spin" />
                          ) : (
                            <Search size={17} />
                          )}
                          Find my matches <ArrowRight size={17} />
                        </button>
                      </div>
                      {!prefs.employment.length && (
                        <p role="alert" className="field-error">
                          Select at least one employment type.
                        </p>
                      )}
                      {!evidence.length && (
                        <button
                          className="text-button"
                          onClick={() => navigate("profile")}
                        >
                          Add a CV first <ArrowRight size={16} />
                        </button>
                      )}
                    </section>
                  </div>
                </>
              )}
            </>
          )}
          {demoMode && (
            <p className="demo-disclaimer">
              Demo · Fictional CV, companies and roles.
            </p>
          )}
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <span>
            <Check size={16} />
          </span>
          {notice}
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {selected && (
        <div
          className="modal-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <div
            className="detail-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="detail-title"
            ref={modalRef}
            tabIndex={-1}
          >
            <div className="detail-topbar">
              <button className="text-button" onClick={() => setSelected(null)}>
                <ArrowLeft size={17} /> Back to matches
              </button>
              <button
                className="icon-button"
                aria-label="Close job details"
                onClick={() => setSelected(null)}
              >
                <X size={21} />
              </button>
            </div>
            <div className="detail-content">
              <CompanyMark company={selected.company} />
              <div className="detail-company">
                {selected.company}
                <span>
                  {demoMode ? "Illustrative role" : `Via ${selected.provider}`}
                </span>
              </div>
              <h1 id="detail-title">{selected.title}</h1>
              <div className="job-meta">
                <span>
                  <MapPin size={14} />
                  {selected.location}
                </span>
                <span>
                  {selected.employment === "unknown"
                    ? "Employment not specified"
                    : selected.employment}
                </span>
                {selected.workplace && selected.workplace !== "unknown" && (
                  <span>{selected.workplace}</span>
                )}
              </div>
              <div className="detail-score">
                <Score score={selected.score} large />
                <div>
                  <h2>
                    {selected.score === null
                      ? "Not enough requirements extracted"
                      : "Requirement coverage"}
                  </h2>
                  <p>
                    How much your CV supports the listed requirements—not your
                    chance of getting hired.
                  </p>
                </div>
              </div>
              <div className="breakdown-title">
                <h2>Requirement details</h2>
                <span>
                  {
                    selected.requirements.filter((r) => r.status === "met")
                      .length
                  }
                  /{selected.requirements.length} matched
                </span>
              </div>
              <p className="breakdown-intro">
                Matched items link to your CV. “Not verified” means you should
                check the requirement yourself.
              </p>
              <div className="requirements">
                {selected.requirements.length === 0 && (
                  <p>
                    Not enough requirements extracted. Open the original posting
                    to review it.
                  </p>
                )}
                {selected.requirements.map((r) => (
                  <div
                    className={`requirement ${r.status === "met" ? "met" : "missing"}`}
                    key={r.id}
                  >
                    <span className="requirement-status">
                      {r.status === "met" ? (
                        <Check size={17} />
                      ) : (
                        <span>–</span>
                      )}
                    </span>
                    <div>
                      <div className="requirement-title">
                        <strong>
                          {r.skill ? `${r.skill}: ` : ""}
                          {r.text}
                        </strong>
                        <span>{r.required ? "Required" : "Preferred"}</span>
                      </div>
                      {r.evidence ? (
                        <>
                          <blockquote>“{r.evidence.quote}”</blockquote>
                          <small>
                            <ShieldCheck size={12} />
                            {r.note || "Exact CV passage · skill mentioned"}
                          </small>
                        </>
                      ) : (
                        <p>Not verified in your CV.</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {selected.description && (
                <div className="job-description">
                  <h2>About this role</h2>
                  {descriptionParagraphs(selected.description).map(
                    (paragraph, index) => (
                      <p key={index}>{paragraph}</p>
                    ),
                  )}
                </div>
              )}
              <div className="detail-provenance">
                <ShieldCheck size={16} />
                <span>
                  Matched requirements link to exact passages from your CV.
                </span>
              </div>
            </div>
            <div className="detail-actions">
              <button
                className="button secondary"
                aria-pressed={saved.includes(selected.id)}
                onClick={() => toggleSave(selected)}
              >
                <Bookmark
                  size={17}
                  fill={saved.includes(selected.id) ? "currentColor" : "none"}
                />
                {saved.includes(selected.id) ? "Saved" : "Save role"}
              </button>
              <button className="text-button" onClick={() => skip(selected)}>
                Skip
              </button>
              {selected.url ? (
                <a
                  className="button primary"
                  href={selected.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Apply on company site <ArrowUpRight size={17} />
                </a>
              ) : (
                <span className="demo-apply">
                  Sample role · applications unavailable
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
