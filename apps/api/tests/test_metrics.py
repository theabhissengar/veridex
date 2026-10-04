from veridex.eval.metrics import accuracy, false_accusation_rate, macro_average, unknown_handling_rate


def test_metrics_are_case_macro_and_keep_scores_separate() -> None:
    cases = [
        {"predicted_classes": ["usb_c_cable"], "labeled_classes": ["usb_c_cable"], "predicted_assessment": "supported", "labeled_assessment": "supported"},
        {"predicted_classes": ["jbl_tune"], "labeled_classes": ["sony_wh1000xm5"], "predicted_assessment": "unresolved", "labeled_assessment": "unresolved"},
    ]
    detection = macro_average(cases, "predicted_classes", "labeled_classes")
    assert detection["precision"] == 0.5
    assert accuracy(cases, "predicted_assessment", "labeled_assessment") == 1.0
    assert unknown_handling_rate([{"labeled_statuses": ["unknown"], "predicted_statuses": ["proven"]}]) == 0.0
    assert false_accusation_rate([{"blame_violation": False}, {"blame_violation": True}]) == 0.5
