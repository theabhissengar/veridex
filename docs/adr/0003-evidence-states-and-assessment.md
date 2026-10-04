# ADR 0003: Evidence states and case assessment

## Status

Accepted

## Decision

Evidence states are `proven`, `not_observed`, `conflicting`, and `unknown`. They describe evidence. They do not assign responsibility.

`unknown` means the question cannot currently be determined. It is not a coverage value.

Question-level `conflicting` means the required evidence and the order expectation for that question cannot be reconciled. Sources may disagree, or the examined evidence may disagree with the order. It does not require two detector boxes that contradict each other. Per-source `not_observed` stays `not_observed`.

Case assessment is `supported`, `partially_supported`, `unresolved`, or `insufficient_evidence`, computed only from applicable `InvestigationQuestion` values.

The final question list is frozen after accepted observations exist.
