# Consolidated Technical Review

**Project:** Categorized Alexa Shopping List (`alexa_shopping_categorizer`)
**Reviewer:** Independent senior technical reviewer (second agent in the workflow)
**Date:** 2026-08-29
**Review type:** Pre-implementation review of specifications, plans, architecture, and Kiro steering.

---

## Executive Summary

### Overall assessment

This is a **high-quality, unusually mature design package** for a greenfield project. The plans
are evidence-based: environment facts were verified via the read-only Home Assistant MCP, and the
three most important reality-based overrides (source entity, no history mining, custom integration
over pyscript) are correct and well-justified. The architecture is sound — a pure categorizer,
a `DataUpdateCoordinator`, a derived sensor as the single non-authoritative projection, and native
`todo.*` services as the single write path. The steering set is comprehensive on the backend.

I independently **verified the core environment claims** against the live instance (see Review
Scope). They hold up exactly.

The design is **not yet ready to enter implementation without resolving a small number of issues**,
concentrated at the **sync/UX boundary** and in **frontend steering coverage**. None of the issues
are architectural dead-ends; all are resolvable with focused clarification rather than redesign.

### Readiness decision

> **CONDITIONALLY READY — Resolve identified issues first.**

Specifically: resolve the **2 High** findings (H-1 card-only write path / "never silently drop";
H-2 frontend is effectively un-steered) and the **open product question** on the Req 1.7 review
gate (M-1) before starting Phase 4/5 (the card). Phases 0–3 (backend scaffolding, categorizer,
coordinator, sensor, services) are **ready to proceed** and are low-risk.

### Finding count by severity

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 0 | — |
| High | 2 | H-1, H-2 |
| Medium | 8 | M-1 … M-8 |
| Low | 9 | L-1 … L-9 |
| Observation | 5 | O-1 … O-5 |

(Steering findings S-01…S-11 and traceability findings F-01…F-05 are mapped into the unified
finding list below; the S-/F- IDs are retained as cross-references.)

### Biggest risks

1. **Silent loss of a tick-off completion** if the card is closed/backgrounded during a grace
   period or mid-retry — directly contradicts Req 5.4 ("never silently drops") and the
   architecture steering rule that the backend must be able to enforce card behaviour. (H-1)
2. **The frontend card is the most requirement-dense, security-sensitive component and has the
   least steering coverage** — three of the seven steering files scope it out. A fresh agent could
   ship an insecure or non-compliant card believing it followed steering. (H-2)
3. **An unresolved product decision** (drop the Req 1.7 "review before live" gate in favour of a
   live Uncategorized bucket) is still an open question but is baked into the plan. (M-1)
4. **Dependency on unverified runtime behaviour** — that `alexa_devices` writes propagate to the
   real Alexa app and that `uid`s are stable — is correctly flagged but cannot be validated in this
   read-only task; the whole two-way sync value proposition rests on it. (M-6)

---

## Review Scope

### Specifications reviewed (`docs/specs/`)
- `requirements.md` — 6 EARS requirements, 26 acceptance criteria. **Primary source of truth.**
- `design.md` — original pyscript-based design, data model, sequences, open questions.
- `tasks.md` — 5 dependency-ordered task waves.

### Plans reviewed (`docs/plans/`)
All 16 documents read in full: `README.md`, `00`–`15`.

### Steering files reviewed (`.kiro/steering/`)
All 7 read in full: `product.md`, `architecture.md`, `security.md`, `home-assistant.md`,
`python.md`, `testing.md`, `documentation.md`. Detailed findings in `steering-review.md`.

### MCP analysis performed (strictly read-only)
Independent validation of the plans' environment claims:

| Claim in plans | MCP verification | Result |
|----------------|------------------|--------|
| HA 2026.8.3, Europe/London, 263 components | `ha_status` | ✅ Confirmed |
| `todo.shopping_list` is native/empty (not Alexa) | `ha_get_entity` → state 0, platform `shopping_list`, `supported_features: 15` | ✅ Confirmed (note: it supports MOVE=8; the Alexa entity does not) |
| `todo.david_carson_amazon_gmail_com_shopping_list` is the Alexa list, `supported_features: 7`, 14 items | `ha_get_entity` / registry | ✅ Confirmed (platform `alexa_devices`, device `cd673d98…`) |
| No automations reference the source entity | `ha_find_automation_references` | ✅ Confirmed (none) |
| No `sensor.*_categorized` naming conflict | `ha_search_entities` | ✅ Confirmed (no matches) |
| Related entities: `bed_time` button, `to_do_list` | `ha_find_related_entities` | ✅ Confirmed |

