# 07 — Native Editing Redesign (0.5.0): Options-flow taxonomy + tap-to-fix

Supersedes the in-card settings panel from `02-card-settings-panels.md`. That inline editor
shipped in 0.4.0 but proved unusable in practice: typing triggered Home Assistant's global
keyboard shortcuts (our shadow-DOM `<input>`s let keystrokes bubble to HA's document-level
hotkey handler), and the hand-rolled form was clunky and poor on mobile — the household will
not use it. We pivot to **native HA UI** for the rare taxonomy curation and a **tap-to-fix**
affordance for the frequent per-item case.

## Decisions (user-confirmed 2026-09-02)

- **B1a — Options-flow taxonomy editor (menu-style).** Manage categories and shops through the
  integration's Options flow (Settings → Devices & Services → the integration → Configure),
  using HA's native form widgets. Menu-driven: choose an area (Categories / Shops / Reload
  defaults), then add / edit / delete a single item at a time. Native widgets are mobile-
  friendly and immune to the hotkey problem (they are not our shadow-DOM inputs).
- **B2 — per-item pencil/edit icon on the card.** Tap on an item still = tick (complete-on-tap
  unchanged). A separate small **pencil icon** per item opens a menu to **set its shop** and
  **set its category** (calls the existing `assign_shop` / `recategorise_item`, which learn).
  This is the family-friendly 80% path.
- **Reload defaults** moves into the Options flow (a menu choice with a confirm), removed from
  the card.
- **Visible version string on the card** (e.g. a small `v0.5.0` in a footer) so we can confirm
  at a glance which card bundle actually loaded — deploy/cache verification.
- **Remove the in-card settings panel** (`settings-panel.js` and its wiring) entirely.

## B1a — Options flow shape

The options flow becomes menu-driven (`async_step_init` shows a menu; HA supports
`async_show_menu`). Steps:

- **init (menu):** Display options · Manage categories · Manage shops · Reload defaults.
- **Display options:** the existing options form (grace period, show_completed,
  collapse_empty_categories, redact_items_in_diagnostics). Unchanged.
- **Manage categories (menu/select):** pick an existing category to edit, or "Add new". Editing
  a category shows a form: name (text) + keywords (text; comma or newline separated) + a
  "delete" boolean. Submitting calls the same logic the services use (add/edit/delete),
  reusing the store + validation already implemented — the options flow is a thin native UI
  over the existing category/shop operations, not a new code path.
- **Manage shops (menu/select):** same pattern for shops (name + keyword rules + delete).
- **Reload defaults:** a confirm step (boolean "replace categories and shops with the shipped
  defaults? learned corrections are kept") → calls the `reload_defaults` operation.

Notes:
- Validation stays server-side (reuse the voluptuous/name rules from `services.py`; factor the
  shared validation into a helper both services and the options flow call, so there is one
  source of truth — no duplicated rules).
- Reordering remains **deferred** (OQ-B). The options flow edits name/keywords/existence only.
- After any change, request a coordinator recompute (same as the services) so the card/panel
  refreshes live.
- Because options changes normally trigger `async_reload_entry`, ensure taxonomy edits made via
  the flow persist to the **store** (not `entry.options`) and recompute without needing a full
  reload; the display-options sub-form keeps its existing reload behaviour.

## B2 — per-item edit affordance (card)

- Each item row gets a small **pencil button** (icon, ARIA-labelled "Edit <item>"). Tapping it
  opens an inline, card-local menu (not an HA dialog, to stay dependency-light and testable)
  offering: **Set shop** (list of `shop_definitions` + `No Preference`) and **Set category**
  (list of `category_definitions` + `Uncategorised`). Choosing an option calls `assign_shop` /
  `recategorise_item` with the item text (and `apply_to_uid`), then closes the menu.
- The set-shop/category option lists are **buttons**, not text inputs — so there is **no typing
  and no hotkey exposure** on the card at all. (The add-item box remains the only card input;
  keep its `stopKeyboardPropagation`.)
- Tap on the row/checkbox is unchanged (tick + undo). The pencil is a distinct target so the
  two gestures never conflict.

## Empty groups

Keep the 0.4.0 rule: a category with **0 unchecked** items is not rendered, and a shop whose
categories are all empty is not rendered. This is verified in the card render tests; the reason
it appeared "not working" was a stale card bundle, addressed by the version string + confirming
the served file. No logic change expected, but re-confirm on deploy.

## Deploy verification

- Render a small, unobtrusive **version footer** on the card (read from a build-time constant
  kept in step with `manifest.json`). Seeing the expected version on screen confirms the fresh
  card loaded; a mismatch means a stale bundle (cache/HACS/restart), not a code bug.
- Keep the panel→card dynamic import version-busting from 0.4.1.

## What is removed / changed

- **Removed:** `src/settings-panel.js`, `renderSettings`, the card's `_renderSettings`,
  `_settingsOpen`, `_buildReloadControl`, `_confirmingReload`, and the reload button. Their
  tests are removed/replaced.
- **Kept:** `_callIntegration` helper (reused by the pencil menu), error surfacing,
  `stopKeyboardPropagation` on the add-item box.
- **Added (backend):** menu-style options flow; a shared validation helper factored out of
  `services.py`.
- **Added (frontend):** per-item pencil + set-shop/set-category menu; version footer.

## Testing

- Options flow: menu navigation; add/edit/delete category and shop via the flow persists to the
  store + recomputes; invalid input rejected; reserved names rejected; reload-defaults confirm
  path. (Backend, pytest.)
- Card: pencil opens the menu; choosing a shop calls `assign_shop`; choosing a category calls
  `recategorise_item`; menu has no text inputs; tick/undo unaffected; version footer renders.
  (node:test + DOM stub.)

## Release

**0.5.0** (minor; new UX surface, removes the inline editor). Bump manifest + pyproject,
CHANGELOG. No store schema change (still v2). Options-flow-only changes plus card changes; the
sensor contract is unchanged (`attributes_version` stays 3).
