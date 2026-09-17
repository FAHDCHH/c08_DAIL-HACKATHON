from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now():
    return datetime.now(timezone.utc)


# many-to-many: a claim is backed by one or more evidence records
claim_evidence = Table(
    "claim_evidence",
    Base.metadata,
    Column("claim_id", ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", ForeignKey("evidence_records.id", ondelete="CASCADE"), primary_key=True),
)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[str] = mapped_column(String(120))
    program: Mapped[str] = mapped_column(String(200))
    period: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source_reports = relationship("SourceReport", back_populates="event", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="event", cascade="all, delete-orphan")
    suggestions = relationship("Suggestion", back_populates="event", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="event", uselist=False, cascade="all, delete-orphan")


class SourceReport(Base):
    __tablename__ = "source_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(80))
    format: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    simulated: Mapped[str] = mapped_column(String(10), default="no")  # "yes" tags a simulated feed
    processed: Mapped[bool] = mapped_column(default=False)  # folded into a generated report yet?
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event = relationship("Event", back_populates="source_reports")
    evidence = relationship("EvidenceRecord", back_populates="source_report", cascade="all, delete-orphan")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_report_id: Mapped[int] = mapped_column(ForeignKey("source_reports.id", ondelete="CASCADE"))
    excerpt: Mapped[str] = mapped_column(Text)  # verbatim, immutable

    source_report = relationship("SourceReport", back_populates="evidence")
    claims = relationship("Claim", secondary=claim_evidence, back_populates="evidence_records")


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    period: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # supported|conflicting|unsupported|uncertain
    reasoning: Mapped[str] = mapped_column(Text)

    event = relationship("Event", back_populates="claims")
    evidence_records = relationship("EvidenceRecord", secondary=claim_evidence, back_populates="claims")
    annotations = relationship("Annotation", back_populates="claim", cascade="all, delete-orphan")


class Suggestion(Base):
    __tablename__ = "suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    about_claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), nullable=True)
    officer_validated: Mapped[str] = mapped_column(String(10), default="pending")  # pending|kept|dismissed

    event = relationship("Event", back_populates="suggestions")


class Annotation(Base):
    __tablename__ = "annotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    claim = relationship("Claim", back_populates="annotations")


class Revision(Base):
    __tablename__ = "revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    instruction: Mapped[str] = mapped_column(Text)  # the officer's note / request
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed|accepted|refused
    before_json: Mapped[str] = mapped_column(Text)  # snapshot to revert to on refuse
    after_json: Mapped[str] = mapped_column(Text)   # the revised draft the agent produced
    pdf_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|approved
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(300), nullable=True)

    event = relationship("Event", back_populates="report")


class GeneratedReport(Base):
    """History of every PDF the agent produced, downloadable and searchable by event."""
    __tablename__ = "generated_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # draft|approved|revision|reverted
    pdf_path: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
