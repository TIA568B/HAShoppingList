"""Constants for the Alexa Shopping List Categoriser integration.

Single home for all identifiers and defaults. No magic strings for the domain,
service names, attribute keys, or storage keys elsewhere in the codebase.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "alexa_shopping_categoriser"

# --- Config entry ---------------------------------------------------------
CONF_SOURCE_ENTITY_ID: Final = "source_entity_id"

# Options (see docs/plans/04)
CONF_GRACE_PERIOD_SECONDS: Final = "grace_period_seconds"
CONF_SHOW_COMPLETED: Final = "show_completed"
CONF_COLLAPSE_EMPTY_CATEGORIES: Final = "collapse_empty_categories"
CONF_REDACT_ITEMS_IN_DIAGNOSTICS: Final = "redact_items_in_diagnostics"

GRACE_PERIOD_MIN: Final = 8
GRACE_PERIOD_MAX: Final = 30
DEFAULT_GRACE_PERIOD_SECONDS: Final = 9
DEFAULT_SHOW_COMPLETED: Final = False
DEFAULT_COLLAPSE_EMPTY_CATEGORIES: Final = True
DEFAULT_REDACT_ITEMS_IN_DIAGNOSTICS: Final = True

# --- Config-entry / store schema versions ---------------------------------
# These two counters version different things and move independently.
CONFIG_ENTRY_VERSION: Final = 1
# Bumped 1 -> 2 for the 0.4.0 one-time re-seed migration (categories/shops re-seeded from
# the shipped default_map.json; learned overrides preserved). See
# docs/plans/feature-map-management/03-migration-and-reload.md.
STORE_SCHEMA_VERSION: Final = 2
# The frontend/sensor attribute contract version (docs/plans/06).
ATTRIBUTES_VERSION: Final = 3

# --- Storage --------------------------------------------------------------
# Per config entry: alexa_shopping_categoriser.<entry_id>
STORAGE_KEY_PREFIX: Final = DOMAIN
STORAGE_VERSION: Final = 1

# --- Coordinator ----------------------------------------------------------
# Safety-net poll; the real trigger is source state_changed.
SAFETY_POLL_MINUTES: Final = 15
DEBOUNCE_SECONDS: Final = 0.5

# --- Categorisation / shops -----------------------------------------------
UNCATEGORISED: Final = "Uncategorised"
NO_PREFERENCE: Final = "No Preference"

# --- Sensor attribute keys (frontend contract, docs/plans/06) -------------
ATTR_ATTRIBUTES_VERSION: Final = "attributes_version"
ATTR_SOURCE_ENTITY_ID: Final = "source_entity_id"
ATTR_LAST_SYNCED: Final = "last_synced"
ATTR_TOTAL_UNCHECKED: Final = "total_unchecked"
ATTR_UNCATEGORISED_COUNT: Final = "uncategorised_count"
ATTR_OPTIONS: Final = "options"
ATTR_CATEGORY_DEFINITIONS: Final = "category_definitions"
ATTR_SHOP_DEFINITIONS: Final = "shop_definitions"
ATTR_SHOP_GROUPS: Final = "shop_groups"

# --- Service names --------------------------------------------------------
SERVICE_RECATEGORISE_ITEM: Final = "recategorise_item"
SERVICE_ADD_CATEGORY: Final = "add_category"
SERVICE_EDIT_CATEGORY: Final = "edit_category"
SERVICE_DELETE_CATEGORY: Final = "delete_category"
SERVICE_ASSIGN_SHOP: Final = "assign_shop"
SERVICE_ADD_SHOP: Final = "add_shop"
SERVICE_EDIT_SHOP: Final = "edit_shop"
SERVICE_DELETE_SHOP: Final = "delete_shop"
SERVICE_RELOAD_MAPS: Final = "reload_maps"
SERVICE_RELOAD_DEFAULTS: Final = "reload_defaults"

# --- Service field names --------------------------------------------------
ATTR_ENTRY_ID: Final = "entry_id"
ATTR_ITEM_TEXT: Final = "item_text"
ATTR_CATEGORY: Final = "category"
ATTR_SHOP: Final = "shop"
ATTR_NAME: Final = "name"
ATTR_NEW_NAME: Final = "new_name"
ATTR_KEYWORDS: Final = "keywords"
ATTR_APPLY_TO_UID: Final = "apply_to_uid"

# --- Validation limits ----------------------------------------------------
MAX_NAME_LENGTH: Final = 64
MAX_KEYWORD_LENGTH: Final = 64

# --- Source todo platform we prefer ---------------------------------------
ALEXA_DEVICES_PLATFORM: Final = "alexa_devices"
TODO_DOMAIN: Final = "todo"

# --- Repair issues --------------------------------------------------------
ISSUE_SOURCE_MISSING: Final = "source_entity_missing"
