from veridex.domain.enums import Category
from veridex.domain.questions import AcceptedObservation, ClaimRef, OrderLine, generate_investigation_questions


def _line(item_id: str, sku: str, canonical: str, category: str, relevant: bool = True, quantity: int = 1) -> OrderLine:
    return OrderLine(item_id, sku, canonical, category, quantity, relevant)


def test_same_inputs_produce_the_same_question_set() -> None:
    lines = [_line("1", "B", "usb_c_cable", Category.ACCESSORY.value), _line("2", "A", "sony_wh1000xm5", Category.PRODUCT.value)]
    claims = [ClaimRef("missing_item", "usb_c_cable", "1", Category.ACCESSORY.value, True)]
    observations = [
        AcceptedObservation("object", "jbl_tune", Category.PRODUCT.value, detector_confidence=0.2),
        AcceptedObservation("object", "cardboard_box", Category.PACKAGING.value, detector_confidence=0.99),
    ]
    shuffled = list(reversed(observations))
    first = generate_investigation_questions(order_lines=lines, claims=claims, observations=observations, claimed_dispute_type="missing_item")
    second = generate_investigation_questions(order_lines=list(reversed(lines)), claims=claims, observations=shuffled, claimed_dispute_type="missing_item")
    confident = generate_investigation_questions(
        order_lines=lines,
        claims=claims,
        observations=[AcceptedObservation("object", "jbl_tune", Category.PRODUCT.value, detector_confidence=0.99), observations[1]],
        claimed_dispute_type="missing_item",
    )
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert [item.to_dict() for item in first] == [item.to_dict() for item in confident]


def test_claim_marks_primary_without_removing_questions() -> None:
    lines = [_line("1", "C", "usb_c_cable", Category.ACCESSORY.value)]
    questions = generate_investigation_questions(
        order_lines=lines,
        claims=[ClaimRef("missing_item", "usb_c_cable", "1")],
        observations=[],
    )
    keys = {item.question_key for item in questions}
    assert keys == {"item:usb_c_cable:presence", "item:usb_c_cable:quantity", "item:usb_c_cable:identity"}
    primary = {item.aspect for item in questions if item.primary}
    assert primary == {"presence"}


def test_unexpected_product_requires_an_accepted_observation() -> None:
    lines = [_line("1", "S", "sony_wh1000xm5", Category.PRODUCT.value)]
    without = generate_investigation_questions(order_lines=lines, claims=[], observations=[])
    with_obs = generate_investigation_questions(
        order_lines=lines,
        claims=[],
        observations=[AcceptedObservation("object", "jbl_tune", Category.PRODUCT.value)],
    )
    assert "item:jbl_tune:identity" not in {item.question_key for item in without}
    added = next(item for item in with_obs if item.question_key == "item:jbl_tune:identity")
    assert added.applicability == "applicable"
    assert added.required_roles == ["invoice", "packing_video", "unboxing_video"]


def test_packaging_is_not_applicable_and_not_an_identity_question() -> None:
    questions = generate_investigation_questions(
        order_lines=[_line("1", "S", "sony_wh1000xm5", Category.PRODUCT.value)],
        claims=[],
        observations=[AcceptedObservation("object", "cardboard_box", Category.PACKAGING.value)],
    )
    box = next(item for item in questions if item.canonical_class == "cardboard_box")
    assert box.applicability == "not_applicable"
    assert box.aspect == "presence"
    assert not any(item.aspect == "identity" and item.canonical_class == "cardboard_box" for item in questions)
