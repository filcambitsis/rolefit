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
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Compass,
  FileText,
  Globe2,
  Layers3,
  Loader2,
  LogOut,
  MapPin,
  Menu,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  cleanPreferences,
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
const countries = [
  ["NL", "Netherlands"],
  ["GR", "Greece"],
  ["GB", "United Kingdom"],
  ["DE", "Germany"],
  ["FR", "France"],
  ["IE", "Ireland"],
  ["US", "United States"],
  ["CA", "Canada"],
  ["ES", "Spain"],
  ["CH", "Switzerland"],
  ["IN", "India"],
  ["PL", "Poland"],
  ["SG", "Singapore"],
  ["AU", "Australia"],
];

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
      <svg viewBox="0 0 72 72">
        <circle className="score-track" cx="36" cy="36" r="30" />
        <circle
          className="score-fill"
          cx="36"
          cy="36"
          r="30"
          strokeDasharray={`${(score ?? 0) * 1.885} 188.5`}
        />
      </svg>
      <span>
        {score ?? "—"}
        <small>{score === null ? "N/A" : large ? "OUT OF 100" : "%"}</small>
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
      {index % 3 === 0 && <span>✳</span>}
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
    key: "families" | "countries" | "employment",
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
      (!prefs.countries.length ||
        j.countries.some((c) => prefs.countries.includes(c))) &&
      prefs.employment.includes(j.employment) &&
      (!prefs.search ||
        `${j.title} ${j.company}`
          .toLowerCase()
          .includes(prefs.search.toLowerCase())) &&
      (tab !== "strong" || j.required_coverage >= 0.8),
  );
  filtered.sort((a, b) =>
    sort === "newest"
      ? b.first_seen.localeCompare(a.first_seen)
      : (prefs.workplace !== "any"
          ? Number(b.workplace === prefs.workplace) -
            Number(a.workplace === prefs.workplace)
          : 0) || (b.score ?? -1) - (a.score ?? -1),
  );
  const strong = jobs.filter(
    (j) => j.required_coverage >= 0.8 && !skipped.includes(j.id),
  ).length;

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
            <Compass size={20} /> Discover roles{" "}
            <span className="nav-count">{jobs.length}</span>
          </button>
          <button
            className={view === "saved" ? "active" : ""}
            onClick={() => navigate("saved")}
          >
            <Bookmark size={20} /> Saved roles{" "}
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
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-icon">
              <ShieldCheck size={20} />
            </span>
            <h3>Proof behind the fit.</h3>
            <p>Every matched requirement points to evidence in your CV.</p>
            <button onClick={() => navigate("profile")}>
              See your evidence <ArrowUpRight size={15} />
            </button>
          </div>
          <div className="user-card">
            <div className="avatar">{demoMode ? "AM" : "RF"}</div>
            <div>
              <strong>
                {demoMode ? "Sample workspace" : "Your workspace"}
              </strong>
              <span>
                {demoMode ? "Explore RoleFit" : "Evidence-grounded matching"}
              </span>
            </div>
            {supabase && !needsAuth ? (
              <button
                aria-label="Sign out"
                onClick={async () => {
                  await supabase!.auth.signOut();
                  setNeedsAuth(true);
                  setJobs([]);
                  setEvidence([]);
                  setSaved([]);
                }}
              >
                <LogOut size={17} />
              </button>
            ) : (
              <Settings2 size={17} />
            )}
          </div>
        </div>
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
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {
                {
                  matches: "Discover roles",
                  saved: "Saved roles",
                  profile: "My CV",
                  preferences: "Preferences",
                }[view]
              }
            </strong>
          </div>
          <div className="topbar-right">
            <span className="mode-pill">
              <span />
              {demoMode ? "Interactive demo" : "Connected workspace"}
            </span>
            <button
              className="icon-button help-button"
              aria-label="How matching works"
              onClick={() =>
                setNotice(
                  "Requirement coverage measures support in your CV for extracted job requirements. Required items carry 85% and preferred items 15%; if only one group exists it carries 100%. No extracted requirements means no score. This is not a hiring probability.",
                )
              }
            >
              <CircleHelp size={19} />
            </button>
            <div className="top-avatar">{demoMode ? "AM" : "RF"}</div>
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
              <span className="eyebrow">YOUR NEXT CHAPTER</span>
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
                      <div className="eyebrow">
                        <span className="blue-line" />
                        {view === "saved"
                          ? "YOUR SHORTLIST"
                          : "A LITTLE LESS SEARCH. A LOT MORE FIT."}
                      </div>
                      <h1>
                        {view === "saved"
                          ? "Worth a closer look."
                          : "Your next move, clearer."}
                      </h1>
                      <p>
                        {view === "saved"
                          ? "The roles you want to come back to."
                          : "AI and data roles, matched to what you’ve actually done."}
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
                  <section className="overview" aria-label="Workspace overview">
                    <div className="overview-main">
                      <div className="overview-icon">
                        <Layers3 size={24} />
                      </div>
                      <div>
                        <span>ROLES TO EXPLORE</span>
                        <strong>
                          {jobs.length}
                          <small>in your workspace</small>
                        </strong>
                      </div>
                      <div className="mini-bars" aria-hidden="true">
                        {[24, 40, 31, 55, 43, 68, 57, 78, 70, 92, 85, 100].map(
                          (h, i) => (
                            <i
                              key={i}
                              style={{
                                height: `${h}%`,
                                animationDelay: `${i * 40}ms`,
                              }}
                            />
                          ),
                        )}
                      </div>
                    </div>
                    <div className="overview-stat">
                      <span>
                        <span className="stat-dot" />
                        HIGH REQUIREMENT COVERAGE
                      </span>
                      <strong>
                        {strong.toString().padStart(2, "0")}
                        <small>80%+ required coverage</small>
                      </strong>
                    </div>
                    <div className="overview-stat">
                      <span>
                        <Bookmark size={13} />
                        SAVED FOR LATER
                      </span>
                      <strong>
                        {saved.length.toString().padStart(2, "0")}
                        <small>Your next possibilities</small>
                      </strong>
                    </div>
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
                            All matches{" "}
                            <span>{jobs.length - skipped.length}</span>
                          </button>
                          <button
                            className={tab === "strong" ? "selected" : ""}
                            onClick={() => setTab("strong")}
                          >
                            High coverage <Sparkles size={14} />
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
                          {prefs.families.length + prefs.countries.length >
                            0 && (
                            <span>
                              {prefs.families.length + prefs.countries.length}
                            </span>
                          )}
                        </button>
                      </div>
                      <div className="location-row">
                        <label className="location-picker">
                          <MapPin size={16} aria-hidden="true" />
                          <span>Work location</span>
                          <select
                            aria-label="Work location"
                            disabled={busy}
                            value={
                              prefs.countries.length > 1
                                ? "multiple"
                                : (prefs.countries[0] ?? "")
                            }
                            onChange={async (event) => {
                              const next = {
                                ...prefs,
                                countries: event.target.value
                                  ? [event.target.value]
                                  : [],
                              };
                              setPrefs(next);
                              setVisibleCount(12);
                              await refresh(next);
                            }}
                          >
                            <option value="">All countries</option>
                            {prefs.countries.length > 1 && (
                              <option value="multiple" disabled>
                                Multiple countries ({prefs.countries.length})
                              </option>
                            )}
                            {countries.map(([code, name]) => (
                              <option key={code} value={code}>
                                {name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <p>
                          Choose several countries in Filters. Remote roles
                          still have country restrictions.
                        </p>
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
                          <article
                            className="job-card"
                            key={job.id}
                            style={{
                              animationDelay: `${Math.min(i, 8) * 65}ms`,
                            }}
                          >
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
                                {job.employment}
                              </span>
                              <span className="workplace-tag">
                                {job.workplace}
                              </span>
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
                              ? "Your shortlist starts here."
                              : evidence.length
                                ? "No roles match these filters."
                                : "Let’s find your fit."}
                          </h2>
                          <p>
                            {view === "saved"
                              ? "Save a role to keep it within reach."
                              : evidence.length
                                ? "Try more countries or a broader role family."
                                : "Add your CV to turn your experience into job matches."}
                          </p>
                          <button
                            className="button primary"
                            onClick={() =>
                              navigate(
                                view === "saved"
                                  ? "matches"
                                  : evidence.length
                                    ? "preferences"
                                    : "profile",
                              )
                            }
                          >
                            {view === "saved"
                              ? "Discover roles"
                              : evidence.length
                                ? "Edit preferences"
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
                    <aside className="context-column">
                      <div className="profile-card">
                        <div className="card-kicker">
                          YOUR MATCHING PROFILE{" "}
                          <button
                            className="icon-button"
                            aria-label="Edit CV"
                            onClick={() => navigate("profile")}
                          >
                            <ArrowUpRight size={17} />
                          </button>
                        </div>
                        <div className="profile-file">
                          <div>
                            <FileText size={24} />
                          </div>
                          <span>
                            <strong>{cvName}</strong>
                            <small>
                              {evidence.length
                                ? "Ready for matching"
                                : "Add your experience"}
                            </small>
                          </span>
                          {evidence.length > 0 && (
                            <span className="verified-check">
                              <Check size={13} />
                            </span>
                          )}
                        </div>
                        <div className="profile-divider" />
                        <div className="evidence-total">
                          <span>Verified evidence spans</span>
                          <strong>{evidence.length}</strong>
                        </div>
                        <div className="profile-skills">
                          {Array.from(
                            new Set(evidence.flatMap((e) => e.skills)),
                          )
                            .slice(0, 6)
                            .map((s) => (
                              <span key={s}>{s}</span>
                            ))}
                        </div>
                        <button
                          className="profile-link"
                          onClick={() => navigate("profile")}
                        >
                          Manage your CV <ArrowRight size={15} />
                        </button>
                      </div>
                      <div className="how-card">
                        <span className="how-icon">
                          <Sparkles size={21} />
                        </span>
                        <h2>
                          A match you can
                          <br />
                          actually explain.
                        </h2>
                        <p>
                          No mystery score. Open any role to see what fits,
                          what’s not verified, and the exact lines in your CV
                          behind it.
                        </p>
                        <div className="how-example">
                          <div>
                            <CheckCheck size={15} />
                            <span>Requirement matched</span>
                          </div>
                          <p>“Built Python services for document search…”</p>
                          <span>
                            <FileText size={12} /> A verified quote from your CV
                          </span>
                        </div>
                        <span className="method-note">
                          Scores show requirement coverage, not hiring
                          probability.
                        </span>
                      </div>
                      <div className="source-note">
                        <span>SOURCED AT THE SOURCE</span>
                        <div>
                          Greenhouse <b>·</b> Lever <b>·</b> Ashby
                        </div>
                        <p>
                          {demoMode
                            ? "This demo uses illustrative companies and roles. No live vacancies or research results are claimed."
                            : "Current postings collected directly from employer job boards."}
                        </p>
                      </div>
                    </aside>
                  </section>
                </>
              )}
              {view === "profile" && (
                <>
                  <section className="page-heading">
                    <div>
                      <div className="eyebrow">
                        <span className="blue-line" />
                        THE EVIDENCE STARTS WITH YOU
                      </div>
                      <h1>Your experience. In focus.</h1>
                      <p>
                        Add a CV. We’ll connect your real experience to the
                        right requirements.
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
                      <div className="section-number">
                        01 <span>YOUR CV</span>
                      </div>
                      <h2>A little context goes a long way.</h2>
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
                          {busy
                            ? "Finding your evidence…"
                            : "Drop your CV here"}
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
                        Find my evidence <ArrowRight size={17} />
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
                      <div className="section-number">
                        02 <span>YOUR VERIFIED EVIDENCE</span>
                      </div>
                      <div className="evidence-heading">
                        <h2>{evidence.length} real pieces of your story.</h2>
                        {evidence.length > 0 && (
                          <button
                            className="text-button danger"
                            onClick={deleteCV}
                          >
                            Delete CV
                          </button>
                        )}
                      </div>
                      <p>
                        These are exact passages from your CV. A requirement is
                        only marked as met when a passage supports it.
                      </p>
                      {!evidence.length && (
                        <div className="evidence-placeholder">
                          <FileText size={35} />
                          <p>Your verified passages will appear here.</p>
                        </div>
                      )}
                      <div className="evidence-list">
                        {evidence.map((ev, i) => (
                          <div className="evidence-row" key={ev.id}>
                            <span className="evidence-index">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div>
                              <blockquote>{ev.quote}</blockquote>
                              <div>
                                {ev.skills.map((s) => (
                                  <span className="small-chip" key={s}>
                                    {s}
                                  </span>
                                ))}
                              </div>
                              <small>
                                <ShieldCheck size={12} />
                                Verified · characters {ev.start}–{ev.end}
                              </small>
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  </div>
                </>
              )}
              {view === "preferences" && (
                <>
                  <section className="page-heading">
                    <div>
                      <div className="eyebrow">
                        <span className="blue-line" />
                        MAKE ROOM FOR THE RIGHT ROLE
                      </div>
                      <h1>What comes next?</h1>
                      <p>Set your essentials. Keep the possibilities open.</p>
                    </div>
                  </section>
                  <div className="preferences-layout">
                    <section className="panel preferences-panel">
                      <div className="preference-section">
                        <div className="section-number">
                          01 <span>YOUR DIRECTION</span>
                        </div>
                        <h2>Which roles feel like you?</h2>
                        <p>Choose a few, or leave them all open.</p>
                        <div className="role-options">
                          {families.map((f, i) => (
                            <button
                              key={f}
                              className={
                                prefs.families.includes(f) ? "chosen" : ""
                              }
                              aria-pressed={prefs.families.includes(f)}
                              onClick={() => togglePreference("families", f)}
                            >
                              <span>{["✳", "⌘", "◈", "▤", "↗"][i]}</span>
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
                        <div className="section-number">
                          02 <span>YOUR PLACE</span>
                        </div>
                        <h2>Where are you looking?</h2>
                        <p>
                          No selection means all listed countries. Remote roles
                          still have country restrictions.
                        </p>
                        <div className="choice-chips">
                          {countries.map(([code, name]) => (
                            <button
                              key={code}
                              className={
                                prefs.countries.includes(code) ? "chosen" : ""
                              }
                              aria-pressed={prefs.countries.includes(code)}
                              onClick={() =>
                                togglePreference("countries", code)
                              }
                            >
                              {prefs.countries.includes(code) ? (
                                <Check size={14} />
                              ) : (
                                <Globe2 size={14} />
                              )}{" "}
                              {name}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="preference-section">
                        <div className="section-number">
                          03 <span>YOUR WORKING STYLE</span>
                        </div>
                        <h2>Make it work for you.</h2>
                        <label>Employment type</label>
                        <div className="choice-chips">
                          {["full-time", "part-time", "internship"].map(
                            (type) => (
                              <button
                                key={type}
                                className={
                                  prefs.employment.includes(type)
                                    ? "chosen"
                                    : ""
                                }
                                aria-pressed={prefs.employment.includes(type)}
                                onClick={() =>
                                  togglePreference("employment", type)
                                }
                              >
                                {prefs.employment.includes(type) && (
                                  <Check size={14} />
                                )}{" "}
                                {type}
                              </button>
                            ),
                          )}
                        </div>
                        <label htmlFor="workplace">
                          Workplace preference{" "}
                          <span>(a preference, not a hard filter)</span>
                        </label>
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
                    <aside className="preferences-aside">
                      <span className="orbit-icon">
                        <Compass size={42} />
                      </span>
                      <h2>
                        Think direction,
                        <br />
                        not destination.
                      </h2>
                      <p>
                        A broader search can uncover a role you hadn’t
                        considered. You can adjust these preferences anytime.
                      </p>
                      <div>
                        <ShieldCheck size={18} />
                        <span>
                          Your skills come from your CV. Your preferences come
                          from you.
                        </span>
                      </div>
                    </aside>
                  </div>
                </>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              rolefit<span>.</span> <small>Built on evidence.</small>
            </span>
            <span>
              {demoMode
                ? "Sample workspace · Fictional companies and roles"
                : "Your experience, your next chapter."}
            </span>
          </footer>
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
                <span>{selected.employment}</span>
                <span>{selected.workplace}</span>
              </div>
              <div className="detail-score">
                <Score score={selected.score} large />
                <div>
                  <span className="eyebrow">REQUIREMENT COVERAGE</span>
                  <h2>
                    {selected.score === null
                      ? "Not enough requirements extracted"
                      : `${selected.score}% requirement coverage`}
                  </h2>
                  <p>
                    Coverage measures support for extracted requirements only.
                    Required items carry 85% and preferred items 15%; a sole
                    group carries 100%. It is not a hiring probability. A high
                    score based on few requirements can be misleading.
                  </p>
                </div>
              </div>
              <div className="breakdown-title">
                <h2>The proof behind your fit</h2>
                <span>
                  {
                    selected.requirements.filter((r) => r.status === "met")
                      .length
                  }
                  /{selected.requirements.length} matched
                </span>
              </div>
              <p className="breakdown-intro">
                Supported means a CV passage matches our checks. “Not verified
                in your CV” means no supporting passage was found, not that you
                lack the skill. Skill matches confirm a mention, not proficiency
                or every condition in the sentence. Degree and experience
                requirements need your review.
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
                            Exact CV passage · skill mentioned
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
                  <p>{selected.description}</p>
                </div>
              )}
              <div className="detail-provenance">
                <ShieldCheck size={16} />
                <span>
                  Employment type: {selected.employment_provenance}. Every match
                  is linked to a verified CV passage.
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
