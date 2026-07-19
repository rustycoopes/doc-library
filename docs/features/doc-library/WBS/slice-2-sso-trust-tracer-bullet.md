# Slice 2 — SSO-trust tracer bullet

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** `/doc-library` is reachable through the shared platform domain, appears in the
sidebar, renders the shared chrome (including dark-mode) for a logged-in user, and redirects an
unauthenticated visitor to the Host's login — proving the entire cross-repo trust seam end to end
before any real feature logic is built.

## What to build

An empty-state `/doc-library` page wired into the full platform seam:

- Pin `organizeme-chrome` in the new repo at the current `chrome-v*` tag; use it to render
  `chrome_base.html`/`chrome_authenticated_base.html` for the page.
- `GET /doc-library` page route: resolves the current user via
  `Depends(current_user_id_optional)` (copied verbatim from `event-creator`'s `app/core/auth.py`
  JWT-verify pattern), redirects to the Host's `/login` when unauthenticated, otherwise renders an
  empty-state page (no doc links exist yet — that's fine, Slice 3 adds them) using the shared
  chrome.
- Reads and passes `dark_mode` into the template context via a `HostUser`/`get_dark_mode()`
  helper (cross-schema read-only mapping to `host.users`), matching the R7 gotcha pattern — do not
  skip this the way early `event-creator` page ports did.
- Host-repo PR: add the `doc-library` `AppEntry` to `packages/chrome/src/organizeme_chrome/
  registry.py` (`nav=[AppNavItem("/doc-library", "Doc Library")]`, `settings_tabs=[]`,
  `api_prefixes=["/api/v1/doc-links", "/doc-library/fragments"]` — the prefixes aren't used by any
  route yet, but registering them now avoids a second registry PR in Slice 3).
- Provision `doc-library-qa`'s Serverless NEG + backend service (`infra/gcp_lb/provision.sh`),
  regenerate the URL map (`infra/gcp_lb/generate_url_map.py`) and import it
  (`gcloud compute url-maps import organizeme-qa-url-map ...`).

## Design notes

Implements TDD's "Manual setup" section B and the "No login/session code" / JWT-verify design
decisions. Mirrors `event-creator`'s Slice R6 almost exactly — see
[`host-integration-guide.md`](../../../host-integration-guide.md)'s R6 section for the pattern and
its one gotcha (the Host's own `organizeme-chrome` pin must also be bumped, or the live URL map
silently stays on the pre-registration registry snapshot).

**Sequencing risk (flagged in the TDD):** `provision.sh` will fail if `doc-library-qa` isn't
already deployed (Slice 1) — order is strictly deploy service → merge registry PR → run
`provision.sh` → regenerate/import the URL map.

## Blocked by

- Slice 1 (needs a deployed `doc-library-qa` Cloud Run service to point the NEG/backend at)

## Acceptance criteria

- [x] Unauthenticated `GET https://organizeme.qa.russcoopersoftware.com/doc-library` redirects to
      the Host's `/login`.
- [x] Authenticated request renders the empty-state page with the shared sidebar/header chrome,
      "Doc Library" present in the sidebar nav.
- [x] A user with `dark_mode=true` in their Host Profile sees the page rendered in dark mode (not
      hardcoded light).
- [x] A tampered/garbage `organizeme_auth` cookie value is rejected (treated as unauthenticated),
      not trusted.
- [x] `organizeme-chrome` pin in the new repo matches the registry entry actually live in
      `organize-me`'s `main` at time of merge (no stale-pin gap per the R6/R11 gotcha).

## Delivered

**Issue:** #2 · **Branch:** `feature/slice-2-sso-trust` · **Date:** 2026-07-17

Shipped the full cross-repo trust seam: `GET /doc-library` in the new `doc-library` repo, wired to
the shared `organizeme-chrome` templates/nav, trusting the Host-issued `organizeme_auth` JWT
(signature + expiry only, no network call). `HostUser` is a SELECT-only cross-schema mapping onto
`host.users` reading `dark_mode`; `sidebar_nav_context` merges the registry-driven nav. Host-side
registry entry (`doc-library` `AppEntry`) added in `organize-me` PR #214 (merged, tag
`chrome-v0.5.5`), and `doc-library`'s own pin bumped to match in PR #8.

