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
    shop: str            # resolved shop preference; "No Preference" when unset (Req 7)

@dataclass(slots=True)
class Category:
    name: str
    keywords: list[str] = field(default_factory=list)

@dataclass(slots=True)
class Shop:
    name: str
    keywords: list[str] = field(default_factory=list)   # shop keyword rules (Req 7.3)

@dataclass(slots=True)
class CategoryMap:
    schema_version: int
    categories: list[Category]                 # ordered; display order
    overrides: dict[str, str]                   # normalized_text -> category name (learned)
    shops: list[Shop]                           # ordered; user-managed shops (excl. "No Preference"), each with keyword rules
    shop_overrides: dict[str, str]              # normalized_text -> shop name (learned, Req 7.2)

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
  },
  "shops": [
    { "name": "Aldi", "keywords": ["nappies", "milk"] },
    { "name": "Asda", "keywords": [
        "clothes", "clothing", "t-shirt", "tshirt", "shirt", "jumper", "hoodie",
        "socks", "underwear", "pants", "knickers", "boxers", "vest",
        "jeans", "trousers", "shorts", "leggings", "joggers",
        "pyjamas", "jammies", "pjs", "dress", "skirt", "coat", "jacket",
        "shoes", "trainers", "slippers", "hat", "gloves", "scarf"
    ] },
    { "name": "Tesco", "keywords": [] }
  ],
  "shop_overrides": {
    "oat milk": "Aldi",
    "washing up liquid": "Asda"
  }
}
```

- `Uncategorized` is implicit — not stored as a category; it is the fallback bucket. It is
  always rendered last.
- `No Preference` is implicit — not stored in `shops`; it is the shop fallback (Req 7.5) and is
  never removable (Req 7.1). `shops` holds only user-managed shops, each with its own keyword
  rules (Req 7.3), in display order.
- `shop_overrides` is the **shop learning** store: normalized item text → shop name (Req 7.2),
  mirroring `overrides` for categories. An override pointing at a deleted shop self-heals to
  `No Preference`.
- **Shop names are also matched inside item text** (Req 7.4): if an item's normalized text
  contains a known shop name (e.g. "tesco nappies" contains "tesco"), that shop wins over the
  learned override and keyword rules. See the precedence in doc 07.
- Storage holds **no item state** (checked/unchecked) and no copy of the list — only the maps and
  learned overrides. This keeps the projection rebuildable and drift-free (NFR3).

### Migration

- **`schema_version` is 1**, and version 1 **includes** `categories`, `overrides`, `shops`, and
  `shop_overrides` (the shop fields were added during design, before any store shipped — finding
  F4-1). There is no v0→v1 category-only store in the wild.
- **Defensive load:** `store.py` must tolerate a store that is missing any top-level key by
  injecting defaults — `categories`/`shops` default to the seed sets, `overrides`/`shop_overrides`
  default to `{}` (use `.get(key, default)`, never index). This makes loading an older/partial
  store safe without a dedicated migrator.
- On load, if `schema_version` < current, run ordered migrators, then persist. Future schema
  changes bump `schema_version` and add an ordered migrator + a migration test.
- The store `schema_version` (persistence) is independent of the sensor `attributes_version`
  (frontend contract) — see the sensor contract section.

## Sensor attribute contract (attributes_version 3)

The sensor's `extra_state_attributes` (canonical). `attributes_version` history: v1 initial,
v2 added `category_definitions` (M-2), v3 restructured to shop-primary `shop_groups` + added
`shop_definitions` and per-item `shop`/`category` (Req 7).

```jsonc
{
  "attributes_version": 3,
  "source_entity_id": "todo.david_carson_amazon_gmail_com_shopping_list",
  "last_synced": "2026-08-29T16:12:11+01:00",
  "total_unchecked": 12,
  "uncategorized_count": 1,
  "options": {
    "grace_period_seconds": 9,
    "show_completed": false,
    "collapse_empty_categories": true
  },
  // Read path for the card's category-settings panel (Req 6.1 "view categories + keywords").
  // Ordered like `categories`; excludes the implicit Uncategorized bucket (it has no keywords).
  // (Finding M-2.)
  "category_definitions": [
    { "name": "Produce", "keywords": ["apple", "banana", "carrot", "lettuce", "onion"] },
    { "name": "Milk",    "keywords": ["milk", "oat milk", "soy milk", "almond milk"] }
  ],
  // Read path for the card's shop-settings panel (Req 7.1 "view shops + their keyword rules").
  // "No Preference" is implicit and always available; it is not listed here.
  "shop_definitions": [
    { "name": "Aldi",  "keywords": ["nappies", "milk"] },
    { "name": "Asda",  "keywords": ["clothes", "t-shirt", "socks", "jeans", "shorts", "pyjamas", "jammies", "..."] },
    { "name": "Tesco", "keywords": [] }
  ],
  // PRIMARY grouping is by shop, then by category (Req 7.7). Shops are ordered by the stored
  // shop order; "No Preference" always last. Within each shop, categories are ordered by the
  // stored category order; "Uncategorized" always last.
  "shop_groups": [
    {
      "name": "Aldi",
      "collapsed": false,
      "categories": [
        {
          "name": "Milk",
          "collapsed": false,
          "items": [
            { "uid": "amzn1.item.abc", "name": "oat milk", "checked": false, "shop": "Aldi", "category": "Milk" }
          ]
        }
      ]
    },
    {
      "name": "No Preference",
      "collapsed": false,
      "categories": [
        {
          "name": "Produce",
          "collapsed": false,
          "items": [
            { "uid": "amzn1.item.def", "name": "carrots", "checked": false, "shop": "No Preference", "category": "Produce" }
          ]
        }
      ]
    }
  ]
}
```

Rules:
- `shop_groups` is the **primary** structure: ordered by stored shop order, `No Preference`
  always last (Req 7.7). Within each shop, `categories` is ordered by stored category order,
  `Uncategorized` always last. An item appears in exactly one shop group and one category within
  it (single shop per item, single category).
- `category_definitions` mirrors the stored category map (name + keyword list) in order, giving
  the card a read source for the category-settings panel without a mutating call (Req 6.1). It
  omits `Uncategorized` (no keywords). Keep it small; for a very large map, fall back to the
  websocket read command instead (see doc 15 R7 / M-4).
- `shop_definitions` mirrors the stored shop map (name + keyword rules) in order for the
  shop-settings panel (Req 7.1). `No Preference` is implicit, always available, never listed.
- Each item carries both a resolved `shop` (Req 7, default `No Preference`) and its `category`,
  so the card can re-pivot (e.g. filter by shop, or show a flat category view) without recomputing.
- Both `shop_groups` and each nested category include `collapsed`, the **server-computed
  auto-collapse suggestion** (from the `collapse_empty_categories` option + whether the group has
  zero unchecked items, Req 3.3). It is a hint, not the source of truth for the UI: the card also
  keeps **card-local manual collapse state** per shop and per category so the user can focus on the
  store they are in while still expanding aisles within it (Req 7.7). Manual state is never written
  back to the sensor. See doc 11.
- When `show_completed` is false, `items` contains only unchecked items but `collapsed`/counts
  still reflect that the category is "done".
- `attributes_version` gates the card; bump it on any breaking change and update this doc. It was
  bumped **1 → 2** when `category_definitions` was added (additive; finding M-2), and **2 → 3**
  for Req 7, which **restructured** the projection to shop-primary (`shop_groups` replaces the
  top-level `categories`) and added `shop_definitions` and per-item `shop`/`category`. Because the
  top-level shape changed, v3 is a breaking change for the card (the card must read `shop_groups`).
- **v3 is the initial *shipped* contract** (finding R7-L1): v1 and v2 were internal design
  iterations only, so there is no v1/v2 card in the wild and no back-compat obligation. The sensor
  emits exactly one contract version at a time (no dual emission). Record this in the CHANGELOG at
  first release.
- **`No Preference` ordering** (finding R7-O1): it renders **last by default**, but this is a card
  display option (`no_preference_position`, default `last`). Rationale for the option: before shop
  learning kicks in, `No Preference` may be the largest group, and some users prefer it first. The
  backend always emits `No Preference` in a stable position; the card may reorder per the option.
- **`attributes_version` (this frontend contract) and the store `schema_version` (persistence,
  above) are independent counters** — they version different things and need not move together
  (followup02 FO-2).

### Source `todo.get_items` response mapping (canonical)

The coordinator builds the projection from the `todo.get_items` response, whose shape is:

```jsonc
{ "todo.<source>": { "items": [ { "summary": "oat milk", "uid": "amzn1.item.abc", "status": "needs_action" } ] } }
```

Mapping into `SourceItem`: `name = summary`, `uid = uid`, `completed = (status == "completed")`.
The response is keyed by entity id; read `response[source_entity_id]["items"]`. (Finding
REVIEW2-001.)

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

assign_shop:
  fields:
    entry_id: { required: false, selector: { config_entry: { integration: alexa_shopping_categorizer } } }
    item_text: { required: true, example: "oat milk", selector: { text: {} } }
    shop: { required: true, example: "Aldi", selector: { text: {} } }   # "No Preference" clears the preference
    apply_to_uid: { required: false, example: "amzn1.item.abc", selector: { text: {} } }

add_shop:
  fields:
    entry_id: { required: false }
    name: { required: true, example: "Lidl", selector: { text: {} } }
    keywords: { required: false, selector: { object: {} } }   # list[str] shop keyword rules

edit_shop:
  fields:
    entry_id: { required: false }
    name: { required: true }
    new_name: { required: false }
    keywords: { required: false, selector: { object: {} } }   # replaces the shop's keyword rules

delete_shop:
  fields:
    entry_id: { required: false }
    name: { required: true }

reload_maps:   # reloads the entire store: categories AND shops (finding F4-3)
  fields:
    entry_id: { required: false }
```

