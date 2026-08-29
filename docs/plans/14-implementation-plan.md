# 14 — Implementation Plan

Phased, each phase independently testable. This reorders the spec's `tasks.md` waves to fit the
custom-integration architecture (the spec's Wave 1 pyscript setup is dropped; history-mining is
replaced by live-list seeding).

## Phase 0 — Scaffolding
- **Objective:** empty, installable integration + tooling + CI.
- **Files:** `custom_components/alexa_shopping_categorizer/{__init__,const,manifest.json}`,
  `pyproject.toml`, `hacs.json`, `.gitignore` updates, CI workflow.
- **Acceptance:** integration loads with a no-op config flow; `ruff`/`mypy`/`pytest` run green.
- **Tests:** smoke test that the component imports and sets up/unloads.

## Phase 1 — Pure categorizer + models + store
- **Objective:** the deterministic categorization core + persistence.
- **Files:** `models.py`, `categorizer.py`, `store.py`, default taxonomy.
- **Dependencies:** Phase 0.
- **Acceptance:** categorizer passes the full vegan matrix (doc 12) at 100% coverage; store
  loads defaults, persists, migrates.
- **Tests:** `test_categorizer.py`, store/migration tests.

## Phase 2 — Config flow + coordinator + sensor
- **Objective:** select source entity, read items, expose the projection.
- **Files:** `config_flow.py`, `coordinator.py`, `sensor.py`, `strings.json`, translations.
- **Dependencies:** Phase 1.
- **Acceptance:** selecting the `alexa_devices` todo list creates an entry; sensor shows the
  categorized projection matching the contract; recomputes on source `state_changed`; handles
  unavailable source.
- **Tests:** `test_config_flow.py`, `test_coordinator.py`, `test_sensor.py`.

## Phase 3 — Services (maintenance + learning)
- **Objective:** category CRUD + learned re-categorization.
- **Files:** `services.py`, `services.yaml`, options flow additions.
- **Dependencies:** Phase 2.
- **Acceptance:** add/edit/delete category and `recategorize_item` persist and re-run;
  delete reassigns items to `Uncategorized` (never deletes); duplicate/invalid rejected.
- **Tests:** `test_services.py`, `test_options_flow.py`.

## Phase 4 — Frontend card: render + live + add
- **Objective:** live categorized view with add-item.
- **Files:** `frontend/**`.
- **Dependencies:** Phase 2 (contract) + 3 (category edit).
- **Acceptance:** card subscribes and re-renders live; add-item calls `todo.add_item`;
  collapse-when-empty works.
- **Tests:** card unit tests (render, collapse, add).

## Phase 5 — Frontend card: tick + undo + errors
- **Objective:** optimistic tick, per-item undo grace period, error surfacing.
- **Files:** `frontend/**`.
- **Dependencies:** Phase 4.
- **Acceptance:** tap→optimistic checked→undo cancels with no call; expiry finalizes via
  `todo.update_item`; independent per-item timers; failed sync retries then reverts + toasts.
- **Tests:** card state-machine unit tests.

## Phase 6 — Diagnostics, repairs, polish, docs
- **Objective:** production-readiness.
- **Files:** `diagnostics.py`, repair issues, `README.md`, `CHANGELOG.md`.
- **Dependencies:** Phases 2–5.
- **Acceptance:** redacted diagnostics; repair issue when source missing; README covers install
  + card + vegan rules; changelog started.
- **Tests:** `test_diagnostics.py`.

## Phase 7 — End-to-end validation (against real HA, post-approval)
- **Objective:** verify the reality-dependent assumptions (writes propagate to Alexa).
- **Acceptance (from spec tasks 5.3–5.6):** add via Alexa voice appears categorized in seconds;
  tick+undo in grace period → no change on Alexa; tick+expire → completed on Alexa; seeding
  puts milk→Milk, dairy→Chilled, meat→Fake Meat, no animal categories.
- **Note:** requires write operations to HA/Alexa and is **out of scope for this design task**
  (MCP is read-only here). Execute only after approval, in the implementation environment.

## Recommended implementation order

0 → 1 → 2 → 3 → 4 → 5 → 6 → 7. Phases 1 and (later) the card's pure logic can proceed in
parallel with backend wiring since the categorizer and the card's timer logic are independent of
HA I/O.
