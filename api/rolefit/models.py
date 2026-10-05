from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CV(Base):
    __tablename__ = "cvs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(200))
    model_version: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50))
    verification_failures: Mapped[int] = mapped_column(Integer, default=0)
    extraction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    cv_id: Mapped[str] = mapped_column(ForeignKey("cvs.id", ondelete="CASCADE"), index=True)
    quote: Mapped[str] = mapped_column(Text)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(50))
    skills: Mapped[list] = mapped_column(JSON, default=list)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("provider", "board", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    board: Mapped[str] = mapped_column(String(100))
    external_id: Mapped[str] = mapped_column(String(150))
    company: Mapped[str] = mapped_column(String(150))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(500))
    countries: Mapped[list] = mapped_column(JSON, default=list)
    family: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="unknown")
    employment: Mapped[str] = mapped_column(String(30))
    employment_provenance: Mapped[str] = mapped_column(String(30))
    workplace: Mapped[str] = mapped_column(String(30))
    workplace_provenance: Mapped[str] = mapped_column(String(30))
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean)
    min_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50))


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    state: Mapped[str] = mapped_column(String(20))


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
