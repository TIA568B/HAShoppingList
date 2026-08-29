# Follow-up Review 02 — Consolidated

**Reviewer:** Independent senior technical reviewer (second agent, second follow-up pass)
**Date:** 2026-08-29
**Trigger:** "Update your review based on the most recent updates."
**Inputs re-read:** `docs/plans/**` (via `git diff`), `.kiro/steering/**` (incl. new
`frontend.md`), `docs/plans/review/**` (incl. new `revision-summary.md`), read-only HA MCP.
**Companion:** `verification-matrix.md` (per-finding on-disk evidence).

---

## Executive Summary

Between Follow-up 01 and now, the remediation that had previously only been *described* has been
**actually applied to the files**. I verified this independently with `git diff` and direct reads
rather than trusting the summary again:

- 16 files changed (5 steering + 11 plan/README), `+363 / −114` lines.
- `.kiro/steering/frontend.md` now exists (the H-2 gap).
- `docs/plans/review/revision-summary.md` now exists (the FU-3 gap).
- Every first-review finding (2 High, 8 Medium, 9 Low) and all 5 third-agent new findings
  (REVIEW2-001…005) have concrete, correctly-targeted edits on disk.

The changes are not just present — they are **good**. The headline fix (H-1: complete-on-tap +
reversing undo) is the right call: it eliminates the silent-drop failure mode against Req 5.4,
keeps enforcement at the public `todo.*` service boundary, and avoids reintroducing server-side
pending state. The third agent also correctly identified three genuinely new issues I had missed
(REVIEW2-001 `summary` vs `name`, REVIEW2-002 add-item reconciliation key, REVIEW2-003 override
loss on rename), and the plan now handles them.

### Readiness decision

> **CONDITIONALLY READY — proceed, subject to human sign-off on the escalated decisions and the
> implementation-environment validation gate.**

This restores and improves on the first review's "CONDITIONALLY READY," and clears the Follow-up
01 regression ("NOT READY"). The remaining conditions are **not** design defects — they are
decisions that require a human, and a runtime validation that requires a write action:

1. **OQ5 / M-1 (human decision):** the Req 1.7 "review before live" hard SHALL is reinterpreted as
   a non-blocking first-setup review affordance. Correctly escalated and preserved in the specs.
   A human must accept this or ask for a blocking gate.
2. **OQ3 / L-7 (human decision, minor):** confirm the widened 8–30s grace range.
3. **M-5 (human acceptance):** confirm the "up to ~5 min on a missed push" worst-case latency.
4. **M-6 / Phase 2.5 (implementation gate):** a one-off manual write validating Alexa
   propagation + uid stability, to run in the implementation environment before card work.

Backend Phases 0–3 are ready now. Card Phases 4–5 are gated on Phase 2.5.

### Finding count (this pass)

| Severity | Count | Note |
|----------|-------|------|
| Critical | 0 | FU-1 (claimed-but-unapplied) is now **closed** |
| High | 0 | H-1, H-2 resolved |
| Medium | 0 open as defects | all resolved; M-1 held as human decision, M-6 as impl gate |
| Low | 0 | all resolved |
| Observation | 2 | FO-1, FO-2 below |

---

## Assessment of the remediation quality

### What was done well
- **H-1 resolution is architecturally sound.** Complete-on-tap makes the completion durable the
  moment it is tapped; the grace window governs undo only. The plan (`08`/`09`/`11`), the steering
  (`frontend.md`, `architecture.md`, `home-assistant.md`), and the tests (`12`) are all
  consistent on this — no residual references to the old deferred-timer model remain.
