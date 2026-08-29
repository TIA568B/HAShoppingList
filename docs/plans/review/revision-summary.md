# Revision Summary (Third-Agent Plan Remediation)

**Author:** Third agent (independent validation + plan remediation).
**Date:** 2026-08-29
**Companion:** [finding-disposition.md](finding-disposition.md) (per-finding evaluation).

This summarises how the previous review (`consolidated-review.md`, `steering-review.md`,
`requirements-traceability.md`) was independently evaluated and what changed as a result. The
original review documents are preserved unchanged.

---

## Changes Incorporated

Driven by **accepted** or **partially accepted** findings:

- **Tick model reworked to complete-on-tap + reversing undo (H-1).** The card now sends
  `todo.update_item(status=completed)` immediately on tap, with bounded retry and
  revert-on-exhaustion, and offers an Undo affordance for the grace window that sends
  `status=needs_action`. This removes the silent-drop failure mode (Req 5.4) without introducing
  server-side pending state. Rewrote `08`, `11`; updated `09`; decision recorded in `15`.
- **New `frontend.md` steering (H-2 / S-01 / S-10)** and widened `testing.md` scope to
  `frontend/**`, giving the card first-class guardrails (state machine, retry rules, XSS-safe
  rendering, accessibility, sanctioned APIs, resource/HACS packaging).
- **Keyword read path added (M-2).** `06` sensor contract gains `category_definitions:
  [{name, keywords}]` so the card settings panel can satisfy Req 6.1. `attributes_version` bumped.
- **Source-entity change defined (M-3).** Options flow excludes source change; a reconfigure flow
  updates `entry.data` + `unique_id` atomically. `04` and `12` updated; `testing.md` reworded.
- **Two-tier reactivity latency contract stated (M-5).** `08`/`14` now say "few seconds on push;
  up to ~5 min on a missed push via the upstream poll."
- **Early runtime-assumption spike added (M-6).** New Phase 2.5 gates card work on a minimal
  manual write validation of Alexa propagation + uid stability (implementer action, not this
  read-only task).
- **Concurrent-change precedence specified (M-7).** Inbound source state wins; an inbound
  change to a locally-tracked uid cancels the local undo affordance. `08`/`11`/`12` updated.
- **Steering drift fixed (M-8 / S-03 / S-04).** `testing.md` regression asserts platform-based
  selection (never a hard-coded entity id); `home-assistant.md` drops the entity-services nudge
  for config-entry-scoped services.
- **Grace-period floor raised to 8s (L-7).** Range 8–30s (default 9) to respect the spec's 8–10s
  intent. `04`/`15` updated.
- **Steering precision fixes (L-4/S-06, L-5/S-07, L-6/S-08, L-8/S-09, L-9/S-11):** categorizer
  carved out as intentionally synchronous; coordinator data type references the `Projection`
  contract; diagnostics reframed around item-text redaction; strings/translations discipline
  added; logging rule de-duplicated to `security.md` as canonical.
- **Documentation-only reinforcements (L-1/F-01, L-2, L-3):** export seed path recorded as
  considered-and-dropped; `after_dependencies` rationale noted; first-refresh ready-vs-failed
  distinction clarified.
- **New-finding fixes** (see New Findings below): `todo.get_items` response contract pinned;
  add-item reconciliation key defined; override migration on category rename added.

## Findings Challenged

No finding was rejected outright, but several recommendations were **narrowed** because the
reviewer's proposed mechanism was heavier than the problem warranted:

- **H-1 mechanism.** I adopted the reviewer's *option (a)* (complete-on-tap + reversing undo) and
  explicitly declined *option (b)* (a backend service that schedules/records the pending
  completion). Option (b) would reintroduce server-side pending item state and a
  reload/restart-surviving timer, contradicting the "no server-side item state / rebuildable
  projection" principle (`03`, `product.md`). Option (a) is smaller and strictly safer.
- **M-2 mechanism.** The reviewer preferred a websocket command to expose keywords. For a
  single-household map that payload is tiny, so I made a `category_definitions` **attribute** the
  default and kept the websocket command only as the large-list escape hatch (tied to M-4). Less
  moving parts for v1.
- **M-4 severity.** Downgraded High-ish concern to **Low** for this user: a shopping-list-sized
  map will not approach the ~16 KB attribute cap, and the mitigation (recorder exclusion +
  websocket fallback) already exists. Kept as steering discipline, not a v1 build item.
- **L-1 scope.** Accepted *documenting* that the spec's "user-supplied export" seed path was
  dropped, but declined to *build* an import feature for v1 — unjustified scope given
  learn-over-time and a non-authoritative map.
