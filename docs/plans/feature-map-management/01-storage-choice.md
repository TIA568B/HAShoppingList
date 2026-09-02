# 01 — Storage Choice: JSON in the HA Store (not SQLite)

## Decision

Keep the category/shop map in **JSON via the Home Assistant `Store` helper**
(`.storage/alexa_shopping_categoriser.<entry_id>`), exactly as today (`store.py`). Do **not**
introduce SQLite. Move only the **seed/default** data out of Python into a shipped
`default_map.json` (see `03-migration-and-reload.md`).

## Why JSON over SQLite for this data

| Factor | JSON in HA `Store` | SQLite |
|---|---|---|
| Data size/shape | Dozens of categories/shops + hundreds of learned overrides = a few KB, read wholesale, recomputed on each change | Optimised for large, queryable, partially-updated datasets — none of which apply |
| HA idiom | Sanctioned persistence path; async-safe, atomic write, versioned; already mandated by architecture/security steering | Non-idiomatic here; needs connection lifecycle + schema/migrations + executor offload for blocking I/O |
| Dependencies | Stdlib only (satisfies "minimise dependencies") | Adds DB management surface and review burden |
| Backup / diff / diagnostics | Human-readable, diffable, trivially export/import, easy to redact in diagnostics | Opaque binary blob |
| Concurrency | Single writer (the coordinator/services), no contention | Concurrency features unused |
| Already built | `store.py` is a defensive, tested JSON Store with migration discipline | Would be a rewrite for no benefit |

SQLite would only pay off if the project grew per-item history, multi-list analytics, or
thousands of rows with query patterns — explicitly out of scope (the list itself lives in
Alexa, not here; the projection is derived and rebuildable — NFR3).

## Where each thing lives (after this feature)

| Data | Location | Editable by user at runtime? |
|---|---|---|
| **Live map** (categories, keywords, shops, shop keyword rules, learned overrides) | HA `Store`, per config entry (unchanged) | **Yes** — via the card panels (Option A) and existing services |
| **Seed/defaults** (starting taxonomy + shops) | Shipped `custom_components/alexa_shopping_categoriser/default_map.json` (new; Option D) | No at runtime (it is shipped data); applied on first run, on the upgrade migration, and on the reload-from-JSON action |
| **Projection** (the grouped view) | Derived in the coordinator; exposed on the sensor | No — always rebuilt from live map + source list |

Canonical schema for the stored map and the sensor contract remains
`docs/plans/06-data-model-and-contract.md`. This feature does not change that schema shape;
it only changes **where the seed comes from** and **how the map is edited**.

## Consequence

The user's real problem ("changing mappings sucks / must run a service") is a **UX** gap, not
a storage-format gap. Option A closes it by giving the existing services a first-class editor.
The storage layer is already correct and stays put.
