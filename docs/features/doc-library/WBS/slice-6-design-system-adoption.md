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

- [ ] Zero DaisyUI classes anywhere in `app/templates/**`.
- [ ] Add-link form, list/tiles toggle, and per-link Edit/Delete controls are all visibly styled
      (not just readable as bare text) in both light and dark mode.
- [ ] Existing functional behavior (create/edit/delete a link, toggle view mode, persisted
      view-mode preference) is unchanged — this is presentation-only.
- [ ] No regression in existing Playwright specs for Doc Library.

## Testing

- Existing E2E coverage for create/edit/delete/view-mode-toggle stays the functional regression
  backstop — expected to pass unmodified.
- Manual visual check in both light and dark mode, given the contrast-defect history in
  `organize-me`'s own Slice 5.

<!-- /to-implementation appends a "## Delivered" section here once this slice ships. -->
