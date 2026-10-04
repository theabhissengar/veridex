from veridex.domain.enums import Category
from veridex.domain.evaluation import ObjectView, RoleCoverage, evaluate_investigation
from veridex.domain.questions import AcceptedObservation, OrderLine, generate_investigation_questions


def _coverage(role: str, final: str, present: bool = True) -> RoleCoverage:
    return RoleCoverage(role, final, evidence_id=f"ev-{role}", frames_examined=120, sampling_rate="1 fps", media_present=present)


def _object(role: str, canonical: str, category: str, quantity: int = 1, strength: str = "high") -> ObjectView:
    return ObjectView(
        canonical,
        category,
        role,
        quantity,
        strength,
        observation_strength="high",
        evidence_id=f"ev-{role}",
        observation_id=f"obs-{role}-{canonical}",
        frame_id=f"frame-{role}",
        timestamp_ms=43000,
        detector_confidence=0.94,
    )


def _eval(lines, objects, coverage, observations=None, dispute=None):
    questions = generate_investigation_questions(
        order_lines=lines,
        claims=[],
        observations=observations or [],
        claimed_dispute_type=dispute,
    )
    return evaluate_investigation(questions=questions, order_lines=lines, objects=objects, coverage_by_role=coverage)


def test_complete_match_is_supported() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "complete")}
    objects = [
        _object("packing_video", "usb_c_cable", Category.ACCESSORY.value),
        _object("unboxing_video", "usb_c_cable", Category.ACCESSORY.value),
    ]
    result = _eval([line], objects, coverage)
    assert result.assessment == "supported"


def test_missing_video_is_unknown_and_insufficient() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {
        "packing_video": _coverage("packing_video", "complete"),
        "unboxing_video": _coverage("unboxing_video", "unassessed", present=False),
    }
    result = _eval([line], [_object("packing_video", "usb_c_cable", Category.ACCESSORY.value)], coverage)
    presence = next(item for item in result.questions if item.question_key == "item:usb_c_cable:presence")
    assert presence.evaluation_status == "unknown"
    assert not any(item.status == "not_observed" and item.role == "unboxing_video" for item in result.findings)
    assert result.assessment == "insufficient_evidence"


def test_complete_absence_is_not_observed_and_question_conflicts_without_two_boxes() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "complete")}
    result = _eval([line], [_object("packing_video", "usb_c_cable", Category.ACCESSORY.value)], coverage)
    unboxing = next(item for item in result.findings if item.role == "unboxing_video" and item.aspect == "presence")
    assert unboxing.status == "not_observed"
    assert "not observed in the examined evidence" in unboxing.summary
    assert unboxing.search_scope["frames_examined"] == 120
    presence = next(item for item in result.questions if item.question_key == "item:usb_c_cable:presence")
    assert presence.evaluation_status == "conflicting"
    assert result.assessment == "unresolved"


def test_partial_coverage_stays_unknown() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "partial")}
    result = _eval([line], [_object("packing_video", "usb_c_cable", Category.ACCESSORY.value)], coverage)
    presence = next(item for item in result.questions if item.question_key == "item:usb_c_cable:presence")
    assert presence.evaluation_status == "unknown"
    assert not any(item.status == "not_observed" and item.role == "unboxing_video" for item in result.findings)


def test_suggestion_does_not_change_a_question() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {
        "packing_video": _coverage("packing_video", "unassessed"),
        "unboxing_video": _coverage("unboxing_video", "unassessed"),
    }
    result = _eval([line], [], coverage)
    assert all(item.evaluation_status == "unknown" for item in result.questions if item.applicability == "applicable")


def test_sony_versus_jbl_is_unresolved() -> None:
    line = OrderLine("1", "S", "sony_wh1000xm5", Category.PRODUCT.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "complete")}
    objects = [
        _object("packing_video", "jbl_tune", Category.PRODUCT.value),
        _object("unboxing_video", "jbl_tune", Category.PRODUCT.value),
    ]
    observations = [
        AcceptedObservation("object", "jbl_tune", Category.PRODUCT.value),
    ]
    result = _eval([line], objects, coverage, observations)
    identity = next(item for item in result.questions if item.question_key == "item:sony_wh1000xm5:identity")
    assert identity.evaluation_status == "conflicting"
    assert result.assessment == "unresolved"
    assert not any(item.canonical_class == "cardboard_box" for item in result.questions)


def test_partially_supported_when_one_question_is_unknown() -> None:
    cable = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "complete")}
    objects = [
        _object("packing_video", "usb_c_cable", Category.ACCESSORY.value, strength="low"),
        _object("unboxing_video", "usb_c_cable", Category.ACCESSORY.value, strength="low"),
    ]
    result = _eval([cable], objects, coverage)
    statuses = {item.aspect: item.evaluation_status for item in result.questions}
    assert statuses["presence"] == "proven"
    assert statuses["quantity"] == "unknown"
    assert "conflicting" not in statuses.values()
    assert result.assessment == "partially_supported"


def test_packaging_does_not_create_a_wrong_item_finding() -> None:
    line = OrderLine("1", "S", "sony_wh1000xm5", Category.PRODUCT.value, 1, True)
    coverage = {"packing_video": _coverage("packing_video", "complete"), "unboxing_video": _coverage("unboxing_video", "complete")}
    objects = [
        _object("packing_video", "sony_wh1000xm5", Category.PRODUCT.value),
        _object("unboxing_video", "sony_wh1000xm5", Category.PRODUCT.value),
        _object("packing_video", "cardboard_box", Category.PACKAGING.value),
    ]
    result = _eval(
        [line],
        objects,
        coverage,
        [AcceptedObservation("object", "cardboard_box", Category.PACKAGING.value)],
    )
    assert not any(item.subject_key == "cardboard_box" and item.aspect == "identity" for item in result.findings)
    box = next(item for item in result.questions if item.canonical_class == "cardboard_box")
    assert box.applicability == "not_applicable"
