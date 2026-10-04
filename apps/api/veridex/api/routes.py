import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from veridex.db.models import (
    Case,
    Claim,
    CoverageDecision,
    Evidence,
    EvidenceCoverage,
    EvidenceObservation,
    EvidenceReference,
    Finding,
    Frame,
    Investigation,
    InvestigationReport,
    Order,
    OrderItem,
    ProcessingJob,
    TimelineEntry,
    utcnow,
)
from veridex.domain.claims import ClaimInput, OrderItemRef, validate_claim
from veridex.domain.enums import CoverageValue, DisputeType, EvidenceRole, Party, infer_kind
from veridex.domain.errors import ClaimValidationError, ContractError, DomainError
from veridex.config import config_dir
from veridex.pipeline.run import snapshot_claims, snapshot_order

router = APIRouter(prefix="/api/v1")


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    claimed_dispute_type: str | None = None


class OrderItemIn(BaseModel):
    sku: str
    name: str
    canonical_class: str
    quantity: int = Field(ge=1)


class OrderIn(BaseModel):
    external_order_id: str
    seller_name: str
    buyer_name: str
    ordered_at: datetime
    currency: str
    items: list[OrderItemIn]


class ClaimIn(BaseModel):
    claim_type: str
    party: str
    canonical_class: str | None = None
    order_item_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    claimed_quantity: int | None = None
    statement: str | None = None


class CoverageIn(BaseModel):
    final_coverage: str
    final_basis: str = ""


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _taxonomy(request: Request):
    return request.app.state.taxonomy


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/cases", status_code=201)
def create_case(payload: CaseCreate, request: Request) -> dict:
    if payload.claimed_dispute_type is not None:
        try:
            DisputeType(payload.claimed_dispute_type)
        except ValueError as exc:
            raise _error(422, "invalid_dispute_type", "claimed_dispute_type is not supported") from exc
    session = request.state.session
    case = Case(title=payload.title, claimed_dispute_type=payload.claimed_dispute_type, status="draft")
    session.add(case)
    session.commit()
    return request.app.state.serializers.case_dict(case, [])


@router.get("/cases")
def list_cases(request: Request) -> dict:
    session = request.state.session
    cases = list(session.scalars(select(Case).order_by(Case.created_at.desc())))
    return {"items": [request.app.state.serializers.case_dict(case) for case in cases]}


