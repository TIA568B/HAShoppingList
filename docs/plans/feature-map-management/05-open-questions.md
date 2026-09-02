# 05 — Open Questions, Assumptions, Risks (this feature)

Resolve the open questions before implementation. Confirmed user decisions are recorded so they
are not re-litigated.

## Confirmed user decisions

- **A is the primary editor;** edits must reflect immediately (they already recompute — no
  manual step).
- **D applied on initial run AND as a one-time upgrade migration** re-seeding from
  `default_map.json`, so the 0.3.0 taxonomy/shops become the live map on upgrade.
- The current store is **test data only** ("not used in anger") → the upgrade migration and the
  reload action use **replace** semantics for categories/shops (not a delicate merge).
- **A reload-from-JSON action** in the admin surface, so future shipped-default updates are one
  click. Replace semantics, with a confirmation warning.
- Single user for now → no need for upgrade-safe merge yet (recorded as a future option).

## Resolved decisions (were open questions; user-confirmed 2026-09-02)

- **OQ-A — Learned overrides on the one-time upgrade migration → KEEP.** The re-seed replaces
  categories/shops but **preserves** `overrides`/`shop_overrides`; they self-heal if they point
  at a category/shop the re-seed removed.
- **OQ-B — Category/shop reordering → DEFER to a later release.** 0.4.0 panels edit
  names/keywords and add/delete only; **order is not user-editable** and stays as seeded
  (first-match-wins order from `default_map.json`). No `reorder_*` service and no `order` field
  in 0.4.0, so the sensor contract shape is unchanged (`attributes_version` stays 3).
- **OQ-C — Reload action placement → BUTTON + backing service.** A "Reload defaults" button in
  the card settings panel (behind a confirm dialog) that calls a new backing service; the
  service is also usable from Developer Tools / automations.
- **OQ-D — Naming → `reload_defaults`.** New service, re-seeds from the shipped
  `default_map.json` (replace). Distinct from the existing `reload_maps` (re-read store from
  disk). Kept the `reload_defaults` name.

## Assumptions

- `default_map.json` is trusted shipped data (not user-writable at runtime); parsed defensively.
- The sensor attribute contract (`attributes_version` 3) does not change unless reordering
  (OQ-B) forces a new signal; if it does, bump per the contract rules in `docs/plans/06`.
- HA `panel_custom`/`frontend` are available at runtime (the sidebar panel already relies on
  this); panel/reload registration remains best-effort and never blocks setup.

## Risks

- **Destructive reload confusion:** a user could click "Reload defaults" and lose category/shop
  curation. Mitigation: explicit confirm dialog + clear copy + `info` log; overrides preserved.
- **Two similarly-named reload paths** (`reload_maps` vs `reload_defaults`). Mitigation: precise
  service descriptions in `services.yaml`/strings; document both in one place (`docs/plans/06`).
- **Seed drift:** `default_map.json` and any lingering `defaults.py` constants disagreeing.
  Mitigation: make JSON the single source; if `defaults.py` remains, it only *loads* the JSON;
  a parity test guards it.

## Release

Target **0.4.0** (minor: new feature). Version bump in `manifest.json` + `pyproject.toml`,
CHANGELOG entry, and — because the store schema changes — an `async_migrate_entry`/store
migrator note in the changelog with a migration test (documentation steering).
