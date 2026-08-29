# 07 — Categorization Engine

Lives in `categorizer.py` as **pure functions** with no `homeassistant` import, so it is fully
unit-testable in isolation (see doc 12 — 100% coverage required here).

## Pipeline

```mermaid
flowchart LR
    RAW[raw item name] --> NORM[normalize]
    NORM --> OV{override match?}
    OV -- yes --> CAT1[assigned category]
    OV -- no --> KW{keyword match?}
    KW -- yes --> CAT2[matched category]
    KW -- no --> UNC[Uncategorized]
```

### 1. Normalize

- Lowercase, trim, collapse whitespace.
- Strip leading quantities/units (e.g. `2x`, `500g`, `1 litre`, `a dozen`).
- Strip punctuation except intra-word hyphens/apostrophes.
- Result is the **normalized key** used for both matching and the learned-overrides dict.

### 2. Override match (learning — highest precedence)

- If `normalized in overrides`, assign `overrides[normalized]`. This is how manual corrections
  persist and win over keywords (Req 2.4, 6.2). Resolves gap G2.
- If the override points at a category that no longer exists, fall through to keyword matching
  (self-healing after a category delete).

### 3. Keyword match

- For each category in order, test whether any keyword is a whole-word/substring match of the
  normalized text. First match wins (category order is significant — put more specific
  categories earlier, e.g. `Fake Meat` before generic `Pantry`).
- Start with **substring/word matching (stdlib only)**. Only if match quality proves poor
  should fuzzy matching (`difflib.get_close_matches`, still stdlib) be added — documented as a
  later enhancement, behind the same pure interface.

### 4. Fallback

- No match → `Uncategorized`. Never guess (Req 1.6, 2.3).

## Vegan rules (non-negotiable — mirrors product steering)

| Item text matches… | Category | Assumption |
|--------------------|----------|------------|
| milk keywords (`milk`, `oat milk`, `soy/soya milk`, `almond milk`, `oat drink`) | **Milk** | plant-based milk |
| dairy-style (`cheese`, `yogurt`/`yoghurt`, `butter`, `cream`) | **Chilled** | plant-based |
| meat keywords (`sausages`, `bacon`, `mince`, `chicken pieces`, `burgers`, `ham`) | **Fake Meat** | plant-based substitute |
| egg / fish / clearly animal-derived (`eggs`, `honey`, `gelatine`, `whey`, `salmon`, `prawns`) | **Uncategorized** | ambiguous/animal → manual review |
| anything else with no match | **Uncategorized** | — |

- There is **no `Dairy` and no `Fish` category** (the `Dairy` in the spec's sample JSON is a
  typo — see doc 01, C3).
- Vegan filtering is **best-effort** on text alone; it cannot catch every hidden animal
  ingredient (NFR4). Ambiguous items route to `Uncategorized` rather than being mis-assigned.
- The Milk/Chilled split is a fixed rule in v1; changing groupings later is a category-map edit
  (Req 6.2), not a code change.

## Bootstrap / seeding (replaces spec's history mining — see doc 01, C2)

On first setup:
1. Load the **default vegan taxonomy** (doc 06 storage schema) — never blocks setup (Req 1.8).
2. Read the **current source list including completed items** via `todo.get_items`
   (both statuses) — this is the corpus (completed items are retained by `alexa_devices`).
3. Categorize each corpus item with the default map; anything unmatched sits in
   `Uncategorized`. No separate "review before live" gate is required because the map is
   editable live via services/card and nothing is destructive — but the card surfaces the
   `Uncategorized` bucket prominently so the user can triage (satisfies the intent of Req 1.7).
4. Optional (future): a one-shot "seed keywords from current list" helper that suggests adding
   frequent uncategorized terms as keywords — deferred, listed in doc 15.

## Meat/milk ambiguity handling

- Because "bacon"/"milk" could in principle be non-vegan, the assumption is plant-based (user
  is vegan). If ever wrong (guest/other household member), the correction path is
  `recategorize_item` / the card's move action (Req 2.4/6.2). A first-seen confirmation prompt
  is a possible enhancement (doc 15), not v1-required.

## Determinism & performance

- Pure, deterministic, order-stable. Complexity is O(items × keywords); trivial for
  shopping-list sizes. If lists ever grow large, precompute a keyword→category index — noted,
  not needed for v1.
