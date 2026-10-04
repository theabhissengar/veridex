"""Case-level metrics. Detector confidence, observation strength, and assessment stay separate."""

from __future__ import annotations


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _prf(predicted: set[str], labeled: set[str]) -> tuple[float, float, float]:
    tp = len(predicted & labeled)
    precision = _safe_div(tp, len(predicted))
    recall = _safe_div(tp, len(labeled))
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def macro_average(cases: list[dict], predicted_key: str, labeled_key: str) -> dict[str, float]:
    if not cases:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    scores = [_prf(set(case[predicted_key]), set(case[labeled_key])) for case in cases]
    count = len(scores)
    return {
        "precision": sum(item[0] for item in scores) / count,
        "recall": sum(item[1] for item in scores) / count,
        "f1": sum(item[2] for item in scores) / count,
    }


def accuracy(cases: list[dict], predicted_key: str, labeled_key: str) -> float:
    if not cases:
        return 0.0
    hits = sum(1 for case in cases if case[predicted_key] == case[labeled_key])
    return hits / len(cases)


def unknown_handling_rate(cases: list[dict]) -> float:
    """Share of labeled-unknown questions that the system left unknown."""
    total = 0
    kept = 0
    for case in cases:
        for labeled, predicted in zip(case["labeled_statuses"], case["predicted_statuses"], strict=True):
            if labeled != "unknown":
                continue
            total += 1
            if predicted == "unknown":
                kept += 1
    return _safe_div(kept, total)


def false_accusation_rate(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    hits = sum(1 for case in cases if case.get("blame_violation") or case.get("names_party_as_cause"))
    return hits / len(cases)
