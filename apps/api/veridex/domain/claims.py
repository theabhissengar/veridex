from dataclasses import dataclass

from veridex.domain.enums import Category, DisputeType, Party, FORBIDDEN_CLAIM_CATEGORIES
from veridex.domain.errors import ClaimValidationError
from veridex.domain.taxonomy import Taxonomy


@dataclass(frozen=True)
class OrderItemRef:
    id: str
    canonical_class: str
    category: Category
    order_relevant: bool


@dataclass(frozen=True)
class ClaimInput:
    claim_type: str
    party: str
    canonical_class: str | None = None
    order_item_id: str | None = None
    evidence_id: str | None = None
    claimed_quantity: int | None = None
    statement: str | None = None


def validate_claim(
    claim: ClaimInput,
    *,
    taxonomy: Taxonomy,
    order_items: list[OrderItemRef],
    case_evidence_ids: set[str],
) -> None:
    try:
        claim_type = DisputeType(claim.claim_type)
    except ValueError as exc:
        raise ClaimValidationError("invalid_claim_type", "claim_type is not a supported V1 dispute type") from exc
    try:
        Party(claim.party)
    except ValueError as exc:
        raise ClaimValidationError("invalid_party", "party is not a supported value") from exc

    if claim.canonical_class is not None and taxonomy.get(claim.canonical_class) is None:
        raise ClaimValidationError("unknown_class", "canonical_class is not in the taxonomy")

    item = None
    if claim.order_item_id is not None:
        item = next((row for row in order_items if row.id == claim.order_item_id), None)
        if item is None:
            raise ClaimValidationError("order_item_not_in_case", "order_item_id does not belong to this case")
        if claim.canonical_class is not None and claim.canonical_class != item.canonical_class:
            raise ClaimValidationError("claim_type_mismatch", "canonical_class does not match the order item")

    if claim.evidence_id is not None and claim.evidence_id not in case_evidence_ids:
        raise ClaimValidationError("evidence_not_in_case", "evidence_id does not belong to this case")

    if claim.claimed_quantity is not None and (
        isinstance(claim.claimed_quantity, bool) or not isinstance(claim.claimed_quantity, int) or claim.claimed_quantity < 1
    ):
        raise ClaimValidationError("invalid_quantity", "claimed_quantity must be a positive integer")

    spec = taxonomy.get(claim.canonical_class) if claim.canonical_class else None
    category = item.category if item is not None else (spec.category if spec else None)
    order_relevant = item.order_relevant if item is not None else (spec.order_relevant if spec else False)

    if claim_type is DisputeType.QUANTITY_MISMATCH and claim.claimed_quantity is None:
        raise ClaimValidationError("invalid_quantity", "quantity_mismatch claims require claimed_quantity")

    if item is None and spec is None:
        raise ClaimValidationError("missing_reference", "A claim must reference an order item or a canonical class")

    if category in FORBIDDEN_CLAIM_CATEGORIES and claim_type in {DisputeType.MISSING_ITEM, DisputeType.WRONG_ITEM}:
        raise ClaimValidationError("claim_type_mismatch", "This claim type cannot target packaging, shipping material, or a document")

    if claim_type is DisputeType.MISSING_ITEM:
        if item is None and not order_relevant:
            raise ClaimValidationError("missing_reference", "missing_item must reference an order item or an order-relevant class")
    elif claim_type is DisputeType.WRONG_ITEM:
        if not order_relevant or category in FORBIDDEN_CLAIM_CATEGORIES:
            raise ClaimValidationError("claim_type_mismatch", "wrong_item must reference an order-relevant class")
    elif claim_type is DisputeType.QUANTITY_MISMATCH:
        if item is None and (not order_relevant or category in FORBIDDEN_CLAIM_CATEGORIES):
            raise ClaimValidationError("missing_reference", "quantity_mismatch must reference an order item or an order-relevant class")
