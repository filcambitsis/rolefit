"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  Bookmark,
  Check,
  ChevronDown,
  Compass,
  FileText,
  Loader2,
  LogOut,
  Menu,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";
import {
  cleanPreferences,
  matchesCareerLevel,
  defaults,
  demoJobs,
  Evidence,
  Job,
  demoEvidence,
  Preferences,
} from "../lib/demo";
import { demoMode, request, supabase } from "../lib/api";

import { JobCard } from "../components/job-card";
import { JobDetails } from "../components/job-details";
import { CVProfile } from "../components/cv-profile";
import { JobPreferences } from "../components/job-preferences";

type View = "matches" | "profile" | "preferences" | "saved";

export default function Home() {
  const [view, setView] = useState<View>("matches");
  const [prefs, setPrefs] = useState<Preferences>(defaults);
  const [evidence, setEvidence] = useState<Evidence[]>(
    demoMode ? demoEvidence : [],
  );
  const [jobs, setJobs] = useState<Job[]>(demoMode ? demoJobs : []);
  const [cvName, setCvName] = useState(
    demoMode ? "Alex Morgan · Sample CV" : "No CV uploaded",
  );
  const [draft, setDraft] = useState("");
  const [selected, setSelected] = useState<Job | null>(null);
  const [saved, setSaved] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [email, setEmail] = useState("");
  const [needsAuth, setNeedsAuth] = useState(false);
  const [sort, setSort] = useState("score");
  const [visibleCount, setVisibleCount] = useState(20);
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
      }>("/me");
      setPrefs(cleanPreferences(profile.preferences));
      setSaved(profile.saved);
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
  async function refresh(nextPrefs = prefs) {
    setBusy(true);
    setError("");
    try {
      if (demoMode) {
        setJobs(demoJobs);
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
        setSelected((current) => (current?.id === job.id ? detail : current));
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
  async function parseCV(file?: File, text?: string) {
    setError("");
    setBusy(true);
    try {
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
      (view !== "saved" || saved.includes(j.id)) &&
      (!prefs.families.length || prefs.families.includes(j.family)) &&
      j.countries.includes("NL") &&
      prefs.employment.includes(j.employment) &&
      (prefs.workplace === "any" || j.workplace === prefs.workplace) &&
      matchesCareerLevel(j, prefs.career_levels) &&
      (!prefs.search ||
        `${j.title} ${j.company}`
          .toLowerCase()
          .includes(prefs.search.toLowerCase())),
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
                      </div>
                      <div className="job-list">
                        {filtered.slice(0, visibleCount).map((job, i) => (
                          <JobCard
                            key={job.id}
                            job={job}
                            i={i}
                            saved={saved}
                            toggleSave={toggleSave}
                            openJob={openJob}
                          />
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
                                ? "No roles match these filters."
                                : "Upload a CV to get started."}
                          </h2>
                          <p>
                            {view === "saved"
                              ? "Save a role to keep it within reach."
                              : evidence.length
                                ? "Try fewer filters or clear your search."
                                : "Add your CV to turn your experience into job matches."}
                          </p>
                          <button
                            className="button primary"
                            onClick={() => {
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
                                ? "Edit preferences"
                                : "Add your CV"}
                            <ArrowRight size={16} />
                          </button>
                        </div>
                      )}
                    </div>
                  </section>
                </>
              )}
              {view === "profile" && (
                <CVProfile
                  evidence={evidence}
                  cvName={cvName}
                  busy={busy}
                  draft={draft}
                  setDraft={setDraft}
                  drag={drag}
                  setDrag={setDrag}
                  fileRef={fileRef}
                  parseCV={parseCV}
                  deleteCV={deleteCV}
                  navigate={navigate}
                />
              )}
              {view === "preferences" && (
                <JobPreferences
                  prefs={prefs}
                  setPrefs={setPrefs}
                  busy={busy}
                  hasCV={!!evidence.length}
                  togglePreference={togglePreference}
                  onApply={async () => {
                    await refresh();
                    setView("matches");
                  }}
                  onProfile={() => navigate("profile")}
                />
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
        <JobDetails
          selected={selected}
          saved={saved}
          toggleSave={toggleSave}
          setSelected={setSelected}
          modalRef={modalRef}
        />
      )}
    </div>
  );
}
