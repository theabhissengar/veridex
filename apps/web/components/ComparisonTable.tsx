export function ComparisonTable({
  expected,
  observed,
}: {
  expected: Array<Record<string, string | number>>;
  observed: Array<Record<string, string | number>>;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Expected items</h2>
        {expected.length === 0 ? <p className="text-sm">No order snapshot.</p> : null}
        {expected.map((item) => (
          <p key={String(item.canonical_class)} className="text-sm">
            {item.canonical_class} quantity {item.quantity}
          </p>
        ))}
      </div>
      <div className="rounded border bg-white p-4">
        <h2 className="font-medium">Observed item estimates</h2>
        {observed.length === 0 ? <p className="text-sm">No accepted object observations.</p> : null}
        {observed.map((item) => (
          <p key={String(item.canonical_class)} className="text-sm">
            {item.canonical_class}: Estimated observed quantity: {item.observed_quantity_estimate} (quantity strength: {item.quantity_strength})
          </p>
        ))}
      </div>
    </div>
  );
}
