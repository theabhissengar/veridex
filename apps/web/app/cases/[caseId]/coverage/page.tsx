"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CoverageEditor } from "@/components/CoverageEditor";
import { api } from "@/lib/api";

export default function CoveragePage() {
  const params = useParams<{ caseId: string }>();
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  async function load() {
    const payload = await api<{ items: Array<Record<string, unknown>> }>(`/api/v1/cases/${params.caseId}/coverage`);
    setItems(payload.items);
  }

  useEffect(() => {
    load().catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  return (
    <section>
      {error ? <p className="text-red-700">{error}</p> : null}
      <CoverageEditor caseId={params.caseId} items={items} onChange={load} />
    </section>
  );
}
