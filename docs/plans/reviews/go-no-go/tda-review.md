# TDA Change Review — GO / NO-GO

# 🟢 GO

Implementation may begin.

Decision date: 2026-08-29
Reviewer: Change Review / Technical Design Authority (independent final gate)

---

## Executive Summary

This is an unusually mature, evidence-based design package for a greenfield Home Assistant
custom integration (`alexa_shopping_categorizer`) plus a bundled Lovelace card. I independently
re-read the specifications, all sixteen plan documents, the seven prior review deliverables, the
four follow-up passes, and all eight steering files, and I independently re-verified the
environment claims against the live Home Assistant instance using the read-only MCP.

The design is internally consistent, grounded in verified Home Assistant reality (not
assumptions), and the review process that produced it has genuine integrity: the chain caught its
own false-closure (a disposition that *described* edits it never applied), corrected it, and
verified the real on-disk diffs before advancing readiness. Every prior High, Medium, and Low
finding is resolved or resolved-by-user; the four human-facing decisions (OQ3 grace range, OQ5
review-gate reinterpretation, OQ7 complete-on-tap visibility, M-5 latency acceptance) carry
recorded user sign-offs; and the two most recent Medium findings (F4-1 store schema tolerance,
F4-2 whole-word matching) are addressed on disk.

Critically for this gate: an experienced implementation agent could build this today without
inventing significant unapproved architectural, security, requirements, or product decisions. The
architecture, the HA integration shape, the data/contract, the sync model, the categorization and
shop-resolution semantics, the failure behaviour, the test matrix, and the phased plan are all
specified to the level of "implement the function," not "decide the design." The only remaining
items are (a) two implementation-environment gates that *cannot* run in a read-only review — a
one-off write spike to confirm Alexa propagation + uid stability (Phase 2.5 / M-6) and the
pre-release E2E validation (Phase 7) — and (b) pre-publish housekeeping (codeowners, repo URL,
hacs.json — OQ6). None of these are unapproved design decisions; they are planned, gated, and
owned.

## Decision

**GO.**

Rationale: the readiness bar for this gate is "no material unapproved decision is left to the
implementation agent, and no material blocker remains." That bar is met. The design overrides the
original spec in exactly three places — source entity, no history mining, custom integration over
pyscript — and each override is correct, verified, and documented with reality winning over the
stale spec. The requirements (including the added Req 7 shop preference) are traced end to end to
plan, contract, tests, and steering. The two-way-sync value proposition rests on two runtime
assumptions that are correctly flagged and explicitly gated behind an early write spike before any
card work — so the risk is bounded and owned, not silently absorbed. That is the right way to
handle an unverifiable-in-review dependency; it does not block starting Phases 0–3.

## Confidence

**High.**

- I independently verified the environment claims that the whole design rests on (source entity
  identity, `supported_features: 7`, native list distinct at `15`, no naming conflict, domain
  unclaimed, HA 2026.8.3) — they hold exactly.
- The review chain is traceable and self-correcting; I confirmed the remediation is real on disk
  (I read the current `06`/`07`/`08`/`09`/`11`/`13`/`14`/`15` and all steering files, and they
  contain the complete-on-tap model, `category_definitions`/`shop_definitions`, reconfigure flow,
  whole-word matching, store-default tolerance, `reload_maps`, and shop diagnostics).
- Confidence is not "Highest" only because two load-bearing runtime behaviours (write propagation
  to Alexa, uid stability) remain unverifiable in a read-only task. This is correctly mitigated by
  the Phase 2.5 gate, so it does not reduce the decision — but it is the residual unknown.

## Review Scope

- **Specifications reviewed:** `docs/specs/requirements.md` (7 requirements incl. Req 7 shop
  preference), `docs/specs/design.md`, `docs/specs/tasks.md`.
- **Plans reviewed:** `docs/plans/README.md` and `00`–`15` (all sixteen, in full).
- **Previous reviews reviewed:** `docs/plans/review/consolidated-review.md`,
  `finding-disposition.md`, `recommended-changes.md`, `requirements-traceability.md`,
  `revision-summary.md`, `steering-review.md`; `followup01/` (consolidated + verification matrix),
  `followup02/` (consolidated + verification matrix), `followup03/` (consolidated + status
  ledger), `followup04/final-pre-build-review.md`.
