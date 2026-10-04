"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CaseAssessmentBadge } from "@/components/Badges";
import { QuestionList } from "@/components/QuestionList";
import { api } from "@/lib/api";

export default function CaseOverview() {
  const params = useParams<{ caseId: string }>();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [claims, setClaims] = useState<Array<Record<string, string>>>([]);
  const [questions, setQuestions] = useState<Array<Record<string, string>>>([]);
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Record<string, unknown>>(`/api/v1/cases/${params.caseId}`)
      .then(async (payload) => {
        setData(payload);
        const claimRows = await api<{ items: Array<Record<string, string>> }>(`/api/v1/cases/${params.caseId}/claims`);
        setClaims(claimRows.items);
        const investigations = (payload.investigations as Array<{ id: string }>) || [];
        if (!investigations[0]) return;
        const detail = await api<{ questions: Array<Record<string, string>> | null; assessment_rationale: string }>(
          `/api/v1/investigations/${investigations[0].id}`,
        );
        setQuestions(detail.questions || []);
        setRationale(detail.assessment_rationale || "");
      })
      .catch((reason: Error) => setError(reason.message));
  }, [params.caseId]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading the case.</p>;
  return (
    <section className="space-y-4">
      <div className="space-y-3 rounded border bg-white p-4">
        <h1 className="text-xl font-semibold">{String(data.title)}</h1>
        <p>Processing status: {String(data.status)}</p>
        <p>Claimed dispute: {String(data.claimed_dispute_type || "none recorded")}</p>
        <CaseAssessmentBadge value={(data.latest_assessment as string) || null} />
        {rationale ? <p className="text-sm">{rationale}</p> : null}
      </div>
      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Claims</h2>
        {claims.length === 0 ? <p className="text-sm">No claims.</p> : null}
        {claims.map((claim) => (
          <p key={claim.id} className="text-sm">
            {claim.party}: {claim.claim_type} {claim.canonical_class || ""}
          </p>
        ))}
      </div>
      <QuestionList items={questions} />
    </section>
  );
}
