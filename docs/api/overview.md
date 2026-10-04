# HTTP API

Base path `/api/v1` on FastAPI. The browser calls this origin directly. Errors use `{ "detail": { "code", "message" } }`.

There is no Next.js copy of these routes.

Closed values include evidence role, party, kind, MIME type, dispute type, coverage, observation type, evidence state, and case assessment. Unknown values are rejected.