- **Steering files reviewed:** `.kiro/steering/` — `product.md`, `architecture.md`, `security.md`,
  `home-assistant.md`, `python.md`, `testing.md`, `documentation.md`, `frontend.md` (all eight).
- **Repository areas inspected:** `docs/**` tree, `.kiro/**`, confirmed greenfield (no
  `custom_components/`, `frontend/`, or `tests/` yet — consistent with a pre-implementation gate).
- **Home Assistant MCP analysis performed (strictly read-only):** `ha_status`;
  `ha_get_entity` on `todo.david_carson_amazon_gmail_com_shopping_list` (state 14,
  `supported_features: 7`) and `todo.shopping_list` (state 0, `supported_features: 15`);
  `ha_search_entities` for `shopping` (2 matches), `categorized` (none), and
  `alexa_shopping_categorizer` (none). No state-changing operation was performed.

## Requirements Gate

**PASS.**

All 7 requirements and their acceptance criteria are traced to the plan, the data contract, the
test matrix, and steering (`requirements-traceability.md` + followup03 status ledger, both
independently spot-checked against the plan text). Two requirement reinterpretations exist and are
handled correctly rather than silently:

- **Req 1.7 ("review before live" gate)** is reinterpreted as a non-blocking first-setup review
  banner + prominent Uncategorized bucket. This is a genuine hard-SHALL reinterpretation. It is
  defensible (the map only affects display grouping and never mutates the Alexa list, so an
  unreviewed map is cosmetic and reversible), it is preserved unchanged in the spec, and it carries
  a recorded user sign-off (OQ5, 2026-08-29).
- **Req 4.1 (grace period "before finalized")** is reinterpreted as complete-on-tap with an
  undo-only window, making completion instantly visible on Alexa. Also a genuine human-facing
  change, also preserved in spec, also signed off (OQ7).

Applying the blocking-ambiguity rule from the mandate: I could not find a significant requirement
where two competent developers would diverge materially without the spec/plan already resolving it
or explicitly deferring it with a mechanism. The two reinterpretations above are exactly the class
of requirement-intent change that must be escalated — and they were, with sign-off. No blocking
ambiguity remains.

## Architecture Gate

**PASS.**

Component boundaries, responsibilities, interfaces, data flow, control flow, state, persistence,
lifecycle, external-service isolation, error boundaries, and security boundaries are all defined
(`03`, `04`, `05`, `08`, `09` + `architecture.md`). The core is clean: a pure, side-effect-free
categorizer + shop resolver; a `DataUpdateCoordinator` that owns all recomputation; an HA Store
for the category/shop maps and learned overrides; a single derived, non-authoritative sensor; and
the native `todo.*` services as the single write path. The no-drift/rebuildable invariant (NFR3)
is preserved even with the added shop dimension (shop data lives only in the store, keyed by
normalized text, never written to the Alexa list).

Answering the mandate's test question directly: **an experienced developer could implement this
architecture without making significant unapproved architectural decisions.** The two "decide the
semantics" items flagged by followup04 (store schema tolerance, whole-word vs substring matching)
are already pinned in `06`/`07`/`python.md`, so they are not open decisions.

## Home Assistant Gate

**PASS.**

The integration design follows current HA conventions and I found nothing that would cause
incorrect entity behaviour, duplicate entities, wrong device relationships, blocking I/O, or
lifecycle/migration bugs:

- `manifest.json` shape is correct for a calculated/service integration (`iot_class: calculated`,
  `integration_type: service`, `dependencies: ["todo"]`, `requirements: []`), with a documented
  rationale for deliberately not using `after_dependencies` (relies on `ConfigEntryNotReady` for
  ordering — idiomatic).
- Config flow enforces one entry per source entity via `unique_id = source_entity_id`; source
  change is correctly modelled as a **reconfigure** flow (not a mutable option), resolving the
  earlier M-3 lifecycle inconsistency.
