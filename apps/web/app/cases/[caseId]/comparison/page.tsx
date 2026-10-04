"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ComparisonTable } from "@/components/ComparisonTable";
import { api } from "@/lib/api";

export default function ComparisonPage() {
  const params = useParams<{ caseId: string }>();
  const [expected, setExpected] = useState<Array<Record<string, string | number>>>([]);
  const [observed, setObserved] = useState<Array<Record<string, string | number>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Array<{ id: string }> }>(`/api/v1/cases/${params.caseId}/investigations`)
      .then(async (list) => {
        if (!list.items[0]) return;
        const detail = await api<{
          expected_snapshot: Array<Record<string, string | number>>;
          observed_snapshot: Array<Record<string, string | number>>;
        }>(`/api/v1/investigations/${list.items[0].id}`);
        setExpected(detail.expected_snapshot || []);
        setObserved(detail.observed_snapshot || []);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  return (
    <section>
      {error ? <p className="text-red-700">{error}</p> : null}
      <ComparisonTable expected={expected} observed={observed} />
    </section>
  );
}
