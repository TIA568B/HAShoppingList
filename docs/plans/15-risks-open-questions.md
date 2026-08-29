# 15 — Risks, Assumptions, Open Questions & Decisions

## Risks

| ID | Risk | Impact | Likelihood | Mitigation | Recommended decision |
|----|------|--------|-----------|------------|----------------------|
| R1 | `alexa_devices` write services don't propagate reliably to the real Alexa app | High (core sync fails) | Low–Med | Retry/backoff + visible errors; Phase 7 E2E validates | Validate in Phase 7 before release; if broken, raise upstream, keep read-only view meanwhile |
| R2 | Item `uid`s not stable across syncs | High (undo/complete target wrong item) | Low | Source uses uid as key; verify in E2E; reconcile by uid | Proceed; add E2E assertion |
| R3 | Reactivity slower than "a few seconds" if push missed | Med (stale view) | Med | 15-min safety poll + manual refresh + last_synced banner | Accept; document expected latency |
| R4 | Vegan filter mis-handles hidden animal ingredients | Med (mis-categorized/animal item shown) | Med | Route ambiguous→Uncategorized; manual correction learns | Accept (NFR4); best-effort by design |
| R5 | Meat/milk assumed plant-based but bought for a guest | Low | Low | Manual re-categorize; optional first-seen confirm (future) | Accept; defer confirm prompt |
| R6 | HACS/custom card install friction | Low | Med | Serve built card as a frontend resource; document steps | Accept |
| R7 | Very large list exceeds attribute size limits | Low | Low | Minimal item objects; exclude from recorder; fallback to a websocket command if needed | Monitor; implement fallback only if hit |
| R8 | `alexa_devices` internal API changes/breaks (unofficial Amazon API) | Med | Med | We depend only on the public todo contract, not internals | Accept; isolate via public services |

## Assumptions (documented, not silently invented)

1. `todo.update_item`/`add_item` on the `alexa_devices` list propagate to Alexa (spec §6 says
   user confirmed; not mutation-tested here — MCP read-only).
2. Item `uid`s are stable for an item's lifetime (supported by source using uid as dict key).
3. Completed items remain retrievable via `todo.get_items` with `status: [needs_action,
   completed]` (confirmed in source).
4. Shopping-list size stays modest (tens–low hundreds), so full recompute per change is fine.
5. Single household user; no multi-tenant/permission complexity needed.
6. Scope is the **shopping** list only; the Alexa **to-do** list is out of scope for v1.
7. Python 3.13 baseline (HA 2026.8).

## Open questions (for user/reviewer)

- OQ1: Confirm the Alexa to-do list (`todo.david_carson_amazon_gmail_com_to_do_list`) is out of
  scope for v1. (Assumed yes.)
- OQ2: Should completed items be visible in the card by default, or only via a toggle?
  (Assumed: hidden by default, toggle to reveal.)
- OQ3: Desired grace-period default — spec says 8–10s; plan defaults to 9s. Confirm.
- OQ4: Is a first-seen confirmation prompt for new meat/milk items wanted in v1, or deferred?
  (Assumed deferred.)
- OQ5: Should there be an explicit "review draft map" gate (spec Req 1.7), or is the live
  `Uncategorized` triage bucket sufficient? (Plan chose the latter; confirm acceptable.)
- OQ6: `codeowners`/repo URL/`hacs.json` details to finalize before publishing.

## Decisions log

| Date | Decision | Rationale | Overrides |
|------|----------|-----------|-----------|
| 2026-08-29 | Source entity is `todo.david_carson_amazon_gmail_com_shopping_list` (alexa_devices), user-selectable in config flow | It is the real Alexa list; native `todo.shopping_list` is empty/unrelated | spec's `todo.shopping_list` (C1) |
| 2026-08-29 | Custom integration + card instead of pyscript | Config flow, coordinator, entities, services, diagnostics, tests, migrations | spec design vehicle (C4) |
| 2026-08-29 | Seed from live list (incl. completed) + defaults + learn over time; drop history mining | No recorder history exists; completed items are retained by alexa_devices | spec Req 1 history bootstrap (C2) |
| 2026-08-29 | No `Dairy`/`Fish` category; milk→Milk, dairy-style→Chilled, meat→Fake Meat, animal→Uncategorized | Requirements + vegan rules; spec's `Dairy` sample was a typo | spec design sample JSON (C3) |
| 2026-08-29 | Grace-period timing lives client-side in the card | Instant undo, no premature service call | — |
| 2026-08-29 | Expose a derived `sensor` only; keep the Alexa list as single write target | Avoid drift / second source of truth (NFR3) | — |