- Coordinator is event-driven (state-change listener) with a 15-minute safety poll; the
  `todo.get_items` response envelope is pinned canonically (`response[source_entity_id]["items"]`,
  `summary → name`, `status == "completed" → completed`), removing a real implementation trap.
- First-refresh readiness correctly distinguishes `ConfigEntryNotReady` (source absent/unavailable,
  retry) from `UpdateFailed` (entity present, read error).
- Single sensor entity with an entry-based stable `unique_id`, `should_poll = False`, availability
  tied to `last_update_success` + source state, attached to a service device (not the Alexa
  device). Recorder exclusion is called out.
- Diagnostics are redacted (item text, opt-in) and now include shop counts; repairs raise on a
  missing source entity; migration is versioned with a defensive-load store.

MCP validation confirmed the source entity supports only CREATE/UPDATE/DELETE (7) with completed
items retained — exactly what the undo model (reversing `update_item(status=needs_action)`)
depends on. The native list at `15` (supports MOVE) is correctly identified as a distinct,
out-of-scope entity.

## Security Gate

**PASS.**

Would I approve this from a security perspective? Yes. The integration owns no credentials (Alexa
auth stays in `alexa_devices`), stores no secrets, makes no outbound network calls of its own,
introduces no webhooks or user-supplied URLs (no SSRF surface), validates all service/flow inputs
with voluptuous, and requires XSS-safe rendering in the card (no `innerHTML` with raw user text,
no `eval`). Item text (personal data) is redacted in diagnostics by default and may appear only at
`debug` logging. Dependencies are stdlib-only for v1 with a pin-and-review rule for any addition.
The card operates as the logged-in HA user through documented services, with no auth bypass. The
security steering is canonical for logging restrictions and is consistent across files. None of
the failure modes that would normally force a NO-GO (credential exposure, unauthorized access, RCE,
sensitive-data exposure, HA compromise, unsafe external requests) are present.

## Reliability Gate

**PASS.**

Failure modes are enumerated with detection and response (`09`): source missing/unavailable
(ConfigEntryNotReady vs UpdateFailed; sensor unavailable with cached projection; repair issue),
read failures (UpdateFailed, retry on next event/poll), write failures (bounded exponential
backoff ×3, then revert optimistic UI + visible error — satisfying Req 5.4's "never silently
drop"), corrupt store (back up + fall back to defaults + repair issue), and concurrent
Alexa-direct changes during the undo window ("source wins," undo affordance cancelled). The
complete-on-tap model is the key reliability decision: because completion is sent immediately, a
closed/backgrounded/crashed card cannot silently lose a completion — the safe failure direction.
The mis-tap trade-off (a completion that syncs before the user could undo) is stated explicitly and
asserted by a test. An implementation agent does not have to invent failure behaviour.

## Testing Gate

**PASS.**

Could an implementation agent write meaningful tests from the current design without inventing
expected behaviour? Yes. The test matrix (`12` + `testing.md`) maps concrete cases to requirement
IDs across the pure categorizer (100% coverage gate), shop resolution and precedence (including the
subtle "shop-name-in-text beats learned override" and the whole-word traps like "graham crackers"
not matching `ham`), config/options/reconfigure flows, coordinator, sensor snapshot against
contract v3, all category and shop services (including override migration on rename), sync/error
paths (complete-on-tap, reversing undo, card-gone-during-window, inbound-delete-during-window),
diagnostics redaction, migration, and the card's pure logic. Mocking strategy, time-freezing, and
snapshot testing are specified. Coverage gates (categorizer 100%, integration ≥90%) and a CI gate
(ruff, mypy --strict, pytest) are defined.

## Implementation Plan Gate

**PASS.**

The phased plan (`14`) is actionable, correctly sequenced, and free of vague "implement the
integration" phases. Phase 0 scaffolding → Phase 1 pure core + store (with F4-1/F4-2 semantics
pinned as the first task) → Phase 2 config/coordinator/sensor → **Phase 2.5 write spike gate** →
Phase 3 services → Phase 4 card render/live/add → Phase 5 tick/undo/errors → Phase 6
diagnostics/repairs/docs → Phase 7 E2E. Dependencies are explicit, high-risk runtime validation is
front-loaded (the spike gates card work), each phase has acceptance criteria and defined tests, and
each produces a demonstrable state. The plan realistically reflects the custom-integration
architecture rather than the abandoned pyscript task waves.

