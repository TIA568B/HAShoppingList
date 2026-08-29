# 05 — Entity & Device Model

## Device

The integration attaches its entities to a single **service device** in the device registry.

| Field | Value |
|-------|-------|
| identifiers | `{(DOMAIN, entry.entry_id)}` |
| name | "Alexa Shopping List Categorizer" |
| manufacturer | "alexa_shopping_categorizer" |
| model | "Shopping List Categorizer" |
| entry_type | `DeviceEntryType.SERVICE` |
| via_device | *(none — it is a derived service, not a child of the Alexa device)* |

Rationale: it is a calculated/service integration, not a physical device. It must **not**
attach to or claim the Alexa `alexa_devices` device. Discovery is not applicable — setup is via
the config flow.

## Entities

### sensor: Categorized Shopping List

| Attribute | Value |
|-----------|-------|
| Platform | `sensor` |
| Purpose | Expose the derived category-grouped projection for the card to render |
| Entity id | `sensor.<entry_slug>_categorized` (e.g. `sensor.alexa_shopping_list_categorized`) |
| Unique ID | `f"{entry.entry_id}_categorized"` — stable, name-independent |
| Suggested name | "Categorized Shopping List" |
| Device class | none (not a standard measurement) |
| State class | none (do **not** set `measurement`; not for long-term statistics) |
| Native value (state) | Count of **unchecked** items across all categories (int) |
| Unit | none |
| `should_poll` | False (coordinator-driven) |
| Update frequency | On every source `state_changed` (debounced) + 15-min safety poll |
| Availability | `coordinator.last_update_success` **and** source entity state is not `unavailable`/`unknown` |
| Diagnostic? | No (this is the primary/user-facing entity, `EntityCategory` unset) |
| Default enabled | Yes |
| Recorder | Recommended to exclude via default recorder exclusion guidance in README (large JSON attribute, changes often) |

#### Attributes (the frontend contract — canonical definition in doc 06)

- `shop_groups`: **primary** structure — ordered list of shop objects `{ name, collapsed, categories: [{ name, collapsed, items: [{uid, name, checked, shop, category}] }] }`; `No Preference` last, `Uncategorized` last within each shop (Req 7.7).
- `category_definitions`: ordered list of `{ name, keywords }` for the category-settings panel (Req 6.1).
- `shop_definitions`: ordered list of `{ name, keywords }` for the shop-settings panel (Req 7.1); `No Preference` implicit.
- `uncategorized_count`: int.
- `total_unchecked`: int (mirrors state).
- `source_entity_id`: str.
- `last_synced`: ISO 8601 timestamp.
- `options`: `{ grace_period_seconds, show_completed, collapse_empty_categories }` echoed for the card.

> The full JSON schema and versioning of this attribute payload live in
> [06-data-model-and-contract.md](06-data-model-and-contract.md). Any change to it is a
> contract change and must update that doc in the same change set.

### Why no new `todo` entity

Creating a second `todo` entity would risk becoming a competing source of truth and drift. The
design keeps the `alexa_devices` list as the **single** write target and exposes only a derived
`sensor`. This satisfies "no drift / rebuildable projection" (NFR3).

## Naming & conflict avoidance (from read-only MCP findings)

- The chosen entity id `sensor.<entry_slug>_categorized` does not collide with existing
  entities (`todo.shopping_list`, the two `alexa_devices` todo entities, or the `bed_time`
  button).
- The integration does not create or rename any Alexa-owned entity, avoiding conflict with
  `alexa_devices` registry management (which actively prunes stale todo/routine entities).
