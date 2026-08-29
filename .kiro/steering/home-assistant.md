---
inclusion: fileMatch
fileMatchPattern: 'custom_components/**'
---

# Home Assistant Development Steering

Applies to all code under `custom_components/alexa_shopping_categorizer/` and its tests.
Follow current (2025-2026) Home Assistant core integration conventions.

## Integration structure

- Domain: `alexa_shopping_categorizer`. Keep it consistent across `manifest.json`,
  `const.py` (`DOMAIN`), config entries, and translations.
- `manifest.json` must include: `domain`, `name`, `version` (required for custom
  components), `codeowners`, `config_flow: true`, `iot_class: calculated`,
  `integration_type: service`, `dependencies: ["todo"]`, and `requirements` (keep empty if
  no third-party libs are needed — prefer stdlib).
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
- The coordinator's data is the computed projection: `dict[str, list[CategorizedItem]]`.
- Read source items via the `todo.get_items` service with
  `data: {status: [needs_action, completed]}` and `return_response=True`. Completed items
  are part of the learning corpus.
- Debounce recomputation so a burst of source updates coalesces.

## Entity design

- One `sensor` entity: `sensor.<config_entry_slug>_categorized`.
  - `unique_id` = `f"{entry.entry_id}_categorized"`. Never derive unique IDs from names or
    entity IDs that can change.
  - State = total unchecked item count (numeric, `state_class` not set — it is not a
    measurement to record long-term; consider excluding from recorder).
  - Attributes = the categorized projection (see the frontend contract) plus `last_synced`.
  - `should_poll = False`; updates come from the coordinator.
  - Availability follows `coordinator.last_update_success` and the source entity being
    available/known.
- Attach entities to a **service device** in the device registry
  (`entry_type = DeviceEntryType.SERVICE`) named after the integration, with
  `identifiers = {(DOMAIN, entry.entry_id)}`. Do not attach to the Alexa device.

## Services

- Define services in `services.yaml` with full field metadata and translations.
- Services: `recategorize_item`, `add_category`, `edit_category`, `delete_category`,
  `reload_category_map`. Validate all input with voluptuous schemas.
- `delete_category` must reassign affected items to `Uncategorized`, never delete items.
- Prefer entity services where a target entity makes sense.

## Sync back to the source list

- Complete an item: `todo.update_item` with `status: completed` targeting the source entity,
  matched by `uid`.
- Undo: `todo.update_item` with `status: needs_action`.
- Add: `todo.add_item` on the source entity.
- Never call Amazon directly. Respect that the source entity uses optimistic concurrency
  (version) internally — always operate by `uid` through the public service.

## Diagnostics and repairs

- Implement `async_get_config_entry_diagnostics` returning a redacted dump: config entry
  (credentials redacted — though this integration stores none), category map summary,
  current projection sizes, source entity id, last sync time. Redact any item text that
  could be personal if the user opts into redaction.
- Raise a repair issue if the configured source todo entity is missing or becomes
  unavailable for an extended period.

## Reauthentication / migration

- This integration holds no credentials (auth belongs to `alexa_devices`), so no reauth flow
  is needed. If the source entity is removed, surface a repair issue.
- Version the config entry and the stored data schema. Provide `async_migrate_entry` for
  future schema changes.

## Error handling expectations

- Wrap source service calls; on failure, retry with backoff, then surface a user-visible
  error (persistent notification or repair issue) and revert optimistic state. Never drop a
  change silently (Requirement 5.4).
- Raise `ConfigEntryNotReady` from setup when the source entity is not yet available.
- Use `HomeAssistantError` for user-facing service failures.
