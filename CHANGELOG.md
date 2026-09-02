# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.1] - 2026-09-02

### Changed
- **Options flow "Manage categories" and "Manage shops" pick-lists are now sorted alphabetically**
  (case-insensitive), instead of stored/seed order, making a category or shop easier to find when
  editing. The "(Add new …)" entry stays pinned last. This affects the selection lists only; the
  stored map order, the sensor's `category_definitions`/`shop_definitions` contract, and the card's
  grouped view are unchanged.

## [0.8.0] - 2026-09-02

### Added
- **New "Canned Food" category.** Tinned/canned goods now group under Canned Food instead of
  Pantry. It is evaluated **first** (before every other category) because an explicit
  `tinned`/`canned`/`tin of`/`can of` marker is the strongest signal and must win over the food
  inside — e.g. "tinned tomatoes" and "canned tomatoes" are Canned Food, not Fruit & Veg via the
  bare `tomatoes` keyword. Also seeds `baked beans`, `spaghetti hoops`, `mushy peas`, and
  `tinned/canned/condensed soup`.

### Changed
- **`tinned` moved from Pantry to Canned Food.** All "tinned X" items follow it. Dried/dry-packed
  pulses without a canned marker (`chickpeas`, `lentils`, `beans`) intentionally **stay in
  Pantry**, since they are sold both ways; add "tinned"/"canned" to route a specific item to
  Canned Food.

### Notes
- Seed-only change: no store schema or sensor attribute contract change. Existing installs keep
  their stored map and learned corrections; use **Reload defaults** (Options flow) to adopt the
  new category. **Learned per-item overrides still win over the seed** — if an item was manually
  assigned to Pantry (or any category) previously, Reload defaults keeps that assignment; correct
  it from the card's pencil or `recategorise_item`.

## [0.7.0] - 2026-09-02

### Added
- **Three more default shops:** **Co-op**, **Marks & Spencer**, and **Home Bargains** (joining
  Aldi, Asda, Tesco, Waitrose, Morrisons, Lidl, Sainsburys). They ship with no keyword rules, so
  they are selectable and match by shop-name-in-text but do not force-assign ordinary items.

### Fixed
- **Shop names containing punctuation now match by name-in-text.** The shop resolver compared the
  raw shop name against normalized item text, so a name like "Marks & Spencer" (whose `&` the
  normalizer strips) could never match "marks & spencer …". The resolver now normalizes the shop
  name the same way as item text before matching. "Co-op" and "Home Bargains" already worked
  (hyphen preserved / no punctuation); this fixes ampersand and other stripped-punctuation names.

### Notes
- Seed-only change (plus the pure-resolver fix): no store schema or sensor attribute contract
  change. Existing installs keep their stored shops and learned corrections; use **Reload
  defaults** (Options flow) to adopt the new default shops. "Sainsbury's" is stored as
  `Sainsburys` (no apostrophe) and is unchanged.

## [0.6.2] - 2026-09-02

### Changed
- **Moved baking sweeteners from Pantry to Baking:** `golden syrup`, `maple syrup`, `treacle`,
  and `black treacle` now categorise as **Baking** rather than Pantry. (The Baking category and
  most baking staples — flours, sugars, `bicarbonate of soda`, `baking powder`, `cocoa powder`,
  `chocolate chips`, etc. — already shipped in 0.6.0.)

### Fixed
- **`chocolate chips` now correctly resolves to Baking** (and `tortilla chips` to Snacks).
  Frozen's over-broad bare `chips` keyword was matching first (Frozen is evaluated first) and
  hijacking any "… chips" item, so Baking's `chocolate chips` keyword never won. Frozen now uses
  `oven chips` (alongside the existing `frozen chips`) instead of bare `chips`. Plain "chips"
  with no qualifier is now Uncategorised rather than silently Frozen.

### Notes
- Seed-only change: no store schema or sensor attribute contract change. Existing installs keep
  their stored map and learned corrections; use **Reload defaults** (Options flow) to adopt the
  updated taxonomy.

### Fixed
- **Card version footer is now dynamic, not hard-coded.** It previously showed a fixed
  `CARD_VERSION` string that had to be bumped by hand and had drifted (stuck at `v0.5.0`),
  defeating its purpose as a deploy-verification signal. The card now derives the version from
  the cache-busting `?v=` query on its own module URL (which the integration sets from
  `manifest.json`), so the footer always reflects the exact build Home Assistant served. If the
  module is ever loaded without that query (e.g. a hand-added bare path), the footer is omitted
  rather than showing a misleading number.

### Docs
- README categorisation section updated for the 0.6.0 taxonomy: all 18 default categories,
  the new match order (specific multi-word categories before broad bare-word ones), and the
  worked examples (ice cream → Frozen, tomato ketchup / apple sauce → Sauces, apple juice →
  Drinks).

## [0.6.0] - 2026-09-02