Behavioral contract:
- `recategorize_item` stores `overrides[normalize(item_text)] = category` (learning). If
  `apply_to_uid` is given, it also immediately re-runs so that item moves now.
- `edit_category`/`add_category` validate that `name` is non-empty, unique, control-char free,
  length-limited.
- `edit_category` with `new_name` **migrates learned overrides**: in the same transaction, any
  `overrides[*] == old_name` is rewritten to `new_name` before persisting and recomputing, so a
  rename does not silently orphan accumulated learning. Category order/position is preserved.
  (Finding REVIEW2-003.)
- `delete_category` removes the category and its keywords; any item currently matching it falls
  through to `Uncategorized` on the next recompute (items are never deleted — Req 6.3). Overrides
  pointing at the deleted category self-heal (fall through to keyword/Uncategorized — see doc 07).
- `assign_shop` stores `shop_overrides[normalize(item_text)] = shop` (Req 7.2 learning). Assigning
  `No Preference` **removes** the override (clears the preference) rather than storing it. If
  `apply_to_uid` is given it also re-runs immediately so that item's shop updates now.
- `add_shop`/`edit_shop` validate that `name` is non-empty, unique (case-insensitive), control-char
  free, length-limited, and not the reserved `No Preference` (Req 7.8); `keywords` sets/replaces the
  shop's keyword rules (Req 7.3). `edit_shop` rename migrates `shop_overrides` pointing at the old
  name to the new name (mirrors `edit_category`, REVIEW2-003).
- `delete_shop` removes the shop (and its keyword rules); any item preferring it — via learned
  override or keyword rule — falls through to `No Preference` on the next recompute; items are
  never deleted (Req 7.6). `No Preference` cannot be deleted.
- All services persist the store, then request a coordinator recompute.
