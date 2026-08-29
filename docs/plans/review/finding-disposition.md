# Finding Disposition (Third-Agent Independent Evaluation)

**Evaluator:** Third agent (plan remediation / independent validation).
**Date:** 2026-08-29
**Inputs:** `docs/specs/**`, `docs/plans/**`, `docs/plans/review/**`, `.kiro/steering/**`, and
independent read-only Home Assistant MCP checks.

This document evaluates **every significant finding** from the second-agent review
(`consolidated-review.md`, `steering-review.md`, `requirements-traceability.md`) and assigns a
disposition. It does not modify the original review — that is preserved as an audit artefact.

## Independent environment re-verification (read-only MCP)

Before dispositioning, I re-checked the environment claims the findings depend on:

| Claim | MCP result | Verdict |
|-------|-----------|---------|
| HA 2026.8.3, Europe/London, 263 components | `ha_status` matches | Confirmed |
| Source entity `todo.david_carson_amazon_gmail_com_shopping_list`, `supported_features: 7`, state 14 | `ha_get_entity` matches | Confirmed |
| Native `todo.shopping_list`, `supported_features: 15` (includes MOVE=8), state 0 | `ha_get_entity` matches | Confirmed — the review's note that the native list supports MOVE and the Alexa list does not is accurate |
| No `sensor.*categorized*` naming conflict | `ha_search_entities` "categorized" → none | Confirmed |
| Only two `shopping` todo entities exist | `ha_search_entities` "shopping" → 2 | Confirmed |

No state-changing operations were performed. The environment is unchanged.

## Disposition summary

| Disposition | Findings |
|-------------|----------|
| Accepted | H-2, M-2, M-3, M-5, M-6, M-7, M-8 (S-03, S-04), L-4 (S-06), L-5 (S-07), L-6 (S-08), L-8 (S-09), L-9 (S-11), S-01, S-05, S-10 |
| Partially Accepted | H-1 (F-03, S-02), M-1 (F-02), M-4 (S-05), L-1 (F-01), L-7 |
| Challenged | — |
| Rejected | — |
| Deferred | — |
| Already Addressed | L-2, L-3, O-1, O-3, O-4, O-5 (documented; reinforced only) |

Note: no finding was fully rejected. Several recommendations were **narrowed** (Partially
Accepted) where the reviewer's proposed mechanism was heavier than needed; the reasoning is
recorded per finding.

---

## H-1 / F-03 / S-02 — Client-only write/retry path can silently drop a completion

- **Finding ID:** H-1 (cross-ref F-03, S-02)
- **Original Severity:** High
- **Validated Severity:** High
- **Disposition:** Partially Accepted

**Assessment.** The underlying defect is real and correctly identified. The plan (`08`, `09`)
places both the grace timer and the retry loop client-side, so a card that is closed,
backgrounded, or crashes between tap and timer-expiry never sends the completion and surfaces no
error — a direct violation of Req 5.4 ("never silently drops") and of the `architecture.md` rule
"no business logic in the card that the backend cannot also enforce."

I accept the defect. I **partially accept** the recommendation: the reviewer offered two options
((a) complete-on-tap with a reversing-undo window, or (b) a backend service that schedules the
pending completion). I adopt **option (a)** and reject option (b) as unnecessary.

**Evidence.**
- The source `alexa_devices` entity retains completed items and supports UPDATE
  (`supported_features: 7`, verified). Marking complete is reversible via
  `todo.update_item(status=needs_action)`. So "complete immediately, undo by reversing" loses
  nothing: the worst case is an un-undone completion that is *already* correctly synced.
- Option (b) (server-side scheduled completion) reintroduces backend-held pending state, a timer
  that must survive reload/restart, and a second code path to enforce — contradicting the
  design's "projection is rebuildable, no server-side item state" principle (`03`, `product.md`).
  It is more complex and less safe than (a).

