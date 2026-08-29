---
inclusion: fileMatch
fileMatchPattern: '{tests/**,frontend/**}'
---

# Testing Steering

Applies to backend tests under `tests/**` and to the card's own tests under `frontend/**`
(so card tests receive the testing steering — finding H-2 / S-10).

## Framework and tooling

- Use `pytest` with `pytest-homeassistant-custom-component` (the standard harness for custom
  integrations). Async tests via `pytest-asyncio` (provided by the harness).
- Tests must run without network access and without a real Home Assistant install beyond the
  test harness. No live Amazon/Alexa calls, ever.

## Coverage expectations

- The pure `categoriser` module: **100%** line and branch coverage. It is the behavioral
  core and has no HA dependency, so there is no excuse for gaps.
- Overall integration: target **>=90%** line coverage; every config/options flow step,
  service, and error branch must be exercised.

## Required test areas

- **Categoriser (pure):** normalization, keyword match, milk->Milk, dairy->Chilled,
  meat->Fake Meat, animal-derived/egg/fish->Uncategorised, learned-override precedence,
  no-match->Uncategorised, empty/odd input. **Shop resolution (Req 7) precedence:** shop-name-in-text
  (beats learned override) -> learned override -> keyword rule -> No Preference; deleted-shop
  self-heals to No Preference; shop independent of category.
- **Config flow:** happy path (select source todo entity), abort on no todo entities, abort
  on already-configured, single-instance-per-source rule.
- **Options flow:** grace-period tuning (range 8–30s), category-map edits round-trip. Options must
  **not** change the source entity.
- **Reconfigure flow:** changing the source entity updates `entry.data` and `unique_id` atomically
  and preserves the (entry-keyed) category store.
- **Coordinator:** builds projection from mocked `todo.get_items` response (active +
  completed), recomputes on source state change, debounces bursts, handles source entity
  unavailable, safety-net poll.
- **Sensor:** attribute schema matches the documented frontend contract exactly (currently
  `attributes_version: 3`, including `category_definitions`, `shops`, and per-item `shop`);
  availability reflects coordinator + source state.
- **Services:** `recategorise_item` persists a learned override and re-runs; `delete_category`
  reassigns to `Uncategorised` (never deletes items); `edit_category` rename **migrates learned
  overrides** to the new name; add/edit validate input; invalid input raises. **Shop services
  (Req 7):** `assign_shop` learns a shop (and `No Preference` clears it); `delete_shop` reassigns
  to `No Preference` (never deletes items); `edit_shop` rename migrates shop overrides;
  `add_shop`/`edit_shop` reject duplicates and the reserved `No Preference`.
- **Sync / error paths:** completion is sent **on tap** via `todo.update_item(status=completed)`
  by `uid` (complete-on-tap); undo is the reversing `status=needs_action` call; failed sync
  retries then surfaces an error and reverts optimistic state (Requirement 5.4). Cover the
  "card gone during undo window" case (completion already synced, nothing dropped) and the
  "inbound source change to a tracked uid cancels the local undo affordance" case (source wins).
- **Diagnostics:** output is redacted; no secrets or (when redaction on) item text leak.

## Mocking expectations

- Mock the source todo entity and `todo.*` services; assert exact service data payloads
  (domain, service, target entity_id, `uid`, `status`).
- Use the harness's `MockConfigEntry` and `hass` fixtures. Freeze time for grace-period and
  debounce tests.
- Snapshot-test the sensor attribute projection to catch contract drift.

## Regression tests

- Every bug fix adds a failing-first test reproducing the bug.
- Keep a regression test asserting source selection targets an entity on the **`alexa_devices`
  platform** and never silently chooses an entity on the `shopping_list` platform. Assert on the
  **platform**, not a specific entity id — the source entity id is account-derived and
  user-selectable, so a hard-coded id is brittle and install-specific (finding M-8 / S-03).

## Frontend

- Where practical, unit-test the card's pure logic (grace-period timer state machine,
  optimistic/undo transitions, collapse-when-empty) with a JS test runner. DOM-heavy paths
  may be covered by lightweight component tests; do not require a full browser E2E in CI.

## CI gate

- `ruff` (lint + format), `mypy` (strict), and `pytest` must all pass. Coverage thresholds
  above are enforced in CI.
