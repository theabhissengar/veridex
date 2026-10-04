from dataclasses import dataclass, field

from veridex.domain.enums import (
    Applicability,
    CaseAssessment,
    Category,
    CoverageValue,
    EvidenceState,
    EvaluationStatus,
    QuestionAspect,
    Strength,
)
from veridex.domain.quantity import strength_meets
from veridex.domain.questions import InvestigationQuestion, OrderLine


@dataclass(frozen=True)
class ObjectView:
    canonical_class: str
    category: str
    evidence_role: str
    observed_quantity_estimate: int | None
    quantity_strength: str | None
    observation_strength: str | None = None
    evidence_id: str | None = None
    observation_id: str | None = None
    frame_id: str | None = None
    timestamp_ms: int | None = None
    detector_confidence: float | None = None


@dataclass(frozen=True)
class RoleCoverage:
    role: str
    final_coverage: str
    evidence_id: str | None = None
    frames_examined: int | None = None
    sampling_rate: str | None = None
    media_present: bool = False


@dataclass
class FindingDraft:
    question_key: str
    subject_key: str
    aspect: str
    status: str
    summary: str
    basis: str
    final_coverage: str
    role: str | None = None
    observation_strength: str | None = None
    expected_quantity: int | None = None
    observed_quantity_estimate: int | None = None
    quantity_strength: str | None = None
    evidence_id: str | None = None
    observation_id: str | None = None
    frame_id: str | None = None
    timestamp_ms: int | None = None
    detector_confidence: float | None = None
    search_scope: dict | None = None


@dataclass
class EvaluationResult:
    questions: list[InvestigationQuestion]
    findings: list[FindingDraft] = field(default_factory=list)
    assessment: str = CaseAssessment.INSUFFICIENT_EVIDENCE.value
    assessment_rationale: str = ""


def _sufficient(coverage: str, sufficient: set[str]) -> bool:
    return coverage in sufficient


def _scope(coverage: RoleCoverage) -> dict:
    return {
        "frames_examined": coverage.frames_examined,
        "sampling_rate": coverage.sampling_rate,
        "final_coverage": coverage.final_coverage,
        "evidence_id": coverage.evidence_id,
    }


def _role_blocks_not_observed(coverage: str, sufficient: set[str]) -> bool:
    if coverage in {CoverageValue.UNASSESSED.value, CoverageValue.LIMITED.value}:
        return True
    return not _sufficient(coverage, sufficient)


def evaluate_investigation(
    *,
    questions: list[InvestigationQuestion],
    order_lines: list[OrderLine],
    objects: list[ObjectView],
    coverage_by_role: dict[str, RoleCoverage],
    sufficient_coverage: set[str] | None = None,
    min_quantity_strength: str = Strength.MEDIUM.value,
    quantity_tolerance: int = 0,
) -> EvaluationResult:
    sufficient = sufficient_coverage or {CoverageValue.COMPLETE.value}
    expected = {line.canonical_class: line for line in order_lines}
    findings: list[FindingDraft] = []

    for question in questions:
        if question.applicability == Applicability.NOT_APPLICABLE.value:
            question.evaluation_status = EvaluationStatus.NOT_APPLICABLE.value
            continue
        role_outcomes: dict[str, str] = {}
        role_objects: dict[str, list[ObjectView]] = {}
        for role in question.required_roles:
            coverage = coverage_by_role.get(role) or RoleCoverage(role=role, final_coverage=CoverageValue.UNASSESSED.value)
            matched = [item for item in objects if item.evidence_role == role and item.canonical_class == question.canonical_class]
            role_objects[role] = [item for item in objects if item.evidence_role == role]
            if not coverage.media_present or _role_blocks_not_observed(coverage.final_coverage, sufficient):
                role_outcomes[role] = EvidenceState.UNKNOWN.value
                findings.append(
                    FindingDraft(
                        question_key=question.question_key,
                        subject_key=question.canonical_class,
                        aspect=question.aspect,
                        status=EvidenceState.UNKNOWN.value,
                        summary=f"{question.canonical_class} cannot currently be determined from {role}.",
                        basis="The source is missing or final coverage is unassessed, limited, or below the sufficient-coverage set.",
                        final_coverage=coverage.final_coverage,
                        role=role,
                        evidence_id=coverage.evidence_id,
                        search_scope=_scope(coverage),
                    )
                )
                continue
            outcome = _covered_role_outcome(question, matched, role_objects[role])
            role_outcomes[role] = outcome
            chosen = next((item for item in matched), None)
            if outcome == EvidenceState.NOT_OBSERVED.value:
                summary = f"{question.canonical_class} was not observed in the examined evidence."
            elif outcome == EvidenceState.PROVEN.value:
                summary = f"{question.canonical_class} was observed in {role}."
            else:
                summary = f"{role} shows a different product class than {question.canonical_class}."
            findings.append(
                FindingDraft(
                    question_key=question.question_key,
                    subject_key=question.canonical_class,
                    aspect=question.aspect,
                    status=outcome,
                    summary=summary,
                    basis="Final coverage is in the sufficient set and the accepted observations were compared with the question subject.",
                    final_coverage=coverage.final_coverage,
                    role=role,
                    observation_strength=None if chosen is None else chosen.observation_strength,
                    evidence_id=coverage.evidence_id if chosen is None else chosen.evidence_id,
                    observation_id=None if chosen is None else chosen.observation_id,
                    frame_id=None if chosen is None else chosen.frame_id,
                    timestamp_ms=None if chosen is None else chosen.timestamp_ms,
                    detector_confidence=None if chosen is None else chosen.detector_confidence,
                    observed_quantity_estimate=None if chosen is None else chosen.observed_quantity_estimate,
                    quantity_strength=None if chosen is None else chosen.quantity_strength,
                    expected_quantity=None if question.canonical_class not in expected else expected[question.canonical_class].quantity,
                    search_scope=_scope(coverage) if outcome == EvidenceState.NOT_OBSERVED.value else None,
                )
            )
        question.evaluation_status = _rollup(
            question,
            role_outcomes,
            role_objects,
            expected.get(question.canonical_class),
            min_quantity_strength,
            quantity_tolerance,
            coverage_by_role,
            sufficient,
        )
        if question.evaluation_status == EvaluationStatus.CONFLICTING.value:
            findings.append(
                FindingDraft(
                    question_key=question.question_key,
                    subject_key=question.canonical_class,
                    aspect="cross_source",
                    status=EvidenceState.CONFLICTING.value,
                    summary=_conflict_summary(question, role_outcomes, role_objects),
                    basis="The required evidence and the order expectation for this question cannot be reconciled.",
                    final_coverage=_dominant_coverage(question, coverage_by_role),
                    expected_quantity=None if question.canonical_class not in expected else expected[question.canonical_class].quantity,
                )
            )

    assessment, rationale = assess(questions)
    return EvaluationResult(questions=questions, findings=findings, assessment=assessment, assessment_rationale=rationale)