@router.get("/cases/{case_id}")
def get_case(case_id: uuid.UUID, request: Request) -> dict:
    case = _case(request, case_id)
    order = case.order
    body = request.app.state.serializers.case_dict(case)
    body["order"] = None if order is None else {"external_order_id": order.external_order_id, "item_count": len(order.items)}
    body["investigations"] = [
        {"id": str(row.id), "status": row.status, "assessment": row.assessment}
        for row in sorted(case.investigations, key=lambda row: row.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    ]
    return body


@router.put("/cases/{case_id}/order")
def put_order(case_id: uuid.UUID, payload: OrderIn, request: Request) -> dict:
    session = request.state.session
    case = _case(request, case_id)
    taxonomy = _taxonomy(request)
    for item in payload.items:
        if taxonomy.get(item.canonical_class) is None:
            raise _error(422, "unknown_class", f"{item.canonical_class} is not in the taxonomy")
    order = case.order
    if order is None:
        order = Order(case_id=case.id, external_order_id=payload.external_order_id, seller_name=payload.seller_name, buyer_name=payload.buyer_name, ordered_at=payload.ordered_at, currency=payload.currency)
        session.add(order)
        session.flush()
    else:
        order.external_order_id = payload.external_order_id
        order.seller_name = payload.seller_name
        order.buyer_name = payload.buyer_name
        order.ordered_at = payload.ordered_at
        order.currency = payload.currency
        for existing in list(order.items):
            session.delete(existing)
    for item in payload.items:
        spec = taxonomy.get(item.canonical_class)
        session.add(
            OrderItem(
                order_id=order.id,
                sku=item.sku,
                name=item.name,
                canonical_class=item.canonical_class,
                category=spec.category.value,
                quantity=item.quantity,
                attributes={},
            )
        )
    if case.status == "draft":
        case.status = "ready"
    session.commit()
    return {"id": str(order.id), "external_order_id": order.external_order_id}


@router.post("/cases/{case_id}/claims", status_code=201)
def create_claim(case_id: uuid.UUID, payload: ClaimIn, request: Request) -> dict:
    session = request.state.session
    case = _case(request, case_id)
    items = [] if case.order is None else [
        OrderItemRef(str(item.id), item.canonical_class, _taxonomy(request).get(item.canonical_class).category, _taxonomy(request).get(item.canonical_class).order_relevant)
        for item in case.order.items
    ]
    evidence_ids = {str(row.id) for row in case.evidence}
    try:
        validate_claim(
            ClaimInput(
                claim_type=payload.claim_type,
                party=payload.party,
                canonical_class=payload.canonical_class,
                order_item_id=None if payload.order_item_id is None else str(payload.order_item_id),
                evidence_id=None if payload.evidence_id is None else str(payload.evidence_id),
                claimed_quantity=payload.claimed_quantity,
                statement=payload.statement,
            ),
            taxonomy=_taxonomy(request),
            order_items=items,
            case_evidence_ids=evidence_ids,
        )
    except ClaimValidationError as exc:
        raise _error(422, exc.code, exc.message) from exc
    claim = Claim(
        case_id=case.id,
        party=payload.party,
        claim_type=payload.claim_type,
        order_item_id=payload.order_item_id,
        canonical_class=payload.canonical_class,
        claimed_quantity=payload.claimed_quantity,
        evidence_id=payload.evidence_id,
        statement=payload.statement,
    )
    session.add(claim)
    session.commit()
    return {"id": str(claim.id)}


@router.get("/cases/{case_id}/claims")
def list_claims(case_id: uuid.UUID, request: Request) -> dict:
    case = _case(request, case_id)
    return {
        "items": [
            {
                "id": str(row.id),
                "party": row.party,
                "claim_type": row.claim_type,
                "canonical_class": row.canonical_class,
                "order_item_id": None if row.order_item_id is None else str(row.order_item_id),
                "claimed_quantity": row.claimed_quantity,
            }
            for row in case.claims
        ]
    }


@router.post("/cases/{case_id}/evidence", status_code=201)
async def upload_evidence(
    case_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    role: str = Form(...),
    party: str = Form(...),
    text_body: str | None = Form(None),
) -> dict:
    session = request.state.session
    case = _case(request, case_id)
    try:
        evidence_role = EvidenceRole(role)
        Party(party)
    except ValueError as exc:
        raise _error(422, "invalid_evidence", "role or party is not a supported value") from exc
    mime = file.content_type or ""
    try:
        kind = infer_kind(evidence_role, mime)
    except ValueError as exc:
        raise _error(422, "invalid_mime", "MIME type is not allowed for this role") from exc
    data = await file.read()
    settings = request.app.state.settings
    if len(data) > settings.max_upload_bytes:
        raise _error(413, "upload_too_large", "The file exceeds the configured upload limit")
    evidence_id = uuid.uuid4()
    key = f"cases/{case.id}/evidence/{evidence_id}/original"
    request.app.state.storage.put(key, data)
    row = Evidence(
        id=evidence_id,
        case_id=case.id,
        kind=kind.value,
        role=evidence_role.value,
        party=party,
        original_filename=file.filename or "upload",
        mime_type=mime,
        byte_size=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        storage_key=key,
        media_metadata={},
        text_body=text_body,
        status="uploaded",
    )
    session.add(row)
    existing = session.scalar(select(CoverageDecision).where(CoverageDecision.case_id == case.id, CoverageDecision.role == evidence_role.value))
    if existing is None:
        session.add(
            CoverageDecision(
                case_id=case.id,
                role=evidence_role.value,
                suggested_coverage=CoverageValue.UNASSESSED.value,
                suggestion_basis="Coverage has not been determined.",
                final_coverage=CoverageValue.UNASSESSED.value,
                final_basis="",
            )
        )
    if case.status == "draft":
        case.status = "ready"
    session.commit()
    return request.app.state.serializers.evidence_dict(row)


@router.get("/cases/{case_id}/evidence")
def list_evidence(case_id: uuid.UUID, request: Request) -> dict:
    case = _case(request, case_id)
    return {"items": [request.app.state.serializers.evidence_dict(row) for row in case.evidence]}


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: uuid.UUID, request: Request) -> dict:
    row = request.state.session.get(Evidence, evidence_id)
    if row is None:
        raise _error(404, "not_found", "Evidence was not found")
    return request.app.state.serializers.evidence_dict(row)