**Decision.** Change the tick model to **complete-on-tap**: the card calls
`todo.update_item(status=completed)` immediately on tap (with bounded retry/backoff and
revert-on-exhaustion), then shows an Undo affordance for the grace window that calls
`todo.update_item(status=needs_action)`. Nothing is ever silently lost; a closed card can only
lose the *ability to undo*, which is the safe failure direction.

**Plan Changes.** Rewrote `08` outbound tick sequence and `11` card state machine to
complete-on-tap + reversing-undo; updated `09` retry semantics (retry is now on the immediate
completion, not a deferred timer); added the "card closed during grace window" behaviour
(completion already sent, undo simply unavailable). Added a decision-log entry in `15`.

**Steering Changes.** New `frontend.md` states the complete-on-tap rule as the sanctioned model
and explicitly blesses the client-side *undo window* as an accepted exception (timing only, never
correctness). Reconciled the `architecture.md` tension by noting the backend can always enforce
the end state because completion goes through the public `todo.*` service immediately.

**Remaining Risk.** If a completion's immediate retries all fail (Alexa outage) the card reverts
and surfaces an error — correct per Req 5.4. Covered by a new test (`sync: completion fails 3x →
revert + surface`) plus a "card gone before undo" note (no data loss by construction).

---

## H-2 / S-01 / S-10 — The frontend card is effectively un-steered

- **Finding ID:** H-2 (cross-ref S-01, S-10)
- **Original Severity:** High
- **Validated Severity:** High
- **Disposition:** Accepted

**Assessment.** Verified directly from steering front-matter: `home-assistant.md`
(`fileMatch: custom_components/**`), `python.md` (`**/*.py`), and `testing.md` (`tests/**`) all
exclude `frontend/`. Only the three `always` files (`product`, `architecture`, `security`) reach
the card. The card owns Req 3.x, 4.x, and 5.4 and renders untrusted user text — the most
requirement-dense and security-sensitive component has the weakest guardrails.

**Evidence.** Front-matter of the three fileMatch files vs. `13-project-structure` placing the
card under `frontend/`.

**Decision.** Create `.kiro/steering/frontend.md` (fileMatch `frontend/**`) and widen
`testing.md` to also match `frontend/**` so card tests receive the testing steering.

**Plan Changes.** None required (plan already describes the card in `11`); the gap was in
steering.

**Steering Changes.** Created `frontend.md` covering: the sensor-attribute + service contract
reference (canonical in `docs/plans/06`), the per-item undo state machine (complete-on-tap +
reversing undo per H-1), client retry/backoff rules, XSS-safe rendering (no raw `innerHTML`),
accessibility, the sanctioned HA websocket/service surface, and frontend-resource
registration/HACS packaging (S-10). Widened `testing.md` `fileMatchPattern` to include
`frontend/**`.

**Remaining Risk.** Low. The card is now first-class steered.

---

## M-1 / F-02 — Req 1.7 "review before live" gate reinterpreted; still an open question

- **Finding ID:** M-1 (cross-ref F-02)
- **Original Severity:** Medium
- **Validated Severity:** Medium
- **Disposition:** Partially Accepted

**Assessment.** The reviewer is correct that Req 1.7 is a hard SHALL and the plan (`07` step 3)
substitutes a live `Uncategorized` triage bucket, with OQ5 still open. I accept that this is a
genuine requirement reinterpretation that must be surfaced, not buried.

I **partially accept** the recommendation. The reviewer frames this as "get an explicit user
decision before Phase 4." That is right, but two nuances matter:

1. Per my mandate, I must **not** silently change a requirement, and I cannot obtain user sign-off
   myself. So the requirement stays; the tension stays documented as an open question.
2. The live-triage approach is defensible on the merits: nothing destructive happens without user
   action, the map is editable live, and the seed is non-authoritative (it never mutates the
   Alexa list). The spec's "review before live" intent was to prevent a bad auto-generated map
   from taking effect unreviewed — and because our map only affects *display grouping*, never the
   source list, the blast radius of an unreviewed map is cosmetic and fully reversible.

