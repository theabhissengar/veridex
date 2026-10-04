export function QuestionList({ items }: { items: Array<Record<string, string>> }) {
  if (items.length === 0) return <p className="text-sm text-stone-600">Questions are frozen after observation aggregation. None are stored yet.</p>;
  const counts: Record<string, number> = {};
  for (const item of items) {
    const status = item.evaluation_status || "pending";
    counts[status] = (counts[status] || 0) + 1;
  }
  return (
    <section className="rounded border bg-white p-4">
      <h2 className="font-medium">Investigation questions</h2>
      <p className="text-sm text-stone-600">{Object.entries(counts).map(([status, count]) => `${status}: ${count}`).join(" · ")}</p>
      <ul className="mt-2 space-y-1 text-sm">
        {items.map((item) => (
          <li key={item.question_key}>
            {item.question_key} · {item.evaluation_status || "not evaluated"}
          </li>
        ))}
      </ul>
    </section>
  );
}
