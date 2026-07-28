# Slice 3 — Doc link CRUD (list view only)

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** A logged-in user can add, view, edit, and delete their own document links — each
with a title, URL, and freeform category — and see them grouped by category, alphabetically
ordered, on `/doc-library`. This is the feature's core value, fully usable end to end (list view
only; tile view arrives in Slice 4).

## What to build

- `doc_links` table migration in the `doc_library` schema: `id` (UUID PK), `user_id` (UUID, FK
  `host.users.id`, `ON DELETE CASCADE`), `title`, `url`, `category` (all `text`, not null),
  `created_at`.
- A single query function (e.g. `app/models/doc_link.py`'s `list_grouped_by_category(db,
  user_id)`) that fetches a user's links ordered `category, title` and groups them in Python — no
  dedicated service layer, per
  [ADR: no dedicated service layer](../../../adr/doc-library-service-layer.md).
- Pydantic schemas: `DocLinkCreate`, `DocLinkUpdate` (partial, no field is ever nulled),
  `DocLinkResponse` — URL validated as `http`/`https` with a non-empty host; title/category
  required and trimmed non-empty.
- Pure JSON API (`/api/v1/doc-links`): `GET` (list), `POST` (create, 201), `PATCH /{id}` (edit,
  200), `DELETE /{id}` (204). Every operation scopes to `Depends(current_user_id)`; an id that
  isn't the requester's own returns 404, never 403.
- HTML fragment routes (`/doc-library/fragments/links`, HTMX-driven, per
  [ADR: HTMX fragments over a JSON-driven frontend](../../../adr/doc-library-htmx-rendering.md)):
  create/edit/delete each return the re-rendered grouped-list partial. Same underlying query/CRUD
  functions as the JSON API — thin route-handler duplication only.
- `/doc-library` page now renders real content: grouped-by-category list of the user's links (or
  the existing empty state if they have none), with inline add/edit/delete controls wired to the
  fragment routes.

## Design notes

Implements the TDD's Schema, API surface, Pydantic schemas, and Layering design decisions in full
for `doc_links` (the `user_preferences`/view-toggle half is Slice 4). See the TDD's Component/Data
Flow diagram for the create-link request sequence.

## Blocked by

- Slice 2 (needs the authenticated `/doc-library` page and JWT-trust seam already working)

## Acceptance criteria

- [x] A user can add a link (title, URL, category) and see it appear on `/doc-library`, grouped
      under its category.
- [x] Categories and links within a category render alphabetically, with no manual ordering
      control.
- [x] A user can edit a link's title/URL/category and see the change reflected immediately.
- [x] A user can delete a link and it disappears immediately.
- [x] Submitting an empty title, empty category, or a non-`http(s)` URL is rejected with a clear
      error, both client-side and server-side. **Partial:** server-side rejection is complete for
      all three; client-side, `required`/`minlength` correctly block empty title/category, but the
      `<input type="url">` browser-native check doesn't itself constrain the scheme to http(s) —
      tracked as a follow-up in Intake issue #11.
- [x] A user cannot view, edit, or delete another user's links — attempting to (e.g. guessing an
      id) returns 404.
- [x] Unauthenticated requests to any `/api/v1/doc-links*` or fragment route return 401.
- [x] No cap on the number of links a user can add.
- [x] Deleting the owning Host user cascades and removes their `doc_links` rows (cross-schema `ON
      DELETE CASCADE`).

## Testing

HTTP-level (`httpx.AsyncClient` + real async test Postgres session), mirroring `event-creator`'s
`tests/test_events_api.py`:

- `tests/test_doc_links_api.py` — 401 unauthenticated; ownership scoping (404 on another user's or
  a nonexistent id, never 403); create/update validation (malformed URL, empty title/category);
  delete removes the row.
- `tests/test_doc_links_fragments.py` — HTMX partial routes return the expected re-rendered
  fragment HTML for create/edit/delete.
- `tests/test_doc_library_page.py` (extended from Slice 2) — grouped/ordered rendering with real
  data, empty state still renders correctly with zero links.
- `tests/test_doc_link_model.py` — DB-level `ON DELETE CASCADE` test against `host.users`,
  matching the R10 pattern (`event-creator`'s `test_event_model.py`).

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->

## Delivered

**Issue:** #3 · **Branch:** `feature/slice-3-doc-link-crud` · **Date:** 2026-07-17

Shipped the feature's core value end to end: `doc_library.doc_links` (migration `0002`, FK to
`host.users.id` `ON DELETE CASCADE`), `list_grouped_by_category`/`get_owned_doc_link` query
functions (no dedicated service layer, per the TDD's layering decision), Pydantic
`DocLinkCreate`/`DocLinkUpdate`/`DocLinkResponse` schemas, a pure JSON `/api/v1/doc-links` CRUD
surface, and HTMX fragment routes under `/doc-library/fragments/links` — both surfaces calling the
same underlying functions, thin route-handler duplication only. `/doc-library` now renders the
user's links grouped by category with an inline add form and per-link inline edit (native
`<details>` disclosure — no extra GET-edit route needed) and delete controls.

**Diverged from plan:**
- The fragment routes deliberately return **401** on an unauthenticated request (via
  `Depends(current_user_id)`), not the 200-with-reauth-prompt pattern `event-creator`'s
  Settings-shell fragments use — those are eagerly loaded on page load and need a renderable
  fallback; these fragments are only ever reached via a user-initiated action on an
  already-authenticated page, and the WBS acceptance criteria explicitly call for 401.
- Inline edit uses a native `<details>`/`<summary>` disclosure already present in the DOM rather
  than a dedicated `GET .../edit` fragment route (not in the original TDD's route list) — avoids
  an extra round trip and any hand-written JS, at the cost of always rendering the edit form
  markup even when collapsed.

**Code review (code-review-master + code-quality-guardian):** two blockers found and fixed before
merge:
1. `DocLinkUpdate`'s field validators short-circuited on `None` to distinguish "field omitted"
   from "field supplied," which also let an explicit JSON `null` through unvalidated — `PATCH
   {"title": null}` passed Pydantic validation, then raised an unhandled `IntegrityError` (500) on
   commit against the NOT NULL column. Fixed: validators now reject `None` outright, relying on
   Pydantic only invoking a field's validator when that field is actually present in the input.
2. `app/models/doc_link.py`'s `user_id` column had no `index=True`, but the migration hand-creates
   `ix_doc_links_user_id` — since the model is what Alembic autogenerate diffs against, the next
   autogenerate run would have proposed dropping an index that actually exists. Fixed by adding
   `index=True` to match.

Also fixed as part of the same round: a fragment-route 422 that embedded pydantic's raw
`ValueError` in the JSON `ctx` field (not serializable, 500'd instead of returning a clean 422);
added PATCH-side validation test coverage on both the JSON API and fragment routes (previously
only tested on create); capped `url`'s max length; aligned `ondelete` casing between the model and
migration.

Seven non-blocking suggestions (HTMX 422s being invisible to the user without JS error-handling,
`type="url"` not enforcing an http(s) scheme client-side, a duplicated query in the JSON API's
list endpoint, missing form `<label>`s, no SRI on the htmx CDN script, case-sensitive category
grouping, a few over-length lines) filed to Intake as issue #11.

**Live-verified** against `https://organizeme.qa.russcoopersoftware.com` post-deploy: unauthenticated
`GET /api/v1/doc-links` and `POST /doc-library/fragments/links` both return 401 through the shared
LB.

