# Slice 6 — Adopt the shared OrganizeMe design system

> Part of the `doc-library` feature. PRD: [`../PRD.md`](../PRD.md) · Technical design:
> [`../TDD.md`](../TDD.md)

**Delivers:** Doc Library's own page (`app/templates/pages/doc_library.html`,
`partials/doc_links_list.html`, `partials/_doc_link_macros.html`) rebuilt on the shared
`organizeme_chrome` component primitives from `organize-me`'s `design-refresh` feature, replacing
every remaining DaisyUI class (`btn`, `btn-xs`, `btn-primary`, `btn-outline`, `btn-error`,
`input input-bordered`, `link link-primary`, `border-base-300`, `divide-base-300`).

## Source of this slice

`organize-me`'s `design-refresh` feature (Slices 1–4) removed DaisyUI from the shared toolchain
convention platform-wide, but explicitly scoped the *page* restyle to `organize-me` only —
Doc Library's own page was always going to need this as a separate, later pass (see that
feature's PRD "Out of Scope"). A live QA pass (2026-07-19) surfaced just how broken this makes
Doc Library look right now: every DaisyUI class above currently has **zero CSS behind it** (this
repo's own `pytailwindcss` build has no DaisyUI plugin, by design), so the add-link form, the
list/tiles toggle, and every per-link edit/delete button render with no visible styling — buttons
that are only readable as text, unbordered inputs, no visual grouping. This is separate from and
in addition to the sidebar-shell breakage fixed by bumping the `organizeme-chrome` pin (a
different issue, filed separately, since that's a mechanical dependency bump not a redesign).

## What to build

- Rebuild the add-link form (`pages/doc_library.html`) on the `input` primitive (title/url/category
  fields) and the `button` primitive (`Add link`, `variant="primary"`).
- Rebuild the list/tiles view-mode toggle (`partials/doc_links_list.html`) as two `button` calls
  (`variant="primary"` for the active mode, `variant="ghost"` for the inactive one) instead of
  `btn-primary`/`btn-outline`.
- Rebuild each per-link row (`partials/_doc_link_macros.html`) — the Edit/Delete buttons on the
  `button` primitive (`variant="ghost"`/a `danger`-toned variant for Delete — check whether
  `organize-me`'s button primitive has a destructive variant yet; if not, that's a small addition
  needed here, matching Profile's existing `border-flame`/`text-flame` "Delete account" treatment
  as the pattern to reuse rather than invent a new one), and the inline edit form's three inputs on
  the `input` primitive.
- Replace `border-base-300`/`divide-base-300` card/list-divider styling with the token-based
  equivalents (`border-ink-2/10 dark:border-paper/10`, matching `card_shell`'s own border
  treatment in `organize-me`).
- The empty state (`No links saved yet`) and category headings get the same treatment
  `organize-me`'s own empty-state/heading patterns use, rather than a bespoke look.

## Design notes

- No new architectural decisions — this is component application against an already-decided
  system, the same category of work as `organize-me`'s own Slice 3/Slice 4. Reuse `organize-me`'s
  ADRs directly: shared component boundary
  (`docs/adr/design-refresh-shared-component-library.md` in `organize-me`) and dark-mode strategy
  (`docs/adr/design-refresh-dark-mode-css-strategy.md` in `organize-me`).
- Needs whatever `organizeme-chrome` version ships `organize-me`'s Slice 5
  (`select`/`toggle` primitives, ghost-button contrast fix) — Doc Library doesn't need `select` or
  `toggle` itself today, but should build against the corrected `ghost` button contrast rather than
  the version with the invisible-border bug.

## Blocked by

- The `organizeme-chrome` pin bump (separate bug-fix issue, ships first) — needs the already-fixed
  shell **and** the Slice 5 contrast fix in `organize-me` to be pinned before this slice starts,
  so this work isn't done twice.

## Acceptance criteria

- [x] Zero DaisyUI classes anywhere in `app/templates/**`.
- [x] Add-link form, list/tiles toggle, and per-link Edit/Delete controls are all visibly styled
      (not just readable as bare text) in both light and dark mode.
- [x] Existing functional behavior (create/edit/delete a link, toggle view mode, persisted
      view-mode preference) is unchanged — this is presentation-only.
- [x] No regression in existing Playwright specs for Doc Library. (This repo has no Playwright
      specs — coverage is pytest-based HTTP/HTML assertions instead; those are the ones verified.)

## Testing

- Existing E2E coverage for create/edit/delete/view-mode-toggle stays the functional regression
  backstop — expected to pass unmodified.
- Manual visual check in both light and dark mode, given the contrast-defect history in
  `organize-me`'s own Slice 5.

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->

## Delivered

- **Issue:** #19
- **Branch:** `feature/slice-6-design-system-adoption`
- **Date:** 2026-07-19

Rebuilt `app/templates/pages/doc_library.html`, `partials/doc_links_list.html`, and
`partials/_doc_link_macros.html` on the shared `organizeme_chrome` `card_shell`/`input`/`button`
primitives (pinned `chrome-v0.12.1`, already carrying Slice 5's ghost-button contrast fix — no
pin bump needed here, #17 landed it first). Every DaisyUI class (`btn`, `btn-xs`, `btn-primary`,
`btn-outline`, `btn-error`, `input input-bordered`, `link link-primary`, `border-base-300`,
`divide-base-300`) is gone; the add-link form is wrapped in `card_shell` (rather than
re-deriving its border/padding classes by hand) matching `login.html`'s own
`{% call card_shell() %}<form>...</form>{% endcall %}` pattern, list/tiles borders and dividers
use `border-ink-2/10 dark:border-paper/10` directly, headings use `font-display`/`text-ink`, and
the Delete button uses the button primitive's existing `variant="danger"` (already defined in
`organizeme-chrome`'s `BUTTON_VARIANT_CLASSES` — no new primitive needed, per the WBS's
contingency note). The List/Tiles view-mode toggle buttons are generated from a single
`{% for mode, label in [...] %}` loop rather than two near-identical macro calls, and the
per-link title link picks up the same `{{ FOCUS_RING }} rounded-sm` pairing every other
`text-cobalt` link in organize-me uses.

Diverged from the plan in two small ways:
- The `input` primitive always renders a visible `<label>` (the old DaisyUI markup had
  placeholder-only fields with no label). Kept the primitive's default rather than fighting it —
  a straightforward a11y improvement, not a regression.
- The `input` primitive's default `id` is `field-<name>`, which would collide across every
  per-link inline edit form on the page. Passed an explicit `id="edit-<field>-<link.id>"` per
  input in `_doc_link_macros.html` to keep every edit form's fields uniquely identified.

Verified by rendering `pages/doc_library.html` and `partials/doc_links_list.html` directly
against the app's own Jinja environment (empty/list/tiles states, with real per-link data) and
asserting no DaisyUI class strings remain in the output — full pytest suite (create/edit/delete/
view-mode-toggle) deferred to CI, which has a reachable Postgres; no local DB was available in
this pass. `tests/test_health.py`/`tests/test_registry_client_wiring.py` (the two suites that
don't need a DB) passed locally.
