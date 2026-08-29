# 06 — Data Model & Contract

This document is **canonical** for the storage schema, the sensor attribute contract, and the
service signatures. Frontend and backend both depend on it; changes here are contract changes.

## Python types (backend)

```python
# categorizer.py — pure, no homeassistant import
from dataclasses import dataclass, field

@dataclass(slots=True, frozen=True)
class SourceItem:
    uid: str            # stable Amazon item id
    name: str           # raw summary text
    completed: bool

@dataclass(slots=True, frozen=True)
class CategorizedItem:
    uid: str
    name: str
    checked: bool
    category: str

@dataclass(slots=True)
class Category:
    name: str
    keywords: list[str] = field(default_factory=list)

@dataclass(slots=True)
class CategoryMap:
    schema_version: int
    categories: list[Category]                 # ordered; display order
    overrides: dict[str, str]                   # normalized_text -> category name (learned)

# A Projection is what the coordinator returns and the sensor exposes:
Projection = dict  # see JSON contract below (built from CategorizedItems)
```

- `overrides` is the **learning** store: normalized item text → category. It takes precedence
  over keyword matching (see doc 07).
- `Category.name` is unique (case-insensitive) within the map.

## Storage schema (HA Store)

Key: `alexa_shopping_categorizer.<entry_id>` (one store per config entry).

```jsonc
{
  "schema_version": 1,
  "categories": [
    { "name": "Produce",   "keywords": ["apple", "banana", "carrot", "lettuce", "onion"] },
    { "name": "Milk",      "keywords": ["milk", "oat milk", "soy milk", "almond milk"] },
    { "name": "Chilled",   "keywords": ["cheese", "yogurt", "butter", "cream", "tofu"] },
    { "name": "Fake Meat", "keywords": ["sausages", "bacon", "mince", "chicken pieces", "burgers"] },
    { "name": "Bakery",    "keywords": ["bread", "bagel", "roll", "sourdough"] },
    { "name": "Frozen",    "keywords": ["frozen peas", "vegan ice cream", "chips"] },
    { "name": "Drinks",    "keywords": ["juice", "squash", "coffee", "tea"] },
    { "name": "Pantry",    "keywords": ["pasta", "rice", "lentils", "beans", "tinned"] },
    { "name": "Household", "keywords": ["toilet roll", "washing up liquid", "bin bags"] }
  ],
  "overrides": {
    "birthday candles": "Household"
  }
}
```

- `Uncategorized` is implicit — not stored as a category; it is the fallback bucket. It is
  always rendered last.
- Storage holds **no item state** (checked/unchecked) and no copy of the list — only the map and
  learned overrides. This keeps the projection rebuildable and drift-free (NFR3).

### Migration

- On load, if `schema_version` < current, run ordered migrators, then persist. v1 defines
  version 1.

## Sensor attribute contract (v1)

The sensor's `extra_state_attributes`:

```jsonc
{
  "attributes_version": 1,
  "source_entity_id": "todo.david_carson_amazon_gmail_com_shopping_list",
  "last_synced": "2026-08-29T16:12:11+01:00",
  "total_unchecked": 12,
  "uncategorized_count": 1,
  "options": {
    "grace_period_seconds": 9,
    "show_completed": false,
    "collapse_empty_categories": true
  },
  "categories": [
    {
      "name": "Produce",
      "collapsed": false,
      "items": [
        { "uid": "amzn1.item.abc", "name": "bananas", "checked": false },
        { "uid": "amzn1.item.def", "name": "carrots", "checked": false }
      ]
    },
    {
      "name": "Uncategorized",
      "collapsed": false,
      "items": [
        { "uid": "amzn1.item.ghi", "name": "birthday candles", "checked": false }
      ]
    }
  ]
}
```

Rules:
- `categories` is ordered by the stored category order; `Uncategorized` always last.
- Each category includes `collapsed` computed from the collapse option + whether it has zero
  unchecked items.
- When `show_completed` is false, `items` contains only unchecked items but `collapsed`/counts
  still reflect that the category is "done".
- `attributes_version` gates the card; bump it on any breaking change and update this doc.

> **HA attribute size note:** entity attributes are capped (~16 KB when recorded). A typical
> shopping list is tiny, but to be safe: exclude the sensor from recorder and keep item objects
> minimal (uid/name/checked only). If a list could ever be very large, doc 15 (R7) covers the
> fallback of a dedicated websocket command instead of a fat attribute.

## Service signatures

`services.yaml` (schemas enforced with voluptuous in `services.py`):

```yaml
recategorize_item:
  fields:
    entry_id: { required: false, selector: { config_entry: { integration: alexa_shopping_categorizer } } }
    item_text: { required: true, example: "oat milk", selector: { text: {} } }
    category: { required: true, example: "Milk", selector: { text: {} } }
    apply_to_uid: { required: false, example: "amzn1.item.abc", selector: { text: {} } }

add_category:
  fields:
    entry_id: { required: false, selector: { config_entry: {} } }
    name: { required: true, selector: { text: {} } }
    keywords: { required: false, selector: { object: {} } }   # list[str]

edit_category:
  fields:
    entry_id: { required: false }
    name: { required: true }
    new_name: { required: false }
    keywords: { required: false, selector: { object: {} } }

delete_category:
  fields:
    entry_id: { required: false }
    name: { required: true }

reload_category_map:
  fields:
    entry_id: { required: false }
```

Behavioral contract:
- `recategorize_item` stores `overrides[normalize(item_text)] = category` (learning). If
  `apply_to_uid` is given, it also immediately re-runs so that item moves now.
- `edit_category`/`add_category` validate that `name` is non-empty, unique, control-char free,
  length-limited.
- `delete_category` removes the category and its keywords; any item currently matching it falls
  through to `Uncategorized` on the next recompute (items are never deleted — Req 6.3).
- All services persist the store, then request a coordinator recompute.
