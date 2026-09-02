# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