**Evidence.** Req 1.7; `07` step 3; `15` OQ5; the fact that seeding is display-only (`03`, `06`
— storage holds no item state, projection is derived).

**Decision.** Keep the live-triage substitution as the recommended v1 behaviour, but (a) make the
"first-setup surfaces Uncategorized prominently" behaviour an explicit, testable acceptance
criterion, and (b) offer a low-cost optional review affordance: on first setup the card shows a
one-time "Review categories" banner linking to the settings panel, satisfying the *intent* of
Req 1.7 without a blocking gate. OQ5 remains open pending user confirmation and is escalated in
the revision summary as a decision requiring human approval.

**Plan Changes.** `07` bootstrap step 3 reworded to describe the first-setup review banner and
the prominent Uncategorized surface; `14` Phase 4 acceptance criteria add "first-setup review
affordance is present"; `12` adds an acceptance test asserting the Uncategorized bucket and the
first-setup review banner are surfaced. `15` OQ5 updated to reflect the compromise and flagged as
needing human confirmation.

**Steering Changes.** None (this is plan/product detail, not a persistent rule).

**Remaining Risk.** If the user actually wants a hard blocking gate, this is Phase 2/4 rework of
bounded size. Escalated for human decision.

---

## M-2 / F-05 — No read path for per-category keyword lists (Req 6.1 view / 6.2 edit)

- **Finding ID:** M-2 (cross-ref F-05)
- **Original Severity:** Medium
- **Validated Severity:** Medium
- **Disposition:** Accepted (mechanism narrowed)

