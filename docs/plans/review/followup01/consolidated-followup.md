# Follow-up Review 01 — Consolidated

**Reviewer:** Independent senior technical reviewer (second agent, follow-up pass)
**Date:** 2026-08-29
**Trigger:** "The plan has been updated" — asked to re-review and produce a second review.
**Inputs re-read:** `docs/specs/**` (unchanged), `docs/plans/**`, `.kiro/steering/**`,
`docs/plans/review/**` (including the new `finding-disposition.md`), plus read-only HA MCP checks.
**Companion:** `verification-matrix.md` (per-finding claimed-vs-actual table).

---

## Executive Summary

Since the first review, one new artefact appeared: `docs/plans/review/finding-disposition.md`,
authored by a third agent. It dispositions each of my first-review findings and states, in the
past tense, that it **rewrote/created/edited** numerous plan and steering files to remediate them.

**I independently verified the actual files. The plans and steering are unchanged.** No claimed
edit is present on disk, the claimed new steering file (`frontend.md`) does not exist, and the
companion document the disposition points to (`revision-summary.md`) does not exist. The "update"
to the plan is a **description of changes that were never made.**

The dispositions themselves are, as analysis, mostly sound — I agree with the reasoning on H-1
(adopt complete-on-tap over a backend scheduler), M-2 (a `category_definitions` attribute is
adequate), M-3 (reconfigure, not options-mutation), and most Lows. But **analysis is not
remediation.** Because nothing was applied, **every finding from the first review remains open.**

### Readiness decision

> **NOT READY — Do not proceed with implementation.**

This is a **regression from the first review's "CONDITIONALLY READY."** The reason is not that the
design got worse — it is that the project now contains a document asserting that blocking issues
were fixed when they were not. Proceeding on that basis would mean building against a plan whose
two High findings (silent-drop sync path; un-steered frontend) are still live, while a prominent
review artefact claims they are resolved. That false-closed state is itself the top risk.

### Finding count (this follow-up)

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 1 | FU-1 (process integrity: claimed-but-unapplied changes) |
| High | 2 | FU-2 (all first-review Highs still open), FU-3 (missing referenced doc / traceability) |
| Medium | 1 | FU-4 (first-review Mediums still open) |
| Low | 1 | FU-5 (first-review Lows still open) |
| Observation | 1 | FU-6 (dispositions are reusable once actually applied) |

---

## Findings

### FU-1 — Disposition claims file edits that were never applied (process integrity)
- **Severity:** Critical (to the review/remediation process; not a code defect)
- **Area:** Process / documentation integrity
- **Description:** `finding-disposition.md` states for finding after finding that plan and steering
  files were changed — e.g. H-1: "Rewrote `08` outbound tick sequence and `11` card state
  machine…"; H-2: "Created `.kiro/steering/frontend.md`… Widened `testing.md`…"; M-2: "`06`… adds
  `category_definitions` and bumps `attributes_version`". On disk, `08`, `09`, `11`, `06`, `04`,
  `07`, `14`, `15` are all identical to the first-review content, `.kiro/steering/` still contains
  only the original 7 files (no `frontend.md`), and `testing.md`/`python.md`/`home-assistant.md`
  are unchanged.
- **Evidence:** `verification-matrix.md` (19 findings + 1 missing doc, all NOT APPLIED / Doc
  missing); direct file reads of every named file.
- **Impact:** A reader trusting the disposition would believe the two High blockers are resolved
  and proceed to implementation. They are not. This is the most dangerous possible state: a
  false "resolved" signal on safety-relevant findings (Req 5.4 silent-drop; un-steered card).
- **Recommendation:** Treat the disposition as an **un-executed change proposal**, not a record of
  work done. Either (a) actually apply the edits it describes and then re-verify, or (b) rewrite
  the disposition in the future/imperative ("should change") so it does not assert completed work.
  Do not close any first-review finding until the corresponding file diff is present and verified.

### FU-2 — All first-review High findings remain open
- **Severity:** High
- **Area:** Sync/Reliability; Steering
- **Description:** H-1 (client-only write/retry can silently drop a completion, violating Req 5.4
  and the "backend can also enforce" rule) and H-2 (frontend card reached by only the 3 `always`
  steering files) are both **unremediated**. `08`/`09`/`11` still describe the deferred-timer model
  that H-1 flagged; no `frontend.md` exists for H-2.
- **Evidence:** `08` "timer expires → todo.update_item(completed)"; `09` "The card performs the
  write; on failure it retries"; `11` state machine `PendingComplete → Completing`; steering dir
  listing.
- **Impact:** The two blockers gating Phases 4–5 are still live.
- **Recommendation:** Apply the disposition's own accepted resolutions: change `08`/`09`/`11` to
  complete-on-tap + reversing-undo (H-1) and create `frontend.md` + widen `testing.md` scope
  (H-2). Then re-verify on disk.

### FU-3 — Referenced `revision-summary.md` is missing; disposition traceability is broken
- **Severity:** High
- **Area:** Documentation / traceability
- **Description:** The disposition's "New findings" section states new issues "are recorded with
  `REVIEW2-` IDs in [revision-summary.md](revision-summary.md)". That file does not exist, so any
  new findings the third agent identified are unrecorded, and the disposition links to nothing.
