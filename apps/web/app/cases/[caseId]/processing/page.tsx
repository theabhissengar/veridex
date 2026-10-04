"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProcessingStages } from "@/components/ProcessingStages";
import { api } from "@/lib/api";

export default function ProcessingPage() {
  const params = useParams<{ caseId: string }>();
  const [items, setItems] = useState<Array<Record<string, string | number | null>>>([]);
  const [error, setError] = useState("");

  async function start() {
    setError("");
    try {
      await api(`/api/v1/cases/${params.caseId}/investigations`, { method: "POST" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start");
    }
  }

  useEffect(() => {
    let stop = false;
    async function poll() {
      try {
        const payload = await api<{ items: Array<Record<string, string | number | null>> }>(`/api/v1/cases/${params.caseId}/processing`);
        if (!stop) setItems(payload.items);
      } catch (reason) {
        if (!stop) setError(reason instanceof Error ? reason.message : "Status unavailable");
      }
    }
    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [params.caseId]);

  return (
    <section className="space-y-3">
      <button className="rounded bg-stone-900 px-3 py-1 text-white" onClick={start}>
        Start investigation
      </button>
      {error ? <p className="text-red-700">{error}</p> : null}
      <ProcessingStages items={items} />
    </section>
  );
}
