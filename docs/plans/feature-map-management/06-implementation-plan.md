# 06 — Implementation Plan (0.4.0)

Phased, each phase independently testable. Decisions locked in `05-open-questions.md`
(A-keep, B-defer, C/D confirmed). No behaviour ships until released (version bump + tag +
GitHub release per `release-and-deployment` steering).

## Phase M1 — Defaults as JSON (Option D, backend)
- Add `custom_components/alexa_shopping_categoriser/default_map.json` with `seed_version`,
  `categories`, `shops` — the exact 0.3.0 taxonomy/shops (parity with current `defaults.py`).
- Reduce `defaults.py` to a loader: `load_default_map()` reads + parses the JSON via the
  executor, defensively (missing/partial/malformed → safe fallback). `default_categories()` /
  `default_shops()` delegate to it so nothing else changes.
- Tests: JSON loads; parity between JSON and the previously-hardcoded seed; malformed file
  degrades safely.
- Acceptance: fresh install seeds identically to 0.3.0, now sourced from JSON.

## Phase M2 — Upgrade re-seed migration (Option D, backend)
- Bump store `schema_version`; add an ordered migrator in `store.py`: on load of a pre-feature
  store, **replace** `categories`/`shops` from `default_map.json`, **preserve**
  `overrides`/`shop_overrides` (OQ-A), persist, recompute. Idempotent.
- Record `seed_version` in the store for diagnostics.
- Tests: pre-feature store re-seeds on load; overrides preserved; running twice is a no-op;
  migration test (required by documentation/testing steering).
- Acceptance: upgrading the running (test) install makes the 0.3.0 map the live map without a
  manual step.

## Phase M3 — `reload_defaults` service (backend)
- New config-entry-scoped service `reload_defaults` (voluptuous, optional `entry_id`): replace
  `categories`/`shops` from `default_map.json`, keep overrides, persist, recompute. Distinct
  from `reload_maps`. `info` log (no item text). `services.yaml` + strings with a clear
  "replaces your categories/shops; keeps learned corrections" description.
- Tests: replaces from JSON; overrides kept + self-heal; distinct from `reload_maps`; entry
  targeting; missing JSON raises cleanly.
- Acceptance: calling the service re-seeds on demand.

## Phase M4 — Card settings panels (Option A, frontend)
- Category panel: read `category_definitions`; add/rename/delete + edit keywords via existing
  services. Shop panel: read `shop_definitions`; add/rename/delete + edit keyword rules;
  common-word add warning. No reordering (OQ-B deferred).
- Inline errors from `ServiceValidationError`; safe-DOM rendering; keyboard/ARIA.
- Reflect changes via the normal sensor update (no optimistic map mutation).
- Tests (node:test + DOM stub): each action dispatches the right service/payload; error
  surfaced; XSS-safe text.

## Phase M5 — Reload button (frontend) + wiring
- "Reload defaults" button in the settings panel behind a confirm dialog; calls
  `reload_defaults`. Rebuild the card bundle into `www/`.
- Tests: confirm dialog gates the call; only fires on confirm.

## Phase M6 — Docs, version, release prep
- Update canonical docs: `06-data-model-and-contract.md` (seed source = JSON, `schema_version`
  bump + migrator, `reload_defaults` alongside `reload_maps`), `07` (defaults live in JSON),
  `13` (file layout), `home-assistant.md` steering (add `reload_defaults`).
- Bump `manifest.json` + `pyproject.toml` to **0.4.0**; CHANGELOG entry incl. the
  `async_migrate_entry`/store-migrator note (documentation steering).
- Full gate: ruff + mypy strict + pytest (≥90%, categoriser 100%) + card `node --test` + build.
- **Stop before release**; get explicit go-ahead, then `./scripts/release.sh`.

## Order

M1 → M2 → M3 (backend, sequential) → M4 → M5 (frontend, after M3 so the button has a service)
→ M6. M4 can start against M1's contract while M2/M3 land, since the panels use existing
services.