## Kiro Steering Gate

**PASS.**

All eight steering files are present, mutually consistent, and aligned with the final plan
(including Req 7). The earlier High gap — the card being effectively un-steered — is closed:
`frontend.md` exists (fileMatch `frontend/**`) and covers the contract, the complete-on-tap state
machine, retry/error surfacing, source-wins reconciliation, add reconciliation, XSS-safe
rendering, accessibility, and cache-busted resource registration; `testing.md` scope is widened to
`{tests/**,frontend/**}`. The steering drift items (hard-coded entity id, entity-services nudge,
lossy coordinator type, credential-redaction framing, duplicated logging rule) are all fixed.
Answering the mandate's question: a new Kiro agent could join tomorrow, read the steering plus the
approved plan, and implement the project without violating the intended architecture. (One
cosmetic nit noted below, non-blocking.)

## AI-Agent Risk Gate

**PASS.**

The areas where an AI agent would typically improvise are specifically constrained: pyscript is
explicitly forbidden in favour of the custom integration; the categorizer is pinned as pure/sync
with whole-word matching (preventing the substring vegan-boundary bug); the `todo.get_items`
envelope, the add-item reconciliation key, and the override-migration-on-rename are all pinned
(closing the REVIEW2-001/002/003 traps that would otherwise be improvised); services are declared
config-entry-scoped, not entity services; the frontend contract and versioning are canonical in
`06` and referenced from steering; dependency additions require pin-and-review. Residual
requirement ambiguity is low and where it existed it was escalated for human sign-off rather than
left to the agent.

## Dependency Gate

**PASS.**

Runtime dependencies are stdlib-only (v1), with the `todo` building block declared in the manifest
and `requirements: []`. The one external system (Amazon Alexa) is reached only transitively through
the core `alexa_devices` integration via the public `todo.*` services and state machine — never
directly, and never via `alexa_devices` internals. The two behavioural unknowns about that
transitive dependency (write propagation, uid stability) are identified, risk-rated, and gated
behind the Phase 2.5 spike and Phase 7 E2E. Dev dependencies (pytest-homeassistant-custom-component,
ruff, mypy, JS toolchain) are appropriate. No undocumented assumption that could materially change
the design is being relied on.

## Scope Gate

**PASS.**

The design is the minimum appropriate architecture for the requirements. Deliberate scope
*reductions* are documented and justified (no history mining, no user-supplied import in v1,
single shop per item, to-do list out of scope). The one scope *addition* is `attributes_version`
contract-versioning infrastructure, which is sound engineering with acceptable added scope. Req 7
(shop preference) is a genuine user-requested requirement added to the spec, not speculative
future-proofing, and it reuses the category model's patterns cleanly. I found no over-engineering
and nothing required by the spec that has been dropped without a documented, signed-off decision.

---

## Blocking Issues

None. There are no blockers.

---

## Non-Blocking Recommendations

These should be addressed in the phase that touches them; none affect the GO decision.

- **NBR-1 (steering precision, cosmetic).** `home-assistant.md`'s "Coordinator pattern" bullet
  still describes the `Projection` as "ordered categories with `collapsed` ... `category_definitions`"
  — pre-Req-7 language that omits the shop-primary `shop_groups` / `shop_definitions` restructure
  that is canonical in `06`. It is not contradictory (it points to `06` as canonical) but it is
  slightly stale. Align the wording when Phase 2 touches the coordinator. (Followup04 already fixed
  the parallel drift in `13`; this one bullet was missed.)
- **NBR-2 (R7-L1).** At first release, add a one-line note to `06`/CHANGELOG that contract v3 is
  the initial shipped version (v1/v2 were internal design iterations, no back-compat obligation).
  Fold into Phase 6 docs.
- **NBR-3 (R7-L2).** Implement the "warn, don't block" behaviour when a user adds a shop whose name
  is a common English word (tier-1 shop-name-in-text matching could hijack ordinary items). Already
  specified in `07`/`frontend.md`; ensure the Phase 3/5 implementation includes the warning.
