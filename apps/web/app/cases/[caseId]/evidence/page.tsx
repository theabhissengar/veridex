"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { EvidencePlayer } from "@/components/EvidencePlayer";
import { EvidenceUploader } from "@/components/EvidenceUploader";
import { API_BASE, api } from "@/lib/api";

export default function EvidencePage() {
  const params = useParams<{ caseId: string }>();
  const [items, setItems] = useState<Array<Record<string, string>>>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function load() {
    const payload = await api<{ items: Array<Record<string, string>> }>(`/api/v1/cases/${params.caseId}/evidence`);
    setItems(payload.items);
  }

  useEffect(() => {
    load().catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  const current = items.find((item) => item.id === selected) || null;
  return (
    <section className="space-y-4">
      <EvidenceUploader caseId={params.caseId} onUploaded={load} />
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {items.length === 0 ? <p className="text-sm text-stone-600">No evidence uploaded.</p> : null}
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.id} className="rounded border bg-white p-3 text-sm">
            <button className="underline" onClick={() => setSelected(item.id)}>
              {item.role} · {item.original_filename} · {item.status}
            </button>
          </li>
        ))}
      </ul>
      {current?.kind === "video" ? <EvidencePlayer src={`${API_BASE}/api/v1/evidence/${current.id}/content`} timestampMs={0} bbox={null} /> : null}
      {current && current.kind !== "video" ? (
        <a className="text-sm underline" href={`${API_BASE}/api/v1/evidence/${current.id}/content`}>
          Open {current.original_filename}
        </a>
      ) : null}
    </section>
  );
}
