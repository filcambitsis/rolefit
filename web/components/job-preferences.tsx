"use client";
import { Check, Loader2, Search, ArrowRight } from "lucide-react";

import { Preferences, families, careerLevels, defaults } from "../lib/demo";
type Props = {
  prefs: Preferences;
  setPrefs: (value: Preferences) => void;
  busy: boolean;
  hasCV: boolean;
  togglePreference: (
    key: "families" | "employment" | "career_levels",
    value: string,
  ) => void;
  onApply: () => Promise<void>;
  onProfile: () => void;
};
export function JobPreferences({
  prefs,
  setPrefs,
  busy,
  hasCV,
  togglePreference,
  onApply,
  onProfile,
}: Props) {
  return (
    <>
      <section className="page-heading">
        <div>
          <h1>Job preferences</h1>
          <p>Choose the roles and employment types you want to see.</p>
        </div>
      </section>
      <div className="preferences-layout">
        <section className="panel preferences-panel">
          <div className="preference-section">
            <h2>Role types</h2>
            <p>
              Select role types, or leave all unselected to include every type.
            </p>
            <div className="role-options">
              {families.map((f) => (
                <button
                  key={f}
                  className={prefs.families.includes(f) ? "chosen" : ""}
                  aria-pressed={prefs.families.includes(f)}
                  onClick={() => togglePreference("families", f)}
                >
                  <strong>{f}</strong>
                  <span className="checkbox">
                    {prefs.families.includes(f) && <Check size={13} />}
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="preference-section">
            <h2>Career level</h2>
            <p>
              Estimated from job titles. Leave all unselected to include every
              level. “Not specified” includes titles without a clear level.
              Internships are controlled separately under employment type.
            </p>
            <div className="choice-chips">
              {careerLevels.map(([value, label]) => (
                <button
                  key={value}
                  className={
                    prefs.career_levels.includes(value) ? "chosen" : ""
                  }
                  aria-pressed={prefs.career_levels.includes(value)}
                  onClick={() => togglePreference("career_levels", value)}
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
              {["full-time", "part-time", "internship", "unknown"].map(
                (type) => (
                  <button
                    key={type}
                    className={prefs.employment.includes(type) ? "chosen" : ""}
                    aria-pressed={prefs.employment.includes(type)}
                    onClick={() => togglePreference("employment", type)}
                  >
                    {prefs.employment.includes(type) && <Check size={14} />}{" "}
                    {type === "unknown" ? "Not specified" : type}
                  </button>
                ),
              )}
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
              Only jobs with the selected arrangement are shown. Choose “Open to
              anything” to include unspecified arrangements.
            </p>
          </div>
          <div className="form-footer">
            <button className="text-button" onClick={() => setPrefs(defaults)}>
              Reset preferences
            </button>
            <button
              className="button primary"
              disabled={busy || !prefs.employment.length || !hasCV}
              onClick={onApply}
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
          {!hasCV && (
            <button className="text-button" onClick={onProfile}>
              Add a CV first <ArrowRight size={16} />
            </button>
          )}
        </section>
      </div>
    </>
  );
}