- **M-1 handling.** The reviewer treated the Req 1.7 gate as needing user sign-off before
  proceeding. I kept the requirement intact and documented the tension (I cannot obtain sign-off),
  added a non-blocking first-setup review affordance that satisfies the *intent*, and escalated
  OQ5 for human decision rather than silently resolving it.

## Findings Rejected

None. Every significant finding reflected a real issue or a worthwhile clarification.

## Findings Deferred

None deferred to a later release. Two items are **gated to the implementation environment**
(not deferred in priority, but cannot be done in this read-only planning task):

- **M-6 runtime spike** — a write action; must run in the implementation environment before card
  work.
- **Phase 7 E2E** — already planned as a pre-release hard gate.

## New Findings

Discovered independently during this evaluation. IDs use the `REVIEW2-` scheme.

### REVIEW2-001 — `todo.get_items` response contract not pinned (item field is `summary`, not `name`)
- **Severity:** Medium — **Area:** Data contract / Coordinator
- **Evidence:** HA `todo.get_items` returns `{ "<entity_id>": { "items": [ {summary, uid,
  status} ] } }` (confirmed against HA docs and community examples). The plan (`04`/`06`) says the
  coordinator normalises the response into `SourceItem(uid, name, completed)` but never states
  that the source field for `name` is `summary` and that `status` is the string
  `needs_action`/`completed`, nor that the response is keyed by entity id.
- **Impact:** An implementer could look for a `name`/`title` key that does not exist, or mishandle
  the entity-id-keyed envelope, breaking projection building.
- **Recommendation:** Pin the exact response contract in `06` and map `summary → SourceItem.name`,
  `status == "completed" → completed`. **Incorporated** into `06` and `04`.

### REVIEW2-002 — Optimistic add-item reconciliation key is undefined (transient duplicate risk)
- **Severity:** Medium — **Area:** Sync / Frontend
- **Evidence:** `08`/`11` say an added item is shown optimistically then "reconciled when the
  inbound flow returns the real item," but `todo.add_item` does not return the created `uid`.
  During the window between optimistic insert and the inbound refresh, there is no `uid` to
  reconcile on, so the design's "reconcile by uid" rule cannot apply to a just-added item.
- **Impact:** The same item can appear twice briefly (optimistic placeholder + real item), or the
  placeholder may linger if names differ after Alexa normalisation.
- **Recommendation:** Define the add reconciliation rule explicitly: the card tags the optimistic
  placeholder with a client token and matches the first inbound needs_action item whose normalised
  `summary` equals the added text, then adopts its real `uid` and drops the placeholder. If no
  match arrives within a bounded window, keep the real inbound item and drop the placeholder.
  **Incorporated** into `08` (add flow) and `11` (state machine), with a `12` test.

### REVIEW2-003 — `edit_category` rename orphans learned overrides (learning-data loss)
- **Severity:** Medium — **Area:** Services / Learning / Data
- **Evidence:** `06` `overrides` maps `normalized_text → category *name*`. `07` self-heal says an
  override pointing at a non-existent category falls through to keyword/Uncategorized. But
  `edit_category` with `new_name` renames the category — every override pointing at the old name
  silently stops working and the item loses its learned placement. The review flagged
  delete-reassignment (Req 6.3) but not rename-orphaning.
- **Impact:** Renaming a category silently discards accumulated learning for items mapped to it —
  a quiet regression of the "learn over time" product rule.
- **Recommendation:** `edit_category` must migrate overrides: any `override == old_name` is
  rewritten to `new_name` in the same transaction before persisting and recomputing.
  **Incorporated** into `06` (service behavioural contract) and `12` (test: rename migrates
  overrides).

### REVIEW2-004 — Bundled card asset needs cache-busting / versioned resource URL
- **Severity:** Low — **Area:** Frontend / Packaging
- **Evidence:** `11`/`13` serve the built card as a registered frontend resource. Browsers
  aggressively cache JS; without a version query string or hashed filename, users can run a stale
  card after an update — a common custom-integration support burden.
- **Recommendation:** Register the resource URL with the integration `version` as a query string
  (or hashed filename) so updates bust the cache. **Incorporated** into `frontend.md` and `11`.

### REVIEW2-005 — No rule for uid collision / re-add after delete in the projection
- **Severity:** Low — **Area:** Sync / Data
- **Evidence:** If an item is deleted on Alexa and a same-named item added later, it gets a new
  `uid`. The design already keys on `uid`, so this is handled — but the plan does not state that
  learned overrides (keyed by normalised text, not uid) correctly re-apply to the new uid, which
  is actually the desired behaviour worth making explicit.