## Delivered — Issue #11 follow-up

**Issue:** #11 · **Branch:** `fix/slice-3-review-followups` · **Date:** 2026-07-28

Closed out 5 of the 7 non-blocking suggestions filed above:

1. **HTMX 422s now visible.** `app/pages/doc_links_fragments.py`'s create/edit fragment routes
   render a validation failure as the shared `alert(variant="danger")` component
   (`partials/_form_error.html`, status 422) instead of a bare `HTTPException`. Both the add-link
   form (`doc_library.html`) and every doc link's inline edit form
   (`_doc_link_macros.html`'s `doc_link_edit_form`) got a `<div data-form-error class="hidden">`
   slot plus `hx-on::response-error="docLibraryShowFormError(event, this)"`, wired to a single
   named function defined once in `doc_library.html`'s head block (not duplicated per-form
   instance). The add form's existing `hx-on::after-request` reset handler now also re-hides the
   error slot on a subsequent successful submit, so a stale error from an earlier failed attempt
   doesn't linger after the user fixes it and resubmits.
2. **URL scheme now enforced client-side.** Both URL inputs got
   `pattern="https?://.+" title="Must start with http:// or https://"` via the shared `input()`
   macro's `attrs=` escape hatch.
3. **Duplicated query removed.** `app/models/doc_link.py` gained `list_for_user(db, user_id)`;
   `list_grouped_by_category` and the JSON API's `GET /doc-links`
   (`app/api/v1/doc_links.py`) both call it instead of each hand-building the same
   `WHERE`/`ORDER BY`.
5. **SRI added** to the htmx CDN `<script>` tag — sha384 computed from the actual served file and
   cross-checked against jsdelivr's own published package-metadata hash for the same file.
7. **Line-length cleanup** fell out of #1 and #3's refactors — verified no line in the three
   originally-flagged files exceeds ~100 chars.

**Not changed:**
- Item 4 (missing `<label>`s) needed no code change — the shared `input()` component
  (`organizeme_chrome`) already renders a `<label for=...>` for every field; verified directly
  against the vendored template and confirmed no call site opts out.
- Item 6 (case-sensitive category grouping) is left as-is, per the issue's own framing as a
  product decision for a later slice rather than a bug.

**Diverged from plan:** the code-review pass (code-review-master + code-quality-guardian) on this
branch caught two real defects in the first pass at item 1 before merge — fixed in the same
branch, not filed separately: the error banner used the `field_error` component (meant for a
single field's own `aria-describedby`) instead of `alert` (the form/page-level banner primitive,
with `role="alert"` already baked in and no field to tie to); and a hard-coded `id="form-error"`
on that banner would have collided if the add form and an edit form both showed an error at once
— fixed by switching to `alert()` without an `id` (it's optional there). Both fixes verified live
in a browser against a locally seeded user, alongside the stale-banner fix.

One further suggestion from that same review pass — the create/edit fragment routes only catch
`pydantic.ValidationError`, not FastAPI's own `RequestValidationError` from `Form(...)` parsing
(reachable only via a non-browser client sending a malformed request body, never through the
actual UI, since all three fields are HTML `required`) — filed to Intake as issue #35 rather than
expanding this branch's scope.
