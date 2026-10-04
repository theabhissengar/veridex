# Contributing

## Branches

`main` is the stable branch. `dev` is the integration branch. Create every new branch from `dev`.

```text
feature/<short-description>
bugfix/<short-description>
chore/<short-description>
refactor/<short-description>
test/<short-description>
docs/<short-description>
```

Examples: `feature/investigation-report`, `bugfix/coverage-evaluation`, `chore/update-ci`, `refactor/evidence-pipeline`, `test/question-evaluation`, `docs/architecture`.

Normal pull requests target `dev` and use a squash merge. Only `dev` is merged into `main`, and that pull request uses a merge commit. Do not open feature pull requests against `main`, and do not push directly to `dev` or `main`.

## Commits

Use a short prefix: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`.

## Pull requests

Describe the change and how you tested it. Required checks must pass, conversations must be resolved, and the branch must be up to date before merge.

Required checks, from the `CI` workflow:

- `backend`
- `frontend`
- `docker`

## Local checks

Backend, from `apps/api`, with PostgreSQL on port 5433 and FFmpeg installed:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Frontend, from `apps/web`:

```bash
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm build
```

Docker, from the repository root. This validates Compose and builds the images. It does not start the stack.

```bash
docker compose config --quiet
docker build -f infrastructure/docker/api.Dockerfile .
docker build -f infrastructure/docker/web.Dockerfile .
```

Playwright is a local end-to-end check. From `apps/web`, run `pnpm exec playwright test` only when the UI and API are already running. It is not a required CI check.
