import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from veridex.db.models import (
    Claim,
    CoverageDecision,
    Evidence,
    EvidenceCoverage,
    EvidenceEvent,
    EvidenceObservation,
    EvidenceReference,
    Finding,
    Frame,
    Investigation,
    InvestigationReport,
    ModelObservation,
    Order,
    OrderItem,
    ProcessingJob,
    TimelineEntry,
)
from veridex.domain.acceptance import AcceptanceConfig, DetectionBox, accept_group
from veridex.domain.coverage import suggest_coverage
from veridex.domain.enums import Category, EvidenceKind, EvidenceRole, ObservationType
from veridex.domain.errors import DomainError
from veridex.domain.evaluation import ObjectView, RoleCoverage, evaluate_investigation
from veridex.domain.questions import AcceptedObservation, ClaimRef, OrderLine, generate_investigation_questions
from veridex.domain.report import build_report
from veridex.domain.taxonomy import Taxonomy
from veridex.pipeline.detector import Detector
from veridex.pipeline.media import duration_ms, extract_frames, probe
from veridex.pipeline.narrator import Narrator
from veridex.pipeline.ocr import OcrEngine
from veridex.storage.local import LocalFilesystemStorage

PHASE_ORDER = ["ordered", "packed", "shipped", "unboxed", "stated"]
ROLE_PHASE = {
    EvidenceRole.PACKING_VIDEO.value: "packed",
    EvidenceRole.UNBOXING_VIDEO.value: "unboxed",
    EvidenceRole.SHIPPING.value: "shipped",
    EvidenceRole.CUSTOMER_STATEMENT.value: "stated",
    EvidenceRole.SELLER_STATEMENT.value: "stated",
}


def load_acceptance(path: Path) -> tuple[AcceptanceConfig, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AcceptanceConfig(
        version=str(payload["version"]),
        min_detector_confidence=payload["min_detector_confidence"],
        min_supporting_frames=payload["min_supporting_frames"],
        min_persistence_ms=payload["min_persistence_ms"],
        max_confidence_spread=payload["max_confidence_spread"],
        max_bbox_center_drift=payload["max_bbox_center_drift"],
        min_stable_frames=payload["min_stable_frames"],
        max_gap_ms=payload["max_gap_ms"],
    ), payload


def run_investigation(
    session: Session,
    investigation_id: uuid.UUID,
    *,
    detector: Detector,
    ocr: OcrEngine,
    storage: LocalFilesystemStorage,
    taxonomy: Taxonomy,
    acceptance_path: Path,
    max_duration_ms: int,
    license_unreviewed: bool,
) -> None:
    investigation = session.get(Investigation, investigation_id)
    if investigation is None:
        raise DomainError("not_found", "Investigation was not found")
    job = session.scalar(select(ProcessingJob).where(ProcessingJob.investigation_id == investigation.id))
    investigation.status = "running"
    investigation.started_at = datetime.now(timezone.utc)
    if job is not None:
        job.status = "running"
        job.started_at = investigation.started_at
        job.stage = "normalize"
    session.commit()
    try:
        _execute(
            session,
            investigation,
            job,
            detector=detector,
            ocr=ocr,
            storage=storage,
            taxonomy=taxonomy,
            acceptance_path=acceptance_path,
            max_duration_ms=max_duration_ms,
            license_unreviewed=license_unreviewed,
        )
    except Exception as exc:
        session.rollback()
        investigation = session.get(Investigation, investigation_id)
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.investigation_id == investigation_id))
        message = exc.message if isinstance(exc, DomainError) else str(exc)
        if investigation is not None:
            investigation.status = "failed"
            investigation.finished_at = datetime.now(timezone.utc)
            investigation.case.status = "failed"
        if job is not None:
            job.status = "failed"
            job.error = message
            job.finished_at = datetime.now(timezone.utc)
        session.commit()
        if isinstance(exc, DomainError):
            return
        raise


