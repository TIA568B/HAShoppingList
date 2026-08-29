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
- **Objective:** the deterministic categorization + shop-resolution core + persistence.
- **Files:** `models.py`, `categorizer.py`, `store.py`, default taxonomy + default shops.
- **Dependencies:** Phase 0.
- **Acceptance:** categorizer passes the full vegan matrix **and the shop-resolution matrix**
  (doc 12) at 100% coverage — including the precedence (shop-name-in-text > learned override >
  keyword rule > No Preference) and deleted-shop self-heal; store loads default categories +
  default shops (Aldi/Asda/Tesco with starter keyword rules), persists, migrates.
- **Tests:** `test_categorizer.py` (categories + shops), store/migration tests.

## Phase 2 — Config flow + coordinator + sensor
- **Objective:** select source entity, read items, expose the projection.
- **Files:** `config_flow.py`, `coordinator.py`, `sensor.py`, `strings.json`, translations.
- **Dependencies:** Phase 1.
- **Acceptance:** selecting the `alexa_devices` todo list creates an entry; sensor shows the
  categorized projection matching the contract (v3: shop-primary `shop_groups`,
  `category_definitions`, `shop_definitions`, per-item shop+category); recomputes on
  source `state_changed` (latency: a few seconds on push, up to ~5 min on a missed push via the
  upstream poll — finding M-5); handles unavailable source; reconfigure flow changes the source.
- **Tests:** `test_config_flow.py`, `test_coordinator.py`, `test_sensor.py`.

## Phase 2.5 — Runtime-assumption spike (implementer, WRITE action)
- **Objective:** de-risk the two-way-sync value proposition before investing in the card.
- **Action:** in the implementation environment, perform **one** manual `todo.update_item` on the
  real Alexa list and confirm it appears on the Alexa app; observe `uid` stability across two
  refreshes. (Findings M-6 / R1 / R2.)
- **Dependencies:** Phase 2.
- **Gate:** card work (Phases 4–5) does not start until this passes.
- **Note:** this is a **write** action for the implementer — explicitly **out of scope** for the
  read-only planning/review tasks; must not be run via a read-only MCP.

## Phase 3 — Services (maintenance + learning) — categories **and shops**
- **Objective:** category + shop CRUD + learned re-categorization/assignment.
- **Files:** `services.py`, `services.yaml`, options flow additions.
- **Dependencies:** Phase 2.
- **Acceptance:** category services as before (add/edit/delete + `recategorize_item`, delete→
  Uncategorized, rename migrates overrides); **shop services** `assign_shop` (learns; `No
  Preference` clears), `add_shop`/`edit_shop` (name + keyword rules; reject reserved
  `No Preference`; rename migrates shop overrides), `delete_shop` (reassign items→`No Preference`,
  never delete); duplicate/invalid rejected.
- **Tests:** `test_services.py` (categories + shops), `test_options_flow.py`.

## Phase 4 — Frontend card: render + live + add
- **Objective:** live shop-primary/category-secondary view with add-item.
- **Files:** `frontend/**`.
- **Dependencies:** Phase 2 (contract) + 3 (category + shop edit).
- **Acceptance:** card subscribes and re-renders live; renders **shop-primary then category**
  from `shop_groups` (`No Preference` last); add-item calls `todo.add_item`; collapse-when-empty
  works at shop and category level.
- **Tests:** card unit tests (shop-primary render, collapse, add).

## Phase 5 — Frontend card: tick + undo + errors
- **Objective:** complete-on-tap with reversing undo, per-item undo window, error surfacing.
- **Files:** `frontend/**`.
- **Dependencies:** Phase 4, **Phase 2.5 spike passed**.
- **Acceptance:** tap sends `todo.update_item(completed)` immediately (finding H-1); undo within
  the window sends the reversing `needs_action` call; window expiry drops the undo affordance with
  no extra call; independent per-item windows; failed sync retries then reverts + toasts (Req 5.4);
  inbound source change to a tracked uid cancels the local undo affordance (source wins, M-7).
- **Tests:** card state-machine unit tests incl. "card gone during undo window" and
  "inbound delete during undo window".
- **Also in this phase:** per-item "set shop" action calling `assign_shop`, and the shop-settings
  panel (`add_shop`/`edit_shop`/`delete_shop`) reading `shop_definitions`. (Req 7.1/7.2)

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

0 → 1 → 2 → **2.5 (gate)** → 3 → 4 → 5 → 6 → 7. Phases 1 and (later) the card's pure logic can
proceed in parallel with backend wiring since the categorizer and the card's timer logic are
independent of HA I/O. The Phase 2.5 spike gates the card phases (4–5) but not the service phase
(3), which can proceed in parallel.
