"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export function CaseCreateForm({ onCreated }: { onCreated: () => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/cases", { method: "POST", body: JSON.stringify({ title }) });
      setTitle("");
      await onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the case");
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input className="flex-1 rounded border px-3 py-2" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Case title" required />
      <button className="rounded bg-stone-900 px-4 py-2 text-white" type="submit">
        Create case
      </button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </form>
  );
}
