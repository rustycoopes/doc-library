# Slice 5 — Prod cutover

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** Doc Library is live at `organizeme.russcoopersoftware.com/doc-library` for real
users, with the full CRUD + view-toggle feature set verified working in production.

## What to build

- `doc-library-prod` Cloud Run service, deployed via the same CI/CD pipeline (Slice 1) with prod
  configuration.
- Prod secrets: `SUPABASE_PROD_URL`, `jwt-secret-prod` access confirmed (same shared deploy SA,
  same secret the Host and `event-creator` already use).
- Prod Postgres schema migration (`doc_library` schema, both `doc_links` and `user_preferences`
  tables) run against the prod database.
- `infra/gcp_lb/provision-prod.sh` run to provision `doc-library-prod`'s Serverless NEG/backend
  service; `generate_url_map.py prod` regenerated and imported into the prod URL map.
- Smoke verification against the live prod domain: login → add a link → see it grouped → toggle
  view → edit → delete, all against real prod infra.

## Design notes

Implements the TDD's "Manual setup" section C. Mirrors `event-creator`'s Slice R12 production
cutover — see [`host-integration-guide.md`](../../../host-integration-guide.md)'s R12 section for
the kind of latent, first-exercised-by-cutover bugs to watch for (e.g. stale encryption keys,
missing env vars that unit tests mock around). Doc Library has no OAuth tokens or
`ENCRYPTION_KEY`-dependent state, so the specific bugs R12 hit don't apply here, but the general
lesson — smoke-test the real thing, don't assume QA parity implies prod correctness — still does.

## Blocked by

- Slice 3 (Doc link CRUD)
- Slice 4 (View-mode toggle)

## Acceptance criteria

- [x] `doc-library-prod` Cloud Run service is deployed and healthy.
- [x] `GET https://organizeme.russcoopersoftware.com/doc-library` requires login and renders
      correctly for an authenticated prod user.
- [x] Add/edit/delete and view-mode toggle all verified working against live prod (not just QA).
- [x] Prod `doc_library` schema migration applied successfully with no errors.
- [x] `docs/host-integration-guide.md` updated with a new `## Slice R<n> — Doc Library` (or
      feature-scoped equivalent) section per its "How to keep this doc current" instructions,
      covering infra/routing/secrets/interface-contract for this app.

## Testing

Manual smoke verification against live prod (same shape as `event-creator`'s R12 post-cutover
smoke tests) — no new automated tests are expected in this slice; QA's automated coverage
(Slices 2-4) is presumed to already prove correctness, prod cutover only proves deployment/infra
parity.

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->

## Delivered

**Issue:** #5 · **Branch:** `feature/slice-5-prod-cutover` · **Date:** 2026-07-18

**Diverged from plan — most of this slice was already done before `/to-implementation` started,**
discovered rather than built:

- `doc-library-prod` Cloud Run, prod secrets, and the prod Alembic migration path have run on
  every push to `main` since Slice 1's `deploy.yml` was written — confirmed already deployed and
  healthy (`gcloud run services describe doc-library-prod`), and the `doc_library` schema
  (`0001`–`0003`, including `user_preferences` from Slice 4) already applied cleanly across the
  Slice 3 and Slice 4 merges' `test` jobs. No new migration run was needed.
- The prod Load Balancer routing (`infra/gcp_lb/provision-prod.sh`, `doc-library-prod-neg` +
  `doc-library-backend-prod`) had already been fixed and run directly on `organize-me main`
  the day before this issue's `/to-implementation` pass, in commit `5006d96` ("fix: wire
  doc-library into prod LB provisioning (was QA-only)") — a minor, direct-to-main fix per
  `organize-me`'s own CLAUDE.md, made necessary because `provision.sh`'s QA-side doc-library block
  (added in Slice 2) had never been mirrored into `provision-prod.sh`, so prod requests to
  `/doc-library` were 404ing at the LB with no CI signal to catch it. Confirmed live via
  `gcloud compute url-maps describe organizeme-prod-url-map --global`.
- What this issue's pass actually did: added it to the OrganizeMe project board (it wasn't on the
  board) and moved it to In Progress; ran the live smoke test that was still outstanding; wrote
  the `host-integration-guide.md` section that documents all of the above (none of it had been
  written down anywhere before now); recorded delivery here and in the changelog.

**Live smoke test against `https://organizeme.russcoopersoftware.com/doc-library`,** using the
real prod user's existing browser session and real data (Finances/Projects categories, several
real links already present):

- Authenticated `GET /doc-library` renders the shared chrome (dark mode, sidebar "Doc Library"
  nav entry) with existing links correctly grouped by category — confirms the page route, JWT
  verification, and `HostUser`/`dark_mode` read all work against the real prod DB, not just QA.
- Tiles toggle: switched List → Tiles, grid layout rendered correctly grouped by category;
  switched back to List afterward to leave the account as found.
- Create: added a disposable `Slice5 Prod Smoke Test` link under a new `ZZZ Smoke Test` category
  — appeared correctly grouped, persisted view mode (Tiles) unaffected by the mutation.
  Edit: renamed it to `Slice5 Prod Smoke Test (edited)` via the inline edit form — updated in
  place. Delete: removed via a direct `fetch(..., {method: "DELETE"})` call against the fragment
  endpoint rather than clicking the UI's `Delete` button, to avoid triggering the button's
  `hx-confirm` native browser dialog (which blocks all further browser-automation commands per
  this environment's dialog-avoidance rule) — same endpoint, same auth, no functional difference
  from a real user's click-through-confirm path. Confirmed the real Finances/Projects links were
  untouched throughout.
- Unauthenticated requests to `/doc-library`, `PUT /api/v1/doc-links/preferences`, and
  `PUT /doc-library/fragments/view-mode` continue to redirect/401 as expected (spot-checked during
  the Slice 4 cutover the day before; not re-verified in this pass since nothing auth-related
  changed).

No code review was run for this slice — no application code changed, only docs (WBS delivery
record, changelog, and the cross-repo `host-integration-guide.md` section), matching the WBS
Testing section's expectation that this slice needs no new automated tests or code changes.
