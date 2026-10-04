"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Finding, FindingList } from "@/components/FindingList";
import { api } from "@/lib/api";

export default function FindingsPage() {
  const params = useParams<{ caseId: string }>();
  const [items, setItems] = useState<Finding[]>([]);
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Array<{ id: string }> }>(`/api/v1/cases/${params.caseId}/investigations`)
      .then(async (list) => {
        const latest = list.items[0];
        if (!latest) return;
        const findings = await api<{ items: Finding[] }>(`/api/v1/investigations/${latest.id}/findings`);
        setItems(findings.items);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  const visible = items.filter((item) => filter === "all" || item.status === filter);
  return (
    <section className="space-y-3">
      <div className="flex gap-2 text-xs">
        {["all", "proven", "not_observed", "conflicting", "unknown"].map((value) => (
          <button key={value} className="rounded border px-2 py-1" onClick={() => setFilter(value)}>
            {value}
          </button>
        ))}
      </div>
      {error ? <p className="text-red-700">{error}</p> : null}
      <FindingList items={visible} selectedId={selectedId} onSelect={setSelectedId} />
    </section>
  );
}
