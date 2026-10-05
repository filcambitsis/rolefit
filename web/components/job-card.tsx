"use client";
import {
  ArrowUpRight,
  Bookmark,
  BriefcaseBusiness,
  Check,
  MapPin,
} from "lucide-react";
import { demoMode } from "../lib/api";
import { Job } from "../lib/demo";
import { Score, CompanyMark } from "./job-display";
type Props = {
  job: Job;
  i: number;
  saved: string[];
  toggleSave: (job: Job) => Promise<void>;
  openJob: (job: Job) => Promise<void>;
};
export function JobCard({ job, i, saved, toggleSave, openJob }: Props) {
  return (
    <article className="job-card" key={job.id}>
      <div className="job-top">
        <CompanyMark company={job.company} index={i} />
        <div className="job-heading">
          <div className="company-line">
            {job.company}
            <span>·</span>
            <span>{demoMode ? "Sample role" : job.provider}</span>
          </div>
          <button className="job-title" onClick={() => openJob(job)}>
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
            fill={saved.includes(job.id) ? "currentColor" : "none"}
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
          <span className="workplace-tag">{job.workplace}</span>
        )}
      </div>
      <div className="job-skills">
        {job.requirements
          .filter((r) => r.skill)
          .slice(0, 4)
          .map((r) => (
            <span
              key={r.id}
              className={r.status === "met" ? "matched-skill" : ""}
            >
              {r.status === "met" && <Check size={12} />} {r.skill}
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
                job.requirements.filter((r) => r.status === "met" && r.required)
                  .length
              }{" "}
              of {job.requirements.filter((r) => r.required).length} required
              items supported
            </span>
            {/senior|staff|principal|director|head of|lead /i.test(
              job.title,
            ) && <span>Senior role · check experience requirements</span>}
          </div>
        </div>
        <button className="text-button" onClick={() => openJob(job)}>
          View evidence <ArrowUpRight size={17} />
        </button>
      </div>
    </article>
  );
}
