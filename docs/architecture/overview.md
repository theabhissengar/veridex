# Architecture

The browser loads the Next.js UI and calls FastAPI. FastAPI stores metadata in PostgreSQL and bytes behind a storage port. A worker in the same codebase claims job rows.

An investigation run:

1. Snapshot order, claims, taxonomy and config versions, and final coverage.
2. Normalize media and record coverage signals. Suggestions never include `complete`.
3. Run detection, OCR, and shipping parsing. Keep raw model rows.
4. Aggregate accepted typed observations and build the phase timeline.
5. Generate investigation questions from the snapshot and those observations.
6. Freeze the question list.
7. Evaluate role outcomes and questions using final coverage only.
8. Write findings.
9. Compute the case assessment.
10. Write the deterministic report.

`not_observed` means the subject was not observed in the examined evidence. It does not mean the subject did not exist.
