# 13 — Project Structure & Dependencies

## Directory layout

```
hashoppinglist/
├── custom_components/
│   └── alexa_shopping_categorizer/
│       ├── __init__.py            # setup/unload/reload, runtime_data, listener wiring
│       ├── manifest.json          # domain, deps=[todo], version, iot_class=calculated
│       ├── const.py               # DOMAIN, service names, attr keys, storage keys, defaults
│       ├── config_flow.py         # config + options flow
│       ├── coordinator.py         # DataUpdateCoordinator; get_items; builds projection
│       ├── categorizer.py         # PURE: normalize + match + vegan rules (no HA import)
│       ├── store.py               # HA Store wrapper for CategoryMap + overrides + migration
│       ├── models.py              # dataclasses (SourceItem, CategorizedItem, Category, ...)
│       ├── sensor.py              # the categorized sensor entity
│       ├── services.py            # service registration + voluptuous schemas + handlers
│       ├── diagnostics.py         # redacted diagnostics
│       ├── services.yaml          # service field metadata
│       ├── strings.json           # config/options/services UI strings
│       └── translations/
│           └── en.json
├── frontend/
│   └── alexa-shopping-categorizer-card/
│       ├── src/                   # card source (TS/JS)
│       ├── dist/                  # built asset served by the integration
│       └── package.json
├── tests/
│   ├── conftest.py
│   ├── test_categorizer.py        # 100% target
│   ├── test_config_flow.py
│   ├── test_options_flow.py
│   ├── test_coordinator.py
│   ├── test_sensor.py
│   ├── test_services.py
│   ├── test_sync.py
│   ├── test_diagnostics.py
│   └── test_migration.py
├── docs/
│   ├── specs/                     # original (unchanged) requirements/design/tasks
│   └── plans/                     # THIS design (split into digestible files)
├── hacs.json                      # HACS metadata
├── README.md
├── CHANGELOG.md
├── pyproject.toml                 # ruff + mypy + pytest config, dev deps
└── .gitignore
```

## Major file responsibilities

| File | Responsibility | Depends on |
|------|----------------|------------|
| `__init__.py` | Entry setup/unload/reload; wire store→coordinator→sensor→services; state listener | coordinator, store, services |
| `const.py` | Single home for all identifiers/defaults | — |
| `config_flow.py` | Select source entity; options (grace, toggles) | HA config entries, const |
| `coordinator.py` | Read source items; call categorizer; hold projection | categorizer, store, models |
| `categorizer.py` | Pure categorization pipeline + vegan rules | models only |
| `store.py` | Persist/load/migrate CategoryMap + overrides | HA Store, models |
| `models.py` | Shared dataclasses/types | — |
| `sensor.py` | Expose projection as attributes; availability | coordinator |
| `services.py` | Category maintenance + learning services | store, coordinator, const |
| `diagnostics.py` | Redacted dump | coordinator, const |
| `frontend/**` | Card UI + interactions | sensor attrs + services (contract in doc 06) |

## Dependencies

### Python / runtime
- **Home Assistant 2026.8** (host). No pinned HA in `requirements` — it is the platform.
- **`todo`** building block — declared in `manifest.json` `dependencies`.
- **stdlib only** for the integration (`difflib` if/when fuzzy matching is added). No
  third-party runtime requirement in v1 — keeps `manifest.json` `requirements: []`.

### Development
- `pytest`, `pytest-homeassistant-custom-component` — HA test harness.
- `ruff` — lint + format.
- `mypy` — strict typing.
- (Frontend) a JS toolchain (e.g. `rollup`/`vite` + a JS test runner) to build/test the card.

### External services
- **Amazon Alexa** — only transitively, through `alexa_devices`. This integration opens no
  external connections.

### Distribution
- `hacs.json` for HACS custom-repository install; `version` in `manifest.json`.

Rationale: minimal dependencies reduce supply-chain risk (security steering) and keep the
integration easy to maintain and certify.
