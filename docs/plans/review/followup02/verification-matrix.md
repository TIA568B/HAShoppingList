# Follow-up Review 02 — Re-verification Matrix (remediation now applied)

**Reviewer:** Independent senior technical reviewer (second agent, second follow-up pass)
**Date:** 2026-08-29
**Purpose:** Re-verify, against the actual on-disk files, whether the remediation described in
`finding-disposition.md` / `revision-summary.md` has now been applied — after Follow-up 01 found
it had been *described but not applied*.

## Method

I used `git diff` against the committed baseline and read the changed regions directly, rather
than trusting the summary. Home Assistant MCP re-checked read-only. Every row below cites the
concrete on-disk evidence.

## Headline result

**The remediation is now genuinely applied and verified on disk.** `git diff --stat` shows 16
files changed (5 steering + 11 plan/README), `.kiro/steering/frontend.md` now exists, and
`docs/plans/review/revision-summary.md` now exists. Each first-review finding's claimed edit is
present and correctly targeted. This reverses Follow-up 01's Critical FU-1 (claimed-but-unapplied).

## First-review findings — re-verification

| Finding | Required change | On-disk evidence | Status |
|---|---|---|---|
| **H-1** | Complete-on-tap + reversing undo; remove deferred-timer silent-drop | `08` outbound section rewritten ("completion sent immediately on tap"; new sequence diagram); `11` state machine now `Unchecked→Completing→UndoWindow`; `09` "Why no deferred client-only finalize"; `15` decision-log entry; `frontend.md` "complete-on-tap (non-negotiable)" | **Resolved** |
| **H-2** | Add `frontend.md`; widen `testing.md` to card | `.kiro/steering/frontend.md` exists (fileMatch `frontend/**`); `testing.md` front-matter now `{tests/**,frontend/**}` | **Resolved** |
| **M-1** | Escalate Req 1.7 as human decision; add non-blocking review affordance | `07` step 3 rewritten (first-setup banner + prominent Uncategorized, "escalated for human confirmation"); `15` OQ5 marked "**needs human decision**"; `11` first-setup banner | **Resolved-pending-human-decision** |
| **M-2** | Expose per-category keywords for the card | `06` adds `category_definitions`; `05` attribute list adds it; `attributes_version` bumped 1→2 | **Resolved** |
| **M-3** | Define source-change vs unique_id | `04` new "Reconfigure flow" section (`async_step_reconfigure`, atomic data+unique_id via `async_update_reload_and_abort`); `testing.md` reconfigure case; `15` decision | **Resolved** |
| **M-4** | Capture attribute-size discipline in steering | `home-assistant.md` new "Sensor attribute contract discipline" subsection (minimal items, recorder exclusion, websocket fallback) | **Resolved** |
| **M-5** | State two-tier latency contract | `08` new "Latency contract (two-tier)" table; `14` Phase 2 acceptance updated; `15` R3 updated | **Resolved** |
| **M-6** | Front-load runtime-assumption spike | `14` new "Phase 2.5 — Runtime-assumption spike (WRITE action)" gating card work; order line `2 → 2.5 (gate) → 3`; `15` R1/R2 updated | **Resolved (impl-gated)** |
| **M-7** | Concurrent-change precedence | `08` new "Concurrent Alexa-direct change" section (source wins); `11` reconciliation rule; `12` test row | **Resolved** |
| **M-8** (S-03/S-04) | Platform-based regression; drop entity-services nudge | `testing.md` regression reworded to platform-based (no hard-coded id); `home-assistant.md` services now "config-entry-scoped… not entity services" | **Resolved** |
| **L-1** | Note export path dropped | `07` blockquote "Seed source — export path considered and dropped for v1" | **Resolved** |
| **L-2** | `after_dependencies` rationale | `04` blockquote "Why not `after_dependencies`" | **Resolved** |
| **L-3** | First-refresh ready-vs-failed distinction | `09` failure table row updated; `04` coordinator note; `home-assistant.md` error-handling bullet | **Resolved** |
| **L-4** (S-06) | Categorizer sync carve-out | `python.md` "Exception — the categorizer is intentionally synchronous and pure" | **Resolved** |
| **L-5** (S-07) | Coordinator `Projection` type | `home-assistant.md` coordinator bullet now references the `Projection` contract, not a bare dict | **Resolved** |
| **L-6** (S-08) | Diagnostics reframed to item text | `home-assistant.md` diagnostics rewritten; drops credential `REDACT_KEYS` framing | **Resolved** |
| **L-7** | Grace floor 8s | `04` options `8–30`; `15` OQ3 + decision-log; `08` note "range 8–30"; `12` out-of-range test | **Resolved** |
| **L-8** (S-09) | Strings/translations discipline | `04` "Strings / translations discipline"; `home-assistant.md` config/options/reconfigure section | **Resolved** |
| **L-9** (S-11) | De-duplicate logging rule | `security.md` marked "(canonical)"; `python.md` + `home-assistant.md` now reference it | **Resolved** |

## New findings raised by the third agent (REVIEW2-\*) — verification

| ID | Change | On-disk evidence | Status |
|---|---|---|---|
| REVIEW2-001 | Pin `todo.get_items` envelope; `summary→name` | `06` "Source `todo.get_items` response mapping (canonical)"; `04` coordinator step 2–3; `home-assistant.md` coordinator bullet; `12` test row | **Applied** |
| REVIEW2-002 | Add-item reconciliation via client token + normalized summary | `08` add-item section; `11` state-machine note; `12` add-item test row | **Applied** |
| REVIEW2-003 | `edit_category` migrates overrides on rename | `06` behavioural contract; `07` note; `14` Phase 3 acceptance; `home-assistant.md` services; `12` test row | **Applied** |
| REVIEW2-004 | Card asset cache-busting | `11` packaging; `frontend.md` packaging | **Applied** |
| REVIEW2-005 | Override learning is uid-independent | `07` normalize/override note | **Applied** |

## Follow-up 01 findings — status

| FU | Was | Now |
|----|-----|-----|
| FU-1 (Critical: claimed-but-unapplied) | Open | **Closed** — edits verified applied on disk this pass |
| FU-2 (Highs still open) | Open | **Closed** — H-1, H-2 resolved |
| FU-3 (missing `revision-summary.md`) | Open | **Closed** — file now exists and is substantive |
| FU-4 (Mediums open) | Open | **Closed** — all Mediums resolved (M-1 pending human sign-off) |
| FU-5 (Lows open) | Open | **Closed** — all Lows resolved |
| Followup01 refinement 1 (mis-tap trade-off explicit) | Requested | **Applied** — `08` "Accepted trade-off (mis-tap)" + `12` test |
| Followup01 refinement 2 (M-4 discipline lands, not just severity) | Requested | **Applied** — `home-assistant.md` subsection |
| Followup01 refinement 3 (M-1 stays human decision) | Requested | **Applied** — OQ5 flagged, requirement preserved |

## Environment re-verification (read-only MCP)

| Check | Result |
|---|---|
| `todo.david_carson_amazon_gmail_com_shopping_list` | state 14, `supported_features: 7` — unchanged |
| HA status | 2026.8.3 — unchanged |

No state-changing MCP operations were performed.

## Bottom line

All 19 first-review findings and all 5 third-agent new findings are **applied and verified on
disk**, and the two Follow-up 01 substantive refinements are incorporated. The only item not fully
"closed" is **M-1/OQ5**, which is correctly held open as a **human decision** (a hard-SHALL
requirement reinterpretation an agent must not self-approve), plus the pre-existing
implementation-environment gates (M-6 spike, Phase 7 E2E) that cannot run in a read-only task.
