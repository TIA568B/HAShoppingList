# Follow-up Review 03 — Consolidated

**Reviewer:** Independent senior technical reviewer (second agent, third follow-up pass)
**Date:** 2026-08-29
**Trigger:** "Update your review based on the most recent version of the plan; tick off anything
addressed."
**Inputs re-read (via `git diff` + direct reads):** `docs/specs/requirements.md` (now includes
Req 7), `docs/plans/**`, `.kiro/steering/**`, `docs/plans/review/revision-summary.md`, read-only
HA MCP.
**Companion:** `status-ledger.md` (every prior finding + open question, with status).

---

## Executive Summary

Two things changed since Follow-up 02:

1. **All outstanding human-decision items are now resolved with recorded sign-offs.** OQ5 (Req 1.7
   review gate), OQ7 (complete-on-tap visibility), OQ3 (grace range), plus M-5 latency acceptance
   and M-6 spike authorisation are all marked "RESOLVED (user, 2026-08-29)" in `docs/plans/15`,
   with matching decision-log entries. The specs are preserved unchanged; the reinterpretations are
   documented, not silently applied.
2. **A new Requirement 7 (per-item shop preference) was added** to the spec and fully designed
   across the plan and steering.

Every prior finding is now **Addressed** or **Resolved by user** (see `status-ledger.md`): 15
first-review findings addressed, 3 resolved by user sign-off, 1 handled via an implementation gate,
all 5 third-agent findings addressed, and both Follow-up 02 observations closed. **No prior finding
remains open.**

The new Req 7 work is high quality and internally consistent. It introduces modest new scope, and
my review of it produced only Low/Observation findings — nothing that blocks progress.

### Readiness decision

> **READY for implementation — subject only to the implementation-environment validation gate
> (Phase 2.5 / Phase 7) and normal pre-publish housekeeping (OQ6).**

This is an upgrade from Follow-up 02's "CONDITIONALLY READY." The conditions that previously held
it back (human decisions) are resolved. What remains is not design work: it is a write-action spike
that can only run in the live environment (M-6), the end-to-end validation before release (Phase
7), and finalising `codeowners`/repo URL/`hacs.json` (OQ6). Backend Phases 0–3 and the frontend
phases are cleared to proceed in order.

### Finding count (this pass)

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 0 | — |
| Low | 2 | R7-L1, R7-L2 |
| Observation | 3 | R7-O1, R7-O2, R7-O3 |

---

## Requirement 7 (per-item shop preference) — review

### What it adds

Each item resolves to exactly one shop (default set Aldi/Asda/Tesco, plus a non-removable
`No Preference`), independently of its category. Resolution precedence: **shop name in item text >
learned override > shop keyword rule > No Preference**. Shops are user-managed with keyword rules,
learn over time, and delete-reassigns to `No Preference` (never deletes items). The projection is
regrouped **shop-primary, then category** (`shop_groups`), with independent manual collapse per
shop and per category.

### Strengths

- **Cleanly orthogonal.** Shop is a second pure resolver in `categorizer.py` fed by the same
  normalize pass; it does not entangle with category logic. `build_projection` returns both `shop`
  and `category` per item, so the card can re-pivot without recomputation.
- **Mirrors the category model consistently.** `shop_overrides` mirrors `overrides`;
  `add/edit/delete_shop` mirror the category services (including override migration on rename —
  the REVIEW2-003 lesson was applied proactively); `No Preference` mirrors `Uncategorized`.
- **Precedence is explicit and tested**, including the subtle rule that a shop name in the item
  text beats a learned override, with a dedicated test for exactly that case.
- **Storage discipline held.** Shop data lives only in the integration store (keyed by normalized
  text), never written to the Alexa list — preserving the rebuildable/no-drift principle (NFR3).
- **Contract versioning done right.** `attributes_version` bumped 2→3, correctly flagged as a
  **breaking** restructure (top-level `categories` → `shop_groups`), with the card told to honour
  the version. The store `schema_version` is correctly kept independent (FO-2).
- **Steering coverage is complete** — product, architecture, home-assistant, frontend, and testing
  steering all describe the shop dimension consistently.

### Findings on Req 7 (all Low / Observation)

#### R7-L1 — `attributes_version` 3 is breaking, but no card-migration/compat note for the contract change
- **Severity:** Low
- **Description:** v3 replaces the top-level `categories` array with `shop_groups`. `06` says the
  card must read `shop_groups` and degrade if the version is higher than it supports. Good — but
  because v2 was itself only just introduced, there is no statement of whether any v2 card could
  exist in the wild, nor a note that the sensor emits exactly one contract version (no dual
  emission). For a greenfield project shipping v3 as the first release this is harmless.
