import pytest

from veridex.domain.claims import ClaimInput, OrderItemRef, validate_claim
from veridex.domain.enums import Category
from veridex.domain.errors import ClaimValidationError
from veridex.domain.taxonomy import default_taxonomy

TAXONOMY = default_taxonomy()
ORDER = [
    OrderItemRef("item-1", "usb_c_cable", Category.ACCESSORY, True),
    OrderItemRef("item-2", "sony_wh1000xm5", Category.PRODUCT, True),
]
EVIDENCE = {"ev-1"}


def _claim(**kwargs) -> ClaimInput:
    payload = {"claim_type": "missing_item", "party": "customer", "order_item_id": "item-1"}
    payload.update(kwargs)
    return ClaimInput(**payload)


def test_valid_claims_pass() -> None:
    validate_claim(_claim(), taxonomy=TAXONOMY, order_items=ORDER, case_evidence_ids=EVIDENCE)
    validate_claim(
        _claim(claim_type="wrong_item", canonical_class="sony_wh1000xm5", order_item_id=None),
        taxonomy=TAXONOMY,
        order_items=ORDER,
        case_evidence_ids=EVIDENCE,
    )
    validate_claim(
        _claim(claim_type="quantity_mismatch", claimed_quantity=2),
        taxonomy=TAXONOMY,
        order_items=ORDER,
        case_evidence_ids=EVIDENCE,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"claim_type": "fraud"},
        {"party": "neighbor"},
        {"canonical_class": "not_a_class"},
        {"order_item_id": "other-case"},
        {"evidence_id": "other-evidence"},
        {"claimed_quantity": 0},
        {"claimed_quantity": True},
        {"claim_type": "quantity_mismatch", "claimed_quantity": None},
        {"order_item_id": None, "canonical_class": None},
        {"order_item_id": None, "canonical_class": "cardboard_box"},
        {"claim_type": "wrong_item", "order_item_id": None, "canonical_class": "cardboard_box"},
    ],
)
def test_invalid_claims_rejected(kwargs: dict) -> None:
    with pytest.raises(ClaimValidationError):
        validate_claim(_claim(**kwargs), taxonomy=TAXONOMY, order_items=ORDER, case_evidence_ids=EVIDENCE)
