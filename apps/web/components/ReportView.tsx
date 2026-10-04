export function ReportView({ markdown }: { markdown: string }) {
  return (
    <section className="space-y-3">
      <p className="text-sm text-stone-600">
        Final coverage is how completely a reviewer says this source shows the event. Suggested coverage is the automatic hint. Observation strength is how stable the grouped detections are. Detector confidence is one model&apos;s score on one frame. Case assessment is whether the applicable questions form a consistent account.
      </p>
      {markdown ? <pre className="whitespace-pre-wrap rounded border bg-white p-4 text-sm">{markdown}</pre> : <p>No report yet.</p>}
    </section>
  );
}
