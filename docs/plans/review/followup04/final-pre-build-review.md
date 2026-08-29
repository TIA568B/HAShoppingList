# Follow-up Review 04 — Final Pre-Build Review

**Reviewer:** Independent senior technical reviewer (second agent, final pre-build pass)
**Date:** 2026-08-29
**Mandate:** A last gate before any code is written. This pass is deliberately **adversarial**: it
does not re-confirm already-ticked findings (see `followup03/status-ledger.md` for those). It hunts
for the class of problems that only surface when someone actually starts implementing —
internal contradictions, under-specified corners, and schema/versioning traps.
**Method:** `git diff` against the prior baseline + close reads of `06`, `07`, `10`, `13` and the
`12` matrix. Read-only HA MCP re-check. I did not modify any plan, spec, or steering file.

---

## Executive Summary

The plan is in strong shape. Since Follow-up 03, the four Req-7 polish items I raised (R7-L1,
R7-L2, R7-O1, R7-O3) were all addressed and verified on disk. Re-reading everything adversarially,
I found **no Critical or High issues** — nothing that changes the architecture or blocks the
project. I did find a small number of **implementation-blocking-or-ambiguous details** that are
cheap to fix now and annoying to discover mid-build. None are showstoppers; most are "pin the
semantics before you write the function" items.

### Go / No-Go

> **GO — cleared to begin implementation**, with the recommendation that **F4-1 (store schema
> version/migration for the shop maps)** and **F4-2 (keyword match: whole-word vs substring)** are
> pinned down as the *first* task in Phase 1, before the categorizer and store are written. They
> are effectively "decide the semantics" items and Phase 1 is exactly where they land.

This does not lower the readiness from Follow-up 03; it sharpens the entry into Phase 1. The prior
gates still stand: the Phase 2.5 write spike (M-6) before card work, Phase 7 E2E before release,
and OQ6 housekeeping before publish.

### Finding count (this pass)

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 2 | F4-1, F4-2 |
| Low | 3 | F4-3, F4-4, F4-5 |
| Observation | 2 | F4-6, F4-7 |

---

## Findings

### F4-1 — Store schema grew for Req 7 without a version bump or a migrator; migration test still category-only
- **Severity:** Medium — **Area:** Persistence / Store / Migration
- **Description:** Req 7 added `shops` and `shop_overrides` to both the `CategoryMap` dataclass and
  the stored JSON (`06`), but the store `schema_version` is still **1**, the Migration section
  still reads "v1 defines version 1," and the only migration test in `12` is
  `store schema_version v0→v1`. There is no defined behaviour for loading a store that predates the
  shop fields (i.e. has no `shops`/`shop_overrides` keys). Because this is greenfield (no store
  exists yet), it is **not a live runtime bug today** — but it is an internal inconsistency that
  will bite the moment the schema evolves, and the "load a store missing the shop keys" path is
  exactly the kind of `KeyError` that surfaces in the first real upgrade.
- **Evidence:** `06` `CategoryMap` now has `shops` + `shop_overrides`; `06` storage JSON includes
  them; `06` Migration still "v1 defines version 1"; `12` migration row unchanged.
- **Impact:** Ambiguous load semantics for a store without shop keys; future upgrade risk;
  test coverage gap.
- **Recommendation:** Decide now and document in `06`: either (a) the shop fields are part of
  schema **version 1** (greenfield, so v1 simply always includes them and `store.py` injects empty
  defaults if absent — a defensive `.get()` with defaults), or (b) bump to **schema_version 2**
  with a migrator that adds default shops + empty `shop_overrides`. Given greenfield, (a) is
  simplest — but the plan must **state** that `store.py` tolerates a missing `shops`/`shop_overrides`
  key by injecting defaults, and `12` should add a "load store lacking shop keys → defaults
  injected" test. This is a one-paragraph decision, best made as the first Phase 1 step.

### F4-2 — Category keyword matching is specified as "whole-word/substring"; shop matching is "whole-word" — pick one and beware `ham`
- **Severity:** Medium — **Area:** Categorizer semantics / correctness
- **Description:** `07` §3 says a category keyword is matched by "a **whole-word/substring** match"
  and then "Start with **substring/word matching**." That is ambiguous (which one?), and it
  conflicts with the shop resolver, which is explicitly **whole-word** (tiers 1 and 3). Substring
  matching is genuinely risky with the current default keywords: `ham` (a Fake Meat keyword)
  substring-matches "**gra**ham crackers" and "c**ham**omile"; `tea` (Drinks) matches "s**tea**k"
  and "**tea** tree"; `roll` (Bakery) matches "**roll**mop" (pickled herring — which should be
  animal/Uncategorized). These are real mis-categorizations the vegan rules are meant to prevent.
- **Evidence:** `07` §3 wording vs. `07` shop tiers "whole-word"; default keyword lists in `06`
  include `ham`, `tea`, `roll`, `cream`, etc.
- **Impact:** False-positive categorizations, some of which cross the vegan boundary (e.g. a
  herring product matching a Bakery keyword). Also an inconsistency between the two resolvers in the
  same pure module.
- **Recommendation:** Standardise on **whole-word, case-insensitive** matching for **both** category
  keywords and shop keywords (and multi-word keywords like "oat milk" as a whole-phrase/token
  match). Update `07` §3 to drop "substring," and add categorizer test rows for the traps
  ("graham crackers" → not Fake Meat; "steak" → not Drinks). Keep `difflib` fuzzy as the explicitly
  deferred enhancement. This aligns the two resolvers and protects the vegan guarantee.