def _execute(session, investigation, job, *, detector, ocr, storage, taxonomy, acceptance_path, max_duration_ms, license_unreviewed) -> None:
    acceptance, acceptance_payload = load_acceptance(acceptance_path)
    evidence_rows = list(session.scalars(select(Evidence).where(Evidence.case_id == investigation.case_id)))
    decisions = {row.role: row for row in session.scalars(select(CoverageDecision).where(CoverageDecision.case_id == investigation.case_id))}
    _stage(session, job, "normalize", 15)
    for evidence in evidence_rows:
        if evidence.kind == EvidenceKind.VIDEO.value:
            _normalize_video(session, evidence, storage, decisions, acceptance_payload, max_duration_ms)
    _stage(session, job, "perceive", 40)
    for evidence in evidence_rows:
        if evidence.kind == EvidenceKind.VIDEO.value:
            _detect_video(session, evidence, storage, detector, taxonomy)
        elif evidence.role == EvidenceRole.INVOICE.value:
            _ocr_evidence(session, evidence, storage, ocr, taxonomy)
        elif evidence.kind == EvidenceKind.SHIPPING_FILE.value:
            _parse_shipping(session, evidence, storage)
        elif evidence.kind == EvidenceKind.STATEMENT.value:
            _record_statement(session, evidence)
    _stage(session, job, "aggregate", 60)
    observations = _aggregate(session, investigation, evidence_rows, acceptance)
    _timeline(session, investigation, observations, evidence_rows)
    _stage(session, job, "questions", 75)
    lines = _order_lines(investigation)
    claims = _claim_refs(investigation, taxonomy)
    accepted = [
        AcceptedObservation(row.observation_type, row.canonical_class, row.category)
        for row in observations
    ]
    questions = generate_investigation_questions(
        order_lines=lines,
        claims=claims,
        observations=accepted,
        claimed_dispute_type=investigation.case.claimed_dispute_type,
    )
    investigation.questions = [question.to_dict() for question in questions]
    session.commit()
    _stage(session, job, "evaluate", 85)
    coverage_rows = list(session.scalars(select(EvidenceCoverage).where(EvidenceCoverage.investigation_id == investigation.id)))
    coverage_by_role = {
        row.role: RoleCoverage(
            role=row.role,
            final_coverage=row.final_coverage,
            evidence_id=None if row.evidence_id is None else str(row.evidence_id),
            frames_examined=row.frames_examined,
            sampling_rate=row.sampling_rate,
            media_present=row.evidence_id is not None,
        )
        for row in coverage_rows
    }
    objects = [
        ObjectView(
            canonical_class=row.canonical_class or "",
            category=row.category or "",
            evidence_role=_role_for(evidence_rows, row.evidence_id),
            observed_quantity_estimate=row.observed_quantity_estimate,
            quantity_strength=row.quantity_strength,
            observation_strength=row.observation_strength,
            evidence_id=str(row.evidence_id),
            observation_id=str(row.id),
            frame_id=(row.supporting_frame_ids or [None])[0],
            timestamp_ms=row.start_timestamp_ms,
            detector_confidence=(row.detector_support or [{}])[0].get("detector_confidence"),
        )
        for row in observations
        if row.observation_type == ObservationType.OBJECT.value and row.canonical_class
    ]
    result = evaluate_investigation(
        questions=questions,
        order_lines=lines,
        objects=objects,
        coverage_by_role=coverage_by_role,
        sufficient_coverage=set(acceptance_payload["sufficient_coverage"]),
        min_quantity_strength=acceptance_payload["min_quantity_strength"],
        quantity_tolerance=acceptance_payload["quantity_tolerance"],
    )
    investigation.questions = [question.to_dict() for question in result.questions]
    investigation.expected_snapshot = [
        {"sku": line.sku, "canonical_class": line.canonical_class, "category": line.category, "quantity": line.quantity}
        for line in lines
    ]
    investigation.observed_snapshot = [
        {
            "canonical_class": row.canonical_class,
            "category": row.category,
            "observed_quantity_estimate": row.observed_quantity_estimate,
            "quantity_strength": row.quantity_strength,
            "observation_strength": row.observation_strength,
        }
        for row in observations
        if row.observation_type == ObservationType.OBJECT.value
    ]
    finding_ids: list[Finding] = []
    for draft in result.findings:
        if draft.status == "not_applicable":
            continue
        finding = Finding(
            investigation_id=investigation.id,
            question_key=draft.question_key,
            subject_key=draft.subject_key,
            aspect=draft.aspect,
            status=draft.status,
            summary=draft.summary,
            basis=draft.basis,
            final_coverage=draft.final_coverage,
            observation_strength=draft.observation_strength,
            expected_quantity=draft.expected_quantity,
            observed_quantity_estimate=draft.observed_quantity_estimate,
            quantity_strength=draft.quantity_strength,
        )
        session.add(finding)
        session.flush()
        session.add(
            EvidenceReference(
                finding_id=finding.id,
                evidence_id=None if not draft.evidence_id else uuid.UUID(draft.evidence_id),
                evidence_observation_id=None if not draft.observation_id else uuid.UUID(draft.observation_id),
                frame_id=None if not draft.frame_id else uuid.UUID(str(draft.frame_id)),
                timestamp_ms=draft.timestamp_ms,
                canonical_class=draft.subject_key,
                detector_confidence=draft.detector_confidence,
                search_scope=draft.search_scope,
                role=draft.role,
            )
        )
        finding_ids.append(finding)
    investigation.assessment = result.assessment
    investigation.assessment_rationale = result.assessment_rationale
    _stage(session, job, "report", 95)
    body, markdown = build_report(
        case_title=investigation.case.title,
        dispute_type=investigation.case.claimed_dispute_type,
        evidence_rows=[
            {
                "role": row.role,
                "party": row.party,
                "original_filename": row.original_filename,
                "text_body": row.text_body,
            }
            for row in evidence_rows
        ],
        coverage_rows=[
            {
                "role": row.role,
                "suggested_coverage": row.suggested_coverage,
                "final_coverage": row.final_coverage,
                "final_basis": row.final_basis,
                "suggestion_basis": row.suggestion_basis,
            }
            for row in coverage_rows
        ],
        expected_items=investigation.expected_snapshot,
        observations=investigation.observed_snapshot
        and [
            {"observation_type": "object", **row}
            for row in investigation.observed_snapshot
        ],
        timeline=[
            {"phase": row.phase, "summary": row.summary}
            for row in session.scalars(select(TimelineEntry).where(TimelineEntry.investigation_id == investigation.id))
        ],
        result=result,
        license_unreviewed=license_unreviewed,
    )
    markdown = Narrator().render(markdown)
    session.add(
        InvestigationReport(
            investigation_id=investigation.id,
            body=body,
            body_markdown=markdown,
            narrator="template",
        )
    )
    investigation.status = "completed"
    investigation.finished_at = datetime.now(timezone.utc)
    investigation.case.status = "completed"
    if job is not None:
        job.stage = "report"
        job.status = "succeeded"
        job.progress = 100
        job.finished_at = investigation.finished_at
        job.error = None
    session.commit()


