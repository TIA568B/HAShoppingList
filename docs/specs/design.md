# Design: Categorized Alexa Shopping List

## 1. Architecture Overview

```
Alexa  <---sync--->  todo.shopping_list (native HA entity)
                            |
                            | state_changed events
                            v
                 [Categorization Engine]  <-- category_map.json (keywords -> category)
                 (pyscript / python_script)
                            |
                            v
                 sensor.shopping_list_categorized
                 (structured JSON: {category: [{id, name, checked}]})
                            |
                            v
                 [Custom Lovelace Card]  (frontend, subscribes to sensor + entity)
                            |
                     user ticks / adds / undoes
                            |
                            v
                 todo.update_item / todo.remove_item  --> back to todo.shopping_list --> Alexa
```

Two data flows exist and must stay reconciled:
- **Inbound:** `todo.shopping_list` changes (from Alexa or elsewhere) → re-run categorization →
  update `sensor.shopping_list_categorized` → frontend re-renders.
- **Outbound:** user actions in the custom card → optimistic local update → after grace period →
  HA `todo` service call → `todo.shopping_list` updates → (loops back through inbound flow, which
  should be a no-op since state already matches).

## 2. Components

### 2.1 Historical Bootstrap Script (one-time / re-runnable)
- Reads history for `todo.shopping_list` via HA's `history`/`logbook` API (or recorder DB query)
  to collect a corpus of past item names.
- Runs simple normalization (lowercase, strip quantities/units) then keyword-clusters items into
  candidate categories using a starter taxonomy (Produce, Bakery, Milk, Chilled, Fake Meat,
  Household, Frozen, Drinks, Pantry, Other) — **egg and other animal-derived categories/keywords
  excluded by design** given the user is vegan, while **milk-keyword items get their own "Milk"
  category, other dairy-style items (cheese, yogurt, butter, cream) are routed to "Chilled", and
  meat-keyword items are routed to "Fake Meat"** rather than being excluded, on the assumption
  they all refer to plant-based products. This includes indirect/hidden animal products where
  reasonably identifiable from item text (e.g. "honey", "gelatine", "whey protein"), though the
  engine should not be expected to catch every hidden ingredient — see §6.
- Outputs a draft `category_map.yaml`/`json` for user review (Requirement 1.4) before it becomes
  the live mapping.

### 2.2 Categorization Engine (pyscript, event-driven)
- Triggered on `todo.shopping_list` state/attribute change.
- For each item: normalize text → substring/fuzzy match against `category_map` → assign
  category, or "Uncategorized" if no match.
- Writes result to `sensor.shopping_list_categorized` as a JSON attribute, structured per
  category with item id, display name, and checked state.
- Also exposes a service (e.g. `pyscript.categorize_recategorize_item`) so the frontend can push
  a manual category correction, which updates `category_map` (Requirement 2.4).

### 2.3 State/Storage
- `category_map` persisted as a JSON file or `input_text`/HA storage helper — keyword list per
  category, editable via Requirement 6.
- `sensor.shopping_list_categorized` is a derived/cached view, always rebuildable from
  `todo.shopping_list` + `category_map` — not a second source of truth, avoiding drift.

### 2.4 Frontend: Custom Lovelace Card
- Subscribes to `sensor.shopping_list_categorized` via HA websocket for live updates
  (Requirement 3.1).
- Renders collapsible category sections; empty/fully-checked categories collapse
  (Requirement 3.3).
- Tick interaction:
  1. On tap: item visually marked checked immediately (optimistic, Requirement 3.2).
  2. Item enters "pending" state with a local countdown timer + inline Undo affordance
     (Requirement 4.1–4.2).
  3. If Undo tapped: revert local state, cancel timer, no backend call made if not yet sent
     (Requirement 4.3).
  4. On timer expiry: call `todo.update_item` (status: completed) against `todo.shopping_list`
     (Requirement 4.4, 5.1).
- Add-item flow: text input → call `todo.add_item` on `todo.shopping_list` directly (native HA
  service, Requirement 5.2) → inbound flow re-categorizes and displays it.
- Error handling: failed service call surfaces a toast/banner and reverts optimistic state if
  retries are exhausted (Requirement 5.4).

## 3. Data Model

