# 04 — Home Assistant Integration Design

Domain: **`alexa_shopping_categoriser`**. Config-entry only (no YAML). Follows current HA core
integration conventions.

## manifest.json

```jsonc
{
  "domain": "alexa_shopping_categoriser",
  "name": "Alexa Shopping List Categoriser",
  "version": "0.1.0",
  "codeowners": ["@davidcarson"],
  "config_flow": true,
  "dependencies": ["todo"],
  "documentation": "https://github.com/<owner>/alexa_shopping_categoriser",
  "iot_class": "calculated",
  "integration_type": "service",
  "issue_tracker": "https://github.com/<owner>/alexa_shopping_categoriser/issues",
  "requirements": []
}
```

- `iot_class: calculated` — the integration derives data from another entity; it does no I/O
  of its own.
- `integration_type: service` — it provides a derived service/entity, not a physical device.
- `dependencies: ["todo"]` — guarantees the `todo` building block (and its services) is loaded.
- `requirements: []` — stdlib only (see doc 13). Add + pin here only if unavoidable.

> **Why not `after_dependencies: ["alexa_devices"]`?** The integration deliberately treats the
> source as *any* `todo` provider, not specifically `alexa_devices`, so we do not couple manifest
> load order to that integration. If `alexa_devices` has not finished setting up its entity when
> we set up, the coordinator's first refresh raises `ConfigEntryNotReady` and HA retries — the
> idiomatic ordering mechanism. (Finding L-2.)

## Config flow

Single user step:

1. Enumerate candidate source lists: entities in the `todo` domain whose registry `platform`
   is `alexa_devices`. Present as a dropdown (friendly name + entity id).
2. If none found, still allow manual entity-id entry, but warn (abort reason
   `no_alexa_lists` with a description pointing to the `alexa_devices` setup).
3. Enforce **single config entry per source entity** (`async_set_unique_id(source_entity_id)`
   then `_abort_if_unique_id_configured()`).
4. Validate the chosen entity exists and is a `todo` entity; store `source_entity_id` in
   `entry.data`.

Default selection heuristic: prefer a `todo` entity whose id contains `shopping` on the
`alexa_devices` platform.

**Strings / translations discipline.** All config/options/reconfigure step titles, field labels,
abort reasons (`no_alexa_lists`, `already_configured`), and error keys are defined as constants
and mirrored in both `strings.json` and `translations/en.json`, kept in sync in the same change
set. No user-facing string is hard-coded in flow logic. (Finding L-8 / S-09.)

## Options flow

The options flow is **menu-style** (`async_show_menu`) as of 0.5.0 (see
`docs/plans/feature-map-management/07`): **Display options · Manage categories · Manage shops ·
Reload defaults**.

- **Display options** (the form): `grace_period_seconds` (int, **8–30**, default **9**; the 8s
  floor respects the spec's 8–10s target, Req 4.1 — L-7), `show_completed` (bool, default false),
  `collapse_empty_categories` (bool, default true), `redact_items_in_diagnostics` (bool, default
  true). Submitting this sub-form persists to `entry.options` and triggers `async_reload_entry`.
- **Manage categories / Manage shops:** pick an existing entry (or "add new") → a native form
  (name + comma/newline keywords + a delete toggle for existing). Applied through the shared
  `map_ops` (the same code path the services use) against the store, then a coordinator
  recompute — so edits reflect live **without** a full reload. Reordering is deferred (OQ-B).
- **Reload defaults:** a confirm step → `store.async_reload_defaults()` + recompute.

> Category/shop editing is available in **two** native surfaces: this Options flow (curation)
> and the card's per-item **pencil menu** (set an item's shop/category, buttons only). The
> earlier in-card inline settings form (0.4.0) was removed in 0.5.0 — it captured HA keyboard
> shortcuts and was poor on mobile (see feature doc 07). The `*_category`/`*_shop` services
> still exist for automations.

> **Source-entity change is *not* an options-flow field.** Because `entry.unique_id` is the
> source entity id (one entry per source), changing the source cannot be a mutable option. To
> change the source, the user either deletes and re-adds the entry, or uses the **reconfigure
> flow** below. (Finding M-3.)

### Reconfigure flow (source-entity change)

- Implement `async_step_reconfigure` on the config flow. It re-runs the source-selection step,
  and on submit updates `entry.data["source_entity_id"]` **and** the entry `unique_id`
  atomically (via `async_update_reload_and_abort` with the new `unique_id`), then reloads.
- The category store is keyed by `entry_id` (see doc 06), so learned data survives a source
  change. The sensor `unique_id` is entry-based, so it is unaffected.
- This is the single sanctioned path for pointing the integration at a different `alexa_devices`
  todo list without losing learned categories.

## Configuration entries

- `entry.data`: `{ "source_entity_id": "todo.<...>" }` (stable).
- `entry.options`: the options above (mutable).
- `entry.unique_id`: the source entity id.

## Setup lifecycle (`async_setup_entry`)

