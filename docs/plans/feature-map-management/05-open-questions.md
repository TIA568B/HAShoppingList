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

## Open questions (need an answer before build)

- **OQ-A — Learned overrides on the one-time upgrade migration:** preserve them (recommended,
  costs nothing, they self-heal) or wipe them too (acceptable since it is test data)? Default
  assumption if unanswered: **preserve**.
- **OQ-B — Category/shop reordering in the panel:** order is significant (first-match-wins). Do
  we add reordering now? If yes, it needs either a new `reorder_categories`/`reorder_shops`
  service or an `order` field on `edit_*`. If deferred, the panel edits names/keywords but not
  order (order stays as seeded). Default assumption: **defer reordering** to keep 0.4.0 focused;
  revisit if the seeded order proves wrong in use.
- **OQ-C — Reload action placement:** card settings-panel button (recommended) vs a
  Developer-Tools-only service vs both. Default assumption: **button + backing
  `reload_defaults` service** (button calls the service).
- **OQ-D — Naming:** confirm `reload_defaults` (new, re-seed from shipped JSON) as distinct from
  the existing `reload_maps` (re-read store from disk). If the distinction is confusing, an
  alternative is `reset_to_defaults`. Default assumption: **`reload_defaults`**.

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