```jsonc
// category_map.json
{
  "categories": {
    "Produce":              { "keywords": ["apple", "banana", "carrot", "lettuce", "onion"] },
    "Milk":                 { "keywords": ["milk", "oat milk", "soy milk", "almond milk"] },
    "Chilled":              { "keywords": ["cheese", "yogurt", "butter", "cream"] },
    "Fake Meat":            { "keywords": ["sausages", "bacon", "mince", "chicken pieces", "burgers"] },
    "Bakery":               { "keywords": ["bread", "bagel", "roll"] },
    "Frozen":               { "keywords": ["frozen peas", "vegan ice cream"] },
    "Drinks":               { "keywords": ["juice", "squash", "coffee", "tea"] },
    "Pantry":               { "keywords": ["pasta", "rice", "lentils", "tofu"] },
    "Household":            { "keywords": ["toilet roll", "washing up liquid", "bin bags"] }
  }
}
```

Note: no "Dairy" or "Fish" category exists in the taxonomy — milk gets its own category, other
dairy-style items (cheese, yogurt, etc.) are grouped under "Chilled", meat-keyword items are
assumed to be plant-based substitutes and routed to "Fake Meat", and any items that read as
fish/egg/genuinely animal-derived are routed to "Uncategorized" for manual review rather than
silently dropped (see §6).

```jsonc
// sensor.shopping_list_categorized attributes
{
  "Dairy": [
    { "id": "abc123", "name": "milk", "checked": false }
  ],
  "Bakery": [
    { "id": "def456", "name": "sourdough", "checked": true }
  ],
  "Uncategorized": [
    { "id": "ghi789", "name": "birthday candles", "checked": false }
  ]
}
```

## 4. Sequence: Tick-off with Undo

```
User taps item  -> Card: mark checked locally, start 8s timer, show "Undo"
                         |
              (within 8s)|--- User taps Undo --> Card: revert item, cancel timer, no HA call
                         |
                (8s pass)|--- Card: call todo.update_item(status=completed)
                                    -> todo.shopping_list updates
                                    -> Categorization Engine re-runs (no-op, already checked)
                                    -> sensor updates -> Card confirms final state
```

## 5. Sequence: Historical Bootstrap

```
User runs bootstrap  -> Script queries history for todo.shopping_list
                      -> Normalize + cluster item names into starter categories
                         (egg and other animal-derived keywords/categories
                         excluded; milk items -> "Milk"; cheese/yogurt/butter
                         -> "Chilled"; meat-keyword items -> "Fake Meat")
                      -> Draft category_map presented to user in UI/YAML for review
                      -> User approves/edits -> category_map.json saved as live mapping
                      -> Categorization Engine runs against current list using new mapping
```

## 6. Open Questions / Assumptions
- Assumes `todo.update_item` / `todo.remove_item` on the Alexa-linked `todo` entity already
  propagate to the real Alexa list, per the user's confirmation this integration exists.
- Historical data source (recorder history vs. a manual export) needs confirming — recorder
  retention is often only 10 days by default, which may be too short for a useful corpus; may
  need the user to raise `recorder` history duration or supply a manual list export instead.
- Fuzzy matching approach (simple substring vs. lightweight NLP) to be decided during
  implementation — start simple (substring/keyword) and only add complexity if match quality is
  poor in practice.
- Vegan-exclusion is keyword-based and will not reliably catch hidden/indirect animal
  ingredients (e.g. "worcester sauce", E-numbers derived from animal sources) — treat this as a
  best-effort filter, not a guarantee, and route ambiguous items to "Uncategorized" rather than
  mis-assigning them.
- Meat-keyword matching cannot distinguish real meat from a plant-based substitute using text
  alone (e.g. "bacon" could be either). The design assumes plant-based given the user is vegan,
  but if this assumption is ever wrong (e.g. shopping for a non-vegan household member/guest),
  the manual re-categorization flow (Req 2.4/6.2) is the correction path — consider surfacing a
  one-time confirmation the first time each new meat-keyword item appears.
- Same ambiguity applies to milk and other dairy-style keywords (e.g. plain "milk" could in
  principle mean cow's milk) — the design assumes non-dairy given the user is vegan, with the
  same manual-correction path available if ever wrong.
- The Milk/Chilled split is a fixed rule (milk → its own category, other dairy-style items →
  Chilled) rather than user-configurable in v1; if the user wants different groupings later,
  that's a category_map edit via Req 6.2, not a code change.
- If historical data includes non-vegan items (e.g. from before switching to vegan, or bought
  for other household members), decide during bootstrap review whether to exclude them from the
  category map entirely or keep them tagged for manual categorization — recommend excluding by
  default and letting the user opt individual items back in during the review step
  (Req 1.4).
