"use client";

import { useEffect, useState } from "react";
import { CaseCreateForm } from "@/components/CaseCreateForm";
import { CaseList } from "@/components/CaseList";
import { API_BASE, api } from "@/lib/api";

type CaseRow = { id: string; title: string; status: string; latest_assessment: string | null };

export default function HomePage() {
  const [items, setItems] = useState<CaseRow[]>([]);
  const [health, setHealth] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const payload = await api<{ items: CaseRow[] }>("/api/v1/cases");
    setItems(payload.items);
  }

  useEffect(() => {
    load().catch((reason: Error) => setError(reason.message));
    fetch(`${API_BASE}/health`)
      .then((response) => response.json())
      .then((payload) => setHealth(payload.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <div className="space-y-6">
      <p className="text-sm text-stone-600">API health: {health || "checking"}</p>
      <CaseCreateForm onCreated={load} />
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <CaseList items={items} />
      <a className="text-sm underline" href="/eval">
        Evaluation
      </a>
    </div>
  );
}