@router.get("/evidence/{evidence_id}/content")
def evidence_content(evidence_id: uuid.UUID, request: Request) -> Response:
    row = request.state.session.get(Evidence, evidence_id)
    if row is None:
        raise _error(404, "not_found", "Evidence was not found")
    return Response(content=request.app.state.storage.get(row.storage_key), media_type=row.mime_type)


@router.get("/frames/{frame_id}/content")
def frame_content(frame_id: uuid.UUID, request: Request) -> Response:
    row = request.state.session.get(Frame, frame_id)
    if row is None:
        raise _error(404, "not_found", "Frame was not found")
    return Response(content=request.app.state.storage.get(row.storage_key), media_type="image/jpeg")


@router.get("/cases/{case_id}/coverage")
def get_coverage(case_id: uuid.UUID, request: Request) -> dict:
    _case(request, case_id)
    rows = list(request.state.session.scalars(select(CoverageDecision).where(CoverageDecision.case_id == case_id)))
    return {"items": [_coverage_dict(row) for row in rows]}


@router.put("/cases/{case_id}/coverage/{role}")
def put_coverage(case_id: uuid.UUID, role: str, payload: CoverageIn, request: Request) -> dict:
    session = request.state.session
    _case(request, case_id)
    try:
        EvidenceRole(role)
        CoverageValue(payload.final_coverage)
    except ValueError as exc:
        raise _error(422, "invalid_coverage", "role or final_coverage is not supported") from exc
    row = session.scalar(select(CoverageDecision).where(CoverageDecision.case_id == case_id, CoverageDecision.role == role))
    if row is None:
        row = CoverageDecision(case_id=case_id, role=role, suggested_coverage=CoverageValue.UNASSESSED.value, suggestion_basis="")
        session.add(row)
    row.final_coverage = payload.final_coverage
    row.final_basis = payload.final_basis
    row.decision_source = "operator"
    row.confirmed_at = utcnow()
    session.commit()
    return _coverage_dict(row)


@router.post("/cases/{case_id}/investigations", status_code=202)
def start_investigation(case_id: uuid.UUID, request: Request) -> dict:
    session = request.state.session
    case = _case(request, case_id)
    running = [row for row in case.investigations if row.status in {"queued", "running"}]
    if running:
        raise _error(409, "investigation_running", "An investigation is already running for this case")
    taxonomy = _taxonomy(request)
    acceptance = json.loads((config_dir() / "acceptance.json").read_text(encoding="utf-8"))
    models = json.loads((config_dir() / "models.json").read_text(encoding="utf-8"))
    order = case.order
    items = [] if order is None else list(order.items)
    investigation = Investigation(
        case_id=case.id,
        status="queued",
        pipeline_version=request.app.state.settings.pipeline_version,
        taxonomy_version=taxonomy.version,
        acceptance_config_version=str(acceptance["version"]),
        coverage_config_version=str(acceptance["version"]),
        model_manifest=models,
        order_snapshot=snapshot_order(order, items, taxonomy),
        claims_snapshot=snapshot_claims(list(case.claims)),
        questions=None,
        expected_snapshot=[],
        observed_snapshot=[],
    )
    session.add(investigation)
    session.flush()
    decisions = list(session.scalars(select(CoverageDecision).where(CoverageDecision.case_id == case.id)))
    for decision in decisions:
        evidence = next((row for row in case.evidence if row.role == decision.role), None)
        session.add(
            EvidenceCoverage(
                investigation_id=investigation.id,
                evidence_id=None if evidence is None else evidence.id,
                role=decision.role,
                suggested_coverage=decision.suggested_coverage,
                suggestion_signals=decision.suggestion_signals,
                suggestion_basis=decision.suggestion_basis,
                final_coverage=decision.final_coverage,
                final_basis=decision.final_basis,
                decision_source=decision.decision_source,
            )
        )
    session.add(ProcessingJob(case_id=case.id, investigation_id=investigation.id, stage="snapshot", status="queued", progress=0))
    case.status = "processing"
    session.commit()
    return {"id": str(investigation.id), "questions": None}


