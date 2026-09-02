# Feature Design — User-Facing Map Management (A + D + reload)

Design-only. **No implementation yet.** This directory extends the approved plan in
`docs/plans/` (it is not a redesign): storage stays JSON in the HA `Store`, the
categoriser/coordinator/recompute path is unchanged, and the card settings panels were
already anticipated in `docs/plans/11-frontend-card.md`. Where this feature touches the
contract or engine, the **canonical** definitions remain in the core docs (06 data
model/contract, 07 categorisation engine, 04 HA integration) — these docs reference them
rather than restating.

## Goal

Let the single user curate the category and shop maps **live, with no code changes and no
YAML**, and see the categorised view re-group **immediately** after every edit. Move the
seed data out of Python into a shipped JSON file, and give the user an explicit
"reload defaults from JSON" action in the integration's admin surface.

## Chosen options (from the options discussion)

- **A — In-card settings panels** as the primary live editor (add/rename/delete categories
  and shops, edit keyword lists). Writes go through the **existing** services, which already
  persist + recompute, so edits are reflected instantly. This is the mechanism that removes
  the "manually run a service" pain.
- **D — Defaults as a shipped `default_map.json`** (data, not Python). Applied:
  - on **initial run** (fresh install seeds from the JSON), and
  - once during the **upgrade that introduces this feature**, as a migration from the
    `defaults.py` seed to the JSON seed — re-seeding the store so the taxonomy/shops added in
    0.3.0 become the live map. The user has confirmed the store is **test data only** ("not
    used in anger"), so this migration performs a **clean re-seed (replace)**, not a delicate
    merge.
- **Reload-from-JSON admin action** — an explicit control in the integration's admin
  interface (and a backing service) that re-seeds the live map from `default_map.json` on
  demand, so future default updates (a JSON edit shipped in a release) can be applied with one
  click instead of hand-editing through the UI. This **replaces** the current map (with a
  clear warning) — it is the manual equivalent of the upgrade migration.

## What this feature deliberately does NOT do (scope guard)

- It does **not** switch storage to SQLite. JSON-in-HA-`Store` is the right fit for this
  data shape and matches the architecture/security steering (see `01-storage-choice.md`).
- It does **not** implement the guarded "merge only new defaults, track deletions" behaviour
  (the earlier "Option C"). Because the user wants a clean re-seed now, replace-semantics are
  simpler and were explicitly chosen. The merge variant is recorded as a **future option** in
  `03-migration-and-reload.md` in case a second user ever needs upgrade-safe merges.
- It does **not** change the sensor attribute contract shape (`attributes_version` stays 3)
  unless the panel needs a new read path; if it does, that is called out in `02-*`.

## Read in this order

| # | Document | Concern |
|---|----------|---------|
| 01 | [01-storage-choice.md](01-storage-choice.md) | Why JSON in the HA `Store` (not SQLite); where each thing lives |
| 02 | [02-card-settings-panels.md](02-card-settings-panels.md) | Option A: the live editor UX, contract reads, service writes, validation, instant recompute |
| 03 | [03-migration-and-reload.md](03-migration-and-reload.md) | Option D: `default_map.json`, initial seed, upgrade re-seed migration, and the reload-from-JSON admin action |
| 04 | [04-security-and-testing.md](04-security-and-testing.md) | Input validation, XSS, redaction; test matrix additions |
| 05 | [05-open-questions.md](05-open-questions.md) | Resolved decisions (OQ-A..D), assumptions, risks |
| 06 | [06-implementation-plan.md](06-implementation-plan.md) | Phased build plan (M1–M6) for 0.4.0 |

## Traceability

- Requirement roots: Req 6 (category maintenance), Req 7.1 (shop maintenance). This feature is
  the **UX + lifecycle** layer over those already-implemented services; it introduces no new
  product rule.
- Target release: **0.4.0** (new feature → minor bump), following the 0.3.0 taxonomy release.
