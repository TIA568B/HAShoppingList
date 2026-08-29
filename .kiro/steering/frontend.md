---
inclusion: fileMatch
fileMatchPattern: 'frontend/**'
---

# Frontend (Custom Lovelace Card) Steering

Applies to the bundled custom card under `frontend/alexa-shopping-categorizer-card/`. The card is
the most requirement-dense and security-sensitive component (Req 3.x, 4.x, 5.4), so it gets
first-class guardrails here. Detailed design lives in `docs/plans/11-frontend-card.md`; the
contract is canonical in `docs/plans/06-data-model-and-contract.md`.

## Contract with the backend

- The card is a **client** of two public surfaces only: the categorized **sensor attributes**
  (canonical schema in `docs/plans/06`) and documented HA services. It holds no private contract
  with Python internals.
- Read categories/keywords for the settings panel from the sensor's `category_definitions`
  attribute (Req 6.1), and shops/keyword-rules from `shop_definitions` (Req 7.1). Do not invent a
  private read path.
- **Shop preference (Req 7):** render a **two-level tree — shop → category (aisle) → items** from
  `shop_groups` (`No Preference` last; `Uncategorized` last within each shop). Each item shows its
  `category`. Shop assignment via `assign_shop` (`No Preference` clears it); shop management via
  `add_shop`/`edit_shop`/`delete_shop` (name + keyword rules). Shop is independent of category — do
  not derive one from the other.
- **Collapse is manual + independent per level, plus auto-collapse-when-empty.** The user can
  collapse/expand each shop and each category independently (to focus on one store while still
  seeing its aisles). Manual collapse state is **card-local** UI state (per shop + per category),
  remembered across sensor updates, never written back to the sensor. The server-provided
  `collapsed` flag is only the auto-collapse-when-empty hint (Req 3.3); it does not override manual
  expand.
- `No Preference` renders last by default; expose a `no_preference_position` card option
  (first/last) since it may be the largest group before shop learning kicks in (finding R7-O1).
- Shop-name-in-text resolution is **whole-word, case-insensitive**. When a user adds a shop whose
  name is a common English word (e.g. "Fresh"), warn — do not block — since tier-1 matching could
  otherwise hijack ordinary items (finding R7-L2).
- Honour `attributes_version`: if the sensor's version is higher than the card supports, degrade
  gracefully (render what is known, show a "please update the card" hint) rather than crashing.
- Sanctioned calls only: `subscribe_entities` (live updates), `call_service` for `todo.add_item`
  / `todo.update_item` on the source entity, `homeassistant.update_entity` (manual refresh), and
  the integration's own services (`add_category`, `edit_category`, `delete_category`,
  `recategorize_item`, shop services, `reload_maps`). No bespoke HTTP endpoints.

## Tick / undo state machine (non-negotiable — complete-on-tap)

- **Send the completion immediately on tap** via `todo.update_item(status=completed)`. Do **not**
  defer the write behind a client-side grace timer. The grace window governs **undo only**.
- Rationale: a closed/backgrounded/crashed card must never silently drop a completion (Req 5.4).
  With complete-on-tap the change is already synced; the worst case is losing the *ability to
  undo*, which is the safe direction. This is the sanctioned resolution of the architecture rule
  "no business logic in the card the backend cannot also enforce" — the backend enforces the end
  state because the write goes through the public `todo.*` service at once.
- Undo is a **reversing** call: `todo.update_item(status=needs_action)`.
- Track per-item state independently, keyed by `uid`, in a map (Req 4.5). The grace window is
  `grace_period_seconds` from the sensor attributes (8–30s, default 9).
- **Source wins on reconcile:** when a sensor update shows a tracked `uid` was changed/removed on
  Alexa directly, adopt the source state and cancel any local undo affordance for that `uid`.
- **Add reconciliation:** an optimistically-added item has no `uid` yet; tag it with a client
  token and adopt the first inbound `needs_action` item whose normalized summary matches, taking
  over its real `uid`. Drop unmatched placeholders after a bounded window.

## Client retry / error surfacing

- Every write (complete, reversing undo, add) retries with bounded exponential backoff (≈3
  attempts) and, on exhaustion, **reverts the optimistic UI** and surfaces a visible,
  dismissible error naming the item and action (Req 5.4). Never fail silently.

## Security (card runs in the HA frontend context)

- Render all user-supplied text (item names, category names, keywords) via safe DOM APIs. **Never**
  `innerHTML` with raw user text and never `eval`. See `security.md` (canonical) for the rule.
- Only call documented HA services/websocket APIs available to the logged-in user; rely on HA
  session auth. No embedded API keys, no auth bypass.

## Accessibility

- Keyboard operable (tab/enter/space to tick and undo), visible focus states, ARIA labels on
  interactive controls, sufficient contrast, and the undo affordance reachable without a mouse.

## Packaging / resource registration

- Serve the built asset from the integration (`async_register_static_paths` + `add_extra_js_url`);
  users must not hand-install JS.
- **Cache-bust** the resource URL with the integration `version` query string (or a content-hashed
  filename) so card updates are not masked by browser caching.
- Keep `hacs.json` and the frontend build output consistent with the documented install steps in
  the README.

## Testing

- Card tests live under `frontend/**` and receive both this steering and `testing.md`.
- Cover the pure logic: complete-on-tap send, reversing-undo within window, window-expiry drops
  affordance (no extra call), independent per-item windows, collapse-when-empty, add
  reconciliation, "card gone during undo window" (nothing dropped), and "inbound delete during
  undo window" (source wins).