**Assessment.** Correct and material. Every service in `04`/`06` is mutating, and the sensor
attributes expose items grouped by category but **not** the keyword lists. Req 6.1 ("display all
categories and their associated keywords") is therefore not satisfiable by the card as specified.

**Evidence.** `06` sensor contract (no `keywords`); all services mutating; Req 6.1.

**Decision.** Add a **`category_definitions`** field to the sensor attribute contract:
`[{name, keywords}]`, ordered like `categories`. I narrow the reviewer's "prefer a websocket
command" recommendation: for a single-household map (a handful of categories, tens of keywords)
the payload is tiny, so a read attribute is simplest and needs no new transport. The websocket
command is retained only as the **large-list escape hatch** (ties to M-4), not the default.

**Plan Changes.** `06` sensor contract adds `category_definitions` and bumps `attributes_version`
to reflect the additive change; `11` settings panel reads `category_definitions`; `12` adds a
test that `category_definitions` matches the stored map.

**Steering Changes.** `frontend.md` references the contract (canonical in `06`) including
`category_definitions` as the read source for the settings panel.

**Remaining Risk.** Low. If the map ever grows large, the websocket fallback (M-4) applies.

---

## M-3 — Options-flow source-entity change vs. `unique_id` = source entity id

- **Finding ID:** M-3
- **Original Severity:** Medium
- **Validated Severity:** Medium
- **Disposition:** Accepted

**Assessment.** Correct lifecycle inconsistency. `04` sets `unique_id = source_entity_id` with
`_abort_if_unique_id_configured()`, yet `testing.md` lists an options-flow "source-entity change"
test. `unique_id` is not mutable through the standard options flow, so that test case is
ambiguous/untestable as written.

**Evidence.** `04` config flow; `testing.md` options-flow area; `06` store keyed by `entry_id`
(so the store is safe either way).

**Decision.** Disallow source-entity change via the options flow. Changing the source is a
**reconfigure** operation (HA `async_step_reconfigure`) that updates `entry.data.source_entity_id`
and the `unique_id` atomically, or the user deletes and re-adds the entry. This aligns with
one-config-entry-per-source and keeps the unique_id invariant.

**Plan Changes.** `04` options flow explicitly excludes source-entity change and documents the
reconfigure path; `12` replaces the "options flow: source-entity change" case with a
"reconfigure flow updates source + unique_id" case.

**Steering Changes.** `testing.md` options-flow bullet reworded from "source-entity change" to
"reconfigure flow: source change updates data + unique_id".

**Remaining Risk.** Low.

---

## M-4 / S-05 — Sensor attribute payload as the contract risks the ~16 KB limit

- **Finding ID:** M-4 (cross-ref S-05, R7)
- **Original Severity:** Medium
- **Validated Severity:** Low
- **Disposition:** Partially Accepted (severity lowered)

**Assessment.** The concern is real in general but **over-rated for this project**. The primary
user is a single household with a shopping-list-sized map (tens to low hundreds of items). `06`
already acknowledges the ~16 KB cap, recommends recorder exclusion, and `15` R7 defines a
websocket fallback. I lower the severity to **Low**: the probability of hitting the cap for this
user is negligible, and the mitigation path already exists.

**Evidence.** `06` attribute-size note; `15` R7; single-household user profile (`product.md`).

**Decision.** Proceed with attributes for v1 (now including `category_definitions` from M-2).
Capture the discipline as steering so it is not lost: keep item objects minimal, exclude the
sensor from recorder, bump `attributes_version` on breaking shape changes, and treat a websocket
command as the sanctioned growth path if a very large list ever appears.

**Plan Changes.** `06` reinforced (already largely present); `05` recorder-exclusion note kept.

**Steering Changes.** Added a "sensor attribute contract" subsection to `home-assistant.md` and a
reference in `frontend.md`.

**Remaining Risk.** Low; monitored via R7.

---

## M-5 / R3 — Reactivity latency contract under-specified

- **Finding ID:** M-5 (cross-ref R3)
- **Original Severity:** Medium
- **Validated Severity:** Low-Medium
- **Disposition:** Accepted

**Assessment.** Correct. Req 2.1's "few seconds" holds only when the `alexa_devices` push works;
on a missed push, worst-case latency is bounded by the upstream 5-minute poll (min of our 15-min
safety poll and their 5-min poll ≈ 5 min). `08`/`14` did not state this bound in acceptance
criteria.

**Evidence.** `08` reactivity; `02` (`alexa_devices` SCAN_INTERVAL=300 + push); Req 2.1.

**Decision.** Document a two-tier latency contract explicitly.

**Plan Changes.** `08` states: "few seconds on push; up to ~5 min on a missed push via the
upstream poll." `14` Phase 2 acceptance criteria updated to reference the two-tier bound.

**Steering Changes.** None (plan-level detail).

**Remaining Risk.** Expectation only; flagged for user acceptance in `15` R3 (already accepted
there).

---

## M-6 / R1 / R2 — Core value rests on two unverified runtime assumptions

- **Finding ID:** M-6 (cross-ref R1, R2)
- **Original Severity:** Medium
- **Validated Severity:** Medium
- **Disposition:** Accepted

**Assessment.** Correct. Two-way sync depends on (1) `todo.update_item`/`add_item` on the
`alexa_devices` list propagating to the real Alexa app, and (2) `uid` stability. Both are
assumptions (`02`, `15`) and cannot be validated in a read-only task.

**Evidence.** `15` R1/R2, assumptions 1–2; `02` "not independently mutation-tested".

**Decision.** Accept the recommendation to **front-load a minimal manual validation** of R1/R2 in
the implementation environment *before* investing in the card (Phase 4/5), in addition to the
existing Phase 7 hard gate. This is a **write** action and is explicitly out of scope for this
read-only planning task — it is a task for the implementer.

**Plan Changes.** `14` adds "Phase 2.5 — Runtime assumption spike (implementer, write action):
one manual `todo.update_item` on the real list observed on the Alexa app; observe uid stability
across two refreshes" as a gate before Phase 4/5. `15` R1/R2 mitigation updated to reference the
early spike.

**Steering Changes.** None.

**Remaining Risk.** If R1 is false the sync feature is not viable; the early spike caps wasted
effort at the backend phases. Escalated as a pre-card gate.

---

## M-7 — Concurrent Alexa-direct change during a card grace period not modelled

- **Finding ID:** M-7
- **Original Severity:** Medium
- **Validated Severity:** Low-Medium
- **Disposition:** Accepted (largely dissolved by H-1 resolution)

**Assessment.** Correct race. With the *original* deferred-timer model, an item held in
`PendingComplete` could be deleted on Alexa mid-window, and the later finalize `update_item(uid)`
would target a nonexistent uid.

The H-1 resolution (complete-on-tap) **removes most of this window**: there is no deferred
finalize call, because completion is sent immediately. The remaining case is narrower: an inbound
**delete** of an item the user just completed, arriving while the card still shows the reversing-
undo affordance. If the user then taps Undo, the `update_item(status=needs_action)` targets a uid
that no longer exists.

**Evidence.** `08` reconciliation note; the reversing-undo model in the H-1 resolution.

**Decision.** Specify precedence: **inbound source state wins.** When a sensor update shows a uid
has been removed/changed, the card cancels any local undo affordance for that uid (the undo
button disappears). An undo call that nonetheless races and targets a missing uid is treated as a
benign no-op/handled error (surfaced softly, not a hard failure).

**Plan Changes.** `08` and `11` add the "inbound change to a locally-tracked uid cancels the
local affordance (source wins)" rule; `12` adds a test (inbound delete of an item in the undo
window cancels the undo affordance).

