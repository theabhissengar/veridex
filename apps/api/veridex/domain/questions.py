from dataclasses import dataclass, field

from veridex.domain.enums import Applicability, Category, DisputeType, EvidenceRole, ObservationType, QuestionAspect


VIDEO_ROLES = [EvidenceRole.PACKING_VIDEO.value, EvidenceRole.UNBOXING_VIDEO.value]
UNEXPECTED_PRODUCT_ROLES = [
    EvidenceRole.PACKING_VIDEO.value,
    EvidenceRole.UNBOXING_VIDEO.value,
    EvidenceRole.INVOICE.value,
]

DISPUTE_ASPECT = {
    DisputeType.MISSING_ITEM.value: QuestionAspect.PRESENCE.value,
    DisputeType.WRONG_ITEM.value: QuestionAspect.IDENTITY.value,
    DisputeType.QUANTITY_MISMATCH.value: QuestionAspect.QUANTITY.value,
}

EXCLUDED_OBSERVATION_CATEGORIES = {
    Category.PACKAGING.value,
    Category.SHIPPING_MATERIAL.value,
    Category.DOCUMENT.value,
    Category.OTHER.value,
    Category.UNKNOWN.value,
}


@dataclass
class OrderLine:
    id: str
    sku: str
    canonical_class: str
    category: str
    quantity: int
    order_relevant: bool


@dataclass
class ClaimRef:
    claim_type: str
    canonical_class: str | None = None
    order_item_id: str | None = None
    category: str | None = None
    order_relevant: bool = False


@dataclass
class AcceptedObservation:
    observation_type: str
    canonical_class: str | None = None
    category: str | None = None
    detector_confidence: float | None = None


@dataclass
class InvestigationQuestion:
    question_key: str
    subject: str
    aspect: str
    required_roles: list[str]
    canonical_class: str
    primary: bool
    applicability: str
    order_item_id: str | None = None
    evaluation_status: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "question_key": self.question_key,
            "subject": self.subject,
            "aspect": self.aspect,
            "required_roles": list(self.required_roles),
            "order_item_id": self.order_item_id,
            "canonical_class": self.canonical_class,
            "primary": self.primary,
            "applicability": self.applicability,
            "evaluation_status": self.evaluation_status,
        }


def question_key(canonical_class: str, aspect: str) -> str:
    return f"item:{canonical_class}:{aspect}"


def _upsert(
    bucket: dict[str, InvestigationQuestion],
    *,
    canonical_class: str,
    aspect: str,
    roles: list[str],
    applicability: str,
    order_item_id: str | None,
    primary: bool,
) -> None:
    key = question_key(canonical_class, aspect)
    existing = bucket.get(key)
    if existing is None:
        bucket[key] = InvestigationQuestion(
            question_key=key,
            subject=canonical_class,
            aspect=aspect,
            required_roles=sorted(set(roles)),
            canonical_class=canonical_class,
            primary=primary,
            applicability=applicability,
            order_item_id=order_item_id,
        )
        return
    existing.required_roles = sorted(set(existing.required_roles) | set(roles))
    existing.primary = existing.primary or primary
    if existing.order_item_id is None:
        existing.order_item_id = order_item_id
    if existing.applicability == Applicability.NOT_APPLICABLE.value and applicability == Applicability.APPLICABLE.value:
        existing.applicability = Applicability.APPLICABLE.value


def _identity_allowed(category: str, order_relevant: bool) -> bool:
    if category in {Category.PACKAGING.value, Category.SHIPPING_MATERIAL.value, Category.DOCUMENT.value}:
        return False
    if category == Category.PRODUCT.value:
        return True
    return category == Category.ACCESSORY.value and order_relevant


def _add_class_questions(
    bucket: dict[str, InvestigationQuestion],
    *,
    canonical_class: str,
    category: str,
    order_relevant: bool,
    order_item_id: str | None,
    primary_aspect: str | None,
) -> None:
    if category not in {Category.PRODUCT.value, Category.ACCESSORY.value} and not order_relevant:
        return
    if category in EXCLUDED_OBSERVATION_CATEGORIES and not order_relevant:
        return
    for aspect in (QuestionAspect.PRESENCE.value, QuestionAspect.QUANTITY.value):
        _upsert(
            bucket,
            canonical_class=canonical_class,
            aspect=aspect,
            roles=VIDEO_ROLES,
            applicability=Applicability.APPLICABLE.value,
            order_item_id=order_item_id,
            primary=primary_aspect == aspect,
        )
    if _identity_allowed(category, order_relevant):
        _upsert(
            bucket,
            canonical_class=canonical_class,
            aspect=QuestionAspect.IDENTITY.value,
            roles=VIDEO_ROLES,
            applicability=Applicability.APPLICABLE.value,
            order_item_id=order_item_id,
            primary=primary_aspect == QuestionAspect.IDENTITY.value,
        )