No create/update/delete/enable/disable/call-service/state-changing MCP operations were performed.
The environment is unchanged.

---

## Readiness Decision (detail)

**CONDITIONALLY READY.** Rationale:

- The **backend design (docs 03–07, 09–10, 12–14)** is implementation-ready. Findings against it
  are Medium/Low refinements, not blockers.
- The **frontend and sync boundary (docs 08, 11)** carry the two High findings and one open
  product question. These should be resolved before Phase 4/5.
- No **Critical** findings: nothing invalidates the chosen architecture or violates safety/security
  in a way that forbids all progress.

Recommended gate: proceed with Phases 0–3 now; hold Phases 4–5 (card) until H-1, H-2, and M-1 are
resolved.

---

## Findings

Severity legend: **Critical** (must not proceed) / **High** (resolve before implementation) /
**Medium** (address before or during) / **Low** (improvement) / **Observation**.

---

### H-1 — Client-only write/retry path can silently drop a completion (violates Req 5.4)
- **Severity:** High
- **Area:** Sync / Reliability / Architecture
- **Cross-ref:** F-03, S-02
- **Description:** Docs `08` and `09` place the grace-period timer *and* the retry/backoff loop
  entirely in the card. If the card is closed, the tab is backgrounded/killed, or the browser dies
  between the tap and the grace-timer firing (or mid-retry), the completion is never sent and no
  error is surfaced. This contradicts Req 5.4 ("SHALL retry and SHALL surface a visible error
  rather than silently dropping the change") and `architecture.md`'s rule "No business logic in the
  card that the backend cannot also enforce."
- **Evidence:** `09` "The card performs the write; on failure it retries up to 3 attempts…";
  `08` "Grace-period timing lives in the card (client-side)"; `architecture.md` "What to avoid: No
  business logic in the card that the backend cannot also enforce."
- **Impact:** An item the user believes they ticked off never syncs to Alexa, silently — the exact
  failure Req 5.4 forbids. Undermines the two-way-sync value proposition.
- **Recommendation:** Decide and document one of: (a) accept the client-side timer as an explicit,
  reasoned exception, and constrain the risk (e.g. fire the completion immediately on tap and use a
  *reversing* undo call within the grace window, so a closed card cannot lose a completion — only
  lose the ability to undo, which is safer); or (b) move finalization to the backend (a service
  the card calls on tap that schedules/records the pending completion server-side). Option (a) is
  the smaller change and arguably better UX-safety (nothing is lost; worst case an un-undone
  completion syncs). Whichever is chosen, add a test for the "card gone during grace period" path.

### H-2 — The frontend card is effectively un-steered
- **Severity:** High
- **Area:** Kiro steering / Frontend
- **Cross-ref:** S-01, S-10
- **Description:** `home-assistant.md` (`custom_components/**`), `python.md` (`**/*.py`), and
  `testing.md` (`tests/**`) all scope away from `frontend/`. Only the three `always` files reach the
  card. The card owns Req 3.x, 4.x, and 5.4 — the most requirement-dense, security-sensitive UX —
  yet has no dedicated steering for its state machine, retry contract, accessibility, sanctioned
  APIs, or resource packaging.
- **Evidence:** front-matter of the three fileMatch steering files vs. `13-project-structure` placing
  the card under `frontend/`.
- **Impact:** Inconsistent, potentially insecure or non-compliant card implementation by a fresh
  agent; the highest-risk component has the weakest guardrails.
- **Recommendation:** Add `.kiro/steering/frontend.md` (fileMatch `frontend/**`) covering the card
  contract, per-item undo state machine, client retry rules (tied to H-1's resolution), XSS-safe
  rendering, accessibility, sanctioned HA websocket/service calls, and resource registration/HACS
  packaging. Widen `testing.md`'s fileMatch to include the card's test path.

---

### M-1 — Req 1.7 "review before live" gate reinterpreted; still an open question
- **Severity:** Medium — **Area:** Requirements / Product — **Cross-ref:** F-02
- **Description:** Req 1.7 is a hard SHALL: present the generated mapping for review *before it is
  used live*. `07` step 3 replaces this with a live `Uncategorized` triage bucket, and `15` OQ5
  still lists this as an **open question**. A hard requirement is being reinterpreted on an
  unresolved assumption.
- **Evidence:** `requirements.md` Req 1.7; `07` "No separate 'review before live' gate is
  required…"; `15` OQ5.
- **Impact:** If the user actually wants the gate, Phase 2/4 rework. It is also a genuine
  requirement-intent change.
- **Recommendation:** Resolve OQ5 with the user before Phase 4. If the live-triage substitution is
  accepted, record it as a dated decision in `15` and add a test asserting the Uncategorized bucket
  is surfaced prominently. If not, add a review-gate step.

### M-2 — No read path for per-category keyword lists (Req 6.1 view / 6.2 edit)
- **Severity:** Medium — **Area:** Data contract / HA — **Cross-ref:** F-05
- **Description:** All integration services are mutating; the sensor attributes expose items grouped
  by category but **not** the keyword lists per category. The card's settings panel needs to *read*
  keywords to let the user view/edit them (Req 6.1/6.2), but nothing in the contract exposes them.
- **Evidence:** `06` sensor attribute contract (no `keywords`); `04`/`06` services (all mutating);
  Req 6.1.
- **Impact:** Req 6.1 "display all categories and their associated keywords" is not satisfiable by
  the card as specified.
- **Recommendation:** Add either a read attribute (e.g. `category_definitions: [{name, keywords}]`)
  or a read-only websocket/service to expose the map. Prefer a small websocket command over
  inflating the sensor attribute (size, see M-4). Update `06` contract in the same change.

### M-3 — Options-flow source-entity change vs. `unique_id` = source entity id
- **Severity:** Medium — **Area:** HA integration lifecycle
- **Description:** `testing.md` requires an options-flow test for "source-entity change", and `04`
  sets `entry.unique_id = source_entity_id` with `_abort_if_unique_id_configured()`. Changing the
  source entity via options would desync `unique_id` from `entry.data.source_entity_id`, and
  `unique_id` is not normally mutable via the options flow. The plans do not describe how a source
  change reconciles the unique_id, the store key (`<entry_id>`-based, so safe), or the sensor
  unique_id (entry-based, safe).
- **Evidence:** `04` config flow (unique_id = source) vs. `testing.md` "Options flow: … source-entity
  change"; `06` store keyed by `entry_id`.
- **Impact:** Ambiguous/absent behaviour for a documented test case; possible confusing state or a
  no-op that the test can't actually exercise.
- **Recommendation:** Decide whether source-entity change is (a) not allowed (must delete & re-add
  the entry — simplest, aligns with unique_id-per-source) or (b) allowed via a reconfigure flow that
  updates `entry.data` and the unique_id. Document the choice in `04` and align the test in `12`.

### M-4 — Sensor attribute payload as the frontend contract risks the ~16 KB recorder/attribute limits
- **Severity:** Medium — **Area:** Data / HA — **Cross-ref:** S-05, R7
- **Description:** The full projection (categories, per-item objects, options, metadata) is carried
  as sensor `extra_state_attributes`. `06` acknowledges the ~16 KB cap and recommends recorder
  exclusion, and `15` R7 offers a websocket fallback "only if hit." For a single household this is
  fine, but the design commits the contract to the attribute channel up front, so the fallback would
  be a contract change later.
- **Evidence:** `06` "HA attribute size note"; `15` R7.
- **Impact:** Low probability for this user, but if hit, a breaking contract migration mid-life.
- **Recommendation:** Acceptable to proceed with attributes for v1 given the user profile. Add
  steering/plan note to keep item objects minimal and to treat a websocket command as the sanctioned
  growth path (bump `attributes_version` if the shape changes). Combine with M-2 (a websocket read
  for keywords could be the same channel).

### M-5 — Debounce + safety-poll interaction with the underlying 5-minute `alexa_devices` poll under-specified
- **Severity:** Medium — **Area:** Reliability / Sync
- **Description:** `08` sets our safety poll to 15 min and relies on `alexa_devices` push +
  its 5-min poll. Worst-case latency for a missed push is bounded by min(our 15m, their 5m) ≈ 5 min,
  not "a few seconds" (NFR1/Req 2.1). The plans mostly acknowledge this (`15` R3, "Accept; document
  expected latency") but the acceptance criteria in `14` Phase 2 still say "recomputes on source
  state_changed" without stating the missed-push latency bound. This is a known caveat, not fully
  reflected in acceptance criteria.
- **Evidence:** `08` reactivity; `15` R3; Req 2.1 "few seconds".
- **Impact:** Expectation mismatch: Req 2.1's "few seconds" only holds when push works.
- **Recommendation:** State the latency contract explicitly in `08`/`14` (few seconds on push;
  up to ~5 min on missed push via upstream poll) and confirm the user accepts it. Consider lowering
  the safety poll only if needed (respecting upstream rate posture — do not poll Amazon directly).

### M-6 — Core value proposition rests on two unverified runtime assumptions
- **Severity:** Medium — **Area:** Reliability / Assumptions — **Cross-ref:** R1, R2
- **Description:** That `todo.update_item`/`add_item` on the `alexa_devices` list propagate to the
  real Alexa app, and that `uid`s are stable, are both **assumptions** (correctly flagged in `02`,
  `15`). They cannot be validated in this read-only task. Everything in Req 5.x depends on the first;
  correct undo/complete targeting depends on the second.
- **Evidence:** `15` R1/R2, assumptions 1–2; `02` "not independently mutation-tested (MCP read-only)".
- **Impact:** If either is false, the sync feature is broken or targets the wrong item.
- **Recommendation:** Make Phase 7 E2E validation of R1/R2 a **hard gate before release** (already
  planned) and, importantly, front-load a minimal manual validation *before* investing in Phase 4/5
  card work — a single manual `todo.update_item` on the real list, observed on the Alexa app, de-risks
  the entire frontend investment cheaply.

### M-7 — Concurrent Alexa-direct change during a card grace period is not modelled
- **Severity:** Medium — **Area:** Data / State / Race conditions
- **Description:** `08`/`11` describe per-item optimistic state and reconcile-by-`uid`, and note a
  pending item "keeps its local state until its timer resolves, so an inbound no-op doesn't clobber
  the pending UI." But the case where the **same item is completed or deleted on Alexa directly while
  the card holds it in PendingComplete** is not specified. If Alexa deletes the item mid-grace, the
  finalize `update_item(uid)` will target a nonexistent uid.
- **Evidence:** `08` "keeps its local state until its timer resolves"; no handling of concurrent
  delete/complete of a pending uid.
- **Impact:** A finalize call could fail or act on a stale uid; reconciliation semantics unclear.
- **Recommendation:** Specify precedence: an inbound change to a `uid` that is locally Pending should
  either cancel the pending timer (source of truth won) or be handled explicitly. Add a test case
  (inbound delete/complete of a pending item).

### M-8 — Steering drift/misleading items (hard-coded entity id; entity-services nudge)
- **Severity:** Medium — **Area:** Steering — **Cross-ref:** S-03, S-04
- **Description:** `testing.md` bakes the user-specific entity id into a permanent regression test
  (should assert on the `alexa_devices` *platform*, not the id). `home-assistant.md` nudges toward
  entity services, which do not fit the config-entry-scoped category services.
- **Evidence:** `testing.md` Regression; `home-assistant.md` Services "Prefer entity services…".
- **Impact:** Brittle test tied to one account; possible awkward service design.
- **Recommendation:** Reword the regression test to assert platform-based selection; remove/qualify
  the entity-services line. See `steering-review.md` S-03/S-04.

---

### L-1 — History-mining override drops the spec's "user-supplied export" path without discussion
- **Severity:** Low — **Cross-ref:** F-01. Req 1.1 offered an export alternative; the plan seeds only
  from the live list. Note the export option and why it's dropped, or keep it as an optional import.

### L-2 — `manifest.json` `dependencies: ["todo"]` may be insufficient; consider `after_dependencies`
- **Severity:** Low — **Area:** HA. The integration depends on the `todo` **building block** (correct)
  but functionally also needs `alexa_devices` to have set up its entity. `dependencies: ["todo"]`
  does not guarantee `alexa_devices` load order. `ConfigEntryNotReady` on a missing source entity
  (planned in `04`) handles this at runtime, so it's not a blocker, but consider documenting why
  `after_dependencies` is intentionally not used.

### L-3 — `async_config_entry_first_refresh()` + immediate `todo.get_items` during setup
- **Severity:** Low — **Area:** HA. Calling `todo.get_items` (a service call) inside the first
  coordinator refresh during `async_setup_entry` is reasonable, but if `alexa_devices` is still
  setting up, the service/entity may transiently be absent. The `ConfigEntryNotReady` path covers it;
  ensure the first refresh distinguishes "entity not ready yet" (retry) from "read failed"
  (`UpdateFailed`). Worth an explicit note in `04`/`09`.

### L-4 — `python.md` async rule vs. sync categorizer not carved out
- **Severity:** Low — **Cross-ref:** S-06. State explicitly that `categorizer.py` is intentionally
  synchronous and pure.

### L-5 — Coordinator data type in steering is lossy
- **Severity:** Low — **Cross-ref:** S-07. `dict[str, list[CategorizedItem]]` cannot express order,
  `collapsed`, or top-level metadata; align steering with the `Projection`/`06` contract.

### L-6 — Diagnostics "redact credentials" framing invites dead code
- **Severity:** Low — **Cross-ref:** S-08. Emphasise item-text redaction; drop the nonexistent-
  credential framing.

### L-7 — Grace-period options range 5–30s vs. spec's 8–10s target
- **Severity:** Low — **Cross-ref:** F-09/NFR2. `04` allows 5–30s (default 9). Spec target is 8–10s.
  Allowing a wider range is a reasonable enhancement but exceeds the spec; confirm the widened range
  is intended (a 5s floor may feel rushed; a 30s ceiling is harmless). Record as a decision.

### L-8 — Missing steering for strings/translations discipline
- **Severity:** Low — **Cross-ref:** S-09. Abort reasons and error keys are referenced in plans but
  not steered.

### L-9 — Logging rule duplicated across three steering files
- **Severity:** Low — **Cross-ref:** S-11. Consolidate to a canonical location per
  `documentation.md`'s own no-duplication rule.

---

### O-1 — `design.md` sample JSON still shows a `Dairy` category
- **Observation.** Correctly identified as a spec typo (C3) and overridden in the plans. Left in the
  spec by design (specs are historical). No action needed beyond the existing override note; flagged
  so implementers don't copy the sample.

### O-2 — Friendly name of the source entity is "Shopping list" (lowercase L)
- **Observation.** MCP shows the friendly name as "Shopping list". Cosmetic; the config-flow dropdown
  should show friendly name + entity id (as planned in `04`). No action.

### O-3 — `attributes_version` is plan-invented infrastructure with no requirement
- **Observation.** — **Cross-ref:** F-04. Good practice; acceptable added scope.

### O-4 — 15-minute safety poll could be a config option
- **Observation.** Not required; fine as a constant for v1.

### O-5 — CI, `pyproject.toml`, `hacs.json` details are TBD (`15` OQ6)
- **Observation.** Expected at this stage; finalize before publishing.

---

## Positive observations (what the design gets right)

- **Reality-based overrides are correct and verified.** Source entity, no history mining, custom
  integration over pyscript — all confirmed sound; MCP validation matches the plans exactly.
- **Clean separation of concerns.** Pure categorizer, coordinator-owned recompute, single write
  target, derived non-authoritative sensor — this directly satisfies the no-drift NFR3.
- **Security posture is strong and consistent** across steering and plans: no credentials, local-only
  data, redacted diagnostics, XSS-safe rendering, no outbound calls, pinned deps, stdlib-first.
- **Testing strategy is concrete** with a real matrix mapped to requirements and coverage gates.
- **The vegan categorization rules — the product's non-negotiable core — are fully, correctly, and
  testably specified** across product steering, `07`, and the test matrix.
- **Open questions and assumptions are honestly surfaced** in `15` rather than hidden.

---

## Conclusion

The design is close to implementation-ready and reflects genuine engineering maturity. The path to
"READY" is short: resolve H-1 (sync-loss safety), H-2 (add frontend steering), and the M-1 open
product question, then proceed. Backend Phases 0–3 can begin immediately. See
`recommended-changes.md` for the prioritized action list and `steering-review.md` for the full
steering assessment.
