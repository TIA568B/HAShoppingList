# 15 — Risks, Assumptions, Open Questions & Decisions

## Risks

| ID | Risk | Impact | Likelihood | Mitigation | Recommended decision |
|----|------|--------|-----------|------------|----------------------|
| R1 | `alexa_devices` write services don't propagate reliably to the real Alexa app | High (core sync fails) | Low–Med | Retry/backoff + visible errors; **Phase 2.5 early manual spike** + Phase 7 E2E validate | **VALIDATED (2026-08-29 Phase 2.5 spike): a manual `todo.update_item` write propagated to the real Alexa app.** Residual full coverage deferred to Phase 7 E2E |
| R2 | Item `uid`s not stable across syncs | High (undo/complete target wrong item) | Low | Source uses uid as key; verify in Phase 2.5 spike + E2E; reconcile by uid | Validated together with R1 in the Phase 2.5 spike; confirm across a full add/complete/undo cycle in Phase 7 |
| R3 | Reactivity slower than "a few seconds" if push missed | Med (stale view) | Med | 15-min safety poll + manual refresh + last_synced banner; two-tier latency contract documented (doc 08) | Accept; up to ~5 min worst case — confirm with user (M-5) |
| R4 | Vegan filter mis-handles hidden animal ingredients | Med (mis-categorised/animal item shown) | Med | Route ambiguous→Uncategorised; manual correction learns | Accept (NFR4); best-effort by design |
| R5 | Meat/milk assumed plant-based but bought for a guest | Low | Low | Manual re-categorise; optional first-seen confirm (future) | Accept; defer confirm prompt |
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
  scope for v1. (Assumed yes; not contradicted.)
- OQ2: Should completed items be visible in the card by default, or only via a toggle?
  (Assumed: hidden by default, toggle to reveal.)
- OQ3: **RESOLVED (user, 2026-08-29).** Grace-period default 9s, range 8–30s — accepted.
- OQ4: Is a first-seen confirmation prompt for new meat/milk items wanted in v1, or deferred?
  (Assumed deferred.)
- OQ5: **RESOLVED (user, 2026-08-29).** Non-blocking first-setup "Review your categories" banner +
  prominent `Uncategorised` bucket accepted in lieu of a blocking review gate (Req 1.7). The
  requirement is preserved unchanged in `docs/specs/`; the plan documents the reinterpretation.
- OQ6: `codeowners`/repo URL/`hacs.json` details to finalize before publishing.
- OQ7: **RESOLVED (user, 2026-08-29).** Complete-on-tap accepted — ticking marks the item complete
  on the Alexa list immediately; the grace window is undo-only (instant-visible completion with an
  undo window), reinterpreting Req 4.1's "before finalized" phrasing.
- OQ8: **RESOLVED (user, 2026-08-29).** `milk` stays an Aldi shop keyword (all milk auto-assigns to
  Aldi until manually re-assigned), per "Nappies and Milk should be Aldi".
- OQ9: **RESOLVED (user, 2026-08-29).** Auto-collapse-when-empty is kept **in addition to** manual
  collapse (finished shops/aisles de-emphasize; manual expand still works).

## Decisions log

