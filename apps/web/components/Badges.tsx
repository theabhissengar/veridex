import { assessmentLabel, coverageLabel, evidenceState } from "@/lib/labels";

export function EvidenceStateBadge({ status }: { status: string }) {
  return <span className="rounded border px-2 py-0.5 text-xs font-medium">{evidenceState[status] || status}</span>;
}

export function CoverageBadge({ value, caption }: { value: string; caption: string }) {
  return (
    <span className="rounded border px-2 py-0.5 text-xs">
      {caption}: {coverageLabel[value] || value}
    </span>
  );
}

export function StrengthNote({ label, value }: { label: string; value: string | number | null }) {
  return (
    <span className="rounded border px-2 py-0.5 text-xs">
      {label}: {value ?? "—"}
    </span>
  );
}

export function CaseAssessmentBadge({ value }: { value: string | null }) {
  return <span className="rounded border px-2 py-0.5 text-xs font-semibold">Case assessment: {value ? assessmentLabel[value] || value : "not run"}</span>;
}