- **NBR-4 (OQ6, housekeeping).** Finalize `codeowners`, repository URL, `hacs.json`, CI workflow,
  and `pyproject.toml` before publishing. Expected at Phase 0/6; not a design blocker.
- **NBR-5 (standing minor assumptions).** OQ2 (completed items hidden by default) and OQ4 (deferred
  first-seen meat/milk confirmation) remain assumptions; both are low-risk and deferred by design.
  Confirm OQ2 opportunistically with the user; no action required to start.

---

## Accepted Risks

- **AR-1 — Alexa write propagation unverified in review.**
  - Risk: `todo.update_item`/`add_item` on the `alexa_devices` list may not reliably propagate to
    the real Alexa app.
  - Rationale for acceptance: cannot be validated in a read-only task; the spec records the user
    confirmed it exists; the design isolates the dependency behind the public `todo.*` contract.
  - Mitigation: Phase 2.5 one-off manual write spike *before* card investment; Phase 7 E2E as a
    hard pre-release gate; retry/backoff + visible error on failure.
  - Owner/monitoring: implementation agent at Phase 2.5 (gate); release owner at Phase 7.

- **AR-2 — Item `uid` stability unverified in review.**
  - Risk: if `uid`s are not stable across syncs, undo/complete could target the wrong item.
  - Rationale: HA core source uses `uid` as the dict key (supports stability); not mutation-tested
    here.
  - Mitigation: observe uid stability across two refreshes in the Phase 2.5 spike; reconcile by
    `uid` throughout; add reconciliation by normalized summary for just-added items.
  - Owner/monitoring: implementation agent at Phase 2.5.

- **AR-3 — Missed-push latency up to ~5 minutes.**
  - Risk: on a missed `alexa_devices` push, the categorized view can lag up to the upstream 5-minute
    poll, exceeding Req 2.1's "few seconds."
  - Rationale: we must not poll Amazon directly; the two-tier latency contract is documented.
  - Mitigation: manual refresh short-circuits it; `last_synced` banner; user accepted (M-5).
  - Owner/monitoring: accepted by user; revisit only if it proves annoying in practice.

- **AR-4 — Best-effort vegan filtering (NFR4).**
  - Risk: hidden/indirect animal ingredients may be mis-handled.
  - Rationale: text-only filtering cannot catch every case by design.
  - Mitigation: ambiguous items route to `Uncategorized`, never mis-assigned; manual correction
    learns. Whole-word matching (F4-2) protects the boundary cases.
  - Owner/monitoring: product-accepted limitation.

- **AR-5 — `alexa_devices` depends on an unofficial Amazon API.**
  - Risk: upstream breakage could disrupt the source entity.
  - Rationale: out of this integration's control; we depend only on the public `todo` contract, not
    internals.
  - Mitigation: isolation via public services; sensor availability + repair issue surface outages.
  - Owner/monitoring: accepted; isolated by design.

---

## Assessment of Previous Reviews

I evaluated the prior review process for effectiveness and false closure.

**Was the process effective?** Yes, and notably so. The specifications were fully analysed;
important requirements (including the sync/UX boundary and the added Req 7) were identified;
architectural assumptions were challenged (pyscript rejected with justification); Home Assistant
assumptions were validated against live MCP *and* HA core source; security and testing were
considered as first-class deliverables; steering was reviewed as a first-class deliverable;
findings were independently challenged; valid findings were incorporated; a few over-heavy
recommended mechanisms were appropriately narrowed (not rejected wholesale); and deferred items
were controlled with explicit gates.

**False-closure check.** The single most important integrity event in this project's history is
that followup01 *caught a false closure*: a third-agent disposition asserted, in the past tense,
that it had applied plan/steering edits which did not exist on disk. Followup01's verification
matrix documented this per-finding, and followup02 then verified — via `git diff` and direct reads —
that the edits were subsequently applied for real. I re-verified the current on-disk state myself
(complete-on-tap in `08`/`09`/`11`, `frontend.md` present, `category_definitions`/`shop_definitions`
in `06`, reconfigure flow in `04`, whole-word matching in `07`/`python.md`, `reload_maps` and shop
diagnostics, testing scope `{tests/**,frontend/**}`). The remediation is genuinely present. This
history is a positive signal: the process detects and corrects false closure rather than trusting
prose.

