---
inclusion: always
---

# Product: Categorized Alexa Shopping List

## What this project is

A Home Assistant custom integration (domain: `alexa_shopping_categorizer`) that presents
the user's Alexa shopping list as a **category-grouped, reactive, tick-with-undo** view,
and keeps it in sync with the underlying Alexa list.

## Ground truth about the environment (verified via read-only MCP, do not re-assume)

- The real Alexa shopping list is the entity
  **`todo.david_carson_amazon_gmail_com_shopping_list`**, provided by the core
  **`alexa_devices`** integration.
- The native `todo.shopping_list` entity (platform `shopping_list`) is **NOT** the Alexa
  list and must not be targeted. The original spec referred to `todo.shopping_list`; that
  was incorrect for this environment. HA reality wins.
- The `alexa_devices` todo entity:
  - Supports CREATE, UPDATE, DELETE (`supported_features = 7`). No MOVE, no due dates.
  - **Retains completed items** and exposes them via `todo_items` with status
    `completed` or `needs_action`.
  - Each item has a stable `uid` and an internal `version` (optimistic concurrency).
  - Marking complete does not delete the item; undo is an update back to `needs_action`.
  - Updates **push** to Home Assistant in near real time (event handler calls
    `async_update_listeners`), with a 300s poll as a backstop.
- Home Assistant version at design time: **2026.8.3**, timezone Europe/London, HACS present,
  pyscript NOT installed.

## Non-negotiable product rules

- The user is **vegan**. Categorization rules:
  - Milk-keyword items -> **`Milk`** category (assumed plant-based).
  - Other dairy-style items (cheese, yogurt, butter, cream) -> **`Chilled`**.
  - Meat-keyword items (sausages, bacon, mince, etc.) -> **`Fake Meat`** (assumed plant-based
    substitute), never excluded.
  - Egg / fish / genuinely animal-derived items -> **`Uncategorized`** for manual review,
    never silently dropped, never auto-assigned to a made-up animal category.
- Categorization must **learn over time**: manual corrections persist and apply to future
  identical items.
- The categorized view is a **derived projection**, never a second source of truth. It must
  always be rebuildable from the Alexa list plus the category map.

## Primary user

A single household power-user running Home Assistant OS with the Alexa Devices integration
already configured.
