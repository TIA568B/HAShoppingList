# Kiro Steering Review (Mandatory)

**Reviewer:** Independent senior technical reviewer (second agent)
**Date:** 2026-08-29
**Scope:** All files in `.kiro/steering/`

This is a first-class review deliverable. Steering files are treated with the same scrutiny as
the technical plans. The guiding question throughout:

> "If a new Kiro agent started implementing this project tomorrow and followed only these
> steering files plus the approved plan, would it consistently make the intended architectural
> and engineering decisions?"

---

## 1. Steering Inventory

| # | File | Inclusion | Purpose | Scope | Assessment |
|---|------|-----------|---------|-------|------------|
| 1 | `product.md` | `always` | Product definition, verified environment ground truth, non-negotiable vegan rules, primary user | Whole project | Strong. Clear, factual, correctly captures the verified source entity and vegan rules. |
| 2 | `architecture.md` | `always` | Chosen approach, component boundaries, dependency rules, data-flow principles, module map, anti-patterns | Whole project | Strong. Mirrors `docs/plans/03`. Enforces pure categorizer + no-Amazon + no-drift. |
| 3 | `security.md` | `always` | Credentials, secrets, logging, input validation, SSRF, dependencies, frontend | Whole project | Strong and appropriately strict. Matches `docs/plans/10`. |
| 4 | `home-assistant.md` | `fileMatch: custom_components/**` | HA integration conventions: manifest, lifecycle, coordinator, entity, services, diagnostics, migration | Backend Python | Strong, detailed, current. Matches `docs/plans/04–05`. |
| 5 | `python.md` | `fileMatch: **/*.py` | Python version, typing, async, code org, deps, error handling, logging | All Python | Strong. `mypy --strict`, 3.13, stdlib-first. |
| 6 | `testing.md` | `fileMatch: tests/**` | Framework, coverage gates, required test areas, mocking, regression, CI | Tests | Strong. Matches `docs/plans/12`. |
| 7 | `documentation.md` | `fileMatch: **/*.md` | Required docs, update triggers, decision recording, changelog/migration, granularity, style | Docs | Good. Matches `docs/plans` conventions. |

**Overall inventory verdict:** the steering set is unusually complete for a greenfield project.
Coverage spans product, architecture, HA specifics, Python, security, testing, and docs. There
are no obviously missing *categories* of steering. The weaknesses are in **precision, coverage
of specific edge decisions, and a few inclusion-scoping gaps**, detailed below.

---

## 2. Steering Findings

### S-01 — `home-assistant.md` and `python.md` do not apply to the frontend card — a security-critical gap
**Severity: High.** **Files:** `home-assistant.md` (`fileMatch: custom_components/**`),
`python.md` (`**/*.py`), `security.md` (`always`), `testing.md` (`tests/**`).

The custom Lovelace card lives in `frontend/` (per `13-project-structure`). It is a substantial,
security-sensitive deliverable: it performs all optimistic-UI, grace-timer, retry, and DOM
rendering of untrusted user text. Yet:

- `home-assistant.md` scopes to `custom_components/**` — excludes `frontend/`.
- `python.md` scopes to `**/*.py` — the card is TS/JS, so excluded.
- `testing.md` scopes to `tests/**` — the card's JS tests likely live under `frontend/`, so the
  testing steering may **not** load when an agent is editing card tests.
- Only `security.md`, `product.md`, and `architecture.md` (`always`) reach the card.

**Impact:** An agent implementing the card gets the "escape user text / no innerHTML" rule (from
`security.md`) but **no** steering on: the client-side retry/backoff contract (Req 5.4), the
per-item undo state machine, the grace-timer-survives-nothing behaviour, accessibility
requirements, or which HA websocket APIs are sanctioned. The most complex and requirement-dense
part of the UX (Req 3.x, 4.x, 5.4) has the **least** steering coverage. There is **no dedicated
`frontend.md` steering file**. Recommendation: add a `frontend.md` (fileMatch `frontend/**`)
capturing the card contract, retry rules, state machine, accessibility, and the escape-all-text
rule; and widen `testing.md` to `frontend/**` test paths.

### S-02 — Steering restates the sync/retry model client-side without capturing the "card-closed" failure mode
**Severity: High.** **Files:** `home-assistant.md` (Error handling), `architecture.md`
(Outbound data flow / "No business logic in the card that the backend cannot also enforce").

`home-assistant.md` says: "Wrap source service calls; on failure, retry with backoff, then
surface a user-visible error … revert optimistic state. Never drop a change silently (Req 5.4)."
`architecture.md` mandates "No business logic in the card that the backend cannot also enforce."
But the plans (`08`, `09`) put the grace timer *and* retry loop **entirely in the card**. These
two steering statements are in direct tension with the plan, and the steering does not resolve
it. An agent could reasonably implement the retry loop in the card (following the plan) and
believe it complied with steering, while actually violating the "backend can also enforce" rule
and the "never silently drop" guarantee (if the card is closed). **The steering should either
(a) explicitly bless the client-side timer as an accepted exception with a stated safety
rationale, or (b) require a backend finalization fallback.** As written it is ambiguous and will
produce inconsistent implementations. This is the single most important steering ambiguity.

