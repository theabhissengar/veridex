from veridex.domain.enums import Category
from veridex.domain.evaluation import ObjectView, RoleCoverage, evaluate_investigation
from veridex.domain.questions import OrderLine, generate_investigation_questions
from veridex.domain.report import blame_violations, build_report


def test_report_allows_banned_words_only_inside_quotations() -> None:
    line = OrderLine("1", "C", "usb_c_cable", Category.ACCESSORY.value, 1, True)
    coverage = {
        "packing_video": RoleCoverage("packing_video", "complete", "ev-p", 120, "1 fps", True),
        "unboxing_video": RoleCoverage("unboxing_video", "complete", "ev-u", 120, "1 fps", True),
    }
    questions = generate_investigation_questions(order_lines=[line], claims=[], observations=[])
    result = evaluate_investigation(
        questions=questions,
        order_lines=[line],
        objects=[
            ObjectView("usb_c_cable", Category.ACCESSORY.value, "packing_video", 1, "high", "high", "ev-p", "o1", "f1", 1000, 0.9),
            ObjectView("usb_c_cable", Category.ACCESSORY.value, "unboxing_video", 1, "high", "high", "ev-u", "o2", "f2", 1000, 0.9),
        ],
        coverage_by_role=coverage,
    )
    _body, markdown = build_report(
        case_title="Cable",
        dispute_type="missing_item",
        evidence_rows=[{"role": "customer_statement", "party": "customer", "original_filename": "note.txt", "text_body": "This is fraud."}],
        coverage_rows=[{"role": "packing_video", "suggested_coverage": "unassessed", "final_coverage": "complete", "final_basis": "operator"}],
        expected_items=[{"canonical_class": "usb_c_cable", "category": "ACCESSORY", "quantity": 1}],
        observations=[{"observation_type": "object", "canonical_class": "usb_c_cable", "observed_quantity_estimate": 1, "quantity_strength": "high", "observation_strength": "high"}],
        timeline=[{"phase": "packed", "summary": "usb_c_cable observed"}],
        result=result,
        license_unreviewed=True,
    )
    conclusion = "\n".join(markdown.split("## 7.")[1].split("## 12.")[0])
    assert blame_violations(conclusion) == []
    assert "> This is fraud." in markdown
    assert blame_violations("The seller is responsible") == ["responsible"]
