---
inclusion: always
---

# Architecture Steering

## Chosen approach

Ship a **custom Home Assistant integration** (config-flow based, HACS-distributable) named
`alexa_shopping_categorizer`, plus a **bundled custom Lovelace card**. Do **not** implement
this as pyscript / `python_script` / raw YAML automations. The original spec proposed
pyscript; we override that because a first-class integration gives us config flow, a
`DataUpdateCoordinator`, proper entities, services, diagnostics, unique IDs, and testability.

## Component boundaries

```
alexa_devices (core)            ── owns the Alexa list entity; DO NOT fork or modify it
        │  (state_changed events + todo services)
        ▼
alexa_shopping_categorizer (this integration)
  ├── coordinator      → reads items from the source todo entity, applies category map
  ├── category engine  → pure functions: normalize + match text → category
  ├── store            → persists category map + learned overrides (HA Store helper)
  ├── sensor entity    → sensor.<name>_categorized: derived JSON projection
  ├── services         → recategorize_item, add_category, edit_category, delete_category,
  │                      reload_category_map
  └── diagnostics      → redacted config + state dump
        │
        ▼
custom Lovelace card (frontend/) → subscribes to the sensor + calls todo/native services
```

## Dependency rules

- This integration **depends on** the source `todo` entity only through the public HA
  state machine and the public `todo.*` services. It must never import from or reach into
  `homeassistant.components.alexa_devices` internals.
- Category-matching logic lives in **pure, side-effect-free functions** (a `categorizer`
  module) so it is unit-testable without Home Assistant.
- All Home Assistant I/O (entity reads, service calls, storage) lives in the coordinator,
  entity, and service layers — never inside the pure categorizer.
- The frontend card talks to the backend only via the sensor state and documented services;
  it holds no private contract with Python internals beyond the sensor attribute schema.

## Data flow principles

- **Inbound:** source todo entity changes (Alexa push or poll) → coordinator recomputes the
  categorized projection → sensor updates → card re-renders. Idempotent.
- **Outbound:** card action → optimistic UI → after grace period → `todo.update_item` /
  `todo.add_item` on the **source** entity → inbound flow reconciles (no-op if already
  matching).
- The projection sensor must be **rebuildable at any time** from (source items + category
  map). Never store completion state or item identity only in the sensor.

## Where functionality lives

| Concern | Location |
| --- | --- |
| Text normalization + keyword/fuzzy match | `categorizer.py` (pure) |
| Category map + learned overrides persistence | `store.py` (HA Store) |
| Reading source items, building projection | `coordinator.py` |
| Exposed sensor | `sensor.py` |
| User-facing operations | `services.py` |
| Setup / config | `__init__.py`, `config_flow.py` |
| UI | `frontend/` (card) |

## File and module granularity

- **Prefer many small, single-responsibility files over one large file** — for both code and
  documentation. Each module in the table above is its own file; do not collapse them into a
  monolithic `__init__.py`. Design/plan docs are likewise split by concern with a linking
  index (see `docs/plans/`).
- When a file starts covering more than one concern or grows unwieldy, split it and link the
  pieces rather than letting it sprawl.

## What to avoid

- No second persisted copy of the shopping list.
- No direct calls to Amazon APIs — always go through the `todo` entity/services.
- No blocking I/O in the event loop.
- No business logic in the card that the backend cannot also enforce. (The tick model is
  **complete-on-tap**: the completion is sent through the public `todo.*` service immediately, so
  the backend always owns the end state; the card's grace window governs undo only. See
  `frontend.md` and `docs/plans/08`.)
- No monolithic catch-all files.