**Steering Changes.** `frontend.md` states the "source wins on reconcile-by-uid" rule.

**Remaining Risk.** Low; the failure direction is safe (a stale undo becomes a no-op).

---

## M-8 / S-03 / S-04 — Steering drift and misleading entity-services nudge

- **Finding ID:** M-8 (cross-ref S-03, S-04)
- **Original Severity:** Medium
- **Validated Severity:** Medium
- **Disposition:** Accepted

**Assessment (S-03).** Correct. `testing.md` bakes the account-specific entity id
`todo.david_carson_amazon_gmail_com_shopping_list` into a permanent regression test. The config
flow makes the source user-selectable and the entity id can change with the Amazon account, so
asserting a specific id is brittle and install-specific. The correct invariant is **platform-
based**: selection targets an `alexa_devices` todo entity and never silently picks the
`shopping_list` platform.

**Assessment (S-04).** Correct. `home-assistant.md` "Prefer entity services where a target entity
makes sense" nudges toward entity services, but the category services operate on the config
entry / shared category map (`06` models them with an optional `entry_id` `config_entry`
selector), not on an entity. Entity services would be an awkward fit.

**Evidence.** `testing.md` Regression; `home-assistant.md` Services; `06` service signatures.

**Decision.** Accept both.

**Plan Changes.** None (plans already model services correctly with `entry_id`).

**Steering Changes.** `testing.md` regression rule reworded to assert **platform-based** selection
(`alexa_devices`, never `shopping_list`), no specific entity id. `home-assistant.md` services
section removes/qualifies the "prefer entity services" line, stating category services are
config-entry-scoped and use an optional `entry_id` selector.

**Remaining Risk.** None.

---

## L-1 / F-01 — History-mining override drops the spec's "user-supplied export" path

- **Finding ID:** L-1 (cross-ref F-01)
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Partially Accepted

**Assessment.** Correct that the spec (Req 1.1) offered "a user-supplied export" as an alternative
seed source, and the plan seeds only from the live list without discussing the export path. I
accept documenting the decision. I **do not** accept building an import feature for v1 — with a
learn-over-time model and a non-authoritative map, an import path is unjustified scope for a
single-household v1. The live list (active + completed, 14+ items) plus learning is sufficient.

**Evidence.** Req 1.1; `01` C2; `15` decision log; the learn-over-time design.

**Decision.** Document that the export path was considered and deliberately not adopted for v1
(and could be a future optional import), rather than implementing it.

**Plan Changes.** `07` bootstrap and `15` decision log note the export alternative was considered
and dropped for v1 with rationale.