### F4-3 — `reload_category_map` name no longer reflects that it also reloads the shop map
- **Severity:** Low — **Area:** Services / naming
- **Description:** The store now holds both the category map and the shop map, and
  `reload_category_map` "forces reload of the store + recompute" — which now includes shops. The
  name implies category-only.
- **Recommendation:** Either rename to `reload_maps` / `reload_store` (cleaner, but it is a public
  service name — decide before first release, not after) or explicitly document that
  `reload_category_map` reloads the entire store (categories **and** shops). Pick before shipping
  `services.yaml`.

### F4-4 — Diagnostics (`10`) not updated for the shop dimension
- **Severity:** Low — **Area:** Diagnostics
- **Description:** `10` lists `category_count`, per-category counts, and `override_count`. It does
  not mention `shop_count`, per-shop counts, or `shop_override_count`. Diagnostics should reflect
  the new dimension so a bug report is useful.
- **Recommendation:** Add shop counts + `shop_override_count` to the diagnostics dump in `10`
  (redaction unchanged — counts only by default). Trivial; fold into Phase 6.

### F4-5 — `13` file responsibilities / `models.py` list not updated for `Shop`; `test_migration.py` scope
- **Severity:** Low — **Area:** Docs consistency
- **Description:** `13`'s `models.py` responsibility row and the `store.py` row still say
  "CategoryMap + overrides" and "categorizer + vegan rules" without the shop additions; the
  `categorizer.py` comment says "normalize + match + vegan rules (no HA import)" but the shop
  resolver also lives there now. Cosmetic drift from the Req 7 changes that landed in `06`/`07`.
- **Recommendation:** One-line updates to `13` so the structure doc matches `06`/`07` (add `Shop`,
  `shops`, `shop_overrides`, shop resolver). Keeps the "canonical structure" doc honest.

### F4-6 — Precedence divergence between category and shop resolvers is intentional but worth a one-line callout
- **Severity:** Observation
- **Description:** For **categories**, a learned override is highest precedence. For **shops**, an
  explicit shop-name-in-text beats a learned override. This asymmetry is deliberate and justified
  (naming the shop in the text is the most explicit signal), and it is documented in `07`/`15`. I
  flag it only because an implementer reading the two resolvers side by side may "helpfully" make
  them consistent and break the intended shop behaviour.
- **Recommendation:** Add a one-line note in `07` at the top of the shop section: "Note: unlike the
  category resolver, tier 1 (shop-name-in-text) intentionally outranks the learned override." Keeps
  a future maintainer from 'fixing' it.

### F4-7 — Add-item optimistic reconciliation could briefly show an item in the wrong shop/category
- **Severity:** Observation
- **Description:** With Req 7, an optimistically-added item (before its real `uid` arrives) must be
  placed in *some* shop group and category. The categorizer is pure, so the card can predict both
  from the typed text — but a `recategorize_item`/`assign_shop` learned override that exists only
  in the backend store would not be reflected in the card's optimistic guess until the inbound
  refresh. Result: a just-typed item may jump shop/category once when the real projection arrives.
  This is cosmetic and self-correcting (the REVIEW2-002 reconciliation adopts the real item), but
  worth naming so it is not treated as a bug during Phase 4/5.
- **Recommendation:** Note in `11` that optimistic placement is a best-effort local guess and may
  re-pivot once on reconciliation; not an error. No behavioural change needed.

---

## Things I specifically checked and found sound

- **No-drift / rebuildable invariant holds with shops.** Shop data lives only in the store (keyed
  by normalized text), never on the Alexa list; the projection is still fully derivable. (`06`,
  product/architecture steering.)
- **Contract versioning is coherent.** `attributes_version: 3` is consistently referenced in `06`,
  `12`, `14`; the store `schema_version` is correctly independent (modulo F4-1's bump question).
- **Complete-on-tap** language is consistent everywhere; no residual deferred-timer references.
- **Steering reaches every surface**, including the card (`frontend.md`, `testing.md` scope
  `{tests/**,frontend/**}`).
- **Security posture unchanged and still sound** for Req 7: shop names/keywords are user text,
  validated by voluptuous and rendered XSS-safe, same as category text. No new external surface.
- **Test matrix tracks the new behaviour** (shop precedence, delete→No Preference, rename migrates
  shop overrides, shop-settings panel, No Preference position option).
- **Environment unchanged** (read-only MCP): source entity `supported_features: 7`, state 14, HA
  2026.8.3.

---

## Recommended entry sequence into Phase 1

1. **First, pin F4-1 and F4-2** (one short decision each, recorded in `06`/`07`): store tolerates
   missing shop keys / schema version stance; and whole-word matching for both resolvers.
2. Then build `models.py` + `categorizer.py` (categories **and** shops) to the whole-word semantics,
   with the trap tests (F4-2) and the "missing shop keys → defaults" test (F4-1).
3. Continue per the doc-14 phase order. Fold F4-3/F4-4/F4-5 into the phases that touch services,
   diagnostics, and docs respectively.

## Confirmations

- No production code was implemented.
- No plans, specs, or steering were modified by me.
- No prior review documents were modified; Follow-ups 01–03 are preserved as audit artefacts.
- The Home Assistant MCP was used strictly read-only; the environment is unchanged.

---

## Final verdict

**GO.** The design is coherent, complete, and internally consistent enough to build. The two
Medium items (F4-1 store/migration, F4-2 matching semantics) are "decide before you write the
function" clarifications that belong at the very start of Phase 1, not blockers to starting. The
Lows and Observations are polish to fold into their respective phases. There is no remaining reason
to keep iterating on the plan before writing code — pin F4-1/F4-2 and begin.