def _covered_role_outcome(question: InvestigationQuestion, matched: list[ObjectView], role_items: list[ObjectView]) -> str:
    if question.aspect == QuestionAspect.IDENTITY.value:
        products = [item for item in role_items if item.category == Category.PRODUCT.value]
        expected_seen = any(item.canonical_class == question.canonical_class for item in role_items)
        other = [item for item in products if item.canonical_class != question.canonical_class]
        if other and not expected_seen:
            return EvidenceState.CONFLICTING.value
        if expected_seen and not other:
            return EvidenceState.PROVEN.value
        if expected_seen and other:
            return EvidenceState.CONFLICTING.value
        return EvidenceState.NOT_OBSERVED.value
    if matched:
        return EvidenceState.PROVEN.value
    return EvidenceState.NOT_OBSERVED.value


def _rollup(
    question: InvestigationQuestion,
    role_outcomes: dict[str, str],
    role_objects: dict[str, list[ObjectView]],
    expected: OrderLine | None,
    min_quantity_strength: str,
    quantity_tolerance: int,
    coverage_by_role: dict[str, RoleCoverage],
    sufficient: set[str],
) -> str:
    examined = {
        role: outcome
        for role, outcome in role_outcomes.items()
        if outcome != EvidenceState.UNKNOWN.value
    }
    if any(outcome == EvidenceState.UNKNOWN.value for outcome in role_outcomes.values()):
        if _examined_conflict(question, examined, role_objects, expected):
            return EvaluationStatus.CONFLICTING.value
        return EvaluationStatus.UNKNOWN.value
    if question.aspect == QuestionAspect.QUANTITY.value:
        return _quantity_status(question, role_objects, expected, min_quantity_strength, quantity_tolerance, coverage_by_role, sufficient)
    if question.aspect == QuestionAspect.PRESENCE.value:
        values = set(role_outcomes.values())
        if values == {EvidenceState.PROVEN.value}:
            return EvaluationStatus.PROVEN.value
        return EvaluationStatus.CONFLICTING.value
    if all(outcome == EvidenceState.PROVEN.value for outcome in role_outcomes.values()):
        return EvaluationStatus.PROVEN.value
    return EvaluationStatus.CONFLICTING.value


def _examined_conflict(
    question: InvestigationQuestion,
    examined: dict[str, str],
    role_objects: dict[str, list[ObjectView]],
    expected: OrderLine | None,
) -> bool:
    if len(examined) < 2:
        return False
    if question.aspect == QuestionAspect.PRESENCE.value:
        return len(set(examined.values())) > 1
    if question.aspect == QuestionAspect.IDENTITY.value:
        classes = []
        for role in examined:
            products = sorted({item.canonical_class for item in role_objects.get(role, []) if item.category == Category.PRODUCT.value})
            classes.append(tuple(products))
        return len(set(classes)) > 1
    return False


