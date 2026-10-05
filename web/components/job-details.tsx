"use client";
import {
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  Check,
  MapPin,
  ShieldCheck,
  X,
} from "lucide-react";
import { demoMode } from "../lib/api";
import { Job } from "../lib/demo";
import type { RefObject } from "react";
import { Score, CompanyMark, descriptionParagraphs } from "./job-display";
type Props = {
  selected: Job;
  saved: string[];
  toggleSave: (job: Job) => Promise<void>;
  setSelected: (job: Job | null) => void;
  modalRef: RefObject<HTMLDivElement | null>;
};
export function JobDetails({
  selected,
  saved,
  toggleSave,
  setSelected,
  modalRef,
}: Props) {
  return (
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
              {selected.requirements.filter((r) => r.status === "met").length}/
              {selected.requirements.length} matched
            </span>
          </div>
          <p className="breakdown-intro">
            Matched items link to your CV. “Not verified” means you should check
            the requirement yourself. Skill mentions do not establish
            proficiency.
          </p>
          <div className="requirements">
            {selected.requirements.length === 0 && (
              <p>
                Not enough requirements extracted. Open the original posting to
                review it.
              </p>
            )}
            {selected.requirements.map((r) => (
              <div
                className={`requirement ${r.status === "met" ? "met" : "missing"}`}
                key={r.id}
              >
                <span className="requirement-status">
                  {r.status === "met" ? <Check size={17} /> : <span>–</span>}
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
  );
}