**Steering Changes.** None.

**Remaining Risk.** Low; thin initial corpus is mitigated by learning over time.

---

## L-2 — `dependencies: ["todo"]` vs. `after_dependencies`

- **Finding ID:** L-2
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Already Addressed (reinforced)

**Assessment.** Correct that `dependencies: ["todo"]` guarantees the `todo` building block but not
`alexa_devices` load order. The plan already handles this at runtime via `ConfigEntryNotReady`
(`04`), which is the idiomatic approach — `after_dependencies: ["alexa_devices"]` would couple us
to a specific integration we intentionally treat as a generic `todo` provider. No change to
behaviour needed; only a documentation note.

**Decision.** Add a one-line rationale to `04` that `after_dependencies` is intentionally not
used (source may be any `todo` provider; `ConfigEntryNotReady` covers ordering).

**Plan Changes.** `04` note added. **Steering Changes.** None.
**Remaining Risk.** None.

---

## L-3 — First refresh must distinguish "not ready yet" from "read failed"

- **Finding ID:** L-3
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Already Addressed (reinforced)

**Assessment.** Reasonable refinement. `04`/`09` already imply `ConfigEntryNotReady` when the
source is absent and `UpdateFailed` on read errors; making the distinction explicit at first
refresh is a worthwhile clarification.

**Decision.** Clarify in `09`: at first refresh, source-entity-absent/`unavailable` →
`ConfigEntryNotReady` (retry); a genuine read error with the entity present → `UpdateFailed`.

**Plan Changes.** `09` failure table note added. **Steering Changes.** None.
**Remaining Risk.** None.

---

## L-4 / S-06 — `python.md` async rule vs. synchronous categorizer

- **Finding ID:** L-4 (cross-ref S-06)
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Accepted

**Assessment.** Correct minor ambiguity: `python.md` says "Public integration functions are
`async`," but `categorizer.py` is intentionally pure and synchronous. A literal reader might make
pure functions async needlessly.

**Decision.** Carve out the categorizer explicitly.

**Steering Changes.** `python.md` async section states the categorizer is intentionally
synchronous and pure; the coordinator offloads heavy work if ever needed.
**Plan Changes.** None. **Remaining Risk.** None.

---

## L-5 / S-07 — Coordinator data type in steering is lossy

- **Finding ID:** L-5 (cross-ref S-07)
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Accepted

**Assessment.** Correct. `home-assistant.md` pins the coordinator data as
`dict[str, list[CategorizedItem]]`, which cannot express category order, `collapsed`, or
top-level metadata defined in `06`.

**Decision.** Replace the lossy type with a reference to the `Projection`/contract in `06`.

**Steering Changes.** `home-assistant.md` coordinator section now references the `Projection`
type defined in `docs/plans/06` rather than a bare dict.
**Plan Changes.** None. **Remaining Risk.** None.

---

## L-6 / S-08 — Diagnostics "redact credentials" framing invites dead code

- **Finding ID:** L-6 (cross-ref S-08)
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Accepted

**Assessment.** Correct. The integration holds no credentials; the "credentials redacted" framing
could invite a dead `REDACT_KEYS` set. The real redaction target is item text (opt-in).

**Decision.** Reframe around item-text redaction.

**Steering Changes.** `home-assistant.md` diagnostics section reworded to emphasise item-text
redaction and drop the credential framing.
**Plan Changes.** None (`10` is already correct). **Remaining Risk.** None.

---

## L-7 — Grace-period options range 5–30s vs. spec's 8–10s

- **Finding ID:** L-7
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Partially Accepted

**Assessment.** Correct that `04` allows 5–30s while the spec target is 8–10s. A wider range is a
reasonable enhancement, but a 5s floor may feel rushed relative to the spec's intent.

**Decision.** Keep a widened range but raise the floor to **8s** (range 8–30s, default 9s) to
respect the spec's lower bound; record as a dated decision. I partially accept: the reviewer
suggested confirming/considering an 8s floor — I adopt the 8s floor rather than leaving it open.