def _quantity_status(
    question: InvestigationQuestion,
    role_objects: dict[str, list[ObjectView]],
    expected: OrderLine | None,
    min_quantity_strength: str,
    quantity_tolerance: int,
    coverage_by_role: dict[str, RoleCoverage],
    sufficient: set[str],
) -> str:
    estimates: list[tuple[int, str]] = []
    for role in question.required_roles:
        coverage = coverage_by_role.get(role)
        if coverage is None or not _sufficient(coverage.final_coverage, sufficient):
            return EvaluationStatus.UNKNOWN.value
        matched = [item for item in role_objects.get(role, []) if item.canonical_class == question.canonical_class]
        if not matched or matched[0].observed_quantity_estimate is None or matched[0].quantity_strength is None:
            return EvaluationStatus.CONFLICTING.value if expected is not None else EvaluationStatus.UNKNOWN.value
        if not strength_meets(matched[0].quantity_strength, min_quantity_strength):
            return EvaluationStatus.UNKNOWN.value
        estimates.append((matched[0].observed_quantity_estimate, matched[0].quantity_strength))
    if not estimates or expected is None:
        return EvaluationStatus.UNKNOWN.value
    numbers = {item[0] for item in estimates}
    if len(numbers) > 1:
        return EvaluationStatus.CONFLICTING.value
    estimate = next(iter(numbers))
    if abs(estimate - expected.quantity) > quantity_tolerance:
        return EvaluationStatus.CONFLICTING.value
    return EvaluationStatus.PROVEN.value


def _conflict_summary(question: InvestigationQuestion, role_outcomes: dict[str, str], role_objects: dict[str, list[ObjectView]]) -> str:
    if question.aspect == QuestionAspect.PRESENCE.value:
        seen = [role for role, outcome in role_outcomes.items() if outcome == EvidenceState.PROVEN.value]
        missed = [role for role, outcome in role_outcomes.items() if outcome == EvidenceState.NOT_OBSERVED.value]
        if seen and missed:
            return f"{question.canonical_class} was observed in the {seen[0]} and was not observed in the examined {missed[0]}."
        if missed and not seen:
            return f"{question.canonical_class} was not observed in the examined evidence, which cannot be reconciled with the order expectation."
    if question.aspect == QuestionAspect.IDENTITY.value:
        observed = sorted({item.canonical_class for items in role_objects.values() for item in items if item.category == Category.PRODUCT.value})
        return f"Expected {question.canonical_class}. Observed product classes: {', '.join(observed) or 'none'}."
    return f"{question.canonical_class} {question.aspect} cannot be reconciled with the order expectation."


def _dominant_coverage(question: InvestigationQuestion, coverage_by_role: dict[str, RoleCoverage]) -> str:
    values = [coverage_by_role[role].final_coverage for role in question.required_roles if role in coverage_by_role]
    return values[0] if values else CoverageValue.UNASSESSED.value


def assess(questions: list[InvestigationQuestion]) -> tuple[str, str]:
    applicable = [question for question in questions if question.applicability == Applicability.APPLICABLE.value]
    if not applicable or all(question.evaluation_status == EvaluationStatus.UNKNOWN.value for question in applicable):
        keys = ", ".join(question.question_key for question in applicable) or "none"
        return CaseAssessment.INSUFFICIENT_EVIDENCE.value, f"No applicable question can be evaluated ({keys})."
    if any(question.evaluation_status == EvaluationStatus.CONFLICTING.value for question in applicable):
        keys = ", ".join(question.question_key for question in applicable if question.evaluation_status == EvaluationStatus.CONFLICTING.value)
        return CaseAssessment.UNRESOLVED.value, f"Applicable questions cannot be reconciled: {keys}."
    if all(question.evaluation_status == EvaluationStatus.PROVEN.value for question in applicable):
        keys = ", ".join(question.question_key for question in applicable)
        return CaseAssessment.SUPPORTED.value, f"Every applicable question is proven: {keys}."
    proven = [question.question_key for question in applicable if question.evaluation_status == EvaluationStatus.PROVEN.value]
    unknown = [question.question_key for question in applicable if question.evaluation_status == EvaluationStatus.UNKNOWN.value]
    if proven and unknown:
        return CaseAssessment.PARTIALLY_SUPPORTED.value, f"Proven: {', '.join(proven)}. Unknown: {', '.join(unknown)}."
    return CaseAssessment.INSUFFICIENT_EVIDENCE.value, "Applicable questions did not produce a supported account."
