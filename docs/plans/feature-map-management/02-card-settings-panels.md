# 02 — Option A: In-Card Settings Panels (the live editor)

The primary user-facing mechanism. Extends the card panels already anticipated in
`docs/plans/11-frontend-card.md`. **No new backend contract or service is required** — every
edit uses services that already exist and already persist + recompute, so the categorised view
re-groups immediately.

## Why edits are already "instant"

Every mutating service (`add_category`, `edit_category`, `delete_category`,
`recategorise_item`, `add_shop`, `edit_shop`, `delete_shop`, `assign_shop`) ends with
`persist store -> coordinator.async_recompute()`. The recompute rebuilds the projection, the
sensor attributes update, and the card (subscribed via `subscribe_entities`) re-renders. So
the moment a panel action's service call returns, the list re-groups. There is **no manual
"apply" or `reload_maps` step** for ordinary edits — that pain only exists today because there
is no editor UI, which is exactly what this panel adds.

> `reload_maps` / the new reload-from-JSON action are only for the *bulk re-seed* case
> (`03-migration-and-reload.md`), never for individual edits.

## Panels

Two panels, reachable from the card (and the sidebar "Shopping List" panel that already
exists):

### Category settings
- **Read:** the sensor's `category_definitions` attribute (name + keywords, in order). This is
  the sanctioned read path (Req 6.1, finding M-2). No private read into Python internals.
- **Actions → existing services:**
  - Add category → `add_category` (name, optional keywords).
  - Rename / edit keywords → `edit_category` (name, new_name?, keywords?). Rename migrates
    learned overrides (already implemented).
  - Delete → `delete_category` (items fall to `Uncategorised`; never deleted).
  - Reassign an item's category → `recategorise_item` (learns for future identical text).
- **Ordering:** category order is significant (first-match-wins). The panel should allow
  reordering; this needs a small service addition (`reorder_categories`) OR an `order` field on
  `edit_category`. Flagged as an open question in `05-open-questions.md` (do not assume).

### Shop settings
- **Read:** the sensor's `shop_definitions` attribute (name + keyword rules, in order).
  `No Preference` is implicit and never listed.
- **Actions → existing services:**
  - Add shop → `add_shop` (name, optional keyword rules). Warns (not blocks) on a common-word
    name (finding R7-L2).
  - Rename / edit keyword rules → `edit_shop` (migrates shop overrides).
  - Delete → `delete_shop` (items fall to `No Preference`; never deleted).
  - Assign an item's shop → `assign_shop` (`No Preference` clears it).

## Interaction model

- Inline edit forms (text input for name, chip/list editor for keywords). On submit, call the
  service; on the websocket ack, the sensor update drives the re-render — the panel does not
  optimistically mutate the map (the map is small and the round-trip is fast; this keeps the
  backend the single source of truth, per the architecture rule).
- Errors from a service (`ServiceValidationError`, e.g. duplicate name) surface inline in the
  panel (dismissible), reusing the card's existing error-surfacing pattern.
- Keyboard operable, ARIA-labelled, focus-visible — same accessibility bar as the rest of the
  card (`frontend.md`).

## Security

- All names/keywords are user-supplied and rendered via **safe DOM APIs only** (textContent /
  the card's `setText`), never `innerHTML` with raw text, never `eval` (canonical rule in
  `security.md`).
- Validation is enforced **server-side** by the services (non-empty, unique case-insensitive,
  length-limited, control-char-free, reserved-name rejection). The panel may pre-validate for
  UX but must not be the only line of defence — the services already are.

## What this does NOT need

- No change to `attributes_version` (reads use the existing `category_definitions` /
  `shop_definitions`), **unless** reordering forces a new signal — see open questions.
- No new persistence; no SQLite; no bespoke websocket/HTTP endpoint (uses `call_service` +
  `subscribe_entities`).
