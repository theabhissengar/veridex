"""Load dataset tiers and score them separately. Empty tiers stay empty."""

import json
from pathlib import Path

from veridex.domain.taxonomy import repo_root
from veridex.eval.metrics import accuracy, false_accusation_rate, macro_average, unknown_handling_rate


def tier_dir(name: str) -> Path:
    return repo_root() / "dataset" / name


def load_ground_truth(name: str) -> list[dict]:
    root = tier_dir(name)
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.glob("*/ground_truth.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def score_cases(cases: list[dict]) -> dict:
    if not cases:
        return {"cases": 0, "published": False}
    paired = []
    for case in cases:
        predicted = case.get("predicted") or {}
        paired.append(
            {
                "predicted_items": predicted.get("items", []),
                "labeled_items": [item["canonical_class"] for item in case.get("expected_items", [])],
                "predicted_assessment": predicted.get("assessment"),
                "labeled_assessment": case.get("assessment"),
                "labeled_statuses": [row.get("status") for row in case.get("questions", [])],
                "predicted_statuses": predicted.get("question_statuses", []),
                "blame_violation": predicted.get("blame_violation", False),
                "names_party_as_cause": predicted.get("names_party_as_cause", False),
            }
        )
    return {
        "cases": len(cases),
        "published": True,
        "item_match": macro_average(paired, "predicted_items", "labeled_items"),
        "assessment_accuracy": accuracy(paired, "predicted_assessment", "labeled_assessment"),
        "unknown_handling": unknown_handling_rate(paired) if any(row["labeled_statuses"] for row in paired) else None,
        "false_accusation_rate": false_accusation_rate(paired),
    }


def evaluate_tiers() -> dict:
    development = score_cases(load_ground_truth("development"))
    evaluation = score_cases(load_ground_truth("evaluation"))
    return {
        "development_validation": development,
        "held_out_evaluation": evaluation,
        "published_number": evaluation if evaluation["published"] else None,
    }
