---
inclusion: fileMatch
fileMatchPattern: 'custom_components/**'
---

# Home Assistant Development Steering

Applies to all code under `custom_components/alexa_shopping_categoriser/` and its tests.
Follow current (2025-2026) Home Assistant core integration conventions.

## Integration structure

- Domain: `alexa_shopping_categoriser`. Keep it consistent across `manifest.json`,
  `const.py` (`DOMAIN`), config entries, and translations.
- `manifest.json` must include: `domain`, `name`, `version` (required for custom
  components), `codeowners`, `config_flow: true`, `iot_class: calculated`,
  `integration_type: service`, `dependencies: ["todo"]`, and `requirements` (keep empty if
  no third-party libs are needed — prefer stdlib).
- The sidebar panel needs `frontend`/`panel_custom` at runtime. Declare these as
  **`after_dependencies: ["frontend", "panel_custom"]`**, not hard `dependencies`: they must
  not become a hard setup requirement (it breaks the test harness, which has no
  `hass_frontend`). Panel registration is best-effort and guarded, and ensures `panel_custom`
  is set up at runtime itself.
- Bumping `manifest.json` `version` is how a change reaches HACS users — see the canonical
  release flow in `release-and-deployment.md`. Editing the workspace alone ships nothing.
- Config-entry only. Do not support YAML configuration.

## Async requirements

- All entrypoints are `async`. Never block the event loop.
- Any blocking work (file I/O beyond the Store helper, CPU-heavy matching over large lists)
  must use `hass.async_add_executor_job`.
- Use the HA `Store` helper (`homeassistant.helpers.storage.Store`) for persistence, not raw
  file writes.

## Lifecycle

- `async_setup_entry`: create the store, load the category map, create the coordinator, call
  `await coordinator.async_config_entry_first_refresh()`, register services, forward the
  `sensor` platform via `async_forward_entry_setups`.
- `async_unload_entry`: unload platforms, remove service registrations if last entry,
  cancel any pending grace-period timers, and detach the source-entity state listener.
- Support reload (`async_reload_entry`) so option changes re-read cleanly.
- Register a config-entry update listener for the options flow.

## Coordinator pattern

- Subclass `DataUpdateCoordinator`. This integration is **event-driven**: primary trigger is
  a state-change listener on the source todo entity (`async_track_state_change_event`);
  `update_interval` is a slow safety-net poll (e.g. 15 minutes) that calls `todo.get_items`.
- The coordinator's data is the computed **`Projection`** as defined in
  `docs/plans/06-data-model-and-contract.md` (ordered categories with `collapsed`, plus top-level
  `total_unchecked`, `uncategorised_count`, `last_synced`, `options`, `category_definitions`,
  `attributes_version`). Do not model it as a bare `dict[str, list[CategorisedItem]]` — that loses
  order, collapse state, and metadata (finding L-5 / S-07).
- Read source items via the `todo.get_items` service with
  `data: {status: [needs_action, completed]}` and `return_response=True`. The response is keyed by
  entity id — read `response[source_entity_id]["items"]`, each item having `summary`, `uid`,
  `status`; map `summary → name`, `status == "completed" → completed`. Completed items are part of
  the learning corpus.
- Debounce recomputation so a burst of source updates coalesces.

## Entity design

- One `sensor` entity: `sensor.<config_entry_slug>_categorised`.
  - `unique_id` = `f"{entry.entry_id}_categorised"`. Never derive unique IDs from names or
    entity IDs that can change.
  - State = total unchecked item count (numeric, `state_class` not set — it is not a
    measurement to record long-term; consider excluding from recorder).
  - Attributes = the categorised projection (see the frontend contract) plus `last_synced`.
  - `should_poll = False`; updates come from the coordinator.
  - Availability follows `coordinator.last_update_success` and the source entity being
    available/known.
- Attach entities to a **service device** in the device registry
  (`entry_type = DeviceEntryType.SERVICE`) named after the integration, with
  `identifiers = {(DOMAIN, entry.entry_id)}`. Do not attach to the Alexa device.

## Services

- Define services in `services.yaml` with full field metadata and translations.
- Services: `recategorise_item`, `add_category`, `edit_category`, `delete_category`,
  `assign_shop`, `add_shop`, `edit_shop`, `delete_shop`, `reload_maps` (re-read the whole store
  from disk — categories and shops), `reload_defaults` (re-seed categories/shops from the shipped
  `default_map.json`, keeping learned overrides; destructive to category/shop edits, so the card
  confirms it). Validate all input with voluptuous schemas.
