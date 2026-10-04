"use client";

import { CoverageBadge } from "@/components/Badges";
import { api } from "@/lib/api";

const finals = ["complete", "partial", "limited", "unassessed"];

export function CoverageEditor({
  caseId,
  items,
  onChange,
}: {
  caseId: string;
  items: Array<Record<string, unknown>>;
  onChange: () => Promise<void>;
}) {
  async function save(role: string, finalCoverage: string) {
    await api(`/api/v1/cases/${caseId}/coverage/${role}`, {
      method: "PUT",
      body: JSON.stringify({ final_coverage: finalCoverage, final_basis: "Operator confirmed final coverage." }),
    });
    await onChange();
  }

  if (items.length === 0) return <p>No coverage records yet. Upload evidence first.</p>;
  return (
    <div className="space-y-3">
      <p className="text-sm text-stone-600">The suggestion is not what the investigation uses until it is confirmed as final coverage.</p>
      {items.map((item) => {
        const signals = (item.suggestion_signals as Record<string, unknown>) || {};
        return (
          <article key={String(item.role)} className="space-y-2 rounded border bg-white p-4">
            <h2 className="font-medium">{String(item.role)}</h2>
            <div className="flex flex-wrap gap-2">
              <CoverageBadge caption="Suggested coverage" value={String(item.suggested_coverage)} />
              <CoverageBadge caption="Final coverage" value={String(item.final_coverage)} />
            </div>
            <p className="text-sm">Duration: {String(signals.duration_ms ?? "not measured")}</p>
            <p className="text-sm">Frames examined: {String(signals.frames_examined ?? "not measured")}</p>
            <p className="text-sm">Sampling rate: {String(signals.sampling_fps ?? "not measured")}</p>
            <p className="text-sm">Scene signals: {JSON.stringify(signals.scene_notes ?? [])}</p>
            <p className="text-sm">{String(item.suggestion_basis || "")}</p>
            <div className="flex gap-2">
              {finals.map((value) => (
                <button key={value} className="rounded border px-2 py-1 text-xs" onClick={() => save(String(item.role), value)}>
                  Set {value}
                </button>
              ))}
            </div>
          </article>
        );
      })}
    </div>
  );
}
