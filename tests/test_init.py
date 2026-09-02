"""Setup / unload lifecycle tests."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import (
    DOMAIN,
    SERVICE_ADD_CATEGORY,
    SERVICE_RELOAD_MAPS,
)
from tests.helpers import set_source_state


async def test_setup_and_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_list: object,
) -> None:
    set_source_state(hass)
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    # Services registered.
    assert hass.services.has_service(DOMAIN, SERVICE_ADD_CATEGORY)
    assert hass.services.has_service(DOMAIN, SERVICE_RELOAD_MAPS)

    # Exactly one sensor entity created for this integration.
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, mock_config_entry.entry_id)
    sensors = [e for e in entities if e.domain == "sensor"]
    assert len(sensors) == 1
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None
    assert state.state == "1"  # one unchecked item

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    # Services deregistered when last entry unloads.
    assert not hass.services.has_service(DOMAIN, SERVICE_ADD_CATEGORY)


async def test_setup_retry_when_source_absent(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_list: object,
) -> None:
    # No source state registered -> first refresh is not-ready and HA retries setup.
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
