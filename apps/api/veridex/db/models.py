import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veridex.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    claimed_dispute_type: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped["Order | None"] = relationship(back_populates="case")
    claims: Mapped[list["Claim"]] = relationship(back_populates="case")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case")
    investigations: Mapped[list["Investigation"]] = relationship(back_populates="case")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), unique=True)
    external_order_id: Mapped[str] = mapped_column(String(120))
    seller_name: Mapped[str] = mapped_column(String(200))
    buyer_name: Mapped[str] = mapped_column(String(200))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(8))

    case: Mapped[Case] = relationship(back_populates="order")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    sku: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    canonical_class: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[int] = mapped_column(Integer)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)

    order: Mapped[Order] = relationship(back_populates="items")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    party: Mapped[str] = mapped_column(String(32))
    claim_type: Mapped[str] = mapped_column(String(32))
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    canonical_class: Mapped[str | None] = mapped_column(String(120))
    claimed_quantity: Mapped[int | None] = mapped_column(Integer)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    statement: Mapped[str | None] = mapped_column(Text)

    case: Mapped[Case] = relationship(back_populates="claims")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32))
    party: Mapped[str] = mapped_column(String(32))
    original_filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(120))
    byte_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(500))
    media_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    text_body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship(back_populates="evidence")


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(500))
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    is_keyframe: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelObservation(Base):
    __tablename__ = "model_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    frame_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    page_number: Mapped[int | None] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(120))
    raw_label: Mapped[str] = mapped_column(String(200))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    detector_confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceEvent(Base):
    __tablename__ = "evidence_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_observation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    frame_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(32))
    canonical_class: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(32))
    timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[dict | None] = mapped_column(JSONB)
    text: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[dict | None] = mapped_column(JSONB)
    detector_confidence: Mapped[float | None] = mapped_column(Float)


class CoverageDecision(Base):
    __tablename__ = "coverage_decisions"
    __table_args__ = (UniqueConstraint("case_id", "role", name="uq_coverage_case_role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    suggested_coverage: Mapped[str] = mapped_column(String(32), default="unassessed")
    suggestion_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggestion_basis: Mapped[str] = mapped_column(Text, default="")
    final_coverage: Mapped[str] = mapped_column(String(32), default="unassessed")
    final_basis: Mapped[str] = mapped_column(Text, default="")
    decision_source: Mapped[str | None] = mapped_column(String(32))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    stage: Mapped[str] = mapped_column(String(32), default="snapshot")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    pipeline_version: Mapped[str] = mapped_column(String(32))
    taxonomy_version: Mapped[str] = mapped_column(String(32))
    acceptance_config_version: Mapped[str] = mapped_column(String(32))
    coverage_config_version: Mapped[str] = mapped_column(String(32))
    model_manifest: Mapped[dict] = mapped_column(JSONB, default=dict)
    order_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    claims_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    questions: Mapped[list | None] = mapped_column(JSONB)
    expected_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    observed_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    assessment: Mapped[str | None] = mapped_column(String(32))
    assessment_rationale: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped[Case] = relationship(back_populates="investigations")


class EvidenceObservation(Base):
    __tablename__ = "evidence_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"))
    observation_type: Mapped[str] = mapped_column(String(32))
    canonical_class: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(32))
    order_item_id: Mapped[str | None] = mapped_column(String(64))
    observed: Mapped[bool | None] = mapped_column(Boolean)
    start_timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    end_timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    supporting_frame_ids: Mapped[list] = mapped_column(JSONB, default=list)
    supporting_event_ids: Mapped[list] = mapped_column(JSONB, default=list)
    observation_strength: Mapped[str | None] = mapped_column(String(16))
    observed_quantity_estimate: Mapped[int | None] = mapped_column(Integer)
    quantity_strength: Mapped[str | None] = mapped_column(String(16))
    detector_support: Mapped[list | None] = mapped_column(JSONB)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[dict | None] = mapped_column(JSONB)
    party: Mapped[str | None] = mapped_column(String(32))
    statement_text: Mapped[str | None] = mapped_column(Text)
    shipping_event_type: Mapped[str | None] = mapped_column(String(64))
    source_payload: Mapped[dict | None] = mapped_column(JSONB)


class EvidenceCoverage(Base):
    __tablename__ = "evidence_coverage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role: Mapped[str] = mapped_column(String(32))
    suggested_coverage: Mapped[str] = mapped_column(String(32))
    suggestion_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    suggestion_basis: Mapped[str] = mapped_column(Text, default="")
    final_coverage: Mapped[str] = mapped_column(String(32))
    final_basis: Mapped[str] = mapped_column(Text, default="")
    decision_source: Mapped[str | None] = mapped_column(String(32))
    frames_examined: Mapped[int | None] = mapped_column(Integer)
    sampling_rate: Mapped[str | None] = mapped_column(String(32))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    observation_ids: Mapped[list] = mapped_column(JSONB, default=list)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True)
    question_key: Mapped[str] = mapped_column(String(200))
    subject_key: Mapped[str] = mapped_column(String(120))
    aspect: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    basis: Mapped[str] = mapped_column(Text)
    final_coverage: Mapped[str] = mapped_column(String(32))
    observation_strength: Mapped[str | None] = mapped_column(String(16))
    expected_quantity: Mapped[int | None] = mapped_column(Integer)
    observed_quantity_estimate: Mapped[int | None] = mapped_column(Integer)
    quantity_strength: Mapped[str | None] = mapped_column(String(16))


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), index=True)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    evidence_observation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    frame_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[dict | None] = mapped_column(JSONB)
    canonical_class: Mapped[str | None] = mapped_column(String(120))
    detector_confidence: Mapped[float | None] = mapped_column(Float)
    search_scope: Mapped[dict | None] = mapped_column(JSONB)
    role: Mapped[str | None] = mapped_column(String(32))


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), unique=True)
    body: Mapped[dict] = mapped_column(JSONB)
    body_markdown: Mapped[str] = mapped_column(Text)
    narrator: Mapped[str] = mapped_column(String(32), default="template")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
