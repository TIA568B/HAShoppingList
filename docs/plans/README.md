# Categorized Alexa Shopping List — Design Plan

This directory is the **implementation source of truth**. It consolidates the requirements in
`docs/specs/` with verified Home Assistant environment findings, and overrides the spec where
reality differs (reality wins; overrides are documented, specs are left untouched).

> **Status:** Design complete and **remediated** against two review passes. The review
> deliverables live in [review/](review/): the original review, `followup01/` (which flagged that
> an earlier remediation was described but not applied), `finding-disposition.md`, and
> `revision-summary.md`. All accepted findings are now **applied on disk**. **Do not begin
> implementation** until a final independent re-verification and the outstanding human decisions
> (OQ3/OQ5/M-5/M-6) are resolved.

## Read in this order

| # | Document | What it covers |
|---|----------|----------------|
| 00 | [00-executive-summary.md](00-executive-summary.md) | What/why, users, high-level architecture, recommended approach |
| 01 | [01-specification-analysis.md](01-specification-analysis.md) | Consolidated requirements, dependencies, conflicts, ambiguities, gaps |
| 02 | [02-environment-analysis.md](02-environment-analysis.md) | Repo + HA MCP read-only findings (confirmed / assumed / recommended) |
| 03 | [03-architecture.md](03-architecture.md) | Components, data/control flow, boundaries, diagrams |
| 04 | [04-ha-integration-design.md](04-ha-integration-design.md) | Manifest, config/options flow, lifecycle, coordinator, services, diagnostics |
| 05 | [05-entity-and-device-model.md](05-entity-and-device-model.md) | Sensor entity, device model, unique IDs, availability |
| 06 | [06-data-model-and-contract.md](06-data-model-and-contract.md) | Dataclasses, storage schema, sensor attribute contract, service signatures |
| 07 | [07-categorization-engine.md](07-categorization-engine.md) | Normalization, matching, vegan rules, learning, default taxonomy |
| 08 | [08-update-and-sync-strategy.md](08-update-and-sync-strategy.md) | Reactivity, tick+undo grace period, sync back, stale data |
| 09 | [09-error-handling-and-resilience.md](09-error-handling-and-resilience.md) | Failure modes, retries, backoff, restarts, outages |
| 10 | [10-logging-diagnostics-security.md](10-logging-diagnostics-security.md) | Logging, diagnostics, redaction, security review |
| 11 | [11-frontend-card.md](11-frontend-card.md) | Custom Lovelace card design and behavior |
| 12 | [12-testing-strategy.md](12-testing-strategy.md) | Test types, mocking, test matrix |
| 13 | [13-project-structure-and-dependencies.md](13-project-structure-and-dependencies.md) | Directory layout, file responsibilities, dependencies |
| 14 | [14-implementation-plan.md](14-implementation-plan.md) | Phased plan, acceptance criteria, recommended order |
| 15 | [15-risks-open-questions.md](15-risks-open-questions.md) | Risks, assumptions, open questions, decisions log |

## One-line summary

A custom Home Assistant integration (`alexa_shopping_categorizer`) that derives a live,
**shop-then-category**-grouped, tick-with-undo projection of the Alexa shopping list
(`todo.david_carson_amazon_gmail_com_shopping_list`, platform `alexa_devices`), learns categories
**and per-item shop preferences** (Aldi/Asda/Tesco/… or No Preference) over time, and syncs changes
back through the native `todo.*` services — paired with a custom Lovelace card.
