from veridex.eval.runner import evaluate_tiers, score_cases


def test_empty_tiers_are_not_a_published_score():
    report = evaluate_tiers()
    assert report["held_out_evaluation"]["cases"] == 0
    assert report["published_number"] is None


def test_scores_stay_split_by_kind():
    scored = score_cases(
        [
            {
                "expected_items": [{"canonical_class": "usb_c_cable"}],
                "assessment": "supported",
                "questions": [{"status": "unknown"}],
                "predicted": {
                    "items": ["usb_c_cable"],
                    "assessment": "supported",
                    "question_statuses": ["unknown"],
                },
            }
        ]
    )
    assert scored["item_match"]["f1"] == 1
    assert scored["assessment_accuracy"] == 1
    assert "detector" not in scored
