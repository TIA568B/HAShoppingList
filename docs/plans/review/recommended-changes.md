# Recommended Changes

**Reviewer:** Independent senior technical reviewer (second agent)
**Date:** 2026-08-29
**Companion documents:** `consolidated-review.md` (full findings), `steering-review.md`,
`requirements-traceability.md`.

Recommendations are grouped by when they should be actioned. Each references its finding ID so it
can be traced back to the evidence. This document recommends changes; it does **not** apply them.

---

## Must Fix Before Implementation

These block starting the **frontend/sync phases (Phase 4–5)**. Backend Phases 0–3 may proceed in
parallel.

### MF-1 — Resolve the client-vs-backend write/finalization boundary and close the silent-drop gap
- **Affected:** `docs/plans/08-update-and-sync-strategy.md`,
  `docs/plans/09-error-handling-and-resilience.md`, `.kiro/steering/home-assistant.md`,
  `.kiro/steering/architecture.md`
- **Finding:** H-1 / F-03 / S-02
- **Problem:** Grace timer + retry live entirely in the card; a closed/backgrounded card can silently
  drop a completion, violating Req 5.4 and the architecture rule "no business logic the backend
  can't enforce."
- **Recommended change:** Choose and document one model. Preferred: **complete-on-tap with a
  reversing-undo window** (send `todo.update_item(completed)` immediately, offer undo that sends
  `needs_action` within the grace window) so nothing is ever silently lost. Alternative: a backend
  service that records/schedules the pending completion server-side. Update `08`/`09` accordingly,
  reconcile the two steering statements, and add a "card gone during grace period" test to `12`.
- **Reason:** Directly satisfies Req 5.4 and removes the sharpest reliability risk.
- **Priority:** Highest.

### MF-2 — Add frontend steering and widen test steering scope
- **Affected:** new `.kiro/steering/frontend.md`; `.kiro/steering/testing.md` (fileMatch)
- **Finding:** H-2 / S-01 / S-10
- **Problem:** The card (Req 3.x/4.x/5.4) is reached by only the three `always` steering files;
  `home-assistant.md`, `python.md`, and `testing.md` all scope it out.
- **Recommended change:** Create `frontend.md` (fileMatch `frontend/**`) covering: the sensor/service
  contract reference, per-item undo state machine, client retry rules (aligned with MF-1),
  XSS-safe rendering, accessibility, sanctioned HA websocket/service calls, and card
  resource registration/HACS packaging. Add the card's test path to `testing.md`'s fileMatch.
- **Reason:** The highest-risk, most requirement-dense component must have first-class guardrails.
- **Priority:** Highest.

### MF-3 — Resolve the Req 1.7 "review before live" open question
- **Affected:** `docs/plans/07-categorization-engine.md`, `docs/plans/15-risks-open-questions.md`
  (OQ5), `docs/plans/14-implementation-plan.md`
- **Finding:** M-1 / F-02
- **Problem:** A hard SHALL (Req 1.7) is reinterpreted as a live Uncategorized bucket on an
  unresolved assumption (OQ5 is still open).
- **Recommended change:** Get an explicit user decision. If the live-triage substitution is accepted,
  record it as a dated decision in `15` and add an acceptance test that the Uncategorized bucket is
  surfaced prominently on first setup. If not, add an explicit review-gate step to `07`/`14`.
- **Reason:** Prevents Phase 2/4 rework and closes a requirement-intent change.
- **Priority:** High.

---

## Should Fix Before Implementation

Address these before the phase they affect; most are cheap clarifications.

### SF-1 — Add a keyword-read path to the frontend contract (Req 6.1/6.2)
- **Affected:** `docs/plans/06-data-model-and-contract.md`, `docs/plans/11-frontend-card.md`
- **Finding:** M-2 / F-05
- **Problem:** No attribute or service exposes per-category keyword lists; the card cannot show them.
- **Recommended change:** Add a read channel — preferably a small read-only websocket command (also
  usable for large lists per M-4) or a `category_definitions` attribute. Update the `06` contract in
  the same change and bump `attributes_version` if the attribute shape changes.
- **Reason:** Makes Req 6.1 satisfiable. **Priority:** High (before Phase 3/5).

### SF-2 — Define source-entity-change behaviour vs. `unique_id`
- **Affected:** `docs/plans/04-ha-integration-design.md`, `docs/plans/12-testing-strategy.md`
- **Finding:** M-3
- **Problem:** `unique_id = source_entity_id` conflicts with an options-flow "change source entity"
  test; unique_id is not normally mutable in options.
- **Recommended change:** Decide: disallow source change (delete + re-add entry) or provide a
  reconfigure flow that updates `entry.data` and unique_id. Document in `04`; align the `12` test.
- **Reason:** Removes an untestable/ambiguous lifecycle case. **Priority:** Medium-High (Phase 2).

### SF-3 — Front-load a minimal manual validation of the two runtime assumptions
- **Affected:** `docs/plans/14-implementation-plan.md` (sequence), `docs/plans/15` (R1/R2)
- **Finding:** M-6 / R1 / R2
- **Problem:** Two-way sync value rests on unverified propagation-to-Alexa and uid-stability.
- **Recommended change:** Before investing in Phase 4/5, perform one manual `todo.update_item` on the
  real list in the implementation environment and confirm it appears on the Alexa app, and observe
  uid stability across two refreshes. Gate card work on this.