| Date | Decision | Rationale | Overrides |
|------|----------|-----------|-----------|
| 2026-08-29 | Source entity is `todo.david_carson_amazon_gmail_com_shopping_list` (alexa_devices), user-selectable in config flow | It is the real Alexa list; native `todo.shopping_list` is empty/unrelated | spec's `todo.shopping_list` (C1) |
| 2026-08-29 | Custom integration + card instead of pyscript | Config flow, coordinator, entities, services, diagnostics, tests, migrations | spec design vehicle (C4) |
| 2026-08-29 | Seed from live list (incl. completed) + defaults + learn over time; drop history mining | No recorder history exists; completed items are retained by alexa_devices | spec Req 1 history bootstrap (C2) |
| 2026-08-29 | No `Dairy`/`Fish` category; milk→Milk, dairy-style→Chilled, meat→Fake Meat, animal→Uncategorised | Requirements + vegan rules; spec's `Dairy` sample was a typo | spec design sample JSON (C3) |
| 2026-08-29 | Tick model is **complete-on-tap + reversing undo** (completion sent immediately; grace window governs undo only) | Removes silent-drop of a completion if the card closes (Req 5.4); backend enforces end state via the public todo service. Note: this makes completion **instantly visible** on Alexa rather than after the grace period — a human-facing reinterpretation of Req 4.1, escalated as OQ7 | Original "client-side deferred finalize timer" (finding H-1); reinterprets Req 4.1 "before finalized" (OQ7 / followup02 FO-1) |
| 2026-08-29 | Expose a derived `sensor` only; keep the Alexa list as single write target | Avoid drift / second source of truth (NFR3) | — |
| 2026-08-29 | Add `category_definitions` read attribute; bump `attributes_version` 1→2 | Card needs to read per-category keywords for Req 6.1; attribute is simpler than a websocket for this small map | — (finding M-2) |
| 2026-08-29 | Source-entity change is a **reconfigure** flow, not an options field | `unique_id` = source id is immutable via options; reconfigure updates data + unique_id atomically | — (finding M-3) |
| 2026-08-29 | Grace-period range 8–30s (default 9), floor raised from 5s to 8s | Respect the spec's 8–10s lower bound | Plan's earlier 5–30s range (finding L-7) |
| 2026-08-29 | `edit_category` rename migrates learned overrides to the new name | Prevent silent learning loss on rename | — (finding REVIEW2-003) |
| 2026-08-29 | Early Phase 2.5 write spike validates R1/R2 before card work | Cheaply de-risk two-way sync before frontend investment | — (finding M-6) |
| 2026-08-29 | **Per-item shop preference** (Req 7): default `No Preference`; default shops Aldi/Asda/Tesco with starter keyword rules (nappies/milk→Aldi, clothing→Asda); shops learn over time; delete_shop→No Preference | User-requested feature; mirrors category learning + delete-reassign semantics | Adds Req 7 (new scope) |
| 2026-08-29 | Shop resolution **precedence**: shop-name-in-text > learned override > keyword rule > No Preference (name-in-text **beats** a learned override) | User confirmed "Tesco Nappies"→Tesco even over a learned preference; naming the shop in the item is the most explicit signal | — (user decision) |
| 2026-08-29 | Shops support **both** keyword rules and learning; **single shop per item**; grouping is **shop-primary then category** (shop → category → items) with **independent manual collapse** per shop and per category | User answers to feature clarifying questions | — (user decisions) |
| 2026-08-29 | **User sign-offs (OQ3/OQ5/OQ7/OQ8/OQ9):** grace 9s/8–30s; non-blocking review banner; complete-on-tap instant-visible; `milk`→Aldi kept; auto-collapse kept alongside manual | Explicit user confirmation | Closes the human-decision open questions |
| 2026-08-29 | **M-5 latency accepted** (few seconds on push; up to ~5 min on missed push) and **M-6 spike authorised** (implementer may run one manual write to validate Alexa propagation + uid stability before card work) | User accepted | — |
| 2026-08-29 | **Phase 2.5 write-spike PASSED (M-6 / R1 / R2 gate cleared):** a manual `todo.update_item` on the real Alexa list propagated to the Alexa app; the two-way-sync foundation holds. The card phases' gate is satisfied. | User-reported result of the implementer-environment spike | Closes the R1/R2 pre-card gate; full sign-off still pending Phase 7 E2E |
| 2026-09-02 | **0.3.0 shipped:** Produce→Fruit & Veg; add Sauces/Baby categories; add Waitrose/Morrisons/Lidl/Sainsburys shops; pizza→Frozen+Waitrose; teriyaki/veggie pasta→Aldi; hide empty (0-count) categories/shops in the card | User-directed taxonomy/shop tweaks + empty-group hiding | — |
| 2026-09-02 | **Map-management feature designed (target 0.4.0), design-only:** (A) in-card settings panels as the live editor over existing services (instant recompute, no manual step); (D) move seed to shipped `default_map.json`, applied on initial run + a one-time upgrade re-seed; add a **reload-from-JSON** admin action (replace semantics, confirm required) via a new `reload_defaults` service distinct from `reload_maps`. Storage stays JSON-in-HA-`Store` (SQLite rejected as over-engineering). Design in `docs/plans/feature-map-management/`. | User wants live, code-free map editing that updates immediately, plus one-click re-seed from a JSON I can update in future; store is test-only so clean replace is acceptable | Defers the guarded "merge new defaults only" variant (former Option C) to a future multi-user need |
| 2026-08-29 | **Req 7 polish (followup03):** v3 is the initial shipped contract (R7-L1); shop-name-in-text is whole-word + warn on dictionary-word shop names (R7-L2); `No Preference` position is a card option, default last (R7-O1); added card test for `shop_definitions` panel (R7-O3) | Address followup03 Low/Observation findings pre-implementation | — |
| 2026-08-29 | **Pre-build polish (followup04):** store schema v1 includes shop fields + `store.py` injects defaults for missing keys (F4-1); **whole-word matching mandatory for both category and shop resolvers** — no substring (F4-2); `reload_category_map`→`reload_maps` (F4-3); diagnostics add shop counts (F4-4); doc 13 updated for `Shop`/shop resolver (F4-5); shop precedence-asymmetry callout (F4-6); optimistic add may re-pivot once (F4-7) | Address followup04 pre-build findings; F4-2 protects the vegan boundary | Category matching was "whole-word/substring" (F4-2); service rename (F4-3) |
| 2026-08-29 | **British spelling throughout (implementation, DEV-001):** domain `alexa_shopping_categorizer`→`alexa_shopping_categoriser`; module `categorizer.py`→`categoriser.py`; service `recategorize_item`→`recategorise_item`; attribute `uncategorized_count`→`uncategorised_count`; fallback label `Uncategorized`→`Uncategorised`; doc `07-categorization-engine`→`07-categorisation-engine`. `attributes_version` stays **3** (initial shipped contract, no consumer to break). Historical specs/reviews left unchanged. | Owner is a UK English speaker; pre-release so no back-compat obligation | Original American spelling of the domain/identifiers (see `reviews/go-no-go/implementation-deviations.md` DEV-001) |
