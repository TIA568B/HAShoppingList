# Follow-up Review 03 — Status Ledger (all findings + decisions)

**Reviewer:** Independent senior technical reviewer (second agent, third follow-up pass)
**Date:** 2026-08-29
**Baseline compared:** the plan/steering/spec state as of the latest edits (commit `additional
planning` plus uncommitted working-tree changes), verified via `git diff` and direct reads.
**Purpose:** For every finding and open question from all prior review rounds, record the current
status: **Addressed**, **Addressed (human-gated)**, **Resolved by user**, or **Open**.

## Legend

- **Addressed** — the plan/steering now handles it; verified on disk.
- **Resolved by user** — an open question that now carries a recorded user sign-off in `15`.
- **Addressed (impl gate)** — handled in the plan; execution belongs to the implementation
  environment (write action), not a read-only review.
- **Open** — still outstanding.

## First-review findings (H/M/L)

| ID | Title | Status | Evidence |
|----|-------|--------|----------|
| H-1 | Client-only write path can silently drop a completion | **Addressed** | Complete-on-tap + reversing undo across `08`/`09`/`11`, `frontend.md`, `architecture.md`; decision in `15` |
| H-2 | Frontend card effectively un-steered | **Addressed** | `frontend.md` exists; `testing.md` scope `{tests/**,frontend/**}` |
| M-1 | Req 1.7 review-gate reinterpreted; open question | **Resolved by user** | OQ5 "RESOLVED (user, 2026-08-29)" in `15`; non-blocking banner in `07`/`11`; spec preserved |
| M-2 | No read path for per-category keywords | **Addressed** | `category_definitions` in `06`/`05`; `attributes_version` bumped |
| M-3 | Options source-change vs unique_id | **Addressed** | Reconfigure flow in `04`; test in `12`; decision in `15` |
| M-4 | Attribute payload size discipline | **Addressed** | `home-assistant.md` "Sensor attribute contract discipline"; recorder exclusion; websocket fallback |
| M-5 | Reactivity latency contract under-specified | **Resolved by user** | Two-tier table in `08`; `14` acceptance; OQ/decision "M-5 latency accepted" in `15` |
| M-6 | Two unverified runtime assumptions | **Addressed (impl gate)** | Phase 2.5 spike in `14`; `15` R1/R2 + "M-6 spike authorised" |
| M-7 | Concurrent Alexa change during grace window | **Addressed** | "Source wins" in `08`/`11`; test in `12` |
| M-8 | Steering drift (hard-coded id) + entity-services nudge | **Addressed** | `testing.md` platform-based regression; `home-assistant.md` config-entry-scoped services |
| L-1 | Export seed path dropped without discussion | **Addressed** | `07` blockquote "export path considered and dropped" |
| L-2 | `after_dependencies` rationale | **Addressed** | `04` blockquote |
| L-3 | First-refresh ready-vs-failed distinction | **Addressed** | `09` table row; `04`; `home-assistant.md` |
| L-4 | Categorizer async carve-out | **Addressed** | `python.md` sync-exception bullet |
| L-5 | Coordinator `Projection` type | **Addressed** | `home-assistant.md` references contract |
| L-6 | Diagnostics credential framing | **Addressed** | `home-assistant.md` diagnostics reframed to item text |
| L-7 | Grace range 5–30 vs spec 8–10 | **Resolved by user** | `04` 8–30; OQ3 "RESOLVED (user)" in `15` |
| L-8 | Strings/translations discipline | **Addressed** | `04` + `home-assistant.md` |
| L-9 | Logging rule duplicated | **Addressed** | `security.md` canonical; `python.md`/`home-assistant.md` reference |

**First-review scorecard:** 15 Addressed, 3 Resolved by user (M-1, M-5, L-7), 1 Addressed via
impl gate (M-6). **0 Open.**

## Third-agent new findings (REVIEW2-\*)