**Plan Changes.** `04` options range changed to 8–30s (default 9); `15` decision log entry added.
`12` options-flow test value stays within range.
**Steering Changes.** None.
**Remaining Risk.** None.

---

## L-8 / S-09 — Missing steering: strings/translations discipline

- **Finding ID:** L-8 (cross-ref S-09)
- **Original Severity:** Low
- **Validated Severity:** Low
- **Disposition:** Accepted

**Assessment.** Correct low-impact gap: no steering enforces keeping `strings.json` /
`translations/en.json` in sync or defining abort/error keys (`no_alexa_lists`,
`already_configured`).

**Decision.** Add a short strings/translations discipline rule.

**Steering Changes.** Added to `home-assistant.md` (config/options-flow UX): keep `strings.json`
and `translations/en.json` in sync; define abort reasons and error keys as constants.
**Plan Changes.** None. **Remaining Risk.** None.

---

## L-9 / S-11 — Logging rule duplicated across three steering files

- **Finding ID:** L-9 (cross-ref S-11)
- **Original Severity:** Observation/Low
- **Validated Severity:** Low
- **Disposition:** Accepted

**Assessment.** Correct. The "item text at debug only; never credentials/full contents at info+"
rule appears near-verbatim in `security.md`, `python.md`, and `home-assistant.md`, contradicting
`documentation.md`'s own no-duplication rule and risking desync.

**Decision.** Make `security.md` canonical; have `python.md` and `home-assistant.md` reference it
rather than restating the full rule.

**Steering Changes.** `security.md` marked canonical for logging restrictions; `python.md` and
`home-assistant.md` logging bullets shortened to a reference.
**Plan Changes.** None. **Remaining Risk.** None (rule unchanged, just de-duplicated).

---

## S-01, S-05, S-10 — Steering gaps (frontend, attribute contract, HACS packaging)

Covered above under H-2 (S-01), M-4 (S-05), and H-2 (S-10). All Accepted and folded into the new
`frontend.md` and the `home-assistant.md` attribute-contract subsection.

---

## O-1 … O-5 — Observations

- **O-1** (`design.md` sample shows `Dairy`): Already Addressed — correctly noted as a spec typo
  overridden in `07`/`01` C3. Specs are historical and left untouched by design. Reinforced only
  by keeping the override note. No change.
- **O-3** (`attributes_version` has no requirement): Already Addressed — good engineering, minor
  added scope, acceptable. No change.
- **O-4** (15-min poll as config option): Already Addressed — fine as a constant for v1. No change.
- **O-5** (CI / `pyproject.toml` / `hacs.json` TBD): Already Addressed — expected pre-publish;
  tracked in `15` OQ6. No change beyond keeping the open item.

---

## New findings

New issues discovered during this evaluation are recorded with `REVIEW2-` IDs in
[revision-summary.md](revision-summary.md) (New Findings section) and incorporated into the plan
where accepted.

---

## Follow-up Review 01 findings (FU-1 … FU-6)

After drafting the dispositions above, I discovered `docs/plans/review/followup01/`, a second-agent
follow-up pass. It found that an **earlier** version of this disposition asserted file edits in the
past tense that had **never been applied** to disk (its Critical finding FU-1). That was a genuine
process-integrity failure. This section dispositions the follow-up's findings.

### FU-1 — Disposition claimed edits that were never applied
- **Validated Severity:** Critical (process) — **Disposition:** Accepted → **Resolved this session.**
- **Assessment.** The follow-up was correct: at the time of its verification, none of the claimed
  plan/steering edits existed, `frontend.md` was absent, and `revision-summary.md` was missing.