- **Recommendation:** Add one line to `06`/CHANGELOG when implementation starts: v3 is the initial
  shipped contract; earlier versions were internal design iterations only. Prevents future
  confusion about back-compat obligations.

#### R7-L2 — Shop-name-in-text matching needs the same collision care as keyword matching
- **Severity:** Low
- **Description:** `07` tier 1 matches a configured shop **name** as a whole word in the item text.
  If a user later adds a shop whose name is a common word (e.g. a shop literally named "Fresh" or
  "Local"), tier 1 could hijack ordinary items ("fresh bread" → shop "Fresh"). The default set
  (Aldi/Asda/Tesco) is safe; the risk is user-added shops with dictionary-word names.
- **Recommendation:** Note in `07`/`frontend.md` that shop-name matching is whole-word and
  case-insensitive, and consider warning (not blocking) when a new shop name is a common English
  word, or scoping tier-1 matching to a leading/trailing token. Low priority; document the edge.

#### R7-O1 — "No Preference last" vs. shopping ergonomics
- **Observation.** `No Preference` renders last. For a user who mostly hasn't assigned shops yet
  (early days, before learning kicks in), the most-populated group will be at the bottom. Not
  wrong — just worth confirming the ordering feels right in practice; easily revisited as a card
  option later.

#### R7-O2 — Interaction of shop keyword rules with the vegan/category keywords
- **Observation.** `milk` is both a category keyword (→ Milk) and a shop keyword (→ Aldi). The
  design correctly treats these as independent dimensions and documents the milk example. No
  conflict; flagged only because the same token driving two dimensions is the kind of thing that
  surprises people reading the map later. The docs already explain it.

#### R7-O3 — Test matrix does not assert the shop-settings panel reads `shop_definitions` (only backend service tests)
- **Observation.** `12` has strong backend shop tests and card render/collapse tests, and a
  "set item shop" card test. There is no explicit card test that the shop-settings panel renders
  from `shop_definitions` (the analogue of the category `category_definitions` read). Minor gap;
  add a card test row for symmetry when building Phase 5.

---

## Cross-document consistency (re-checked for Req 7)

- **Spec ↔ plan:** Req 7's 8 criteria + precedence map onto FR18–FR22 (`01`), the `07` resolver,
  the `06` contract/services, and the `12` matrix. Consistent.
- **Contract coherence:** `05` attribute list, `06` `shop_groups`/`shop_definitions`/per-item
  `shop`, and `11` card rendering agree; `attributes_version: 3` is stated consistently in `06`,
  `12`, and `14`.
- **Steering ↔ plan:** product (precedence + grouping), architecture (orthogonal dimension),
  home-assistant (services + precedence-in-categorizer), frontend (tree + manual collapse), and
  testing (shop matrix) all align with the plan. No contradictions.
- **Decisions/sign-offs:** `15` decision log records the shop feature, its precedence, and the
  user sign-offs (OQ3/5/7/8/9, M-5, M-6). Traceable.

## What remains (not blockers)

1. **M-6 / Phase 2.5 (implementation gate):** one manual write to confirm Alexa propagation + uid
   stability, before card work. Write action — implementer only.
2. **Phase 7 E2E (pre-release gate):** existing.
3. **OQ6 (housekeeping):** `codeowners`, repo URL, `hacs.json`, CI, `pyproject.toml`.
4. **Standing minor assumptions:** OQ2 (completed hidden by default) and OQ4 (deferred meat/milk
   confirm) — both low-risk and deferred by design.
5. **Req 7 polish:** R7-L1/R7-L2 documentation edges and R7-O3 test symmetry — fold into the
   relevant phase.

---

## Bottom line

The plan has converged. It absorbed every review finding, resolved the human-facing decisions with
recorded sign-offs, and added a well-integrated new feature (per-item shop preference) without
disturbing the core architecture or the no-drift/rebuildable guarantees. It is **ready to
implement**, with the only gates being the live-environment validation spike and normal
pre-publish tasks. The Req 7 findings are all Low/Observation and can be handled during the phases
that touch them.

## Confirmations

- No production code was implemented.
- No plans, specs, or steering were modified by me (I reviewed the applied changes; I did not
  author them).
- No prior review documents were modified; Follow-ups 01 and 02 are preserved as audit artefacts.
- The Home Assistant MCP was used strictly read-only; the environment is unchanged
  (`supported_features: 7`, state 14, HA 2026.8.3).