- **Reason:** Cheaply de-risks the entire frontend investment. **Priority:** Medium-High.
- **Note:** This is a **write** action and must be done in the implementation environment by the
  implementing party, **not** via the read-only review MCP.

### SF-4 — Specify concurrent Alexa-change-during-grace precedence
- **Affected:** `docs/plans/08-update-and-sync-strategy.md`, `docs/plans/11-frontend-card.md`,
  `docs/plans/12-testing-strategy.md`
- **Finding:** M-7
- **Problem:** No rule for when an item held in card `PendingComplete` is completed/deleted on Alexa
  directly.
- **Recommended change:** Define precedence (inbound change to a pending uid cancels the local timer /
  source wins) and add a test (inbound delete/complete of a pending item).
- **Reason:** Prevents finalize calls against stale/absent uids. **Priority:** Medium.

### SF-5 — State the reactivity latency contract explicitly
- **Affected:** `docs/plans/08-update-and-sync-strategy.md`, `docs/plans/14-implementation-plan.md`
- **Finding:** M-5 / R3
- **Problem:** Req 2.1 "few seconds" only holds on push; missed-push latency is ~5 min via upstream.
- **Recommended change:** Document the two-tier latency contract in `08`/`14` acceptance criteria and
  confirm the user accepts it.
- **Reason:** Aligns expectations with reality. **Priority:** Medium.

### SF-6 — Fix steering drift and the misleading entity-services nudge
- **Affected:** `.kiro/steering/testing.md`, `.kiro/steering/home-assistant.md`
- **Finding:** M-8 / S-03 / S-04
- **Problem:** Regression test hard-codes a user-specific entity id; services steering nudges toward
  entity services that don't fit config-entry-scoped category operations.
- **Recommended change:** Reword the regression rule to assert selection targets the `alexa_devices`
  **platform** (and never the `shopping_list` platform), not a specific id. Remove/qualify the
  "prefer entity services" line for this project.
- **Reason:** Portable, correct guardrails. **Priority:** Medium.

### SF-7 — Confirm the widened grace-period range (5–30s vs. spec 8–10s)
- **Affected:** `docs/plans/04-ha-integration-design.md`, `docs/plans/15` (decision log)
- **Finding:** L-7
- **Recommended change:** Confirm the 5–30s range is intended (spec target is 8–10s); record as a
  dated decision. Consider an 8s floor to respect the spec's intent.
- **Reason:** Keeps the plan traceable to the spec. **Priority:** Medium-Low.

---

## Can Be Addressed During Implementation

Refinements safe to fold into the relevant phase.

| ID | Affected | Change | Finding |
|----|----------|--------|---------|
| CI-1 | `07`, `15` | Note that the spec's "user-supplied export" seed path was considered and dropped (or keep as optional import). | L-1 / F-01 |
| CI-2 | `04`, manifest | Document why `after_dependencies` is intentionally not used; rely on `ConfigEntryNotReady`. | L-2 |
| CI-3 | `04`, `09` | Ensure first refresh distinguishes "source not ready yet" (retry / ConfigEntryNotReady) from "read failed" (UpdateFailed). | L-3 |
| CI-4 | `.kiro/steering/python.md` | Carve out `categorizer.py` as intentionally synchronous/pure. | L-4 / S-06 |
| CI-5 | `.kiro/steering/home-assistant.md` | Replace lossy `dict[str, list[CategorizedItem]]` coordinator-data type with a reference to the `Projection`/doc-06 contract. | L-5 / S-07 |
| CI-6 | `.kiro/steering/home-assistant.md` | Reframe diagnostics redaction around item text; drop nonexistent-credential framing. | L-6 / S-08 |
| CI-7 | new `frontend.md` or `04` | Add strings/translations discipline (abort reasons, error keys). | L-8 / S-09 |
| CI-8 | steering set | Consolidate the duplicated logging rule to one canonical location (per `documentation.md`). | L-9 / S-11 |
| CI-9 | `.kiro/steering/home-assistant.md` or `frontend.md` | Add sensor-attribute contract discipline: bump `attributes_version` on breaking change, keep item objects minimal, exclude sensor from recorder, websocket fallback for large lists. | M-4 / S-05 |
| CI-10 | implementers | Do not copy the `Dairy` sample JSON from `docs/specs/design.md` (spec typo, overridden). | O-1 |
| CI-11 | `15`, publishing | Finalize `codeowners`, repo URL, `hacs.json`, CI, `pyproject.toml`. | O-5 |

---

## Suggested sequencing

1. **Now (parallel with backend Phase 0–3):** MF-2, MF-3, SF-6, SF-7, and the steering CI-items.
2. **Before Phase 2:** SF-2, SF-5, CI-2/CI-3.
3. **Before Phase 3:** SF-1 (contract).
4. **Before Phase 4/5 (card):** MF-1, SF-3, SF-4, CI-9.
5. **Before release:** Phase 7 E2E (R1/R2 hard gate), CI-11.

Resolving MF-1, MF-2, and MF-3 moves the readiness decision from **CONDITIONALLY READY** to
**READY** for the frontend/sync phases.
