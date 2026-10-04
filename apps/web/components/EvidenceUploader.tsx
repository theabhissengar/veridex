"use client";

import { FormEvent, useState } from "react";
import { API_BASE } from "@/lib/api";

const roles = ["packing_video", "unboxing_video", "product_photo", "invoice", "customer_statement", "seller_statement", "shipping", "order_file"];
const parties = ["seller", "customer", "carrier", "platform"];

export function EvidenceUploader({ caseId, onUploaded }: { caseId: string; onUploaded: () => Promise<void> }) {
  const [role, setRole] = useState("packing_video");
  const [party, setParty] = useState("seller");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    form.set("role", role);
    form.set("party", party);
    setError("");
    const response = await fetch(`${API_BASE}/api/v1/cases/${caseId}/evidence`, { method: "POST", body: form });
    if (!response.ok) {
      const payload = await response.json();
      setError(payload.detail?.message || "Upload failed");
      return;
    }
    await onUploaded();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2 rounded border bg-white p-4">
      <input name="file" type="file" required />
      <select value={role} onChange={(event) => setRole(event.target.value)} className="rounded border px-2 py-1">
        {roles.map((item) => (
          <option key={item}>{item}</option>
        ))}
      </select>
      <select value={party} onChange={(event) => setParty(event.target.value)} className="ml-2 rounded border px-2 py-1">
        {parties.map((item) => (
          <option key={item}>{item}</option>
        ))}
      </select>
      <textarea name="text_body" className="block w-full rounded border px-2 py-1" placeholder="Statement text, if this file is a statement" />
      <button className="rounded bg-stone-900 px-3 py-1 text-white" type="submit">
        Upload evidence
      </button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </form>
  );
}
