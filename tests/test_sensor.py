"""Sensor tests: attribute contract shape, state value, availability."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import ATTRIBUTES_VERSION
from tests.conftest import SOURCE_ENTITY_ID
from tests.helpers import SourceListMock, make_items, set_source_state


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, src: SourceListMock) -> str:
    """Set up the entry with src active; caller keeps src active for the whole test."""
    set_source_state(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    sensors = [
        e
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if e.domain == "sensor"
    ]
    return sensors[0].entity_id


async def test_sensor_attribute_contract(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    src = SourceListMock(
        make_items(
            ("u1", "oat milk", False),
            ("u2", "carrots", False),
            ("u3", "jeans", False),
        )
    )
    with src:
        entity_id = await _setup(hass, mock_config_entry, src)
        state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "3"

    attrs = state.attributes
    # Top-level contract keys (attributes_version 3).
    assert attrs["attributes_version"] == ATTRIBUTES_VERSION
    assert attrs["source_entity_id"] == SOURCE_ENTITY_ID
    assert attrs["total_unchecked"] == 3
    assert "last_synced" in attrs
    assert set(attrs["options"]) == {
        "grace_period_seconds",
        "show_completed",
        "collapse_empty_categories",
    }
    # Definition lists for the settings panels.
    cat_names = [c["name"] for c in attrs["category_definitions"]]
    assert "Milk" in cat_names and "Fake Meat" in cat_names
    shop_names = [s["name"] for s in attrs["shop_definitions"]]
    assert shop_names == [
        "Aldi",
        "Asda",
        "Tesco",
        "Waitrose",
        "Morrisons",
        "Lidl",
        "Sainsburys",
        "Co-op",
        "Marks & Spencer",
        "Home Bargains",
    ]
    assert "No Preference" not in shop_names  # implicit

    # shop_groups: shop-primary then category, with the documented item shape.
    groups = attrs["shop_groups"]
    assert groups[-1]["name"] == "No Preference"  # always last
    aldi = next(g for g in groups if g["name"] == "Aldi")
    milk_cat = next(c for c in aldi["categories"] if c["name"] == "Milk")
    item = milk_cat["items"][0]
    assert set(item) == {"uid", "name", "checked", "shop", "category"}
    assert item["shop"] == "Aldi"
    assert item["category"] == "Milk"

    # jeans -> Asda / Uncategorised (no category keyword); carrots -> No Preference / Fruit & Veg
    asda = next(g for g in groups if g["name"] == "Asda")
    assert any(c["name"] == "Uncategorised" for c in asda["categories"])


async def test_sensor_unavailable_when_source_unavailable(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        entity_id = await _setup(hass, mock_config_entry, src)
        assert hass.states.get(entity_id).state == "1"

        # Source goes unavailable -> coordinator refresh fails -> sensor unavailable.
        hass.states.async_set(SOURCE_ENTITY_ID, "unavailable", {"supported_features": 7})
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
        await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "unavailable"