def _stage(session, job, stage: str, progress: int) -> None:
    if job is not None:
        job.stage = stage
        job.progress = progress
    session.commit()


def _normalize_video(session, evidence, storage, decisions, acceptance_payload, max_duration_ms: int) -> None:
    existing = session.scalars(select(Frame).where(Frame.evidence_id == evidence.id)).first()
    info = probe(Path(storage.path_for(evidence.storage_key)))
    length = duration_ms(info)
    if length is not None and length > max_duration_ms:
        raise DomainError("video_too_long", f"Video duration {length} ms exceeds the configured limit")
    evidence.media_metadata = {"duration_ms": length, "probe": {"format": info.get("format", {})}}
    if existing is None:
        dest = Path(storage.root) / f"cases/{evidence.case_id}/evidence/{evidence.id}/frames"
        extracted = extract_frames(Path(storage.path_for(evidence.storage_key)), dest)
        for index, timestamp, path in extracted:
            relative = path.relative_to(storage.root).as_posix()
            session.add(
                Frame(
                    evidence_id=evidence.id,
                    frame_index=index,
                    timestamp_ms=timestamp,
                    storage_key=relative,
                    is_keyframe=index == 0,
                )
            )
    frames = list(session.scalars(select(Frame).where(Frame.evidence_id == evidence.id)))
    sampling = 1.0
    suggested, basis, signals = suggest_coverage(
        media_present=True,
        duration_ms=length,
        frames_examined=len(frames),
        sampling_fps=sampling,
        short_duration_ms=acceptance_payload["short_duration_ms"],
        min_sampling_fps=acceptance_payload["min_sampling_fps"],
    )
    decision = decisions.get(evidence.role)
    if decision is not None:
        decision.suggested_coverage = suggested
        decision.suggestion_basis = basis
        decision.suggestion_signals = signals
    snapshot = session.scalar(
        select(EvidenceCoverage).where(
            EvidenceCoverage.investigation_id == _current_investigation_id(session, evidence.case_id),
            EvidenceCoverage.role == evidence.role,
        )
    )
    if snapshot is not None:
        snapshot.suggested_coverage = suggested
        snapshot.suggestion_basis = basis
        snapshot.suggestion_signals = signals
        snapshot.frames_examined = len(frames)
        snapshot.sampling_rate = "1 fps"
        snapshot.duration_ms = length
        snapshot.evidence_id = evidence.id
    session.commit()


