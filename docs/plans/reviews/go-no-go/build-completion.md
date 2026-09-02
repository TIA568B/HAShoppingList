# Build Completion Report — alexa_shopping_categoriser

Date: 2026-08-29
Author: Implementation / Build Agent
Gate: TDA decision was **GO** (`docs/plans/reviews/go-no-go/tda-review.md`, 2026-08-29) before
any code was written.

---

## Implementation Summary

Built the approved `alexa_shopping_categoriser` Home Assistant custom integration plus its
bundled Lovelace card, following the phased plan in `docs/plans/14-implementation-plan.md` and
all eight `.kiro/steering/` files.

The integration reads an Alexa Devices `todo` list through the public `todo.*` services,
computes a **derived, shop-primary → category-secondary projection** (never a second copy of
the list), learns categories and shop preferences over time, and exposes the projection on a
single sensor. The bundled card renders the tree and drives tick/undo/add/shop interactions
using **complete-on-tap + reversing undo**. No Amazon credentials are held and the integration
makes no outbound network calls of its own.

Backend (`custom_components/alexa_shopping_categoriser/`):
`__init__.py` (lifecycle), `const.py`, `manifest.json`, `models.py`, `defaults.py`,
`categoriser.py` (pure), `projection.py` (pure), `store.py`, `coordinator.py`, `sensor.py`,
`config_flow.py` (config + options + reconfigure), `services.py` (9 services), `diagnostics.py`,
`repairs.py`, `frontend.py` (card resource registration), `services.yaml`, `strings.json`,
`translations/en.json`, `www/alexa-shopping-categoriser-card.js` (shipped card bundle).

Frontend (`frontend/alexa-shopping-categoriser-card/`): pure modules `normalize.js`,
`escape.js`, `tick-controller.js`, `collapse-state.js`, `add-reconciler.js`; `card.js`
(custom element); `index.js` (registration); rollup build; `node:test` suite.

## Requirements → Implementation

| Req | Requirement | Where implemented | Verified by |
| --- | --- | --- | --- |
| 1.2–1.6, 1.8 | Vegan default taxonomy; ambiguous → Uncategorised; never blocks setup | `defaults.py`, `categoriser.py`, `store.py` | `test_categoriser.py`, `test_store.py` |
| 1.7 (intent) | Non-blocking review opportunity | card review banner + prominent Uncategorised | `card.js` (`_renderReviewBanner`) |
| 2.1–2.3 | Ongoing categorisation; Uncategorised fallback | `categoriser.py`, `coordinator.py` | `test_categoriser.py`, `test_coordinator.py` |
| 2.4 | Manual correction persists (learning) | `services.recategorise_item` → `overrides` | `test_services.py` |
| 3.1 | Live update on source change | coordinator state listener + card `subscribe` | `test_coordinator.py` (recompute), card render |
| 3.2 | Optimistic tick | `tick-controller.js` | `tick-controller.test.js` |
| 3.3 | Collapse empty categories | `projection.py` (`collapsed`) + `collapse-state.js` | `test_sensor.py`, `collapse-state.test.js` |
| 4.1–4.5 | Undo window, per-item, independent | `tick-controller.js` | `tick-controller.test.js` |
| 5.1–5.4 | Sync back; retry; never silently drop | `card._updateItem`/`_addItem`, retry/backoff, revert + error | `tick-controller.test.js` |
| 6.1–6.3 | Category maintenance; delete → Uncategorised | `services.py`, `category_definitions` attr | `test_services.py` |
| 7.1–7.8 | Per-item shop preference + precedence + grouping | `categoriser.resolve_shop`, `projection.py`, shop services | `test_categoriser.py`, `test_services.py`, `test_sensor.py` |

Findings closed in code: H-1 (complete-on-tap), M-2 (`category_definitions`), M-3 (reconfigure),
M-7 (source-wins reconcile), M-8 (platform-based source selection regression test), L-3
(NotReady vs UpdateFailed), REVIEW2-001 (get_items envelope), REVIEW2-002 (add reconciliation),
REVIEW2-003 (rename migrates overrides), F4-1 (store default injection), F4-2 (whole-word
matching), F4-3 (`reload_maps`), R7-L2 (dictionary-word shop warning), R7-O1
(`no_preference_position`).

## Implementation Phases

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Scaffolding, manifest, tooling, CI | Complete |
| 1 | Pure categoriser + models + store | Complete (categoriser 100% cov) |
| 2 | Config flow + coordinator + sensor | Complete |
| 2.5 | Runtime write-spike (real Alexa write) | **Not run — implementer-environment gate, out of scope here** (see Known Issues) |
| 3 | Services (category + shop CRUD + learning) | Complete |
| 4 | Card render + live + add | Complete |
| 5 | Card tick + undo + errors + shop actions | Complete |
| 6 | Diagnostics, repairs, docs | Complete |
| 7 | End-to-end validation (real HA/Alexa) | **Not run — implementer-environment gate, out of scope here** (see Known Issues) |

## Tests

Backend — command:
`.venv/bin/python -m pytest tests/ --cov=custom_components.alexa_shopping_categoriser --cov-report=term-missing --cov-fail-under=90`
Result: **99 passed**. Total coverage **96%**. Pure `categoriser.py` **100%** (gate met).

