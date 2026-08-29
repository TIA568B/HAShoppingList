# Requirements Traceability Review

**Reviewer:** Independent senior technical reviewer (second agent)
**Date:** 2026-08-29
**Primary source of truth:** `docs/specs/requirements.md` (6 EARS-style requirements)
**Cross-referenced against:** `docs/specs/design.md`, `docs/plans/**`, `.kiro/steering/**`

## How to read this

- **Requirement** — the atomic acceptance criterion from `docs/specs/requirements.md`.
- **Spec source** — requirement number.
- **Plan reference** — where the plan addresses it.
- **Impl phase** — phase in `14-implementation-plan.md`.
- **Test coverage** — planned test (from `12-testing-strategy.md`).
- **Steering** — the steering rule(s) that reinforce it.
- **Status** — Covered / Partially Covered / Missing / Incorrect / Unclear.
- **Issues** — cross-reference to a finding ID (see `consolidated-review.md`).

## Traceability matrix

| Requirement | Spec | Plan reference | Impl phase | Test coverage | Steering | Status | Issues |
|---|---|---|---|---|---|---|---|
| **1.1** Read historical data to build initial mapping | Req 1.1 | `01` C2, `07` §Bootstrap, `15` decision log | Phase 1/2 | `test_coordinator` (seed from live list) | product (ground truth), home-assistant (coordinator) | **Incorrect** (deliberate, documented override) | F-01 |
| **1.2** Exclude egg/animal-derived from category set | Req 1.2 | `07` vegan table, `06` schema | Phase 1 | categorizer matrix ("eggs","honey"→Uncategorized) | product (non-negotiable) | Covered | — |
| **1.3** Milk keywords → "Milk" | Req 1.3 | `07` vegan table, `06` schema | Phase 1 | categorizer "2x oat milk"→Milk | product | Covered | — |
| **1.4 (crit.)** Dairy-style → "Chilled" | Req 1.4 | `07`, `06` | Phase 1 | categorizer "cheddar cheese"→Chilled | product | Covered | — |
| **1.4 (review gate)** Present generated mapping for review before live | Req 1.7 | `07` §Bootstrap step 3, `15` OQ5 | Phase 2/4 | *none explicit* | — | **Partially Covered** | F-02 |
| **1.5** Meat keywords → "Fake Meat" | Req 1.5 | `07`, `06` | Phase 1 | categorizer "smoky bacon"→Fake Meat | product | Covered | — |
| **1.6** Unmappable → "Uncategorized" (never guess) | Req 1.6 | `07` §4 | Phase 1 | categorizer "birthday candles"→Uncategorized | product | Covered | — |
| **1.7** Present mapping for user review | Req 1.7 | `07` step 3, `15` OQ5 | Phase 4 (card triage) | *none explicit* | — | **Partially Covered** | F-02 |
| **1.8** Fallback default taxonomy; never block setup | Req 1.8 | `06` defaults, `07` step 1, `04` config flow | Phase 1/2 | config flow "no alexa_devices todo" | home-assistant | Covered | — |
| **2.1** Categorize new items within a few seconds | Req 2.1 | `08` reactivity, `05` availability | Phase 2 | coordinator recompute-on-state-change | home-assistant (coordinator) | Covered | note F-08 (latency claim) |
| **2.2** Match against mapping | Req 2.2 | `07` pipeline | Phase 1/2 | categorizer matrix | product | Covered | — |
| **2.3** No match → Uncategorized, easy manual assign | Req 2.3 | `07` §4, `11` move action | Phase 4/5 | card move; services recategorize | home-assistant (services) | Covered | — |
| **2.4** Manual correction persists (learning) | Req 2.4 | `07` §2 overrides, `06` overrides dict | Phase 3 | services recategorize_item; override precedence | product (learn over time) | Covered | — |
| **3.1** Live update on any source change | Req 3.1 | `08` inbound flow, `11` subscribe | Phase 2/4 | coordinator state_changed; card js | architecture (data flow) | Covered | — |
| **3.2** Optimistic UI on tick | Req 3.2 | `08` outbound, `11` state machine | Phase 5 | card js tap→checked | — | Covered | — |
| **3.3** Collapse/de-emphasize empty categories | Req 3.3 | `06` collapsed field, `11` | Phase 4 | card js "all checked → collapsed" | — | Covered | — |
| **4.1** Grace period 8–10s before finalize | Req 4.1 | `08`, `04` options (default 9, range 5–30) | Phase 5 | options flow grace=12 | — | Covered | note F-09 (range vs spec) |
| **4.2** Undo control during grace | Req 4.2 | `11` state machine | Phase 5 | card js | — | Covered | — |
| **4.3** Undo reverses UI + sent change | Req 4.3 | `08`, `11` | Phase 5 | card js undo<N no call; undo completed | home-assistant (undo=needs_action) | Covered | — |
| **4.4** Expiry finalizes + syncs | Req 4.4 | `08`, `11` | Phase 5 | card js timer expires → update_item | home-assistant | Covered | — |
| **4.5** Independent per-item undo | Req 4.5 | `08`, `11` Map<uid> | Phase 5 | card js two items pending | — | Covered | — |
| **5.1** Complete → todo service on source | Req 5.1 | `08`, `11` interactions table | Phase 5 | sync finalize update_item | home-assistant | Covered | — |
| **5.2** Add via view → todo.add_item | Req 5.2 | `08` add flow, `11` | Phase 4 | sync add item | home-assistant | Covered | — |
| **5.3** Alexa-direct changes reflected | Req 5.3 | `08` inbound | Phase 2 | coordinator | product (push behavior) | Covered | — |
| **5.4** Failed sync retries + visible error, never silent drop | Req 5.4 | `09` retry/backoff, `11` toast | Phase 5 | sync update_item fails 3x → revert+surface | home-assistant, python | **Partially Covered** | F-03 |
| **6.1** View all categories + keywords | Req 6.1 | `04` services, `11` settings panel | Phase 3/5 | services tests | home-assistant | Covered | — |
| **6.2** Add/edit/remove applies immediately | Req 6.2 | `04`/`06` services | Phase 3 | services persistence+recompute | home-assistant | Covered | — |
| **6.3** Delete category → items to Uncategorized, never delete items | Req 6.3 | `06` delete contract, `07` §2 self-heal | Phase 3 | services delete_category | home-assistant (must reassign) | Covered | — |

