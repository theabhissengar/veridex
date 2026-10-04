"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Timeline } from "@/components/Timeline";
import { api } from "@/lib/api";

export default function TimelinePage() {
  const params = useParams<{ caseId: string }>();
  const [items, setItems] = useState<Array<{ position: number; phase: string; summary: string }>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Array<{ id: string }> }>(`/api/v1/cases/${params.caseId}/investigations`)
      .then(async (list) => {
        if (!list.items[0]) return;
        const timeline = await api<{ items: Array<{ position: number; phase: string; summary: string }> }>(
          `/api/v1/investigations/${list.items[0].id}/timeline`,
        );
        setItems(timeline.items);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  return (
    <section>
      {error ? <p className="text-red-700">{error}</p> : null}
      <Timeline items={items} />
    </section>
  );
}
