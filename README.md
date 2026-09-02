# Alexa Shopping List Categoriser

A Home Assistant custom integration that presents your Alexa-synced shopping list as a
**shop-grouped, category-sorted, tick-with-undo** view, and keeps it in sync with the
underlying Alexa list. It adds no second copy of your list: the view is a derived
projection, always rebuildable from the Alexa list plus your saved category and shop maps.

- **Domain:** `alexa_shopping_categoriser`
- **Integration type:** service (calculated) — no devices, no cloud calls of its own
- **Bundled Lovelace card:** `alexa-shopping-categoriser-card`

## What it does

- Groups your shopping list **by shop, then by category (aisle)** — e.g. `Aldi → Milk → oat milk`.
- Categorises new items automatically and **learns** from your manual corrections.
- Resolves a **preferred shop** per item (learns too), with a fixed precedence.
- **Tick items off with a short undo window**; completion is sent to Alexa immediately so a
  closed tab never loses a tick.
- Live-updates when the list changes anywhere (including directly via Alexa).

## Prerequisites

1. **Home Assistant 2026.8** or newer.
2. The core **Alexa Devices** integration configured, exposing your shopping list as a
   `todo` entity (e.g. `todo.<account>_shopping_list`). This integration reads and writes
   **only** through that entity's public `todo.*` services — it never talks to Amazon
   directly and stores no Amazon credentials.
3. **HACS** (recommended) for installation and updates.

> Note: the native `todo.shopping_list` (platform `shopping_list`) is **not** the Alexa
> list and is intentionally never offered as a source.

## Installation

### Via HACS (recommended)

1. Add this repository as a HACS custom repository (category: Integration).
   Repository URL: `https://bitbucket.org/tia568b/hashoppinglist/`
2. Install "Alexa Shopping List Categoriser".
3. Restart Home Assistant.

> Note: HACS's one-click "Open in HACS" My-button only resolves **GitHub** repositories, so
> there is no HACS button here — this project is hosted on Bitbucket. Add it as a custom
> repository using the URL above.

### Manual

1. Copy `custom_components/alexa_shopping_categoriser/` into your HA `config/custom_components/`.
2. Restart Home Assistant.

## Configuration (config flow)

Once installed and Home Assistant has restarted, add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=alexa_shopping_categoriser)

1. Or manually: go to **Settings → Devices & Services → Add Integration** and search for
   **Alexa Shopping List Categoriser**.
2. Pick your Alexa shopping list from the dropdown. Only `todo` entities on the
   **Alexa Devices** platform are listed; the one whose id contains `shopping` is preselected.
   - If no Alexa list is found, the flow aborts and points you at the Alexa Devices setup.
3. Finish. A sensor `sensor.<name>_categorised_shopping_list` appears, exposing the grouped
   projection for the card.

Only one entry per source list is allowed. To point at a **different** Alexa list later,
use the entry's **Reconfigure** action — your learned categories and shops are preserved.

### Options

Open the integration's **Configure** to tune:

| Option | Default | Range |
| --- | --- | --- |
| Undo window (seconds) | 9 | 8–30 |
| Show completed items | off | — |
| Collapse categories with no remaining items | on | — |
| Redact item text in diagnostics | on | — |

The source list is **not** an option (it is the entry's identity) — use Reconfigure instead.

## The card

The card is bundled and served by the integration (cache-busted by version), so you do not
hand-install JavaScript. Add it to a dashboard:

```yaml
type: custom:alexa-shopping-categoriser-card
entity: sensor.alexa_shopping_list_categoriser_categorised_shopping_list
# optional:
# source_entity: todo.<account>_shopping_list   # defaults to the sensor's source
# no_preference_position: last                   # or "first"
```

The card renders **shop → category → items**. You can:

- Tick an item (undo appears for the configured window).
- Add an item (goes straight onto the Alexa list).
- Collapse/expand each shop and each category independently, or **Focus** a shop to collapse
  the others. Empty (fully-ticked) groups auto-collapse; you can still expand them.

If you build the card yourself: `cd frontend/alexa-shopping-categoriser-card && npm ci &&
npm run build`, then copy `dist/alexa-shopping-categoriser-card.js` into
`custom_components/alexa_shopping_categoriser/www/`. A pre-built copy ships in `www/`.

## Categorisation rules (vegan by design)

The primary user is vegan, so the default taxonomy assumes plant-based products:

| Item text matches… | Category | Assumption |
| --- | --- | --- |
| milk keywords (`milk`, `oat milk`, `soy/soya milk`, `almond milk`, `oat drink`) | **Milk** | plant-based milk |
| dairy-style (`cheese`, `yogurt`/`yoghurt`, `butter`, `cream`, `tofu`) | **Chilled** | plant-based |
| meat keywords (`sausages`, `bacon`, `mince`, `chicken pieces`, `burgers`, `ham`) | **Fake Meat** | plant-based substitute |
| egg / fish / clearly animal-derived, or no match | **Uncategorised** | manual review — never guessed |

Matching is **whole-word** (case-insensitive), so `ham` does not match "graham crackers"
and `tea` does not match "steak". Categorisation is best-effort on text alone; ambiguous
items go to **Uncategorised** rather than being mis-assigned. Correct any item from the card
(or the `recategorise_item` service) and the choice is remembered for future identical items.

## Shop preference

Each item resolves to exactly one shop, or the always-present **No Preference** default.
Default shops are **Aldi, Asda, Tesco** with starter keyword rules (e.g. `nappies`/`milk` →
Aldi, clothing → Asda). Resolution precedence, highest to lowest:

1. **Shop name in the item text** (e.g. "tesco nappies" → Tesco) — beats everything.
2. **Learned assignment** (you previously assigned this exact item a shop).
3. **Shop keyword rule**.
4. **No Preference** (never guessed).

Manage shops from the card or via the shop services. Deleting a shop reassigns its items to
**No Preference** — items are never deleted.

## Services

All services are config-entry-scoped (optional `entry_id` when you have more than one entry):

| Service | Purpose |
| --- | --- |
| `recategorise_item` | Learn a category for an item's text (Uncategorised clears it) |
| `add_category` / `edit_category` / `delete_category` | Manage categories (delete → items to Uncategorised) |
| `assign_shop` | Learn a shop for an item's text (No Preference clears it) |
| `add_shop` / `edit_shop` / `delete_shop` | Manage shops (delete → items to No Preference) |
| `reload_maps` | Reload the stored categories and shops from disk |

## Privacy & security

- No Amazon credentials are stored here; authentication belongs to Alexa Devices.
- No outbound network calls of the integration's own; all I/O is local HA services.
- Shopping-list item text is personal data and is **redacted in diagnostics by default**.

## Troubleshooting

- **"No Alexa lists found":** set up the core Alexa Devices integration first.
- **Sensor unavailable / repair issue:** the source `todo` entity is missing or offline;
  check Alexa Devices. The view recovers automatically when the source returns.
- **Card not updating instantly:** a missed Alexa push can lag until the upstream ~5-minute
  poll; a manual entity refresh short-circuits it.

## Development

```bash
# Backend
python -m venv .venv && .venv/bin/pip install homeassistant pytest-homeassistant-custom-component ruff mypy
.venv/bin/ruff check custom_components tests && .venv/bin/ruff format --check custom_components tests
.venv/bin/mypy custom_components/alexa_shopping_categoriser
.venv/bin/python -m pytest tests/

# Card
cd frontend/alexa-shopping-categoriser-card && npm ci && npm test && npm run build
```

See `docs/plans/` for the full technical design.
