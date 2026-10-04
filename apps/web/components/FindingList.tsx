"use client";

import { CoverageBadge, EvidenceStateBadge, StrengthNote } from "@/components/Badges";
import { EvidencePlayer } from "@/components/EvidencePlayer";
import { API_BASE } from "@/lib/api";

export type Finding = {
  id: string;
  question_key: string;
  status: string;
  summary: string;
  basis: string;
  final_coverage: string;
  observation_strength: string | null;
  observed_quantity_estimate: number | null;
  quantity_strength: string | null;
  evidence_references: Array<{
    detector_confidence: number | null;
    timestamp_ms: number | null;
    role: string | null;
    evidence_id: string | null;
    bbox: { x: number; y: number; w: number; h: number } | null;
  }>;
};

export function FindingList({ items, selectedId, onSelect }: { items: Finding[]; selectedId: string | null; onSelect: (id: string) => void }) {
  const selected = items.find((item) => item.id === selectedId) || null;
  const reference = selected?.evidence_references.find((item) => item.evidence_id) || null;
  const video = reference && (reference.role || "").includes("video");
  return (
    <div className="space-y-3">
      {items.length === 0 ? <p>No findings yet. Run an investigation after evidence and final coverage are ready.</p> : null}
      {items.map((item) => (
        <article key={item.id} className="space-y-2 rounded border bg-white p-4">
          <button className="text-left text-xs text-stone-500 underline" onClick={() => onSelect(item.id)}>
            {item.question_key}
          </button>
          <div className="flex flex-wrap gap-2">
            <EvidenceStateBadge status={item.status} />
            <CoverageBadge caption="Final coverage" value={item.final_coverage} />
            <StrengthNote label="Observation strength" value={item.observation_strength} />
            <StrengthNote label="Detector confidence" value={item.evidence_references[0]?.detector_confidence ?? null} />
          </div>
          <p>{item.summary}</p>
          <p className="text-sm text-stone-600">{item.basis}</p>
          {item.observed_quantity_estimate != null ? (
            <p>
              Estimated observed quantity: {item.observed_quantity_estimate} (quantity strength: {item.quantity_strength})
            </p>
          ) : null}
        </article>
      ))}
      {selected && video && reference?.evidence_id ? (
        <EvidencePlayer
          src={`${API_BASE}/api/v1/evidence/${reference.evidence_id}/content`}
          timestampMs={reference.timestamp_ms}
          bbox={reference.bbox}
        />
      ) : null}
    </div>
  );
}