- **Confirmed resolved:** H-1, H-2; M-2, M-3, M-4, M-5, M-7, M-8; L-1 through L-9; REVIEW2-001
  through REVIEW2-005; FO-2; R7-L1, R7-L2, R7-O1, R7-O3; F4-1 through F4-7 (verified against `06`,
  `07`, `10`, `13`, `15` and steering).
- **Resolved by recorded user sign-off:** M-1/OQ5, OQ7/FO-1, OQ3/L-7, M-5, plus shop sign-offs
  OQ8/OQ9.
- **Remaining unresolved (correctly, not defects):** M-6/R1/R2 — held as an implementation-
  environment write gate, not a design defect; Phase 7 E2E — pre-release gate; OQ6 — pre-publish
  housekeeping; OQ2/OQ4 — low-risk standing assumptions deferred by design.
- **Correctly rejected:** none were rejected outright; several mechanisms were narrowed with sound
  reasoning (e.g. `category_definitions` attribute over a websocket command for a small map;
  complete-on-tap over a backend scheduler that would reintroduce server-side pending state).
- **Incorrectly rejected / unnecessarily accepted:** I found none.
- **New issues discovered by me:** none blocking; only NBR-1 (one stale steering bullet).

## Kiro Steering Assessment

**Sufficient.** The steering set is complete across product, architecture, security, Home
Assistant, Python, testing, documentation, and frontend, and it reaches every surface including the
card. It reinforces the approved architecture (pure categorizer, coordinator-owned recompute,
single write target, no Amazon calls, complete-on-tap), establishes project-specific conventions
(whole-word matching as a correctness rule, config-entry-scoped services, `attributes_version`
discipline, recorder exclusion), encodes persistent security constraints (canonical logging rule,
no credentials, XSS-safe rendering, no outbound calls), sets testing expectations (coverage gates,
required areas, platform-based regression), and sets documentation requirements. Files are
mutually consistent; the previously-flagged contradiction (client-only enforcement vs. "backend can
enforce") is resolved by the complete-on-tap ruling that both the plan and steering now state.

- **Important gaps:** none material.
- **Contradictions:** none.
- **Rules that could cause implementation problems:** none. The only imperfection is cosmetic
  (NBR-1: one `home-assistant.md` coordinator bullet uses pre-Req-7 `Projection` wording while
  pointing to `06` as canonical). This does not mislead an implementer and is not a NO-GO.

## Implementation Agent Readiness

**YES.**

A competent implementation agent could begin building this project today without making significant
unapproved architectural, security, requirements, or product decisions. The architecture is
settled; the HA integration shape, lifecycle, and contract are specified; the categorization and
shop-resolution semantics (including matching mode and precedence) are pinned; the sync/undo model
is decided and steered; failure behaviour is enumerated; the test matrix and coverage gates are
concrete; the phased plan is sequenced with acceptance criteria; and the two "decide the semantics"
entry items for Phase 1 (store default tolerance, whole-word matching) are already resolved on
disk. The requirement reinterpretations that *would* have required agent judgement were escalated
and signed off by the user. The only actions the agent must still take that are not pre-decided are
the planned validation gates (Phase 2.5 write spike, Phase 7 E2E) and pre-publish housekeeping —
all of which are explicitly owned and gated, not open design questions.

---

## Safety Confirmation

- No production code was written.
- No specifications were modified.
- No plans were modified.
- No steering files were modified.
- No previous review findings were modified.
- The Home Assistant MCP was used only in read-only mode (status query, entity reads, entity
  searches).
- No changes were made to Home Assistant (no create/update/delete, no service calls, no state
  changes, no automations/scripts/helpers, no restart/reload).
- This decision was made independently, by re-reading the source material and re-verifying the
  environment, not by deferring to the prior approval decisions.

---

# FINAL DECISION: GO

The project has passed the Change Review / Technical Design Authority
gate and is approved to proceed to implementation.

No material blocking issues were identified.
