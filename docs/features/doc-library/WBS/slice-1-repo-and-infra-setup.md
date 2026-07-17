# Slice 1 — Repo & infra setup

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** A new `doc-library` repo whose CI/CD pipeline builds, tests, and deploys a minimal
FastAPI skeleton to its own QA Cloud Run service — with every secret and GitHub Actions
credential it will ever need for this feature already in place, before any real page or endpoint
exists.

## What to build

Stand up the `doc-library` repo and its deploy pipeline, with no Doc Library feature logic yet —
this is pure scaffolding so Slice 2 onward can focus entirely on the SSO-trust seam and feature
code, not on infra.

- New GitHub repo `doc-library`, FastAPI project skeleton (mirroring `event-creator`'s repo
  layout: `app/`, `tests/`, `migrations/`, `pyproject.toml`, `Dockerfile`, `.github/workflows/`)
  with a trivial health-check route and no other behavior yet.
- CI workflow (build → test → deploy) mirroring `event-creator`'s `.github/workflows/` shape,
  targeting a `doc-library-qa` Cloud Run service.
- GitHub Actions secrets set in the new repo: `GCP_SA_KEY` (copied from the existing shared
  deploy service account — no new GCP SA needed), `SUPABASE_QA_URL`, `SUPABASE_PROD_URL`.
- Confirm (don't recreate) that the shared deploy SA already has `secretmanager.secretAccessor` on
  `jwt-secret-{qa,prod}` — it does today since every service shares one deploy SA.
- Explicitly confirm and document that `ENCRYPTION_KEY` is **not** needed for this app (no
  third-party credentials stored) — a deliberate omission, not an oversight, per the TDD.
- Own Postgres schema (`doc_library`) created in the shared Supabase instance, with its own
  Alembic history (`version_table_schema=doc_library`) — no tables yet, just the schema and
  migration scaffolding wired up.
- Confirm the `doc_library` migration role has `REFERENCES` privilege on `host.users` (TDD Open
  Question #2) — extend the R1 grant mechanism if it doesn't.

## Design notes

Implements TDD's "Manual setup — repo, secrets, infra" section A (steps 1-6). See
[`host-integration-guide.md`](../../../host-integration-guide.md)'s manual-steps checklist and
[`how-to-add-a-hosted-app.md`](../../../how-to-add-a-hosted-app.md) for the general pattern this
follows — this slice does *not* yet touch the Host repo's registry or the Load Balancer (that's
Slice 2's job); it only needs the service reachable at its own `*.run.app` URL for smoke-testing.

## Blocked by

None — can start immediately.

## Acceptance criteria

- [x] `doc-library` repo exists with a working CI/CD pipeline (build, test, deploy stages all
      green).
- [x] A deploy of the skeleton app succeeds and the health-check route responds at the Cloud
      Run `*.run.app` URL for `doc-library-qa`.
- [x] `GCP_SA_KEY`, `SUPABASE_QA_URL`, `SUPABASE_PROD_URL` are set as GitHub Actions secrets in
      the new repo (not inherited from the Host repo).
- [x] `doc_library` Postgres schema exists with its own independent Alembic history
      (`version_table_schema=doc_library`), verified by running an empty migration successfully.
- [x] `doc_library`'s migration role has confirmed `REFERENCES` privilege on `host.users`.
- [x] `ENCRYPTION_KEY` is confirmed unnecessary and explicitly noted as such in the new repo's own
      setup docs (e.g. its README or an equivalent doc), not silently omitted.

## Testing

Infra/CI verification, not application-level tests: a green CI run on the new repo is the
acceptance signal for the pipeline; a successful `alembic upgrade head` against QA (creating no
tables yet) verifies the schema/migration-history setup. No unit or HTTP-level tests are
meaningful yet since there's no feature code — `tests/test_health.py` (a trivial 200-OK check,
matching `event-creator`'s own `tests/test_health.py`) is the only test this slice needs.

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->

## Delivered (2026-07-17, issue #1, branch `feature/slice-1-infra-finish`)

The initial repo scaffold (app skeleton, CI/CD workflows, GitHub Actions secrets) had already
landed directly on `main` via `/new-hosted-app` (commit 817fbe3) before this issue's
`/to-implementation` pass started; this slice's work was finishing the remaining acceptance
criteria on top of that scaffold:

- Added the missing `uv.lock` — the scaffold commit omitted it, which broke `uv sync --frozen` in
  both CI and the Dockerfile and caused the first `Deploy` run on `main` to fail outright.
- Added `migrations/versions/0001_create_doc_library_schema.py`: creates the `doc_library`
  schema, a `doc_library_app` role, and the R1-pattern `REFERENCES`-only grant on `host.users`
  (TDD Open Question #2) — confirmed against organize-me's own R1 migration
  (`d4e5f6a7b8c9_schema_separation_host_event_creator.py`) as the source of the grant pattern.
  Unlike `event-creator`'s baseline migration (a no-op adopting tables already moved by
  organize-me's R1), this is real DDL since `doc_library` never existed in any monolith.
- **Diverged from plan:** hit a chicken-and-egg bug not anticipated in the WBS — Alembic creates
  its own version table in `version_table_schema` *before* running the first migration, so on a
  brand-new database `alembic upgrade head` failed with `InvalidSchemaNameError: schema
  "doc_library" does not exist` even though migration 0001 itself creates that schema. Fixed by
  having `migrations/env.py` run `CREATE SCHEMA IF NOT EXISTS doc_library` before configuring the
  Alembic context, ahead of any migration.
- **Diverged from plan:** the `doc-library` GCP Artifact Registry repo didn't exist yet (only
  `event-creator` and `organizeme` did), so the first `deploy-qa` run failed at `docker push` with
  `Repository "doc-library" not found`. Created it manually
  (`gcloud artifacts repositories create doc-library ...`, Docker format, same region as the
  others) — not called out as a manual step in the TDD's playbook, worth adding there.
- Added `.env.local.example` and documented in the README that `ENCRYPTION_KEY` is deliberately
  unneeded (no third-party credentials stored) — matches TDD manual-setup step A.5.
- Removed a stray `ENCRYPTION_KEY` GitHub Actions secret that had been set on the repo by the
  scaffold step (unused anywhere in code/workflows) to keep the secret set consistent with "no
  `ENCRYPTION_KEY`" being a deliberate, documented choice rather than a silent leftover.
- Added `github-sa-key.json` / `*-sa-key.json` to `.gitignore` — a local SA-key file used to seed
  `GCP_SA_KEY` was sitting untracked in the repo root, one `git add -A` away from being committed.

All six acceptance criteria verified: CI green (test + deploy-qa) on PR #6, `GET
https://doc-library-qa-n7cbjtsj5a-nn.a.run.app/health` → `200 {"status": "ok"}`, all three
GitHub Actions secrets confirmed present, `doc_library` schema/Alembic history confirmed via the
CI `alembic upgrade head` step, `REFERENCES` grant confirmed via migration 0001, `ENCRYPTION_KEY`
omission documented in the README, and the shared deploy SA's `secretmanager.secretAccessor`
grant on `jwt-secret-{qa,prod}` confirmed via `gcloud secrets get-iam-policy`.

Code review (code-review-master + code-quality-guardian) found no blocking issues; three
non-blocking hardening/cleanup suggestions were filed as issue #7 (`modelsuggested` label) rather
than actioned in this slice.
