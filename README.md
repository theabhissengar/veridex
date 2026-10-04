# Veridex

AI-powered evidence investigation. Veridex reconstructs what available evidence shows in an e-commerce package dispute. It does not decide who is responsible.

The browser loads the Next.js UI and calls the FastAPI API directly. A worker in the same Python codebase processes media.

## Run

```bash
docker compose up --build
```

The UI is at http://localhost:3000 and the API is at http://localhost:8000.

Detector weights are not included. A run that needs detection fails with `weights_missing` until `weights/yolo.pt` is configured. The UI does not invent detections. Tests inject a stub detector.

`VERIDEX_ALLOW_UNREVIEWED_MODEL=1` is set in Compose for local prototyping only. Model licenses are not assumed. See `docs/ml/models.md`.

## Tests

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

API tests need PostgreSQL. `docker compose up postgres` then:

```bash
$env:VERIDEX_DATABASE_URL="postgresql+psycopg://veridex:veridex@localhost:5433/veridex"
pytest tests/test_api.py
```

## Layout

- `apps/web` — Next.js UI
- `apps/api` — FastAPI, worker, and investigation rules
- `packages/contracts` — JSON Schemas
- `dataset` — fixtures, development, and held-out evaluation tiers
- `docs/adr` — architecture decisions
