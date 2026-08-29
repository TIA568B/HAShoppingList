"""Redacted diagnostics for a config entry.

Item text is personal data; it is redacted by default (option
``redact_items_in_diagnostics``). This integration owns no credentials, so there is no
credential redaction set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_REDACT_ITEMS_IN_DIAGNOSTICS, DEFAULT_REDACT_ITEMS_IN_DIAGNOSTICS

if TYPE_CHECKING:
    from . import AlexaShoppingConfigEntry

# Keys within item objects that carry personal data.
_ITEM_TEXT_KEYS = {"name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AlexaShoppingConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for the config entry."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    category_map = runtime.store.category_map
    projection = coordinator.data

    redact_items = entry.options.get(
        CONF_REDACT_ITEMS_IN_DIAGNOSTICS, DEFAULT_REDACT_ITEMS_IN_DIAGNOSTICS
    )

    shop_groups: list[dict[str, Any]] = []
    if projection is not None:
        for shop in projection["shop_groups"]:
            categories = []
            for cat in shop["categories"]:
                items = cat["items"]
                if redact_items:
                    items = [async_redact_data(item, _ITEM_TEXT_KEYS) for item in items]
                categories.append(
                    {
                        "name": cat["name"],
                        "collapsed": cat["collapsed"],
                        "item_count": len(cat["items"]),
                        "items": items,
                    }
                )
            shop_groups.append(
                {
                    "name": shop["name"],
                    "collapsed": shop["collapsed"],
                    "categories": categories,
                }
            )

    return {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
            "source_entity_id": coordinator.source_entity_id,
        },
        "map_summary": {
            "schema_version": category_map.schema_version,
            "category_count": len(category_map.categories),
            "shop_count": len(category_map.shops),
            "override_count": len(category_map.overrides),
            "shop_override_count": len(category_map.shop_overrides),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_synced": projection["last_synced"] if projection else None,
            "total_unchecked": projection["total_unchecked"] if projection else None,
            "uncategorised_count": projection["uncategorised_count"] if projection else None,
        },
        "shop_groups": shop_groups,
    }
