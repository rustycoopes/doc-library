# Slice 4 — List/tiles view toggle, persisted

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** A user can switch `/doc-library` between list and tile layouts with an in-page
toggle, and their choice is remembered the next time they visit — from any device, since it's
stored server-side.

## What to build

- `user_preferences` table migration in the `doc_library` schema: `user_id` (UUID PK, FK
  `host.users.id`, `ON DELETE CASCADE`), `view_mode` (text/enum, `list` | `tiles`). No row exists
  until a user's first write (get-or-create), not created eagerly at registration.
- `ViewModePreference` schema and `PUT /api/v1/doc-links/preferences` JSON endpoint (full
  replace).
- `PUT /doc-library/fragments/view-mode` HTMX fragment route: toggles and persists `view_mode`,
  returns the grouped grid re-rendered in the new mode.
- Tile-view rendering for the grouped links (same grouping/ordering as list view — category then
  title — just a different layout per category group).
- `/doc-library` page reads the user's current `view_mode` (defaulting to `list` when no
  preference row exists yet) to decide initial rendering, with a toggle control wired to the
  fragment route above.

## Design notes

Implements the TDD's `user_preferences` schema and view-mode API/fragment design decisions. Get-
or-create logic mirrors `event_creator.user_settings`'s lazy-creation pattern (created on first
write, not at registration) referenced in the TDD and `host-integration-guide.md`'s Slice R2
interface contract.

## Blocked by

- Slice 3 (needs real `doc_links` data to render in both view modes — toggling an empty list isn't
  a meaningful test of the layout)

## Acceptance criteria

- [x] A first-time visitor (no preference row yet) sees list view by default.
- [x] Clicking the toggle switches the visible layout between list and tiles without a full page
      reload.
- [x] The chosen view mode persists across a full logout/login cycle and across a fresh browser
      session (server-side, not localStorage/cookie-only).
- [x] Tile view groups by category the same way list view does — same alphabetical ordering rules.
- [x] Unauthenticated requests to the view-mode endpoints return 401.
- [x] A user's view-mode preference is never visible to or settable by another user.

## Testing

HTTP-level, mirroring `event-creator`'s Settings-fragment tests
(`tests/test_settings_fragments.py`):

- `tests/test_preferences_api.py` — get-or-create path (no row yet → `list` default returned);
  persists and correctly reads back a changed value; 401 unauthenticated.
- `tests/test_doc_links_fragments.py` (extended from Slice 3) — view-mode toggle fragment route
  returns the correctly re-rendered partial for both modes.
- `tests/test_doc_library_page.py` (extended) — page reflects the persisted `view_mode` on load,
  including the never-set-yet default case.

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->

## Delivered

**Issue:** #4 · **Branch:** `feature/slice-4-view-mode-toggle` · **Date:** 2026-07-17

Shipped `doc_library.user_preferences` (migration `0003`, PK `user_id` FK `host.users.id`
`ON DELETE CASCADE`, `view_mode` `Text` with a `CHECK (view_mode IN ('list', 'tiles'))` for
defense-in-depth alongside the Pydantic `Literal["list", "tiles"]` validation on every route),
`get_view_mode`/`set_view_mode` query functions (`app/models/user_preference.py` — the latter an
atomic `INSERT ... ON CONFLICT DO UPDATE` so two concurrent first-writes for the same user can't
race into a duplicate-PK error), a pure JSON `PUT /api/v1/doc-links/preferences` endpoint, and an
HTMX `PUT /doc-library/fragments/view-mode` fragment route. `/doc-library` now reads the user's
persisted `view_mode` (defaulting to `list`) on load, and every mutation fragment
(create/edit/delete/toggle) re-renders in the currently persisted mode via a shared `_render_list`
helper, so a create/edit/delete never silently resets a tile-view user back to list. Tile-view
markup shares its per-link body (view link, edit disclosure, delete button) with list-view via a
new Jinja macro (`app/templates/partials/_doc_link_macros.html`) rather than duplicating it.

**Diverged from plan:** none — implemented per the TDD/WBS as written.

**Code review (code-review-master + code-quality-guardian):** no blockers; all suggestions were
minor/moderate and fixed inline before merge, none needed an Intake follow-up issue:
1. `set_view_mode` originally committed its own transaction, unlike every other mutation in this
   codebase (`app/models/doc_link.py`'s functions are commit-free; the route handler owns the
   transaction boundary). Fixed by moving `db.commit()` into the two callers
   (`app/api/v1/preferences.py`, `update_view_mode_fragment`).
2. Added the `CHECK` constraint noted above — the TDD describes `view_mode` as "text/enum," and
   the only prior guard was the Pydantic schema, which a direct-SQL write would bypass.
3. Tile-view category/title ordering wasn't actually exercised by any test with more than one
   category — added `test_tile_view_groups_categories_and_titles_alphabetically`.
4. The list-vs-tiles distinction in tests relied on brittle exact-Tailwind-class string matches.
   Added a `data-view-mode="{list|tiles}"` attribute on the swapped `#doc-links-list` div as a
   stable structural marker and switched the relevant assertions to use it, including a new
   `test_view_mode_fragment_returns_structurally_different_markup_per_mode`.
5. Added `test_view_mode_fragment_does_not_affect_another_users_preference` — the HTMX fragment
   route had no cross-user-isolation test of its own (only the JSON API did).
6. Factored the `ValidationError` → 422 conversion (duplicated three times across the create/edit/
   view-mode fragment handlers) into a shared `_as_422` helper in
   `app/pages/doc_links_fragments.py`.
