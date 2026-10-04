# ADR 0002: One worker and a Postgres job table

## Status

Accepted

## Decision

The API and the worker are the same Python codebase. Compose runs `python -m veridex.worker`. Jobs are rows claimed with `SELECT … FOR UPDATE SKIP LOCKED`. There is no Redis, Celery, or second service.

## Consequences

Perception and reasoning stay in-process. A crashed job can remain `running` until an operator retries by starting a new investigation.
