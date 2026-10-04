import { CaseAssessmentBadge } from "@/components/Badges";

type CaseRow = { id: string; title: string; status: string; latest_assessment: string | null };

export function CaseList({ items }: { items: CaseRow[] }) {
  if (items.length === 0) return <p className="text-sm text-stone-600">No cases yet.</p>;
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.id} className="rounded border bg-white p-4">
          <a className="font-medium" href={`/cases/${item.id}`}>
            {item.title}
          </a>
          <div className="mt-2 flex gap-2 text-sm">
            <span>Status: {item.status}</span>
            <CaseAssessmentBadge value={item.latest_assessment} />
          </div>
        </li>
      ))}
    </ul>
  );
}