1. Create `CategoryStore(hass, entry)`; `await store.async_load()` (creates defaults if empty).
2. Create `AlexaShoppingCoordinator(hass, entry, store)`.
3. `await coordinator.async_config_entry_first_refresh()` — raises `ConfigEntryNotReady` if the
   source entity is unavailable.
4. Store runtime data on `entry.runtime_data` (typed).
5. Subscribe to source `state_changed` via `async_track_state_change_event`; store the
   unsubscribe callback for unload.
6. Register services (idempotent; only once across entries) — see doc 06.
7. `await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])`.
8. Register the options update listener.

## Unload lifecycle (`async_unload_entry`)

1. `async_unload_platforms(entry, [Platform.SENSOR])`.
2. Cancel any pending grace-period finalization timers owned by the backend (if any live
   server-side; primary timing lives in the card — see doc 08).
3. Detach the source `state_changed` listener.
4. Deregister services if this is the last entry.
5. Return the unload success bool.

## Reload behaviour

- `async_reload_entry` = unload + setup. Used on options change and manual reload.
- The category store is untouched by reload (persisted independently), so learned data
  survives.

## DataUpdateCoordinator

- `AlexaShoppingCoordinator(DataUpdateCoordinator[Projection])`.
- `update_interval = timedelta(minutes=15)` — a **safety-net** poll; the real trigger is the
  source `state_changed` event, which calls `coordinator.async_request_refresh()` (debounced).
- `_async_update_data`:
  1. Call `todo.get_items` on the source entity with
     `data={"status": ["needs_action", "completed"]}, return_response=True`.
  2. Parse the response envelope — `todo.get_items` returns
     `{ "<source_entity_id>": { "items": [ {"summary": ..., "uid": ..., "status": ...} ] } }`.
     Read the list at `response[source_entity_id]["items"]`. (Finding REVIEW2-001.)
  3. Normalize each item into a `SourceItem` dataclass: `name = item["summary"]`,
     `uid = item["uid"]`, `completed = item["status"] == "completed"`.
  4. Run `categoriser.build_projection(items, category_map, overrides, options)`.
  5. Return the `Projection`.
- **First-refresh readiness vs. read failure:** if the source entity is absent or
  `unavailable`/`unknown` at first refresh, raise `ConfigEntryNotReady` (HA retries setup). A
  genuine error while the entity is present (service raises, malformed envelope) is `UpdateFailed`.
  (Finding L-3; see doc 09.)
- Debounce source events (e.g. 0.5s) to coalesce bursts.
- On read failure raise `UpdateFailed`; availability follows `last_update_success`.

## Entity platforms

- One platform: `sensor` (see doc 05). No new `todo` entity is created — the source list stays
  the single write target.

## Services

Defined in `services.yaml` with translations; validated with voluptuous. See doc 06 for
schemas. Summary:

| Service | Purpose | Req |
|---------|---------|-----|
| `recategorise_item` | Set/learn a category for an item's normalized text; re-run | 2.4, 6.2 |
| `add_category` | Create a category (optionally with keywords) | 6.1, 6.2 |
| `edit_category` | Rename a category / edit its keywords | 6.2 |
| `delete_category` | Delete a category; reassign its items to `Uncategorised` | 6.3 |
| `assign_shop` | Set/learn (or clear via `No Preference`) an item's shop; re-run | 7.2, 7.5 |
| `add_shop` | Create a shop (optionally with keyword rules) | 7.1, 7.3 |
| `edit_shop` | Rename a shop / edit its keyword rules (migrates learned shop overrides) | 7.1, 7.3 |
| `delete_shop` | Delete a shop; reassign its items to `No Preference` | 7.6 |
| `reload_maps` | Force reload of the whole store (categories **and** shops) + recompute | 6.2, 7.1 |

Completion/undo/add of *items* use the **native** `todo.update_item` / `todo.add_item`
directly from the card against the source entity — the integration does not wrap those.

## Events

- No custom bus events required for v1. The sensor state change is the frontend's signal. (A
  future `alexa_shopping_categoriser_sync_failed` event is possible but doc 09 uses a persistent
  notification / repair issue instead.)

## WebSocket / HTTP APIs

- None custom. The card uses HA's standard state subscription (`subscribe_entities`) and the
  standard `call_service` websocket command. No bespoke HTTP views.

## Diagnostics

- `async_get_config_entry_diagnostics`: redacted dump — entry data/options, source entity id,
  category count, per-category item counts, learned-override count, `last_update_success`,
  `last_synced`, and (only if `redact_items_in_diagnostics` is false) item text. Uses
  `async_redact_data`.

## Repairs

- Raise a repair issue (`ir.async_create_issue`) if the source entity is missing at setup or
  goes unavailable beyond a threshold, guiding the user to check `alexa_devices`.

## Reauthentication

- Not applicable — no credentials owned here. If the source entity disappears, that is a
  repair issue, not a reauth.

## Configuration migration

- `async_migrate_entry` handles config-entry version bumps; the store carries its own
  `schema_version` and migrates on load. v1 starts both at version 1.
