# ADR 0001: The browser calls FastAPI directly

## Status

Accepted

## Decision

Next.js serves the UI. The browser calls the FastAPI HTTP API using `NEXT_PUBLIC_API_BASE_URL`. V1 has no Next.js route handlers, rewrites, or server actions that proxy the API. FastAPI sends CORS headers for the web origin.

## Consequences

There is no backend-for-frontend. A proxy is a later change only if the browser must not hold a credential. V1 has no auth.
