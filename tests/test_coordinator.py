"""Coordinator tests: projection build, recompute, availability, envelope mapping."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.coordinator import (
    AlexaShoppingCoordinator,
)
from custom_components.alexa_shopping_categoriser.store import CategoryStore
from tests.conftest import SOURCE_ENTITY_ID
from tests.helpers import SourceListMock, make_items, set_source_state


async def _make_coordinator(
    hass: HomeAssistant, entry: MockConfigEntry
) -> AlexaShoppingCoordinator:
    entry.add_to_hass(hass)
    store = CategoryStore(hass, entry.entry_id)
    await store.async_load()
    return AlexaShoppingCoordinator(hass, entry, store)


async def test_build_projection_active_and_completed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    items = make_items(
        ("u1", "oat milk", False),
        ("u2", "cheddar cheese", False),
        ("u3", "bought bread", True),  # completed -> not counted, hidden by default
    )
    with SourceListMock(items):
        coord = await _make_coordinator(hass, mock_config_entry)
        projection = await coord._async_update_data()

    assert projection["attributes_version"] == 3
    assert projection["total_unchecked"] == 2
    # oat milk -> Aldi/Milk ; cheddar cheese -> No Preference/Chilled
    shop_names = [g["name"] for g in projection["shop_groups"]]
    assert "Aldi" in shop_names
    assert shop_names[-1] == "No Preference"  # always last


async def test_source_unavailable_first_refresh_raises_not_ready(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass, state="unavailable")
    with SourceListMock(make_items(("u1", "oat milk", False))):
        coord = await _make_coordinator(hass, mock_config_entry)
        with pytest.raises(ConfigEntryNotReady):
            await coord._async_update_data()


async def test_source_unavailable_after_data_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    with SourceListMock(make_items(("u1", "oat milk", False))):
        coord = await _make_coordinator(hass, mock_config_entry)
        await coord.async_refresh()
        assert coord.data is not None
        # Now the source goes unavailable at runtime.
        set_source_state(hass, state="unavailable")
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()


async def test_malformed_envelope_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    entry = mock_config_entry
    entry.add_to_hass(hass)
    store = CategoryStore(hass, entry.entry_id)
    await store.async_load()
    coord = AlexaShoppingCoordinator(hass, entry, store)

    from unittest.mock import patch

    from homeassistant.core import ServiceRegistry

    async def _bad_call(registry, domain, service, *args, **kwargs):  # type: ignore[no-untyped-def]
        if domain == "todo" and service == "get_items":
            return {"wrong_entity": {"items": []}}
        return None

    with (
        patch.object(ServiceRegistry, "async_call", _bad_call),
        pytest.raises(UpdateFailed),
    ):
        await coord._async_update_data()


async def test_skips_malformed_items(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    items = [
        {"uid": "u1", "summary": "oat milk", "status": "needs_action"},
        {"uid": "u2"},  # missing summary -> skipped
        {"summary": "no uid"},  # missing uid -> skipped
        "not a dict",  # skipped
    ]
    with SourceListMock(items):  # type: ignore[arg-type]
        coord = await _make_coordinator(hass, mock_config_entry)
        projection = await coord._async_update_data()
    assert projection["total_unchecked"] == 1


async def test_repair_issue_raised_and_cleared(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    from homeassistant.helpers import issue_registry as ir

    from custom_components.alexa_shopping_categoriser.const import (
        DOMAIN,
        ISSUE_SOURCE_MISSING,
    )

    set_source_state(hass)
    with SourceListMock(make_items(("u1", "oat milk", False))):
        coord = await _make_coordinator(hass, mock_config_entry)
        await coord.async_refresh()  # healthy: no issue
        registry = ir.async_get(hass)
        issue_id = f"{ISSUE_SOURCE_MISSING}_{mock_config_entry.entry_id}"
        assert registry.async_get_issue(DOMAIN, issue_id) is None

        # Source goes unavailable -> issue raised.
        set_source_state(hass, state="unavailable")
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
        assert registry.async_get_issue(DOMAIN, issue_id) is not None

        # Source recovers -> issue cleared.
        set_source_state(hass)
        await coord._async_update_data()
        assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_recompute_on_source_state_change(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coord = mock_config_entry.runtime_data.coordinator
        assert coord.data["total_unchecked"] == 1

        # Simulate an inbound change: add a second item and fire a state change.
        src.items.append({"uid": "u2", "summary": "carrots", "status": "needs_action"})
        hass.states.async_set(SOURCE_ENTITY_ID, "4", {"supported_features": 7})
        await hass.async_block_till_done()

        # Flush the request-refresh debouncer (0.5s cooldown).
        from datetime import timedelta

        from homeassistant.util import dt as dt_util
        from pytest_homeassistant_custom_component.common import async_fire_time_changed

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

        assert coord.data["total_unchecked"] == 2