- **Recommendation:** Note that override learning is uid-independent (keyed by normalised text) so
  a re-added item inherits its learned category automatically. **Incorporated** as a clarifying
  note in `07`.

## Architectural Changes

- **Sync/tick model** changed from *deferred client-side finalize* to *complete-on-tap +
  reversing undo* (H-1). This is the most significant behavioural change: completion is now always
  synced immediately, and the grace window governs only undo, not whether the change is sent.
- **Frontend contract** extended with `category_definitions` (read path for keywords, M-2) and a
  pinned `todo.get_items` response mapping (REVIEW2-001). `attributes_version` bumped once for the
  additive attribute change.
- **Lifecycle**: source-entity change is a reconfigure operation, not an options edit (M-3).
- No change to the core boundaries: pure categorizer, coordinator-owned recompute, single write
  target (the Alexa list), derived non-authoritative sensor.

## Steering Changes

Summarised; details in finding-disposition.md.

- **Created:** `.kiro/steering/frontend.md` (fileMatch `frontend/**`).
- **Modified:** `testing.md` (scope widened to `frontend/**`; regression rule now platform-based),
  `home-assistant.md` (coordinator data type → `Projection`; diagnostics reframed to item-text;
  entity-services nudge removed; strings/translations discipline; sensor-attribute-contract
  subsection; logging reference), `python.md` (categorizer carved out as sync; logging reference),
  `security.md` (marked canonical for logging restrictions).

## Remaining Risks

- **R1/R2 (unverified runtime behaviour):** Alexa write-propagation and uid stability remain
  assumptions until the Phase 2.5 spike / Phase 7 E2E in the implementation environment. This is
  the single largest residual risk and is a hard pre-card gate.
- **Req 1.7 (OQ5):** The live-triage + non-blocking review affordance is a *reinterpretation* of a
  hard SHALL. Requires human confirmation. If a blocking gate is wanted, bounded Phase 2/4 rework
  follows.
- **Best-effort vegan filtering (NFR4):** unchanged accepted limitation; ambiguous items route to
  Uncategorized.
- **Publishing details (OQ6):** `codeowners`, repo URL, `hacs.json`, CI, `pyproject.toml` to be
  finalised before release.

## Decisions Requiring Human Approval

> **Update (2026-08-29): all resolved by the user.** OQ5 (non-blocking review), OQ7
> (complete-on-tap instant-visible), OQ3 (grace 9s/8–30s), M-5 (latency accepted), and M-6 (spike
> authorised) were all confirmed. Plus shop-feature sign-offs OQ8 (`milk`→Aldi) and OQ9
> (auto-collapse kept). See `docs/plans/15` decisions log / OQ list. The items below are retained
> for historical context.

1. **OQ5** — accept the live-triage + first-setup review affordance in lieu of a blocking
   "review before live" gate (Req 1.7)? (Escalated; requirement preserved meanwhile.)
2. **OQ7** — accept **complete-on-tap** making completion instantly visible on Alexa (rather than
   after the grace window), a human-facing reinterpretation of Req 4.1? (Raised by followup02
   FO-1; escalated; requirement preserved meanwhile.)
3. **OQ3 / L-7** — grace-period range 8–30s (default 9). Confirm the widened range is acceptable.
4. **M-5 latency** — confirm acceptance of "up to ~5 min on a missed push" worst case.
5. **M-6** — authorise the implementer to run the minimal write spike (R1/R2) before card work.

## Relationship to Follow-up Review 02

Follow-up 02 independently verified (via `git diff`) that all remediation is applied on disk and
restored **CONDITIONALLY READY**, closing FU-1…FU-5. Its two non-blocking observations are
incorporated: FO-1 → new **OQ7** (complete-on-tap is instantly visible; escalated for human
sign-off); FO-2 → clarifying note in `06`/`12` that `attributes_version` and store
`schema_version` version independently. The followup02 documents are preserved as audit artefacts.

---

## Relationship to Follow-up Review 01

`docs/plans/review/followup01/` recorded that an earlier disposition pass **described** edits it
never applied (its Critical FU-1), leaving all first-review findings open and this
`revision-summary.md` missing. That state is now corrected: the edits are **applied and verified
on disk** this session (spot-checked via content greps for `complete-on-tap`,
`category_definitions`, `attributes_version: 2`, `Phase 2.5`, the `frontend.md` file, and the
`testing.md` scope/regression changes). The two follow-up substantive refinements are incorporated
(explicit mis-tap trade-off in `08`/`12`; M-4 discipline landed in steering; M-1/OQ5 kept as a
human decision). The original followup01 documents are preserved unchanged as audit artefacts.
