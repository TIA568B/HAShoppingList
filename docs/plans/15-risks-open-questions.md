# 15 — Risks, Assumptions, Open Questions & Decisions

## Risks

| ID | Risk | Impact | Likelihood | Mitigation | Recommended decision |
|----|------|--------|-----------|------------|----------------------|
| R1 | `alexa_devices` write services don't propagate reliably to the real Alexa app | High (core sync fails) | Low–Med | Retry/backoff + visible errors; **Phase 2.5 early manual spike** + Phase 7 E2E validate | Validate in the Phase 2.5 spike *before* card work (finding M-6); if broken, raise upstream, keep read-only view meanwhile |
| R2 | Item `uid`s not stable across syncs | High (undo/complete target wrong item) | Low | Source uses uid as key; verify in Phase 2.5 spike + E2E; reconcile by uid | Proceed; validate in Phase 2.5 |
| R3 | Reactivity slower than "a few seconds" if push missed | Med (stale view) | Med | 15-min safety poll + manual refresh + last_synced banner; two-tier latency contract documented (doc 08) | Accept; up to ~5 min worst case — confirm with user (M-5) |
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
- OQ3: Grace-period default is 9s; range narrowed to **8–30s** (8s floor respects the spec's
  8–10s intent — finding L-7). Confirm the widened ceiling is acceptable.
- OQ4: Is a first-seen confirmation prompt for new meat/milk items wanted in v1, or deferred?
  (Assumed deferred.)
- OQ7 **(needs human decision — followup02 FO-1):** the **complete-on-tap** model (finding H-1)
  is a behavioural reinterpretation of Req 4.1. The spec frames the grace period as happening
  *before* the completion is finalized, which reads as "don't send until the timer expires."
  Complete-on-tap sends the completion **immediately** and treats the window as undo-only, so a
  user watching the Alexa app sees the item complete instantly rather than after ~9s. This is the
  safer engineering choice (nothing silently lost — Req 5.4) and is recorded in the decision log,
  but it is a **human-facing** behaviour change alongside OQ5. Confirm the user expects
  instant-visible completion with an undo window, rather than a delayed send.
- OQ5 **(needs human decision — finding M-1):** Req 1.7 is a hard SHALL ("review before live").
  The plan reinterprets it as a **non-blocking** first-setup "Review your categories" banner +
  prominent `Uncategorized` bucket, justified because the map only affects display grouping and
  never mutates the Alexa list (cosmetic, reversible blast radius). Confirm this is acceptable, or
  request a blocking gate (bounded Phase 2/4 rework). The requirement is preserved unchanged in
  `docs/specs/` meanwhile.
- OQ6: `codeowners`/repo URL/`hacs.json` details to finalize before publishing.

## Decisions log

| Date | Decision | Rationale | Overrides |
|------|----------|-----------|-----------|
| 2026-08-29 | Source entity is `todo.david_carson_amazon_gmail_com_shopping_list` (alexa_devices), user-selectable in config flow | It is the real Alexa list; native `todo.shopping_list` is empty/unrelated | spec's `todo.shopping_list` (C1) |
| 2026-08-29 | Custom integration + card instead of pyscript | Config flow, coordinator, entities, services, diagnostics, tests, migrations | spec design vehicle (C4) |
| 2026-08-29 | Seed from live list (incl. completed) + defaults + learn over time; drop history mining | No recorder history exists; completed items are retained by alexa_devices | spec Req 1 history bootstrap (C2) |
| 2026-08-29 | No `Dairy`/`Fish` category; milk→Milk, dairy-style→Chilled, meat→Fake Meat, animal→Uncategorized | Requirements + vegan rules; spec's `Dairy` sample was a typo | spec design sample JSON (C3) |
| 2026-08-29 | Tick model is **complete-on-tap + reversing undo** (completion sent immediately; grace window governs undo only) | Removes silent-drop of a completion if the card closes (Req 5.4); backend enforces end state via the public todo service. Note: this makes completion **instantly visible** on Alexa rather than after the grace period — a human-facing reinterpretation of Req 4.1, escalated as OQ7 | Original "client-side deferred finalize timer" (finding H-1); reinterprets Req 4.1 "before finalized" (OQ7 / followup02 FO-1) |
| 2026-08-29 | Expose a derived `sensor` only; keep the Alexa list as single write target | Avoid drift / second source of truth (NFR3) | — |
| 2026-08-29 | Add `category_definitions` read attribute; bump `attributes_version` 1→2 | Card needs to read per-category keywords for Req 6.1; attribute is simpler than a websocket for this small map | — (finding M-2) |
| 2026-08-29 | Source-entity change is a **reconfigure** flow, not an options field | `unique_id` = source id is immutable via options; reconfigure updates data + unique_id atomically | — (finding M-3) |
| 2026-08-29 | Grace-period range 8–30s (default 9), floor raised from 5s to 8s | Respect the spec's 8–10s lower bound | Plan's earlier 5–30s range (finding L-7) |
| 2026-08-29 | `edit_category` rename migrates learned overrides to the new name | Prevent silent learning loss on rename | — (finding REVIEW2-003) |
| 2026-08-29 | Early Phase 2.5 write spike validates R1/R2 before card work | Cheaply de-risk two-way sync before frontend investment | — (finding M-6) |