def _current_investigation_id(session, case_id):
    investigation = session.scalar(
        select(Investigation).where(Investigation.case_id == case_id, Investigation.status == "running").order_by(Investigation.started_at.desc())
    )
    return None if investigation is None else investigation.id


def _detect_video(session, evidence, storage, detector: Detector, taxonomy: Taxonomy) -> None:
    frames = list(session.scalars(select(Frame).where(Frame.evidence_id == evidence.id).order_by(Frame.frame_index)))
    for frame in frames:
        for raw in detector.detect(storage.path_for(frame.storage_key)):
            spec = taxonomy.get(raw["raw_label"])
            model_row = ModelObservation(
                evidence_id=evidence.id,
                frame_id=frame.id,
                model_name=detector.name,
                model_version=detector.version,
                raw_label=raw["raw_label"],
                raw_payload=raw,
                detector_confidence=raw.get("detector_confidence"),
            )
            session.add(model_row)
            session.flush()
            session.add(
                EvidenceEvent(
                    model_observation_id=model_row.id,
                    case_id=evidence.case_id,
                    evidence_id=evidence.id,
                    frame_id=frame.id,
                    event_type="object_detected",
                    canonical_class=None if spec is None else spec.canonical_class,
                    category=Category.UNKNOWN.value if spec is None else spec.category.value,
                    timestamp_ms=frame.timestamp_ms,
                    bbox=raw.get("bbox"),
                    detector_confidence=raw.get("detector_confidence"),
                )
            )
    session.commit()


def _ocr_evidence(session, evidence, storage, ocr: OcrEngine, taxonomy: Taxonomy) -> None:
    if evidence.mime_type == "application/pdf":
        raise DomainError("ocr_unavailable", "PDF invoices need a rendered page before OCR. Upload a JPEG or PNG invoice in V1.")
    for raw in ocr.recognize(storage.path_for(evidence.storage_key)):
        text = raw.get("text") or ""
        matched = next((spec for spec in taxonomy.classes.values() if spec.canonical_class in text.lower() or spec.display_name.lower() in text.lower()), None)
        model_row = ModelObservation(
            evidence_id=evidence.id,
            model_name=ocr.name,
            model_version=ocr.version,
            raw_label=text[:200],
            raw_payload=raw,
            detector_confidence=raw.get("score"),
            page_number=1,
        )
        session.add(model_row)
        session.flush()
        session.add(
            EvidenceEvent(
                model_observation_id=model_row.id,
                case_id=evidence.case_id,
                evidence_id=evidence.id,
                event_type="text_recognized",
                canonical_class=None if matched is None else matched.canonical_class,
                category=None if matched is None else matched.category.value,
                text=text,
                page_number=1,
                region=raw.get("region"),
                detector_confidence=raw.get("score"),
            )
        )
    session.commit()