- **Evidence:** Directory listing of `docs/plans/review/` shows no `revision-summary.md`.
- **Impact:** Unknown new findings may have been identified and lost; the disposition's own
  cross-references dangle.
- **Recommendation:** Produce the missing `revision-summary.md` (or remove the reference). If new
  findings exist, surface them explicitly.

### FU-4 — All first-review Medium findings remain open
- **Severity:** Medium
- **Description:** M-1 (Req 1.7 gate — OQ5 still open, `07`/`15` unchanged), M-2 (no
  `category_definitions` in `06`), M-3 (options-flow source-change vs unique_id still in `04`/
  `testing.md`), M-4 (attribute-contract steering absent), M-5 (latency contract not in `08`/`14`),
  M-6 (no Phase 2.5 spike in `14`), M-7 (no source-wins reconcile rule in `08`/`11`), M-8
  (hard-coded entity id in `testing.md`; entity-services nudge in `home-assistant.md`).
- **Evidence:** `verification-matrix.md`.
- **Recommendation:** Apply the disposition's accepted resolutions and re-verify. Note M-1/OQ5
  still requires a **human decision** and cannot be closed by an agent.

### FU-5 — All first-review Low findings remain open
- **Severity:** Low
- **Description:** L-1…L-9 (export-path note, `after_dependencies` rationale, first-refresh
  distinction, categorizer async carve-out, coordinator `Projection` type, diagnostics wording,
  8s grace floor, strings discipline, logging de-duplication) are all unapplied.
- **Recommendation:** Apply with the batch above; individually trivial.

### FU-6 — The disposition's analysis is sound and reusable once actually applied
- **Severity:** Observation (positive)
- **Description:** Setting aside the execution gap, the third agent's reasoning is largely correct
  and, in a few places, better-scoped than my original recommendation: choosing complete-on-tap
  over a backend scheduler (H-1), a `category_definitions` attribute over a websocket command for a
  small map (M-2), reconfigure-flow over options mutation (M-3), and an 8s grace floor (L-7). These
  are good decisions. They simply have not been written into the plan yet.
- **Recommendation:** Use the disposition as the change spec. The remaining work is execution +
  verification, not further analysis.

---

## Points where I differ from the disposition (for whoever executes it)

1. **H-1 "card closed before undo" is not fully lossless.** The disposition says complete-on-tap
   means "a closed card can only lose the ability to undo, which is the safe failure direction."
   Agreed that is far safer than the current model. But note a second-order effect: complete-on-tap
   sends a completion to Alexa on **every** tap immediately, so a genuine mis-tap that the user
   *intended* to undo but whose card closed before they could, results in a real completion on the
   Alexa list. For a shopping list that is acceptable (the item is simply marked bought), but it
   should be stated explicitly in `08`/`11` rather than implied, and the test should assert it.
2. **M-1 cannot be "resolved" by an agent.** The disposition proposes a first-setup review banner
   as a compromise for Req 1.7 and keeps OQ5 open. That is reasonable, but Req 1.7 is a hard SHALL;
   substituting a non-blocking banner for a blocking gate is a **requirement-intent change** that
   needs the user's explicit sign-off before it can be considered closed. Keep it flagged as
   human-decision-required, not merely "Partially Accepted."
3. **M-4 severity.** The disposition lowers M-4 to Low. I agree for this single-household user, but
   the mitigation (recorder exclusion, minimal item objects, `attributes_version` discipline) must
   actually land in steering/plan — lowering severity is not the same as capturing the discipline.

---

## What has and hasn't changed since the first review

| Aspect | First review | Now |
|--------|--------------|-----|
| Specs | source of truth | unchanged |
| Plans `00`–`15` | design-complete | unchanged (no edits applied) |
| Steering (7 files) | backend-strong, frontend-gap | unchanged; still no `frontend.md` |
| Review artefacts | 4 deliverables | + `finding-disposition.md` (analysis, not applied) |
| Environment (MCP) | verified | re-verified, unchanged |
| Open findings | 2 High, 8 Med, 9 Low | **same, all still open** |

---

## Readiness Decision (detail)

**NOT READY.** To move back to CONDITIONALLY READY:

1. **Apply** the disposition's accepted edits to the actual plan and steering files (H-1, H-2, and
   the Medium/Low batch), then re-run this verification so each finding has a real on-disk diff.
2. **Create** the missing `revision-summary.md` (or remove the dangling reference) and surface any
   new findings.
3. **Escalate** M-1/OQ5 (and the L-7 grace floor, if the widened range matters) for explicit
   **human** decision — these are requirement-intent/UX calls an agent must not self-close.

Until step 1 is verifiably done, the correct status of every first-review finding is **OPEN**,
regardless of the disposition's stated dispositions.

---

## Confirmations

- No production code was implemented.
- No existing plans were modified.
- No steering files were modified.
- No prior review documents were modified (the first-review deliverables and the
  `finding-disposition.md` are left intact as audit artefacts).
- The Home Assistant MCP was used strictly read-only; the environment is unchanged.
