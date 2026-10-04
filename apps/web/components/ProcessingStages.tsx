export function ProcessingStages({ items }: { items: Array<Record<string, string | number | null>> }) {
  if (items.length === 0) return <p>No processing jobs yet.</p>;
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <article key={String(item.id)} className="rounded border bg-white p-3 text-sm">
          <p>Stage: {item.stage}</p>
          <p>Status: {item.status}</p>
          <p>Progress: {item.progress}</p>
          {item.error ? <p>Error: {item.error}</p> : null}
        </article>
      ))}
    </div>
  );
}
