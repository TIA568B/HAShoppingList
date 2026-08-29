"""The Alexa Shopping List Categoriser integration.

Presents an Alexa-synced `todo` shopping list as a shop-primary, category-secondary
projection, learning categories and shop preferences over time. It owns no credentials
and makes no outbound network calls; all reads/writes go through the public `todo.*`
services on the source entity.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SOURCE_ENTITY_ID, CONFIG_ENTRY_VERSION, DOMAIN
from .coordinator import AlexaShoppingCoordinator
from .runtime import AlexaShoppingRuntimeData
from .services import async_register_services, async_unregister_services
from .store import CategoryStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type AlexaShoppingConfigEntry = ConfigEntry[AlexaShoppingRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: AlexaShoppingConfigEntry) -> bool:
    """Set up Alexa Shopping List Categoriser from a config entry."""
    source_entity_id: str = entry.data[CONF_SOURCE_ENTITY_ID]

    store = CategoryStore(hass, entry.entry_id)
    await store.async_load()

    coordinator = AlexaShoppingCoordinator(hass, entry, store)
    await coordinator.async_config_entry_first_refresh()

    unsub_state = coordinator.async_subscribe_source_changes()

    entry.runtime_data = AlexaShoppingRuntimeData(
        coordinator=coordinator,
        store=store,
        unsub_state=unsub_state,
    )

    async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.debug("Set up entry for source %s", source_entity_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AlexaShoppingConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        runtime = entry.runtime_data
        runtime.unsub_state()

    # Deregister services if this was the last entry.
    remaining = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id and e.state.recoverable
    ]
    if not remaining:
        async_unregister_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: AlexaShoppingConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry.

    v1 is the initial shipped config-entry version. Future schema bumps add ordered
    migrators here. The stored data schema is versioned independently in the Store.
    """
    # Downgrade (a higher stored version than we support) is not supported.
    return entry.version <= CONFIG_ENTRY_VERSION
