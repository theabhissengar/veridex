export function Timeline({ items }: { items: Array<{ position: number; phase: string; summary: string }> }) {
  if (items.length === 0) return <p>No timeline yet.</p>;
  return (
    <ol className="space-y-2">
      {items.map((item) => (
        <li key={item.position} className="rounded border bg-white p-3 text-sm">
          {item.phase}: {item.summary}
        </li>
      ))}
    </ol>
  );
}