## Non-functional / cross-cutting requirements

| NFR | Source | Plan | Test | Status | Issues |
|---|---|---|---|---|---|
| NFR1 reactive ≤ few seconds | Req 2.1/3.1 | `08` (push + 15m poll) | coordinator | Covered (worst-case caveats) | F-08 |
| NFR2 grace 8–10s | Req 4.1 | `04` default 9, range 5–30 | options flow | Covered | F-09 |
| NFR3 no drift / rebuildable | design §2.3 | `03`, `05`, `06` | sensor snapshot | Covered | — |
| NFR4 best-effort vegan | design §6 | `07`, `10` | categorizer matrix | Covered | — |
| NFR5 local-only personal data | derived | `10` security | diagnostics redaction | Covered | — |

## Findings — Missing / Partial / Incorrect / Unclear

### F-01 — Requirement 1.1 (history mining) deliberately overridden — traceable but verify user sign-off
**Status: Incorrect (intentional override).** Req 1.1 mandates reading "HA history/logbook for `todo.shopping_list`, or a user-supplied export". The plan (`01` C2, `15` decision log) drops history mining entirely because the recorder has no history for the Alexa entity, and seeds from the live list (active + completed) instead. This is a sound, evidence-based decision and is documented. **However:** the override changes *what data seeds the model*. The spec also offered "a user-supplied export" as an alternative that the plan does **not** adopt or discuss. If the current live list is short (14 items), the seed corpus is thin, and the "user-supplied export" path in Req 1.1 was the spec's hedge against exactly that. The plan should explicitly note that the export alternative was considered and why it was dropped (or retained as an optional import). Severity: **Low** (documented, but one spec-offered path silently disappears).

### F-02 — Requirement 1.7 (review-before-live gate) is reinterpreted, not implemented
**Status: Partially Covered.** Req 1.7 is a hard "SHALL present the generated category/keyword mapping to the user for review **before it is used live**." The plan (`07` step 3, `15` OQ5) explicitly replaces this gate with a live `Uncategorized` triage bucket and asks the reviewer to confirm this is acceptable (OQ5 is still open). There is **no explicit test** for Req 1.7 in the test matrix. This is a genuine requirement reinterpretation that is still an open question — it must be resolved with the user before Phase 2, not deferred into implementation. Severity: **Medium**.

### F-03 — Requirement 5.4 retry/error surfacing lives only in the card; backend cannot enforce it
**Status: Partially Covered.** Req 5.4 says failed sync SHALL retry and surface a visible error, never silently drop. The plans place *all* write timing and retry logic client-side in the card (`08`, `09` "The card performs the write; on failure it retries…"). This creates a contradiction with `architecture.md` steering: **"No business logic in the card that the backend cannot also enforce."** If the card is closed/backgrounded when a grace timer would fire, or the browser tab dies mid-retry, the completion is silently lost — violating "never silently drops." No plan document resolves what happens to a pending completion when the card is not open. Severity: **High** (see F-13 in consolidated review). Tests cover the card path but not the "card gone" path.

### F-04 — No traceability for the `attributes_version` / contract-drift guard to a requirement
**Status: Observation.** `06` introduces `attributes_version` and snapshot testing (good engineering), but there is no requirement driving it — it is plan-invented infrastructure. This is acceptable and low-risk, but flagged for completeness as design-added scope. Severity: **Observation**.

### F-05 — Requirement 6.1 "view categories" has no backend read service
**Status: Partially Covered.** Services in `04`/`06` are all *mutating* (add/edit/delete/recategorize/reload). Req 6.1 ("display all categories and their associated keywords") is served only by the sensor attributes exposing item projections — but the sensor attribute contract in `06` exposes **items grouped by category**, not the **keyword lists** per category. The card's settings panel needs to read the keyword lists to let the user view/edit them (Req 6.1/6.2), yet no attribute or read service exposes `keywords`. This is a genuine gap in the frontend contract. Severity: **Medium** (see F-14).

## Summary

- **26 acceptance criteria** traced. 20 Covered, 4 Partially Covered, 1 Incorrect-by-design, 1 (1.7) is both an open question and a reinterpretation.
- The categorization/vegan requirements (the product's non-negotiable core) are **fully and correctly** traced with strong test coverage.
- The weak spots are all at the **edges of the sync/UX boundary**: the review-before-live gate (F-02), the card-only write path vs. "never silently drop" (F-03), and the missing keyword-read path in the contract (F-05).
