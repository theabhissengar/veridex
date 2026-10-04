export const evidenceState: Record<string, string> = {
  proven: "PROVEN",
  not_observed: "NOT_OBSERVED",
  conflicting: "CONFLICTING",
  unknown: "UNKNOWN",
};

export const assessmentLabel: Record<string, string> = {
  supported: "SUPPORTED",
  partially_supported: "PARTIALLY_SUPPORTED",
  unresolved: "UNRESOLVED",
  insufficient_evidence: "INSUFFICIENT_EVIDENCE",
};

export const coverageLabel: Record<string, string> = {
  complete: "COMPLETE",
  partial: "PARTIAL",
  limited: "LIMITED",
  unassessed: "UNASSESSED",
};
