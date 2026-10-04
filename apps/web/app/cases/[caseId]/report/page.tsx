"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ReportView } from "@/components/ReportView";
import { api } from "@/lib/api";

export default function ReportPage() {
  const params = useParams<{ caseId: string }>();
  const [markdown, setMarkdown] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ items: Array<{ id: string }> }>(`/api/v1/cases/${params.caseId}/investigations`)
      .then(async (list) => {
        const latest = list.items[0];
        if (!latest) return;
        const report = await api<{ markdown: string }>(`/api/v1/investigations/${latest.id}/report`);
        setMarkdown(report.markdown);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  return (
    <section>
      {error ? <p className="text-red-700">{error}</p> : null}
      <ReportView markdown={markdown} />
    </section>
  );
}