@router.get("/cases/{case_id}/investigations")
def list_investigations(case_id: uuid.UUID, request: Request) -> dict:
    case = _case(request, case_id)
    rows = sorted(case.investigations, key=lambda row: row.started_at or row.finished_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return {"items": [_investigation_summary(row) for row in rows]}


@router.get("/cases/{case_id}/processing")
def processing(case_id: uuid.UUID, request: Request) -> dict:
    _case(request, case_id)
    rows = list(request.state.session.scalars(select(ProcessingJob).where(ProcessingJob.case_id == case_id)))
    return {
        "items": [
            {
                "id": str(row.id),
                "investigation_id": None if row.investigation_id is None else str(row.investigation_id),
                "stage": row.stage,
                "status": row.status,
                "progress": row.progress,
                "error": row.error,
            }
            for row in rows
        ]
    }


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: uuid.UUID, request: Request) -> dict:
    row = _investigation(request, investigation_id)
    return _investigation_summary(row) | {
        "model_manifest": row.model_manifest,
        "questions": row.questions,
        "expected_snapshot": row.expected_snapshot,
        "observed_snapshot": row.observed_snapshot,
        "assessment_rationale": row.assessment_rationale,
        "acceptance_config_version": row.acceptance_config_version,
        "coverage_config_version": row.coverage_config_version,
    }


@router.get("/investigations/{investigation_id}/observations")
def list_observations(investigation_id: uuid.UUID, request: Request) -> dict:
    _investigation(request, investigation_id)
    rows = list(request.state.session.scalars(select(EvidenceObservation).where(EvidenceObservation.investigation_id == investigation_id)))
    return {"items": [_observation_dict(row) for row in rows]}


@router.get("/investigations/{investigation_id}/coverage")
def investigation_coverage(investigation_id: uuid.UUID, request: Request) -> dict:
    _investigation(request, investigation_id)
    rows = list(request.state.session.scalars(select(EvidenceCoverage).where(EvidenceCoverage.investigation_id == investigation_id)))
    return {
        "items": [
            {
                "role": row.role,
                "suggested_coverage": row.suggested_coverage,
                "suggestion_basis": row.suggestion_basis,
                "final_coverage": row.final_coverage,
                "final_basis": row.final_basis,
                "frames_examined": row.frames_examined,
                "sampling_rate": row.sampling_rate,
            }
            for row in rows
        ]
    }


@router.get("/investigations/{investigation_id}/timeline")
def timeline(investigation_id: uuid.UUID, request: Request) -> dict:
    _investigation(request, investigation_id)
    rows = list(request.state.session.scalars(select(TimelineEntry).where(TimelineEntry.investigation_id == investigation_id).order_by(TimelineEntry.position)))
    return {"items": [{"position": row.position, "phase": row.phase, "summary": row.summary} for row in rows]}