Files: `test_categoriser.py`, `test_store.py`, `test_init.py`, `test_coordinator.py`,
`test_sensor.py`, `test_config_flow.py`, `test_services.py`, `test_diagnostics.py`,
`test_frontend.py`.

Coverage by module (line): categoriser 100, projection 100, diagnostics 100, repairs 100,
frontend 100, models 100, runtime 100, const 100, __init__ 98, coordinator 96, sensor 95,
config_flow 94, services 94, store 90.

Frontend — command (in `frontend/alexa-shopping-categoriser-card/`): `node --test`
Result: **24 passed** (tick/undo/expiry, per-item independence, card-gone-during-window,
source-wins, add reconciliation, collapse manual+auto, normalize parity, escape).

The required sync/error scenarios are covered: complete-on-tap send, reversing undo within
window, window-expiry drops affordance with no extra call, failed sync reverts + surfaces error
(Req 5.4), card gone during undo window (nothing dropped), inbound change cancels affordance.

## Validation

| Tool | Command | Result |
| --- | --- | --- |
| Ruff lint | `ruff check custom_components tests` | PASS |
| Ruff format | `ruff format --check custom_components tests` | PASS |
| Mypy (strict) | `mypy custom_components/alexa_shopping_categoriser` | PASS (15 files) |
| Pytest + coverage | see above | PASS (99, 96%, ≥90% gate) |
| Card build | `npm run build` | PASS (bundle produced) |
| Card tests | `node --test` | PASS (24) |
| Dependency audit (card) | `npm audit` | 0 vulnerabilities |

CI (`.github/workflows/ci.yml`) runs the backend gate (ruff, format, mypy strict, pytest with
`--cov-fail-under=90` and a categoriser 100% gate) and the frontend gate (npm ci, test, build).

## Deviations

- **DEV-001 (material, recorded):** full British-spelling rename directed by the owner — domain
  `alexa_shopping_categorizer` → `alexa_shopping_categoriser`, module `categoriser.py`, service
  `recategorise_item`, attribute `uncategorised_count`, label `Uncategorised`, and design doc
  `07-categorisation-engine.md`. `attributes_version` stays 3 (initial shipped contract, no
  consumer to break). Historical specs/reviews left unchanged; active plans + steering updated.
  See `docs/plans/reviews/go-no-go/implementation-deviations.md`.

No other material deviations. Minor implementation notes: `apply_to_uid` is accepted for API
compatibility and is satisfied by the unconditional recompute (documented inline in `services.py`);
card minification (terser) was intentionally omitted to keep the dev-dependency surface minimal
and free of known-vulnerable transitive packages.

## Known Issues / Outstanding

1. **Phase 2.5 write-spike (M-6 / R1 / R2) — PASSED (2026-08-29, user-reported).** A manual
   `todo.update_item` on the real Alexa list propagated to the Alexa app, so the two-way-sync
   foundation (write propagation, R1) holds and the card-phase gate is cleared. `uid` stability
   (R2) is validated together with it by the same spike; a full add/complete/undo cycle is still
   to be exercised in Phase 7. The agent did not run the spike itself (read-only MCP scope); this
   records the user's result.
2. **Phase 7 end-to-end validation — NOT executed** (needs live HA/Alexa writes across the full
   add → categorise → tick/undo → complete cycle). Should be run as the pre-release gate.
3. **Environment constraint:** HA `2026.8.3` requires Python `3.14.2`, unavailable on this
   machine (Python `3.13.7`). Tests ran against the latest 3.13-compatible harness,
   `homeassistant==2026.2.3`. The APIs used (config entries, `DataUpdateCoordinator`, `todo.*`
   services, Store, issue/entity registries, static-path + `add_extra_js_url`) are stable across
   these releases, but the suite has not been executed against 2026.8.3 specifically. Re-run CI
   on the target once a 3.14 environment is available.
4. **Pre-publish housekeeping (OQ6, NBR-4):** finalise real `codeowners`/repository URL in
   `manifest.json` and `hacs.json` before publishing. Placeholders currently reference
   `davidcarson`.

None of the above are blocking defects in the delivered code; items 1–2 are planned,
owned runtime gates.

## Documentation updated

- `README.md` (new): prerequisites, install, config-flow walkthrough, card setup, options,
  vegan rules, shop precedence, services, privacy, troubleshooting, dev commands.
- `CHANGELOG.md` (new): Keep a Changelog / semver; initial-contract and migration notes.
- Active plan docs `docs/plans/00`–`15` and doc `07` filename updated for the rename.
- `docs/plans/15-risks-open-questions.md` Decisions log: rename decision entry.
- `docs/plans/reviews/go-no-go/implementation-deviations.md` (new): DEV-001.

## Steering changes

Steering files were updated for the British-spelling rename only (domain/module/service/label
spelling in all eight `.kiro/steering/*.md`). No steering rules were weakened, removed, or
otherwise changed; the architecture, security, testing, and HA conventions remain as approved.

## Final Status

**BUILD COMPLETE** for all phases that can be executed in this environment (Phases 0, 1, 2, 3,
4, 5, 6). Two planned runtime-validation gates — **Phase 2.5 (write spike)** and **Phase 7
(E2E)** — remain outstanding because they require live writes to the user's Alexa account, which
is outside this task's read-only scope. They must be run in the implementation environment before
production/release.