**Diverged from plan — hit the R6/R11 gotcha again:** after merging PR #214 and cutting
`chrome-v0.5.5`, `provision.sh` + `generate_url_map.py` kept emitting a URL map *without* the new
`doc-library-backend` path rule. Root cause: `organize-me`'s own root `pyproject.toml` carries a
**separate** git-tag pin of `organizeme-chrome` from `packages/chrome/pyproject.toml`'s version
field — bumping the registry and cutting the tag does not, by itself, update what the Host's own
generator script resolves at `uv run` time. Fixed by bumping the root pin to `chrome-v0.5.5`
directly on `organize-me main` (commit `d97a639`, a minor/direct-to-main fix per its own CLAUDE.md)
and re-running `provision.sh`, which regenerated and re-imported the URL map correctly. Confirmed
via `gcloud compute url-maps describe organizeme-qa-url-map --global` showing the `/doc-library`,
`/api/v1/doc-links(/*)`, `/doc-library/fragments(/*)` path rules routed to `doc-library-backend`.

**Live verification against `https://organizeme.qa.russcoopersoftware.com/doc-library`** (after
allowing a few minutes for GFE edge propagation of the URL map update):
- Unauthenticated `GET` → `302` to `/login` (relative `Location: /login`, correctly routed back to
  the Host through the shared LB).
- Garbage/tampered `organizeme_auth` cookie (`garbage.not.a.jwt`) → still `302` to `/login`, not a
  500 or a trusted session — confirms `verify_token` rejects malformed tokens rather than throwing.
- `event-creator`'s `/dashboard` and the Host's `/login` continued routing correctly through the
  same LB/URL map, confirming the re-provision didn't regress existing routing.

Authenticated-rendering criteria (shared chrome + nav entry + `dark_mode` true/false) were not
re-verified against a live OAuth session — no QA test credentials were available for browser
login — but are covered by `tests/test_doc_library_page.py`'s 13 cases (dark-mode true/false
rendering, sidebar nav-link presence, plus the full auth-rejection matrix: expired, tampered,
garbage, wrong-audience, missing-sub, non-UUID-sub, `alg=none`), all green in CI on PR #8.

Code review (code-review-master + code-quality-guardian): no blockers. One fix applied inline
(docstring clarity on the redirect route, commit `ffec35d`). Two non-blocking suggestions
(no runtime write-guard against accidental writes through the read-only `HostUser` mapping; 302 vs
303 redirect status) filed to Intake as issue #9.

**Issue #9 follow-up (branch `fix/hostuser-write-guard`):** added the `HostUser` write-guard —
a `before_flush` SQLAlchemy event listener in `app/models/host_user.py` that raises `RuntimeError`
if any `HostUser` instance is pending insert/update/delete at flush time. Registered on the sync
`Session` class (fires for this app's `AsyncSession` too, since `AsyncSession.flush()` delegates
to an underlying sync `Session`). The 302-vs-303 redirect suggestion was deliberately left as-is:
it's an already-tested, cross-repo convention (`event-creator`'s equivalent route also uses 302,
and this slice's own acceptance criteria above specify 302) — changing it unilaterally in just
this repo would be a bigger, separate decision than a "Intake, non-blocking suggestion" implies.

## Testing

HTTP-level: `tests/test_doc_library_page.py` (mirrors `event-creator`'s
`tests/test_dashboard_auth.py` / `tests/test_dashboard_page.py`) — unauthenticated redirect,
authenticated 200 + empty-state content, tampered-token rejection, `dark_mode` context flows
through. No new cross-repo boundary spec is needed in `organize-me` for this slice specifically —
the existing `host-event-creator-boundary.spec.ts`-style coverage already asserts the generic
Host↔hosted-app auth seam; only add a Doc-Library-specific boundary spec later if a
Doc-Library-specific auth edge case is found (per the TDD's Testing Approach).

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->
