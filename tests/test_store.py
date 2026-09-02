"""Tests for the CategoryStore: defaults, defensive load, migration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.alexa_shopping_categoriser.const import (
    NO_PREFERENCE,
    STORE_SCHEMA_VERSION,
)
from custom_components.alexa_shopping_categoriser.store import CategoryStore


async def test_load_seeds_defaults(hass: HomeAssistant) -> None:
    store = CategoryStore(hass, "entry1")
    category_map = await store.async_load()

    assert category_map.schema_version == STORE_SCHEMA_VERSION
    assert any(c.name == "Milk" for c in category_map.categories)
    assert any(c.name == "Fake Meat" for c in category_map.categories)
    shop_names = {s.name for s in category_map.shops}
    assert shop_names == {"Aldi", "Asda", "Tesco", "Waitrose", "Morrisons", "Lidl", "Sainsburys"}
    assert NO_PREFERENCE not in shop_names  # implicit, not stored
    assert category_map.overrides == {}
    assert category_map.shop_overrides == {}


async def test_partial_store_missing_shop_keys_gets_defaults(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    # Simulate an older/partial store lacking shop fields.
    hass_storage["alexa_shopping_categoriser.entry2"] = {
        "version": 1,
        "data": {
            "schema_version": 1,
            "categories": [{"name": "Produce", "keywords": ["apple"]}],
            "overrides": {"apple": "Produce"},
        },
    }
    store = CategoryStore(hass, "entry2")
    category_map = await store.async_load()

    assert [c.name for c in category_map.categories] == ["Produce"]
    assert category_map.overrides == {"apple": "Produce"}
    # Missing keys injected from defaults.
    assert {s.name for s in category_map.shops} == {
        "Aldi",
        "Asda",
        "Tesco",
        "Waitrose",
        "Morrisons",
        "Lidl",
        "Sainsburys",
    }
    assert category_map.shop_overrides == {}


async def test_save_and_reload_roundtrip(hass: HomeAssistant) -> None:
    store = CategoryStore(hass, "entry3")
    category_map = await store.async_load()
    category_map.overrides["oat milk"] = "Milk"
    category_map.shop_overrides["oat milk"] = "Aldi"
    await store.async_replace(category_map)

    store2 = CategoryStore(hass, "entry3")
    reloaded = await store2.async_load()
    assert reloaded.overrides == {"oat milk": "Milk"}
    assert reloaded.shop_overrides == {"oat milk": "Aldi"}
