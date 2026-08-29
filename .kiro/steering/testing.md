---
inclusion: fileMatch
fileMatchPattern: 'tests/**'
---

# Testing Steering

## Framework and tooling

- Use `pytest` with `pytest-homeassistant-custom-component` (the standard harness for custom
  integrations). Async tests via `pytest-asyncio` (provided by the harness).
- Tests must run without network access and without a real Home Assistant install beyond the
  test harness. No live Amazon/Alexa calls, ever.

## Coverage expectations

- The pure `categorizer` module: **100%** line and branch coverage. It is the behavioral
  core and has no HA dependency, so there is no excuse for gaps.
- Overall integration: target **>=90%** line coverage; every config/options flow step,
  service, and error branch must be exercised.

## Required test areas

- **Categorizer (pure):** normalization, keyword match, milk->Milk, dairy->Chilled,
  meat->Fake Meat, animal-derived/egg/fish->Uncategorized, learned-override precedence,
  no-match->Uncategorized, empty/odd input.
- **Config flow:** happy path (select source todo entity), abort on no todo entities, abort
  on already-configured, single-instance-per-source rule.
- **Options flow:** grace-period tuning, source-entity change, category-map edits round-trip.
- **Coordinator:** builds projection from mocked `todo.get_items` response (active +
  completed), recomputes on source state change, debounces bursts, handles source entity
  unavailable, safety-net poll.
- **Sensor:** attribute schema matches the documented frontend contract exactly; availability
  reflects coordinator + source state.
- **Services:** `recategorize_item` persists a learned override and re-runs; `delete_category`
  reassigns to `Uncategorized` (never deletes items); add/edit validate input; invalid input
  raises.
- **Sync / error paths:** completing an item calls `todo.update_item(status=completed)` by
  `uid`; undo calls `status=needs_action`; failed sync retries then surfaces an error and
  reverts optimistic state (Requirement 5.4).
- **Diagnostics:** output is redacted; no secrets or (when redaction on) item text leak.

## Mocking expectations

- Mock the source todo entity and `todo.*` services; assert exact service data payloads
  (domain, service, target entity_id, `uid`, `status`).
- Use the harness's `MockConfigEntry` and `hass` fixtures. Freeze time for grace-period and
  debounce tests.
- Snapshot-test the sensor attribute projection to catch contract drift.

## Regression tests

- Every bug fix adds a failing-first test reproducing the bug.
- Keep a regression test asserting the source entity is
  `todo.david_carson_amazon_gmail_com_shopping_list`-style (alexa_devices platform) selection
  logic and that `todo.shopping_list` is not silently chosen.

## Frontend

- Where practical, unit-test the card's pure logic (grace-period timer state machine,
  optimistic/undo transitions, collapse-when-empty) with a JS test runner. DOM-heavy paths
  may be covered by lightweight component tests; do not require a full browser E2E in CI.

## CI gate

- `ruff` (lint + format), `mypy` (strict), and `pytest` must all pass. Coverage thresholds
  above are enforced in CI.