- `delete_category` must reassign affected items to `Uncategorised`, never delete items.
  `delete_shop` must reassign affected items to `No Preference`, never delete items (Req 7.6).
- `edit_category`/`edit_shop` rename must migrate learned overrides pointing at the old name to the
  new name, so a rename does not silently discard learning (finding REVIEW2-003). `add_shop`/
  `edit_shop` also set/replace the shop's keyword rules (Req 7.3) and reject the reserved
  `No Preference` (Req 7.8).
- `assign_shop` persists a learned shop override (normalized item text → shop) mirroring
  `recategorise_item`; `No Preference` clears it. The resolution **precedence** (shop name in item
  text > learned override > keyword rule > No Preference — shop-name-in-text beats a learned
  override) lives in the pure categoriser, not in services. The projection is grouped
  **shop-primary, then category** (Req 7.7).
- These are **config-entry-scoped** services operating on the shared category map, targeted by an
  optional `entry_id` (`config_entry` selector) — **not** entity services. Do not register them
  via `async_register_entity_service`; the category map is not an entity (finding S-04).

## Config / options / reconfigure flow

- Options flow tunes `grace_period_seconds` (8–30, default 9), `show_completed`,
  `collapse_empty_categories`, `redact_items_in_diagnostics`. Options must **not** change the
  source entity.
- Because `entry.unique_id` is the source entity id, changing the source is a **reconfigure**
  operation (`async_step_reconfigure`) that updates `entry.data` and `unique_id` atomically, not
  an options edit (finding M-3).
- Keep `strings.json` and `translations/en.json` in sync in the same change set. Define abort
  reasons (`no_alexa_lists`, `already_configured`) and error keys as constants, never hard-coded
  strings (finding L-8 / S-09).

## Sensor attribute contract discipline

- The sensor's attributes are the frontend contract (canonical in `docs/plans/06`). Keep item
  objects minimal (`uid`, `name`, `checked`). Bump `attributes_version` on any breaking shape
  change and update doc 06 in the same change set.
- Exclude the sensor from the recorder (large JSON attribute, changes often). If a list ever grows
  large enough to approach the ~16 KB attribute cap, expose the projection via a dedicated
  websocket read command instead of inflating the attribute (finding M-4 / S-05).

## Sync back to the source list

- **Complete-on-tap:** completion is sent to the source **immediately on tap** via
  `todo.update_item(status: completed)`, matched by `uid` — not deferred behind a client-side
  grace timer. The grace window governs undo only. This guarantees a tapped completion is never
  silently lost if the card closes (Req 5.4) and keeps enforcement at the backend/service boundary
  (finding H-1).
- Undo: reversing `todo.update_item(status: needs_action)`.
- Add: `todo.add_item` on the source entity.
- Never call Amazon directly. Respect that the source entity uses optimistic concurrency
  (version) internally — always operate by `uid` through the public service.

## Diagnostics and repairs

- Implement `async_get_config_entry_diagnostics` returning a redacted dump: entry data/options,
  category map summary, current projection sizes, source entity id, last sync time. The relevant
  redaction target is **item text** (personal data) via `async_redact_data`, gated on the
  `redact_items_in_diagnostics` option (default true). This integration stores no credentials, so
  do not add a credentials `REDACT_KEYS` set for keys that do not exist (finding L-6 / S-08).
- Raise a repair issue if the configured source todo entity is missing or becomes
  unavailable for an extended period.

## Reauthentication / migration

- This integration holds no credentials (auth belongs to `alexa_devices`), so no reauth flow
  is needed. If the source entity is removed, surface a repair issue.
- Version the config entry and the stored data schema. Provide `async_migrate_entry` for
  future schema changes.

## Error handling expectations

- Wrap source service calls; on failure, retry with backoff, then surface a user-visible
  error and revert optimistic state. Never drop a change silently (Requirement 5.4). Because
  writes are sent on the user action (complete-on-tap), a closed card cannot silently drop a
  completion — the change is already synced.
- At **first refresh**, distinguish "source entity not ready yet" (absent or
  `unavailable`/`unknown` → raise `ConfigEntryNotReady`, HA retries) from a genuine read error
  with the entity present (→ `UpdateFailed`) (finding L-3).
- Raise `ConfigEntryNotReady` from setup when the source entity is not yet available.
- Use `HomeAssistantError` for user-facing service failures.