def _parse_shipping(session, evidence, storage) -> None:
    payload = json.loads(Path(storage.path_for(evidence.storage_key)).read_text(encoding="utf-8"))
    for scan in payload.get("scans") or []:
        session.add(
            EvidenceEvent(
                case_id=evidence.case_id,
                evidence_id=evidence.id,
                event_type="shipping_scan_parsed",
                text=scan.get("event_type"),
                timestamp_ms=None,
            )
        )
        evidence.media_metadata = payload
    session.commit()


def _record_statement(session, evidence) -> None:
    session.add(
        EvidenceEvent(
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            event_type="statement_recorded",
            text=evidence.text_body,
        )
    )
    session.commit()


def _aggregate(session, investigation, evidence_rows, acceptance: AcceptanceConfig) -> list[EvidenceObservation]:
    created: list[EvidenceObservation] = []
    by_evidence = {row.id: row for row in evidence_rows}
    events = list(session.scalars(select(EvidenceEvent).where(EvidenceEvent.case_id == investigation.case_id)))
    grouped: dict[tuple, list[EvidenceEvent]] = {}
    for event in events:
        if event.event_type != "object_detected" or not event.canonical_class:
            continue
        grouped.setdefault((event.evidence_id, event.canonical_class), []).append(event)
    for (evidence_id, canonical), rows in grouped.items():
        sorted_rows = sorted(rows, key=lambda item: item.timestamp_ms or 0)
        frame_ids: dict[str, int] = {}
        boxes = []
        for source_index, row in enumerate(sorted_rows):
            frame_key = str(row.frame_id)
            if frame_key not in frame_ids:
                frame_ids[frame_key] = len(frame_ids)
            boxes.append(
                DetectionBox(
                    frame_ids[frame_key],
                    row.timestamp_ms or 0,
                    row.detector_confidence or 0,
                    row.bbox,
                    canonical,
                    source_index,
                )
            )
        accepted = accept_group(canonical, boxes, acceptance)
        if accepted is None:
            continue
        supporting_rows = [sorted_rows[box.source_index] for box in accepted.supporting]
        observation = EvidenceObservation(
            investigation_id=investigation.id,
            evidence_id=evidence_id,
            observation_type=ObservationType.OBJECT.value,
            canonical_class=canonical,
            category=sorted_rows[0].category,
            observed=True,
            start_timestamp_ms=accepted.start_timestamp_ms,
            end_timestamp_ms=accepted.end_timestamp_ms,
            supporting_frame_ids=[str(row.frame_id) for row in supporting_rows if row.frame_id],
            supporting_event_ids=[str(row.id) for row in supporting_rows],
            observation_strength=accepted.observation_strength.value,
            observed_quantity_estimate=accepted.observed_quantity_estimate,
            quantity_strength=accepted.quantity_strength.value,
            detector_support=[
                {
                    "frame_id": str(row.frame_id) if row.frame_id else None,
                    "timestamp_ms": row.timestamp_ms,
                    "detector_confidence": row.detector_confidence,
                    "bbox": row.bbox,
                }
                for row in supporting_rows
            ],
        )
        session.add(observation)
        created.append(observation)
    for event in events:
        evidence = by_evidence.get(event.evidence_id)
        if evidence is None:
            continue
        if event.event_type == "text_recognized":
            session.add(
                EvidenceObservation(
                    investigation_id=investigation.id,
                    evidence_id=event.evidence_id,
                    observation_type=ObservationType.DOCUMENT_TEXT.value,
                    canonical_class=event.canonical_class,
                    category=event.category,
                    normalized_text=event.text,
                    page_number=event.page_number,
                    region=event.region,
                )
            )
        elif event.event_type == "statement_recorded":
            session.add(
                EvidenceObservation(
                    investigation_id=investigation.id,
                    evidence_id=event.evidence_id,
                    observation_type=ObservationType.STATEMENT.value,
                    party=evidence.party,
                    statement_text=event.text,
                )
            )
        elif event.event_type == "shipping_scan_parsed":
            session.add(
                EvidenceObservation(
                    investigation_id=investigation.id,
                    evidence_id=event.evidence_id,
                    observation_type=ObservationType.SHIPPING_EVENT.value,
                    shipping_event_type=event.text,
                    source_payload=evidence.media_metadata,
                )
            )
    session.commit()
    return list(session.scalars(select(EvidenceObservation).where(EvidenceObservation.investigation_id == investigation.id)))