- **The mis-tap trade-off is stated explicitly** (Follow-up 01's refinement 1): `08` now says a
  mis-tap whose card closes before undo becomes a real completion, and calls this the acceptable
  direction versus silently losing an intended completion. A test asserts it. This is exactly the
  honesty I asked for.
- **`frontend.md` is a strong, first-class steering file** covering the contract, the
  complete-on-tap state machine, retry/error surfacing, source-wins reconciliation, add
  reconciliation, XSS-safe rendering (referencing `security.md` as canonical), accessibility,
  and cache-busted resource registration. The card is no longer under-steered.
- **Genuinely new findings caught.** REVIEW2-001/002/003 are real defects that would have bitten
  during implementation (a missing `summary` mapping, an impossible "reconcile by uid" on an item
  with no uid yet, and silent learning loss on category rename). Their fixes are precise.
- **Steering de-duplication and precision fixes** (L-4…L-9) are all applied cleanly; the logging
  rule is now canonical in `security.md` with references elsewhere, resolving the earlier
  self-contradiction with `documentation.md`.
- **Escalations are handled with discipline.** M-1/OQ5 is not silently self-resolved; the
  requirement is preserved in `docs/specs/` and flagged for human decision. That is the correct
  behaviour for a hard-SHALL reinterpretation.

### Where I still differ / minor cautions (Observations)

#### FO-1 — Complete-on-tap changes the felt behaviour of Req 4.1; ensure the user expects it
- **Observation.** The spec (Req 4.1) frames the grace period as happening *before* the completion
  is "finalized," which reads as "don't send until the timer expires." Complete-on-tap sends
  immediately and treats the window as undo-only. This is the safer engineering choice and I
  endorse it, but it is a **behavioural reinterpretation of Req 4.1**, not just an internal detail:
  a user watching the Alexa app will see the item complete instantly, not after ~9s. The decision
  log records the rationale, but this is arguably a second human-facing decision alongside OQ5.
  Recommend surfacing it briefly to the user for confirmation, or noting it in OQ-form like OQ5.
  Not a blocker.

#### FO-2 — `attributes_version` bumped to 2 but the migration test row still says "store v0→v1"
- **Observation.** `12` bumped the sensor snapshot to "contract v2" (good), but the migration test
  row is still `store v0→v1`. The **store** schema (version 1) and the **attributes_version** (2)
  are correctly independent, so this is not a defect — but a reader may conflate them. A one-line
  note in `06` or `12` clarifying that `attributes_version` (frontend contract) and the store
  `schema_version` (persistence) version independently would prevent confusion. Cosmetic.

Neither observation affects readiness.

---

## Cross-document consistency (re-checked)

- **Steering ↔ plan on the tick model:** consistent. `frontend.md`, `architecture.md`,
  `home-assistant.md`, `08`, `09`, `11`, `12` all describe complete-on-tap; no stale deferred-timer
  language remains.
- **Contract coherence:** `05` (attribute list), `06` (canonical contract, `category_definitions`,
  `attributes_version: 2`, `get_items` mapping), `11` (card reads `category_definitions`), and
  `home-assistant.md` (contract discipline) agree.
- **Lifecycle:** `04` reconfigure flow, unique_id invariant, and `testing.md`/`12` reconfigure test
  align (M-3 fully consistent).
- **Traceability:** the `12` test matrix now carries rows for H-1, M-2, M-3, M-7, L-7,
  REVIEW2-001/002/003 and the two follow-up card cases — coverage tracks the changes.

## What has changed since Follow-up 01

| Aspect | Follow-up 01 | Now |
|--------|--------------|-----|
| Claimed edits applied? | No (described only) | **Yes — verified on disk** |
| `frontend.md` | absent | present, substantive |
| `revision-summary.md` | missing | present, substantive |
| First-review findings | all open | all resolved (M-1 human-gated) |
| REVIEW2-001…005 | n/a | applied |
| Readiness | NOT READY | **CONDITIONALLY READY** |

---

## Readiness Decision (detail)

**CONDITIONALLY READY.** Recommended gating:

- **Proceed now:** Phases 0–3 (scaffolding, pure categorizer + store, config/coordinator/sensor,
  services). No open design defects block these.
- **Before Phases 4–5 (card):** complete the **Phase 2.5** manual write spike (M-6) in the
  implementation environment.
- **Obtain human sign-off** on OQ5/M-1 (Req 1.7 reinterpretation), and ideally FO-1 (complete-on-
  tap being immediately visible), plus quick confirmations on OQ3/L-7 and M-5.
- **Before release:** Phase 7 E2E hard gate (spec tasks 5.3–5.6).

Once the human decisions are recorded and the Phase 2.5 spike passes, this moves to **READY**.

---

## Confirmations

- No production code was implemented.
- No plans were modified by me (I reviewed the third agent's applied changes; I did not author
  them).
- No steering files were modified by me.
- No prior review documents were modified; Follow-up 01 is preserved as an audit artefact of the
  earlier claimed-but-unapplied state.
- The Home Assistant MCP was used strictly read-only; the environment is unchanged
  (`supported_features: 7`, state 14, HA 2026.8.3).
