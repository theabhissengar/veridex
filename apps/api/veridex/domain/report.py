import re

from veridex.domain.evaluation import EvaluationResult, FindingDraft
from veridex.domain.questions import InvestigationQuestion

BANNED = ("lying", "liar", "fraud", "stole", "guilty", "responsible")
QUOTE_LINE = re.compile(r"^\s*>")


def blame_violations(markdown: str) -> list[str]:
    hits: list[str] = []
    for line in markdown.splitlines():
        if QUOTE_LINE.match(line):
            continue
        lowered = line.lower()
        for word in BANNED:
            if re.search(rf"\b{word}\b", lowered):
                hits.append(word)
    return hits


def build_report(
    *,
    case_title: str,
    dispute_type: str | None,
    evidence_rows: list[dict],
    coverage_rows: list[dict],
    expected_items: list[dict],
    observations: list[dict],
    timeline: list[dict],
    result: EvaluationResult,
    license_unreviewed: bool,
) -> tuple[dict, str]:
    questions = result.questions
    findings = result.findings
    sections = [
        ("Case facts", f"Title: {case_title}\n\nClaimed dispute type: {dispute_type or 'not set'}"),
        ("Evidence available", _evidence_section(evidence_rows)),
        ("Evidence coverage", _coverage_section(coverage_rows)),
        ("Expected items", _expected_section(expected_items)),
        ("Observed item estimates", _observed_section(observations)),
        ("Timeline", _timeline_section(timeline)),
        ("Evidence findings", _findings_section(findings, questions)),
        ("Conflicting evidence", _status_section(findings, "conflicting")),
        ("Unknown and insufficient evidence", _status_section(findings, "unknown")),
        ("Case-level assessment", f"Assessment: {result.assessment}\n\n{result.assessment_rationale}"),
        ("Limitations", _limitations(license_unreviewed)),
        ("Evidence references", _references(findings)),
    ]
    body = {
        "sections": [{"title": title, "body": text} for title, text in sections],
        "assessment": result.assessment,
        "assessment_rationale": result.assessment_rationale,
    }
    markdown = "\n\n".join(f"## {index}. {title}\n\n{text}" for index, (title, text) in enumerate(sections, start=1))
    conclusion = "\n\n".join(text for title, text in sections[6:11])
    violations = blame_violations(conclusion)
    if violations:
        raise RuntimeError(f"Report conclusions contain banned wording: {violations}")
    return body, markdown


def _evidence_section(rows: list[dict]) -> str:
    if not rows:
        return "No evidence has been uploaded."
    lines = []
    for row in rows:
        lines.append(f"- {row.get('role')} from {row.get('party')} ({row.get('original_filename')})")
        quote = row.get("text_body")
        if quote:
            lines.append("> [quoted statement]")
            for part in str(quote).splitlines() or [str(quote)]:
                lines.append(f"> {part}")
    return "\n".join(lines)


def _coverage_section(rows: list[dict]) -> str:
    if not rows:
        return "No coverage records."
    lines = ["Final coverage is what the rules used. Suggested coverage is the automatic hint."]
    for row in rows:
        lines.append(
            f"- {row.get('role')}: suggested {row.get('suggested_coverage')}, final {row.get('final_coverage')}. {row.get('final_basis') or row.get('suggestion_basis') or ''}"
        )
    return "\n".join(lines)


def _expected_section(items: list[dict]) -> str:
    if not items:
        return "No order items."
    return "\n".join(
        f"- {item['canonical_class']} ({item.get('category')}) quantity {item['quantity']}" for item in items
    )


def _observed_section(observations: list[dict]) -> str:
    objects = [row for row in observations if row.get("observation_type") == "object"]
    if not objects:
        return "No accepted object observations."
    lines = []
    for row in objects:
        lines.append(
            f"- {row.get('canonical_class')}: Estimated observed quantity: {row.get('observed_quantity_estimate')} "
            f"(quantity strength: {row.get('quantity_strength')}; observation strength: {row.get('observation_strength')})"
        )
    return "\n".join(lines)


def _timeline_section(entries: list[dict]) -> str:
    if not entries:
        return "No timeline entries."
    return "\n".join(f"- {entry.get('phase')}: {entry.get('summary')}" for entry in entries)


def _findings_section(findings: list[FindingDraft], questions: list[InvestigationQuestion]) -> str:
    if not findings:
        return "No findings."
    lines = []
    for question in questions:
        related = [finding for finding in findings if finding.question_key == question.question_key]
        if not related:
            continue
        lines.append(f"### {question.question_key}")
        lines.append(f"Evaluation status: {question.evaluation_status}")
        for finding in related:
            lines.append(f"- {finding.status}: {finding.summary}")
    return "\n".join(lines)


def _status_section(findings: list[FindingDraft], status: str) -> str:
    matched = [finding for finding in findings if finding.status == status]
    if not matched:
        return "None."
    return "\n".join(f"- {finding.question_key}: {finding.summary}" for finding in matched)


def _limitations(license_unreviewed: bool) -> str:
    lines = [
        "This report is an evidence reconstruction for a human reviewer.",
        "NOT_OBSERVED means the item was not observed in the examined evidence. It does not mean the item did not exist.",
        "V1 does not automatically decide that a video is a complete packing or a complete unboxing.",
        "Estimated observed quantity is a peak count, not a counted inventory.",
        "Detector confidence, observation strength, evidence coverage, and the case assessment are different readouts.",
    ]
    if license_unreviewed:
        lines.append("A model license used for this run has not been reviewed.")
    return "\n".join(lines)


def _references(findings: list[FindingDraft]) -> str:
    lines = []
    for finding in findings:
        if finding.evidence_id or finding.search_scope:
            lines.append(
                f"- {finding.question_key} {finding.status}: evidence {finding.evidence_id} "
                f"frame {finding.frame_id} timestamp_ms {finding.timestamp_ms} "
                f"detector_confidence {finding.detector_confidence} scope {finding.search_scope}"
            )
    return "\n".join(lines) if lines else "No references."
