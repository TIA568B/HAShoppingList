# 02 — Existing Environment Analysis

All Home Assistant findings below were gathered via the Home Assistant MCP in **strictly
read-only mode**. No entity, device, area, automation, script, helper, or configuration was
created, modified, enabled, disabled, or triggered. No state-changing service was called.

## Repository (confirmed)

- Greenfield repo. Only `docs/specs/` (requirements, design, tasks) and a generic `.gitignore`
  exist. Single "Initial commit" on `main`.
- No `custom_components/`, no Python sources, no tests, no CI, no tooling config.
- `.gitignore` already ignores `*.py[cod]`, `.DS_Store`, `node_modules/`, `dist/` — adequate
  starting point; will extend for Python/HA artifacts during implementation.

## Home Assistant instance (confirmed via MCP)

| Property | Value |
|----------|-------|
| API status | running |
| Version | 2026.8.3 |
| Timezone | Europe/London |
| Unit system | °C (metric) |
| Components loaded | 263 |
| HACS | Installed (device "HACS — hacs.xyz" present) |
| pyscript | Not detected (no entities) |

### Todo entities (confirmed)

| Entity | Platform | State (count) | Notes |
|--------|----------|--------------:|-------|
| `todo.shopping_list` | `shopping_list` | 0 | Native HA list. **Not** Alexa. Unrelated. Ignore. |
| `todo.david_carson_amazon_gmail_com_shopping_list` | `alexa_devices` | 14 | **The real Alexa shopping list.** Source entity. |
| `todo.david_carson_amazon_gmail_com_to_do_list` | `alexa_devices` | 0 | Alexa to-do list. Out of scope v1. |

- Related entity on the same device: `button.david_carson_amazon_gmail_com_bed_time` (a
  routine). Device id prefix `cd673d98...`.
- No automations reference the shopping list entity.
- State value is the **count of active (needs_action) items** — the "14" — not the full
  contents. Completed items are not reflected in the state number.

### History / recorder (confirmed)

- `get_history` (240h) and `get_entity_summary` (30d) and `get_logbook` (720h) all return
  **no history** for the Alexa shopping list entity.
- Implication: the spec's history-mining bootstrap (Req 1) has no data to mine. Overridden
  (see doc 01, C2).

### `alexa_devices` todo behavior (confirmed from HA core source, `dev` branch)

Read from the current core source of `homeassistant/components/alexa_devices/todo.py` and
`coordinator.py` (matches the observed `supported_features: 7`):

- `supported_features = CREATE_TODO_ITEM | UPDATE_TODO_ITEM | DELETE_TODO_ITEM` (= 7). **No**
  `MOVE_TODO_ITEM`, **no** `SET_DUE_*`.
- `todo_items` returns **all** items, each with `uid` (stable Amazon item id), `summary`
  (name), and `status` mapped to `COMPLETED` / `NEEDS_ACTION`. **Completed items are
  retained and returned.**
- Complete/undo is `set_todo_list_item_checked_status` (does not delete). Rename is
  `rename_todo_list_item`. Delete is separate. Items carry an internal `version` for
  optimistic concurrency — abstracted away behind the public `todo.*` services (we operate by
  `uid`).
- The coordinator has `SCAN_INTERVAL = 300` (5-min poll) **and** a push path: `on_todo_event`
  handler updates the cache and calls `async_update_listeners()`. So the source entity's HA
  state updates in near real time when the list changes on Alexa — satisfying the reactive
  requirement without us polling Amazon.

### Areas (confirmed, context only)

13 areas exist (Bedroom, Kitchen, Lounge, Office, etc.). Not directly relevant; the
integration will attach its entities to a **service device**, not an area.

## Confirmed / Assumption / Recommendation

**Confirmed**
- Source entity identity, platform, supported features, completed-item retention, push+poll
  reactivity, absence of recorder history, HACS present, pyscript absent, HA 2026.8.3.

**Assumptions** (documented; see doc 15 for full list)
- The `alexa_devices` todo services reliably propagate completion/adds back to the real Alexa
  app (spec §6 states the user confirmed this; not independently mutation-tested because MCP is
  read-only for this task).
- Item `uid`s are stable across polls/pushes for the lifetime of an item (supported by the
  source code using `uid` as the dict key and for updates/deletes).

**Recommendations**
- Make the source entity **user-selectable** in the config flow (auto-suggest `alexa_devices`
  todo entities) rather than hard-coding the current entity id, so the integration survives
  account/entity-id changes and is reusable.
- Consider excluding the projection sensor from the recorder to avoid noisy history.

## MCP tooling limitation noted

`todo.get_items` is a **read-only** query service. Attempts to call it through the MCP wrapper
errored (the wrapper does not appear to return `ServiceResponse` payloads). This is a tooling
limitation only — **no state change occurred**. At runtime the integration will use
`todo.get_items` with `return_response=True`, which is the documented, supported mechanism.
