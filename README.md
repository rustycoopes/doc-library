# Doc Library

An OrganizeMe hosted app — its own repo, own Cloud Run service(s), and own Postgres schema
(`doc_library`). Trusts the Host-issued JWT cookie for identity; never handles login, sessions,
or passwords itself. See `docs/how-to-add-a-hosted-app.md` for the platform pattern this repo
follows, and `CLAUDE.md` for how to work in this codebase.

## Setup

```
uv sync --group dev
```

Copy `.env.local.example` to `.env.local` (never commit `.env.local` — see `.gitignore`) and fill
in `DATABASE_URL`/`JWT_SECRET` for local development against the QA Supabase database.

**No `ENCRYPTION_KEY`.** Doc Library stores no third-party credentials (no OAuth tokens, no
storage-provider connections) — unlike `event-creator`, which uses it to encrypt stored
`storage_configs` rows. This is a deliberate omission per the TDD, not an oversight: don't add it
to `.env.local.example`, GitHub Actions secrets, or any `--set-secrets` flag by copying the
`event-creator` example.

## Running locally

```
uv run uvicorn app.main:app --reload --port 8000
```

## Tests

```
uv run pytest
uv run mypy app tests
```

## Migrations

```
uv run alembic revision --autogenerate -m "..."
uv run alembic upgrade head
```

## Deployment

CI/CD lives in `.github/workflows/ci.yml` (QA, on PR) and `.github/workflows/deploy.yml` (prod, on
push to `main`) — see `docs/host-integration-guide.md` and `docs/secrets-and-accounts.md` for the
manual setup (GitHub Actions secrets, GCP Secret Manager grants, Load Balancer registration) this
CI pipeline depends on.