def generate_investigation_questions(
    *,
    order_lines: list[OrderLine],
    claims: list[ClaimRef],
    observations: list[AcceptedObservation],
    claimed_dispute_type: str | None = None,
) -> list[InvestigationQuestion]:
    """Return a stable question list. Detector confidence is ignored."""
    bucket: dict[str, InvestigationQuestion] = {}
    lines = sorted(order_lines, key=lambda line: (line.sku, line.canonical_class, line.id))
    order_classes = {line.canonical_class for line in lines}
    class_meta = {line.canonical_class: line for line in lines}

    for line in lines:
        for aspect in (QuestionAspect.PRESENCE.value, QuestionAspect.QUANTITY.value):
            _upsert(
                bucket,
                canonical_class=line.canonical_class,
                aspect=aspect,
                roles=VIDEO_ROLES,
                applicability=Applicability.APPLICABLE.value,
                order_item_id=line.id,
                primary=False,
            )
        if _identity_allowed(line.category, line.order_relevant):
            _upsert(
                bucket,
                canonical_class=line.canonical_class,
                aspect=QuestionAspect.IDENTITY.value,
                roles=VIDEO_ROLES,
                applicability=Applicability.APPLICABLE.value,
                order_item_id=line.id,
                primary=False,
            )

    for claim in claims:
        line = next((row for row in lines if row.id == claim.order_item_id), None) if claim.order_item_id else None
        if line is None and claim.canonical_class:
            line = class_meta.get(claim.canonical_class)
        aspect = DISPUTE_ASPECT[claim.claim_type]
        if line is not None:
            key = question_key(line.canonical_class, aspect)
            if key in bucket:
                bucket[key].primary = True
            continue
        if not claim.canonical_class:
            continue
        category = claim.category or Category.PRODUCT.value
        relevant = claim.order_relevant or category == Category.PRODUCT.value
        if category in EXCLUDED_OBSERVATION_CATEGORIES or not relevant:
            continue
        _add_class_questions(
            bucket,
            canonical_class=claim.canonical_class,
            category=category,
            order_relevant=relevant,
            order_item_id=None,
            primary_aspect=aspect,
        )

    for observation in observations:
        if observation.observation_type != ObservationType.OBJECT.value:
            continue
        if not observation.canonical_class or not observation.category:
            continue
        canonical = observation.canonical_class
        category = observation.category
        if category == Category.PRODUCT.value and canonical not in order_classes:
            _upsert(
                bucket,
                canonical_class=canonical,
                aspect=QuestionAspect.IDENTITY.value,
                roles=UNEXPECTED_PRODUCT_ROLES,
                applicability=Applicability.APPLICABLE.value,
                order_item_id=None,
                primary=False,
            )
            continue
        on_order = canonical in order_classes
        non_relevant_accessory = category == Category.ACCESSORY.value and not (
            on_order and class_meta[canonical].order_relevant
        )
        if category in EXCLUDED_OBSERVATION_CATEGORIES or (non_relevant_accessory and not on_order):
            key = question_key(canonical, QuestionAspect.PRESENCE.value)
            if key not in bucket:
                _upsert(
                    bucket,
                    canonical_class=canonical,
                    aspect=QuestionAspect.PRESENCE.value,
                    roles=VIDEO_ROLES,
                    applicability=Applicability.NOT_APPLICABLE.value,
                    order_item_id=None,
                    primary=False,
                )

    if claimed_dispute_type in DISPUTE_ASPECT:
        aspect = DISPUTE_ASPECT[claimed_dispute_type]
        for question in bucket.values():
            if question.aspect == aspect and question.applicability == Applicability.APPLICABLE.value:
                question.primary = True

    return [bucket[key] for key in sorted(bucket)]