@router.get("/investigations/{investigation_id}/findings")
def findings(investigation_id: uuid.UUID, request: Request) -> dict:
    _investigation(request, investigation_id)
    session = request.state.session
    rows = list(session.scalars(select(Finding).where(Finding.investigation_id == investigation_id)))
    payload = []
    for row in rows:
        refs = list(session.scalars(select(EvidenceReference).where(EvidenceReference.finding_id == row.id)))
        payload.append(
            {
                "id": str(row.id),
                "question_key": row.question_key,
                "subject_key": row.subject_key,
                "aspect": row.aspect,
                "status": row.status,
                "summary": row.summary,
                "basis": row.basis,
                "final_coverage": row.final_coverage,
                "observation_strength": row.observation_strength,
                "expected_quantity": row.expected_quantity,
                "observed_quantity_estimate": row.observed_quantity_estimate,
                "quantity_strength": row.quantity_strength,
                "evidence_references": [
                    {
                        "evidence_id": None if ref.evidence_id is None else str(ref.evidence_id),
                        "role": ref.role,
                        "evidence_observation_id": None if ref.evidence_observation_id is None else str(ref.evidence_observation_id),
                        "frame_id": None if ref.frame_id is None else str(ref.frame_id),
                        "timestamp_ms": ref.timestamp_ms,
                        "canonical_class": ref.canonical_class,
                        "detector_confidence": ref.detector_confidence,
                        "search_scope": ref.search_scope,
                        "bbox": _cited_bbox(session, ref.evidence_observation_id),
                    }
                    for ref in refs
                ],
            }
        )
    return {"items": payload}


@router.get("/investigations/{investigation_id}/report")
def report(investigation_id: uuid.UUID, request: Request) -> dict:
    row = _investigation(request, investigation_id)
    stored = request.state.session.scalar(select(InvestigationReport).where(InvestigationReport.investigation_id == row.id))
    if stored is None:
        raise _error(404, "report_not_ready", "The report is not available until the investigation completes")
    return {"body": stored.body, "markdown": stored.body_markdown, "narrator": stored.narrator, "assessment": row.assessment}


def _case(request: Request, case_id: uuid.UUID) -> Case:
    case = request.state.session.get(Case, case_id)
    if case is None:
        raise _error(404, "not_found", "Case was not found")
    return case


def _investigation(request: Request, investigation_id: uuid.UUID) -> Investigation:
    row = request.state.session.get(Investigation, investigation_id)
    if row is None:
        raise _error(404, "not_found", "Investigation was not found")
    return row


def _cited_bbox(session, observation_id) -> dict | None:
    if observation_id is None:
        return None
    observation = session.get(EvidenceObservation, observation_id)
    if observation is None or not observation.detector_support:
        return None
    return observation.detector_support[0].get("bbox")


def _coverage_dict(row: CoverageDecision) -> dict:
    return {
        "role": row.role,
        "suggested_coverage": row.suggested_coverage,
        "suggestion_signals": row.suggestion_signals,
        "suggestion_basis": row.suggestion_basis,
        "final_coverage": row.final_coverage,
        "final_basis": row.final_basis,
        "decision_source": row.decision_source,
    }


def _investigation_summary(row: Investigation) -> dict:
    return {
        "id": str(row.id),
        "case_id": str(row.case_id),
        "status": row.status,
        "pipeline_version": row.pipeline_version,
        "taxonomy_version": row.taxonomy_version,
        "assessment": row.assessment,
        "questions": row.questions,
    }


def _observation_dict(row: EvidenceObservation) -> dict:
    return {
        "id": str(row.id),
        "observation_type": row.observation_type,
        "canonical_class": row.canonical_class,
        "category": row.category,
        "observed_quantity_estimate": row.observed_quantity_estimate,
        "quantity_strength": row.quantity_strength,
        "observation_strength": row.observation_strength,
        "normalized_text": row.normalized_text,
        "party": row.party,
        "statement_text": row.statement_text,
        "shipping_event_type": row.shipping_event_type,
        "detector_support": row.detector_support,
    }