### S-03 — `testing.md` regression rule hard-codes a user-specific entity id
**Severity: Medium.** **File:** `testing.md` (Regression tests).

The rule: *"Keep a regression test asserting the source entity is
`todo.david_carson_amazon_gmail_com_shopping_list`-style (alexa_devices platform) selection
logic and that `todo.shopping_list` is not silently chosen."* This bakes a single household's
account-derived entity id into a permanent regression test. The plans (`04` config flow, `02`
recommendations) correctly make the source entity **user-selectable** and warn that the entity
id can change with the Amazon account. A regression test asserting a specific entity id will
break if the account/email changes and is wrong for any reuse. The intent (assert selection
targets the `alexa_devices` *platform* and never auto-picks the `shopping_list` platform) is
correct; the **entity-id specificity is not**. This is also mild specification drift toward a
single install. Recommend rewording to assert on **platform**, not entity id.

### S-04 — `home-assistant.md` says "Prefer entity services where a target entity makes sense" — misleading for this design
**Severity: Medium.** **File:** `home-assistant.md` (Services).

The integration's services (`add_category`, `edit_category`, `delete_category`,
`recategorize_item`, `reload_category_map`) operate on the **config entry / category map**, not
on an entity. The `06` contract correctly models them with an optional `entry_id`
(`config_entry` selector), **not** as entity services. The steering line nudges an agent toward
registering these as entity-target services (via `async_register_entity_service`), which would
be awkward — the target would have to be the derived sensor, conflating "act on the sensor" with
"edit the shared category map." Recommend removing or qualifying this line for this project
(entity services are not a natural fit here).

### S-05 — No steering captures the `attributes_version` / sensor-attribute-size constraints
**Severity: Medium.** **Files:** none (gap). Relevant plans: `06` (attribute contract,
`attributes_version`, ~16 KB recorder cap, "exclude from recorder"), `05` (recorder exclusion).

The frontend/backend contract, its versioning discipline, and the HA attribute-size limit are
important, cross-cutting, and easy to get wrong — yet no steering file mentions them.
`documentation.md` says "Any change to the sensor attribute schema … updates the contract
section" (good), but nothing steers an agent to: bump `attributes_version` on breaking change,
keep item objects minimal, exclude the sensor from the recorder, or fall back to a websocket
command if the list is large (`15` R7). This is design knowledge that lives only in the plans,
not the steering. Recommend adding a short "sensor attribute contract" subsection to
`home-assistant.md` (or the new `frontend.md`).

### S-06 — `python.md` async guidance vs. a pure, synchronous categorizer is slightly contradictory
**Severity: Low.** **File:** `python.md` (Async patterns) vs. `architecture.md` / `07`.

`python.md`: "Public integration functions are `async`." The categorizer (`categorizer.py`) is
deliberately **pure and synchronous** (no HA import, unit-testable standalone). A literal reader
could think the categorizer functions must be async. The plans are clear the categorizer is sync
and the *coordinator* offloads if needed, but the steering does not carve out the categorizer as
an intentional exception. `python.md` does say offload CPU-bound work with
`async_add_executor_job`, but never states "the categorizer is intentionally sync." Minor, but
worth an explicit carve-out to prevent an agent from needlessly making pure functions async.

### S-07 — `home-assistant.md` coordinator data type contradicts the plan's `Projection` type
**Severity: Low.** **File:** `home-assistant.md` (Coordinator pattern).

Steering: *"The coordinator's data is the computed projection: `dict[str, list[CategorizedItem]]`."*
The plan (`06`) defines the sensor attribute payload as a **richer** structure: an ordered list
of category objects each with `name`, `items`, `collapsed`, plus top-level `total_unchecked`,
`uncategorized_count`, `last_synced`, `options`, `attributes_version`. A bare
`dict[str, list[CategorizedItem]]` cannot represent order, `collapsed`, or the top-level
metadata. The steering's type signature is an oversimplification that, if followed literally,
under-builds the contract. Recommend aligning the steering to reference the `Projection`/contract
in `docs/plans/06` rather than pinning a lossy dict type.

### S-08 — `home-assistant.md` diagnostics line about redacting credentials is slightly self-contradictory
**Severity: Low / Observation.** **File:** `home-assistant.md` (Diagnostics and repairs).

"returning a redacted dump: config entry (credentials redacted — though this integration stores
none)…". Harmless, but it invites an agent to add a `REDACT_KEYS` set for credentials that do not
exist. `security.md` and `10` are clearer (redact *item text* on opt-in). Minor wording cleanup:
emphasise item-text redaction, drop the credential framing.

### S-09 — Missing steering: config/options-flow UX strings, translations, and `strings.json` discipline
**Severity: Low.** **Files:** gap. `home-assistant.md` mentions `translations` and `services.yaml`
metadata but gives no rule about keeping `strings.json`/`translations/en.json` in sync, abort
reasons (`no_alexa_lists`, `already_configured`), or error keys. The plans reference these
(`04`), but there is no steering to enforce the discipline. Low impact for a single-locale v1.