| ID | Title | Status | Evidence |
|----|-------|--------|----------|
| REVIEW2-001 | `todo.get_items` field is `summary`, not `name` | **Addressed** | `06` canonical mapping; `04` coordinator; `home-assistant.md`; `12` |
| REVIEW2-002 | Add-item reconciliation key undefined | **Addressed** | `08` add flow (client token + normalized summary); `11`; `12` |
| REVIEW2-003 | `edit_category` rename orphans overrides | **Addressed** | `06` behavioural contract; `07`; `14`; `12` |
| REVIEW2-004 | Card asset cache-busting | **Addressed** | `11` packaging; `frontend.md` |
| REVIEW2-005 | uid re-add after delete / override re-apply | **Addressed** | `07` override note (uid-independent learning) |

## Follow-up 02 observations

| ID | Title | Status | Evidence |
|----|-------|--------|----------|
| FO-1 | Complete-on-tap is a visible reinterpretation of Req 4.1 | **Resolved by user** | OQ7 "RESOLVED (user, 2026-08-29)" in `15`; decision log |
| FO-2 | `attributes_version` vs store `schema_version` confusion | **Addressed** | `06` explicit "independent counters" note; `12` clarifying note |

## Open questions in doc 15

| OQ | Status |
|----|--------|
| OQ1 (to-do list out of scope) | Assumed yes; not contradicted — **effectively closed** |
| OQ2 (completed items hidden by default) | Assumed; **Open (minor)** — still an assumption, low risk |
| OQ3 (grace range) | **Resolved by user** |
| OQ4 (first-seen meat/milk confirm) | Deferred; **Open (minor, deferred by design)** |
| OQ5 (Req 1.7 review gate) | **Resolved by user** |
| OQ6 (codeowners/repo/hacs.json) | **Open** — pre-publish housekeeping |
| OQ7 (complete-on-tap visible) | **Resolved by user** |
| OQ8 (`milk`→Aldi shop keyword) | **Resolved by user** |
| OQ9 (auto-collapse kept alongside manual) | **Resolved by user** |

## New scope this round — Requirement 7 (per-item shop preference)

Added to `docs/specs/requirements.md` as Req 7 (8 acceptance criteria + precedence + notes) and
designed across the plan and steering. Traceability of the new requirement:

| Req 7 criterion | Plan | Test | Steering | Status |
|-----------------|------|------|----------|--------|
| 7.1 view/add/edit/remove shops + keyword rules; `No Preference` non-removable | `06` (`shops`, `shop_definitions`), `04` services, `11` panel | `12` shop services, shop_definitions | product, home-assistant, frontend | Covered |
| 7.2 assignment learns (persist) | `07` tier 2, `06` `assign_shop`/`shop_overrides` | `12` assign_shop | product | Covered |
| 7.3 keyword-rule match | `07` tier 3, `06` `shops[].keywords` | `12` "nappies"→Aldi | product | Covered |
| 7.4 shop name in text takes precedence | `07` tier 1 (beats override), `06` note | `12` "tesco nappies" (+ over learned) | product, home-assistant | Covered |
| 7.5 no signal → No Preference | `07` tier 4 | `12` no-signal→No Preference | product | Covered |
| 7.6 delete shop → items to No Preference | `06` `delete_shop`, `07` self-heal | `12` delete_shop; deleted-shop→NP | home-assistant | Covered |
| 7.7 group shop→category→items; independent collapse | `06` `shop_groups`, `11` tree + manual collapse | `12` render/collapse rows | product, frontend | Covered |
| 7.8 validate shop name (unique, reserved NP) | `06` `add_shop`/`edit_shop` contract | `12` add_shop duplicate/No Preference | home-assistant | Covered |

**Req 7 verdict:** fully traced across spec → plan → contract → tests → steering, and internally
consistent (shop is orthogonal to category, single shop per item, mirrors category
learning/delete semantics, never written to the Alexa list). New findings on Req 7 are in
`consolidated-followup.md` (all Low/Observation).

## Overall

Every prior High, Medium, and Low finding is **Addressed** or **Resolved by user**; the only items
that remain are (a) minor standing assumptions (OQ2, OQ4 — deferred by design), (b) pre-publish
housekeeping (OQ6), and (c) the implementation-environment validation gate (M-6 / Phase 7). No
open blocker remains in the design itself.