def _timeline(session, investigation, observations, evidence_rows) -> None:
    roles = {row.id: row.role for row in evidence_rows}
    entries = []
    if investigation.order_snapshot:
        entries.append(("ordered", "Order snapshot recorded"))
    for observation in observations:
        role = roles.get(observation.evidence_id)
        phase = ROLE_PHASE.get(role or "", "stated")
        if observation.observation_type == ObservationType.OBJECT.value:
            entries.append((phase, f"{observation.canonical_class} estimated quantity {observation.observed_quantity_estimate}"))
        elif observation.observation_type == ObservationType.SHIPPING_EVENT.value:
            entries.append(("shipped", observation.shipping_event_type or "shipping event"))
        elif observation.observation_type == ObservationType.STATEMENT.value:
            entries.append(("stated", "Statement recorded"))
    entries.sort(key=lambda item: PHASE_ORDER.index(item[0]) if item[0] in PHASE_ORDER else 99)
    for position, (phase, summary) in enumerate(entries):
        session.add(TimelineEntry(investigation_id=investigation.id, position=position, phase=phase, summary=summary, observation_ids=[]))
    session.commit()


def _order_lines(investigation: Investigation) -> list[OrderLine]:
    return [
        OrderLine(
            id=item["id"],
            sku=item["sku"],
            canonical_class=item["canonical_class"],
            category=item["category"],
            quantity=item["quantity"],
            order_relevant=item["order_relevant"],
        )
        for item in investigation.order_snapshot.get("items", [])
    ]


def _claim_refs(investigation: Investigation, taxonomy: Taxonomy) -> list[ClaimRef]:
    refs = []
    for claim in investigation.claims_snapshot or []:
        spec = taxonomy.get(claim.get("canonical_class") or "")
        refs.append(
            ClaimRef(
                claim_type=claim["claim_type"],
                canonical_class=claim.get("canonical_class"),
                order_item_id=claim.get("order_item_id"),
                category=None if spec is None else spec.category.value,
                order_relevant=False if spec is None else spec.order_relevant,
            )
        )
    return refs


def _role_for(evidence_rows, evidence_id) -> str:
    for row in evidence_rows:
        if row.id == evidence_id:
            return row.role
    return ""


def snapshot_order(order: Order | None, items: list[OrderItem], taxonomy: Taxonomy) -> dict:
    if order is None:
        return {"items": []}
    payload = []
    for item in items:
        spec = taxonomy.get(item.canonical_class)
        payload.append(
            {
                "id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "canonical_class": item.canonical_class,
                "category": item.category,
                "quantity": item.quantity,
                "order_relevant": False if spec is None else spec.order_relevant,
            }
        )
    return {"external_order_id": order.external_order_id, "items": payload}


def snapshot_claims(claims: list[Claim]) -> list[dict]:
    return [
        {
            "claim_type": claim.claim_type,
            "party": claim.party,
            "canonical_class": claim.canonical_class,
            "order_item_id": None if claim.order_item_id is None else str(claim.order_item_id),
            "claimed_quantity": claim.claimed_quantity,
        }
        for claim in claims
    ]
