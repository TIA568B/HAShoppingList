---
inclusion: fileMatch
fileMatchPattern: '**/*.md'
---

# Documentation Steering

## What must exist

- `README.md`: what the integration does, prerequisites (core `alexa_devices` configured,
  HACS), install steps, config-flow walkthrough, the card setup, and the vegan
  categorisation rules.
- `docs/plans/`: the technical design (source of truth for implementation). Keep it updated
  when the design changes.
- `docs/specs/`: original requirements/design/tasks. These are historical source-of-truth
  for *requirements*; where they conflict with verified Home Assistant reality, the plan
  documents the override and reality wins. Do not silently edit the specs to match reality.

## When documentation must be updated

- Any change to the **sensor attribute schema** or **service signatures** updates the
  contract section in the design doc in the same change set (frontend and backend both
  depend on it).
- Any new/removed config or options field updates the README config section.
- Any change to the default category taxonomy or vegan rules updates both `product` steering
  and the README.

## Design-decision recording

- Record notable decisions (and reversals of the original spec, e.g. custom integration over
  pyscript, source entity choice, learn-over-time instead of history mining) as short dated
  entries in the design doc's "Decisions" section. State the decision, why, and what it
  overrides.

## Changelog / migration

- Maintain a `CHANGELOG.md` once implementation starts (Keep a Changelog format, semver).
- Any config-entry or stored-data schema change requires an `async_migrate_entry` note in the
  changelog and a migration test.

## File granularity

- **Favour multiple small, digestible documents over a single massive file.** Split docs by
  concern (one topic per file) and provide a short index/README that links them in reading
  order. A reader should be able to open one file and understand one thing.
- Rule of thumb: if a doc grows past a few hundred lines or covers more than one clear
  concern, split it. The design plan in `docs/plans/` is intentionally split this way.

## Style

- Prose for rationale, tables for enumerations, Mermaid for flows. Keep it concise and
  actionable. Do not duplicate the same fact across multiple docs — link to the canonical
  location.
