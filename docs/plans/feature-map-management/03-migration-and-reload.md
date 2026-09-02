# 03 — Option D: `default_map.json`, Seeding, Upgrade Re-seed, and Reload

Moves the seed out of Python (`defaults.py`) into a shipped JSON file, defines when it is
applied, and adds an explicit user-triggered reload. Storage of the *live* map is unchanged
(JSON in the HA `Store`; see `01-storage-choice.md`).

## The shipped file

`custom_components/alexa_shopping_categoriser/default_map.json` — the canonical seed, shipped
with the integration and updatable in a release (a JSON edit, no Python change). Shape mirrors
the stored map (canonical in `docs/plans/06`):

```jsonc
{
  "seed_version": 1,
  "categories": [ { "name": "Fruit & Veg", "keywords": ["apple", "..."] }, ... ],
  "shops":      [ { "name": "Aldi", "keywords": ["nappies", "milk", "..."] }, ... ]
}
```

- `default_map.json` holds **only** `categories` and `shops` (+ a `seed_version`). It never
  holds learned `overrides` / `shop_overrides` — those are user data, seeded empty.
- `defaults.py` becomes a thin loader/parser of this file (or is removed, with a tiny
  `load_default_map()` helper). The default values themselves live in JSON. Loading a bundled
  file is read-only disk I/O done via the executor (never blocking the event loop).
- `seed_version` is an integer bumped whenever the shipped defaults change materially. It lets
  the reload/upgrade logic and diagnostics report which seed the store was last built from.

## When the seed is applied

Three moments, all **replace**-semantics for the categories/shops (learned overrides are
preserved unless explicitly stated):

### 1. Initial run (fresh install)
Store is empty → seed the live map from `default_map.json` (categories + shops), with empty
overrides. (Same behaviour as today, just sourced from JSON instead of `defaults.py`.)

### 2. The upgrade that introduces this feature (one-time migration)
On upgrading to the version that ships this feature, migrate the store from the old
`defaults.py`-seeded shape to the JSON-seeded shape by **re-seeding categories + shops from
`default_map.json`**, so the 0.3.0 taxonomy/shops become the live map.

- **Rationale / user decision:** the user has confirmed the current store is **test data only
  ("not used in anger")** and explicitly wants earlier mappings reflected on upgrade. So this
  migration **replaces** categories + shops wholesale rather than doing a delicate merge.
- **Learned overrides: PRESERVED** (decision OQ-A, user-confirmed). They key on normalised text
  and self-heal if they point at a category/shop the re-seed removed (existing behaviour). The
  migration replaces `categories`/`shops` only; `overrides`/`shop_overrides` are carried over
  untouched.
- Mechanics: bump the store `schema_version`, add an ordered migrator in `store.py` that loads
  `default_map.json` and overwrites `categories`/`shops`, persists, and recomputes. A
  migration test is required (documentation/testing steering).

### 3. Reload-from-JSON admin action (on demand, repeatable)
An explicit control so future default updates (a shipped JSON edit) can be applied with one
click, instead of hand-editing via the panels.

- **Semantics: replace** categories + shops from `default_map.json` (the manual equivalent of
  the upgrade migration). This is the user's stated intent: "easier to reload than for me to
  make the changes through the interface myself."
- **Destructive-action warning:** because it overwrites the user's category/shop edits, the
  admin surface must show a clear confirmation ("This replaces your categories and shops with
  the shipped defaults. Learned item corrections are kept. Continue?"). Never silent.
- **Overrides:** kept (same as the migration). An override pointing at a category/shop that the
  reload removed self-heals to keyword match / `Uncategorised` / `No Preference`.

## Where the reload action lives (admin surface)

The integration is config-entry based and already registers a sidebar **"Shopping List"**
panel. Options, in rough order of fit:

1. **A button in the card's settings panel** ("Reload defaults") guarded by a confirm dialog,
   calling a new backend service. Most discoverable; consistent with Option A. **Recommended.**
2. **A backing service** `reload_defaults` (distinct from the existing `reload_maps`, which
   reloads the *store from disk*; this new one re-seeds the store *from the shipped JSON*).
   Needed regardless, since the button calls it; also usable from Developer Tools / automations.
3. Options-flow toggle — poor fit (options flow is for settings, not one-shot destructive
   actions). Rejected.

Naming to avoid confusion (both exist):
- `reload_maps` (existing) — re-read the **store** from disk into memory + recompute. Non-
  destructive. Used after out-of-band store edits.
- `reload_defaults` (new) — **replace** the store's categories/shops from the shipped
  `default_map.json` + recompute. Destructive to category/shop edits; confirm required.

## Contract / doc impact

- `docs/plans/06` (canonical): add `default_map.json` as the seed source; note the store
  `schema_version` bump + the new migrator; document `reload_defaults` alongside `reload_maps`.
- `docs/plans/07`: note the default taxonomy/shops now live in `default_map.json` (the vegan
  rules and matching semantics are unchanged).
- `docs/plans/13`: add `default_map.json` to the file layout and responsibilities table.
- `home-assistant.md` steering already lists services; add `reload_defaults` when implemented.

## Future option (not now): upgrade-safe merge

If a second user ever needs upgrade-safe behaviour (don't clobber their curation), add a
`seed_version`-guarded **merge** mode: on upgrade, add only categories/shops that are new since
the store's recorded `seed_version`, never re-adding ones the user deleted (track seeded keys).
Deferred deliberately — the current single user wants clean replace.