### S-10 — Missing steering: HACS packaging / frontend-resource registration expectations
**Severity: Low / Observation.** **Files:** gap. `11` and `13` describe serving the built card as
a frontend resource and `hacs.json`. No steering captures how the card asset is registered/served
(e.g. `async_register_static_paths` + `add_extra_js_url`, or panel registration) or the HACS
`hacs.json` shape. This is genuinely error-prone (a common custom-integration failure point) and
would benefit from a short rule, likely in the proposed `frontend.md`.

---

## 3. Cross-Steering Consistency

| Pair | Consistent? | Notes |
|------|-------------|-------|
| product ↔ architecture | Yes | Same source entity, same vegan rules, same no-drift principle. |
| product ↔ home-assistant | Yes | Both name the source entity; supported_features 7; completed retained. |
| architecture ↔ home-assistant | Mostly | Coordinator data type differs (S-07); otherwise aligned. |
| architecture ↔ plans | Tension | "No business logic in card the backend can't enforce" vs. card-only timer/retry (S-02). |
| security ↔ python ↔ home-assistant (logging) | Yes | All three agree: item text at `debug` only, never at info+. No conflict; some duplication (see S-11). |
| testing ↔ home-assistant/python | Yes | Coverage gates, mocking, and required areas align with the plan's test matrix. |
| documentation ↔ all | Yes | Update triggers reference the contract and decision log correctly. |

### S-11 — Duplication of the logging rule across three steering files
**Severity: Observation.** The "item text at debug only; never credentials/full contents at
info+" rule appears near-verbatim in `security.md`, `python.md`, and `home-assistant.md`. This
contradicts `documentation.md`'s own "Do not duplicate the same fact across multiple docs — link
to the canonical location." Not harmful (the rule is consistent), but it is drift-prone: a future
edit to one copy can desync the others. Consider making `security.md` canonical and having the
others reference it.

---

## 4. Plan and Steering Alignment

- Steering **accurately reinforces** the core architecture: custom integration over pyscript,
  pure categorizer, HA Store persistence, single write target, no Amazon calls, service-based
  category maintenance, vegan rules. These are the decisions most likely to be gotten wrong by a
  fresh agent, and the steering nails them.
- Steering **captures security requirements** well (no credentials, local-only, redaction, input
  validation, XSS-safe rendering, SSRF posture, pinned deps).
- Steering **captures testing expectations** well (coverage gates, required areas, mocking,
  regression-first).
- Steering **does not fully capture**: the frontend contract/versioning (S-05), the card's
  behavioural rules (S-01), and the client-vs-backend enforcement boundary for sync (S-02).
- Steering **introduces one drifted specific** (hard-coded entity id, S-03) and one misleading
  nudge (entity services, S-04).
- Steering does **not** introduce unsupported *product* requirements — no scope creep beyond the
  plans. Good.

---

## 5. Missing Steering (guidance that should exist but does not)

1. **`frontend.md`** — the biggest gap. Card contract, per-item undo state machine, client-side
   retry/backoff rules, accessibility, XSS-safe rendering (currently only in security), sanctioned
   websocket/service calls, resource registration/packaging. (S-01, S-02, S-10)
2. **Sensor attribute contract discipline** — versioning, size limits, recorder exclusion. (S-05)
3. **Client-vs-backend enforcement boundary** — explicit ruling on where the grace timer/retry
   lives and the accepted safety trade-off. (S-02)
4. **Config/options-flow strings/translations discipline** — abort reasons, error keys. (S-09)
5. **Recorder exclusion guidance** — mentioned in plans; not steered.

---

## 6. Steering Effectiveness — Overall Assessment

> "Are the Kiro steering files sufficient to ensure consistent implementation of this project?"

**Answer: Mostly, with changes required.**

**Why "mostly":** For the **backend** (`custom_components/**`, `**/*.py`, `tests/**`) the steering
is genuinely strong. A fresh agent building the integration, coordinator, categorizer, store,
sensor, services, diagnostics, and tests — guided by these files plus the plan — would make the
intended decisions with high consistency. The architecture, security, and Python steering are
precise and enforce the hard-won reality-based overrides.

**Why "with changes required":** The **frontend card** — which owns the most requirement-dense and
security-sensitive UX (Req 3.x, 4.x, 5.4) — is effectively **un-steered** beyond three
always-on files, because `home-assistant.md`, `python.md`, and `testing.md` all scope away from
`frontend/`. Combined with the unresolved client-vs-backend enforcement ambiguity (S-02) and the
missing sync-failure/card-closed rule, a fresh agent implementing the card could plausibly ship
something that silently drops completions (violating Req 5.4) while believing it followed
steering. That is the gap that pushes the answer from "yes" to "mostly."

**The three changes that most improve consistency:**
1. Add a `frontend.md` steering file (S-01) and widen `testing.md` to card tests.
2. Resolve the client-vs-backend sync-enforcement boundary explicitly in steering (S-02).
3. Fix the two drifted/misleading items: hard-coded entity id (S-03) and entity-services nudge (S-04).
