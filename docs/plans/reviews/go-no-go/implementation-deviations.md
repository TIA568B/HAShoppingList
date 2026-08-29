# Implementation Deviations

Material deviations from the approved design discovered or directed during implementation.
Minor implementation choices are not recorded here.

---

Deviation ID: DEV-001
Date: 2026-08-29
Affected requirement: Naming / identifiers across the whole project (integration domain,
  module names, service names, sensor attribute keys, category/shop fallback labels).
Approved design: Uses American spelling throughout — integration domain
  `alexa_shopping_categorizer`, module `categorizer.py`, service `recategorize_item`,
  attribute `uncategorized_count`, fallback label `Uncategorized`, and the word
  "categorization"/"categorize" in prose and identifiers.
Implementation reality: The project owner (a UK English speaker) directed a full switch to
  British spelling. Applied:
  - Integration domain: `alexa_shopping_categorizer` -> `alexa_shopping_categoriser`.
  - Package directory: `custom_components/alexa_shopping_categorizer/` ->
    `custom_components/alexa_shopping_categoriser/`.
  - Module: `categorizer.py` -> `categoriser.py`; test `test_categorizer.py` ->
    `test_categoriser.py`.
  - Design doc: `07-categorization-engine.md` -> `07-categorisation-engine.md`.
  - Frontend card dir (when built): `alexa-shopping-categoriser-card/`.
  - Service name: `recategorize_item` -> `recategorise_item` (other service names —
    `add_category`, `assign_shop`, etc. — are unaffected as "category"/"shop" are already
    British-compatible).
  - Sensor attribute key: `uncategorized_count` -> `uncategorised_count`.
  - Category fallback label value: `Uncategorized` -> `Uncategorised`.
  - Python identifiers: `UNCATEGORIZED` -> `UNCATEGORISED`,
    `ATTR_UNCATEGORIZED_COUNT` -> `ATTR_UNCATEGORISED_COUNT`,
    `SERVICE_RECATEGORIZE_ITEM` -> `SERVICE_RECATEGORISE_ITEM`,
    `CategorizedItem` -> `CategorisedItem`, `categorize`/`categorize_item` ->
    `categorise`/`categorise_item`, and all prose/docstrings.
  - `attributes_version` remains **3** (see below).
Reason for deviation: Direct owner instruction; consistency with the primary (single
  household) user's language. Because the project is pre-release (no shipped domain, no
  store on disk in the wild, no card in the wild), there is no back-compat obligation.
Impact:
  - The HA integration domain and the sensor attribute contract change spelling. Since this
    is the *initial* shipped contract (contract v3 per doc 06, finding R7-L1), there is no
    prior consumer to break. `attributes_version` is therefore NOT bumped — the change is a
    spelling of the same v3 shape, and there is no v3 card in the wild that reads
    `uncategorized_count`. The card (Phases 4-5) will be written against the British keys
    from the outset.
  - The `No Preference` shop fallback is unaffected (already British-compatible).
  - "category"/"categories"/"Category" tokens are unchanged (already spelling-neutral).
Security impact: None. No change to auth, data handling, logging, diagnostics redaction,
  input validation, or external-call posture. The rename is purely lexical.
Testing impact: Test module renamed; all backend tests updated and passing (categoriser at
  100% coverage). No test semantics changed. The regression test asserting source selection
  targets the `alexa_devices` platform (finding M-8) is unaffected.
Documentation updated:
  - All active plan docs (`docs/plans/00`-`15`, `README.md`) updated to British spelling;
    `07` renamed and its inbound references fixed.
  - Historical records deliberately NOT edited (they must reflect what was reviewed):
    `docs/specs/**` (historical requirements source-of-truth per documentation steering),
    `docs/plans/review/**`, and `docs/plans/reviews/go-no-go/tda-review.md`. The design
    "Decisions" record and this deviation entry capture the override instead.
  - Steering files updated to the new domain/module/service spelling (they are living
    implementation guidance, not historical records).
Further approval required: No. Owner-directed, pre-release, no contract consumers, no
  security/behavioural change. Recorded here for traceability.