### Added
- **Large default-taxonomy expansion.** `default_map.json` now seeds a much broader UK
  grocery vocabulary across existing categories (Fruit & Veg, Milk, Sauces, Chilled, Fake
  Meat, Baby, Bakery, Frozen, Drinks, Pantry, Household) so common items categorise on first
  sight.
- **Seven new default categories:** Herbs & Spices, Baking, Cereals, Snacks, Health & Beauty,
  Medicine, and Pets.

### Changed
- **Category match order: specific multi-word categories now run before broad bare-word ones.**
  `Frozen`, `Sauces`, and `Drinks` are evaluated before `Fruit & Veg` (and `Sauces` still before
  `Chilled`). Under the engine's whole-word, first-match-wins semantics this makes multi-word
  items resolve correctly instead of being hijacked by a bare produce/dairy keyword:
  - `vanilla ice cream` / `strawberry ice cream` / `frozen yoghurt` → **Frozen** (not Chilled's
    `cream`/`yoghurt` or Fruit & Veg's `strawberry`).
  - `tomato ketchup` / `tomato sauce` / `apple sauce` / `mango chutney` → **Sauces** (not Fruit &
    Veg's `tomato`/`apple`/`mango`).
  - `tomato juice` / `apple juice` / `cranberry juice` → **Drinks**.
  Produce, dairy, and meat are unaffected (verified: `strawberries`/`broad beans` → Fruit & Veg,
  `double cream`/`cheddar cheese` → Chilled, `chicken breast` → Fake Meat). Two deliberate
  gray-area outcomes: `tomato puree` → Fruit & Veg and `coconut milk` → Milk (the latter matches
  the vegan "milk-keyword → Milk" rule).
- Added `apples` (plural) to Fruit & Veg so both singular and plural resolve.

### Notes
- Seed-only change: no store schema change (still `schema_version` 2) and no sensor attribute
  contract change (`attributes_version` 3). Existing installs keep their stored map and
  learned corrections; use **Reload defaults** (Options flow) to pick up the new taxonomy.
- Vegan boundary preserved: eggs, honey, fish/seafood, offal, and gelatine-risk sweets are
  intentionally left uncategorised for manual review rather than guessed.

## [0.5.0] - 2026-09-02

### Changed
- **Taxonomy management moved to a native Options flow** (Settings → Devices & Services →
  the integration → Configure). A menu offers: Display options · Manage categories · Manage
  shops · Reload defaults. Categories/shops are added/renamed/deleted and their keywords
  edited using Home Assistant's native form widgets — mobile-friendly and immune to the
  keyboard-shortcut problem. Replaces the in-card settings panel.
- **Per-item pencil menu on the card:** each item has a small pencil that opens a
  buttons-only menu to set its **shop** or **category** (calls `assign_shop` /
  `recategorise_item`, which learn). The menu has **no text inputs**, so it cannot trigger HA
  global keyboard shortcuts. Tapping an item still ticks it (unchanged).
- **Reload defaults** moved into the Options flow (behind a confirm). The `reload_defaults`
  service still exists for automations/Developer Tools.
- Category/shop mutation + validation logic consolidated into a shared `map_ops` module used
  by both the services and the Options flow (single source of truth).

### Added
- A small **version footer** on the card (e.g. `v0.5.0`) so a stale/cached card is obvious at
  a glance — deploy verification.

### Removed
- The in-card settings panel (`settings-panel.js`) and its inline text-input editor, which was
  unusable (HA hotkey capture) and poor on mobile.

### Notes
- No store schema change (still `schema_version` 2). Sensor attribute contract unchanged
  (`attributes_version` 3). Fixes the 0.4.x reports: settings hotkey capture and clunky/mobile
  editing. Empty (0-count) categories/shops remain hidden.

## [0.4.1] - 2026-09-02

### Fixed
- **Typing in the settings panel no longer triggers Home Assistant keyboard shortcuts.**
  Keystrokes in the card's text fields (settings name/keyword inputs and the add-item box)
  were bubbling to HA's global hotkey handler (e.g. "c" opening the quick-bar), making the
  fields unusable. The card now stops keyboard-event propagation on its inputs (without
  preventing default, so typing works normally).
- **Sidebar panel now always loads the matching card version.** The panel imported the card
  with a non-cache-busted relative path, so a browser could keep serving an old card after an
  update (symptom: empty/0-count categories still shown because the stale card lacked the
  empty-hide logic). The panel now propagates its own version query onto the card import.

## [0.4.0] - 2026-09-02

### Added
- **In-card settings panels** to manage the maps live, with no code or YAML: add / rename /
  delete categories and shops and edit their keyword lists. Edits apply immediately (each
  action calls the existing service, which persists and recomputes). Category/shop **ordering
  is not editable yet** (deferred).
- **Defaults now ship as `default_map.json`** (data, not Python). The seed taxonomy/shops are
  read from this file, so future default updates are a JSON edit rather than a code change.
- **`reload_defaults` service** and a **"Reload defaults" button** (behind a confirm) in the
  settings panel: replaces your categories and shops with the shipped defaults while **keeping**
  your learned item corrections. Distinct from `reload_maps` (which only re-reads the store
  from disk).

### Changed
- Store schema `schema_version` bumped **1 → 2**. On upgrade, an `async_migrate`-style store
  migrator performs a **one-time re-seed**: categories and shops are replaced from
  `default_map.json` while `overrides`/`shop_overrides` (learned corrections) are preserved.
  The migration is idempotent. This makes the 0.3.0 taxonomy/shops the live map on upgrade
  without a manual step. A migration test covers it.
- `CategoryMap` gains a `seed_version` field recording which shipped seed the categories/shops
  were last built from (used by the migrator, `reload_defaults`, and diagnostics).

### Notes
- The sensor attribute contract is unchanged (`attributes_version` stays 3) — the panels read
  the existing `category_definitions` / `shop_definitions` attributes.

## [0.3.0] - 2026-09-02

### Added
- New default categories: **Fruit & Veg** (replaces Produce; adds cucumber, garlic, tomato,
  potato, pepper, mushroom, spinach, broccoli, …), **Sauces** (teriyaki, soy sauce, ketchup,
  mayo, mango chutney, salad cream, pesto, …), and **Baby** (nappies, wipes, baby food,
  formula).
- New default shops: **Waitrose** (keyword rule `pizza`), **Morrisons**, **Lidl**,
  **Sainsburys** (alongside existing Aldi, Asda, Tesco).
- Default keyword rules: `teriyaki`/`teriyaki sauce`/`veggie pasta` → **Aldi**; `pizza` →
  **Waitrose** shop and **Frozen** category.
- Expanded category keywords so common items categorise on first sight (chickpeas/olives →
  Pantry, yogurts → Chilled, chicken → Fake Meat, ice tea → Drinks).

### Changed
- **Empty categories and shops are hidden.** A category with zero unchecked items (count `0`)
  no longer renders a header, and a shop whose categories are all empty is hidden entirely.
- Category match order: **Sauces** is evaluated before **Chilled** so multi-word sauces (e.g.
  "salad cream") win over Chilled's bare `cream` keyword. Whole-word, first-match-wins semantics
  are unchanged.

### Notes
- Category/shop changes affect the **default seed** used on a fresh setup. Existing installs keep
  their stored map; use `reload_maps` only if you want to re-seed, or add the new
  categories/shops via the services / card. Learned overrides are preserved.

## [0.2.0] - 2026-09-02

### Added
- Dedicated **"Shopping List"** sidebar panel (left-nav entry, cart icon) that hosts the
  bundled card, so the categorised view is reachable without adding the card to a dashboard.
  Registered via `panel_custom` and served by the integration, cache-busted by version. The
  panel auto-discovers the categorised sensor by its attribute contract.

### Changed
- `manifest.json` gains `after_dependencies: ["frontend", "panel_custom"]` so the panel can
  register at runtime without making the frontend a hard setup dependency.

## [0.1.0] - 2026-08-XX

### Added
- Initial implementation of the `alexa_shopping_categoriser` custom integration:
  - Config flow selecting an Alexa Devices `todo` list as the source (one entry per list),
    with a reconfigure flow to change the source without losing learned data, and an
    options flow (undo window 8–30s, show-completed, collapse-empty, diagnostics redaction).
  - `DataUpdateCoordinator` that reads the source via `todo.get_items` (active + completed),
    is event-driven on source `state_changed` with a 15-minute safety poll, and builds a
    derived shop-primary → category-secondary projection.
  - Pure, dependency-free categoriser + shop resolver with **whole-word** matching, vegan
    default taxonomy, and learn-over-time overrides.
  - `sensor.<name>_categorised_shopping_list` exposing the projection
    (**`attributes_version` 3** — the initial shipped contract; earlier versions were
    internal design iterations only, so there is no back-compat obligation).
  - Services: `recategorise_item`, `add_category`, `edit_category`, `delete_category`,
    `assign_shop`, `add_shop`, `edit_shop`, `delete_shop`, `reload_maps`.
  - Redacted diagnostics (item text redacted by default) and a repair issue when the source
    entity is missing/unavailable.
  - Bundled Lovelace card `alexa-shopping-categoriser-card` (complete-on-tap + reversing
    undo, per-item undo windows, source-wins reconciliation, add reconciliation, manual +
    auto collapse per shop/category), served by the integration and cache-busted by version.

### Notes
- Persistence store `schema_version` is 1 and already includes the shop fields; `store.py`
  injects defaults for any missing top-level key, so partial/older stores load safely.
  Future schema changes will bump `schema_version`, add an ordered migrator, and include a
  migration test (`async_migrate_entry` handles config-entry version bumps).
- British spelling is used throughout (domain `alexa_shopping_categoriser`, service
  `recategorise_item`, `Uncategorised`, `uncategorised_count`). See
  `docs/plans/reviews/go-no-go/implementation-deviations.md` (DEV-001).