- **Decision.** In this session I have **actually applied** every edit the disposition describes.
  Verified on disk: `frontend.md` now exists in `.kiro/steering/`; `06` carries
  `attributes_version: 2` + `category_definitions`; `08`/`09`/`11` use complete-on-tap; `14` has
  Phase 2.5; `testing.md` scope is `{tests/**,frontend/**}` with a platform-based regression rule;
  `home-assistant.md`/`python.md`/`security.md` carry the S-04/S-06/S-07/S-08/S-09/S-11 fixes.
  `revision-summary.md` exists. The disposition's claims are now backed by real diffs.
- **Remaining Risk.** None beyond normal re-verification, which any subsequent reviewer should run.

### FU-2 — All first-review Highs still open — **Resolved.** H-1 and H-2 edits are applied (above).
### FU-3 — Missing `revision-summary.md` — **Resolved.** The file now exists and lists REVIEW2-001…005.
### FU-4 — All first-review Mediums still open — **Resolved.** M-1…M-8 edits applied (see per-finding entries and the verification greps this session).
### FU-5 — All first-review Lows still open — **Resolved.** L-1…L-9 edits applied.
### FU-6 — Disposition analysis is sound and reusable — **Accepted (positive).** The analysis stands; it is now executed rather than merely described.

### Follow-up's substantive differences (dispositioned)
1. **Mis-tap under complete-on-tap is not fully lossless.** Accepted. Stated explicitly in `08`
   and asserted by a test in `12` (a mis-tap whose card closes before undo becomes a real, safe
   completion). This is the correct trade-off vs. silently losing an intended completion.
2. **M-1 cannot be closed by an agent.** Accepted. OQ5 remains **human-decision-required**; the
   requirement is preserved in `docs/specs/` and the plan only adds a non-blocking review
   affordance. Escalated in the revision summary's "Decisions Requiring Human Approval".
3. **M-4 discipline must land, not just severity change.** Accepted. The recorder-exclusion /
   minimal-item-object / `attributes_version` discipline is now written into `home-assistant.md`
   and referenced from `frontend.md`, not merely down-graded in severity.

**Net effect:** the FU-1 false-closed state is corrected — remediation is applied and verifiable,
not described. The correct next step is an independent re-verification pass (as the follow-up
itself recommends) plus the human decisions on OQ3/OQ5/M-5/M-6.

---

## Follow-up Review 02 observations (FO-1, FO-2)

Follow-up 02 independently verified (via `git diff`) that all remediation is now applied on disk
and moved readiness to **CONDITIONALLY READY**, closing FU-1…FU-5. It raised two non-blocking
Observations; both are accepted and incorporated.

### FO-1 — Complete-on-tap is a human-facing reinterpretation of Req 4.1
- **Validated Severity:** Observation — **Disposition:** Accepted.
- **Assessment.** Correct. Req 4.1 reads as "don't finalize until the timer expires";
  complete-on-tap sends immediately and makes the completion **instantly visible** on Alexa, with
  the window governing undo only. This is a human-facing behaviour change, not just an internal
  detail, and deserves the same escalation status as OQ5.
- **Decision.** Added **OQ7** to `15` (needs human decision), cross-referenced from the `15`
  decision-log entry and from `08`. The requirement is preserved in `docs/specs/`.
- **Remaining Risk.** Human decision only; the engineering choice is sound and safer than the
  alternative.

### FO-2 — `attributes_version` vs. store `schema_version` could be conflated
- **Validated Severity:** Observation (cosmetic) — **Disposition:** Accepted.
- **Assessment.** Correct. The migration test row (`schema_version` v0→v1) and the sensor snapshot
  (`attributes_version: 2`) reference two independent counters; a reader could conflate them.
- **Decision.** Added a clarifying note in both `06` (canonical) and `12` stating the two version
  independently. The `12` migration row now reads "store schema_version v0→v1".
- **Remaining Risk.** None.

**Net:** followup02 confirms the remediation is real and good. The only items not closable by an
agent remain the human decisions (OQ3/OQ5/**OQ7**/M-5) and the implementation-environment gates
(M-6 Phase 2.5 spike, Phase 7 E2E).
