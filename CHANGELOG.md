# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
