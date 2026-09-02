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
    assert shop_names == {
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
    }
    assert NO_PREFERENCE not in shop_names  # implicit, not stored
    assert category_map.overrides == {}
    assert category_map.shop_overrides == {}


async def test_v1_store_reseeds_categories_and_shops_but_keeps_overrides(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    # A pre-feature (schema_version 1) store with a stale "Produce" category and learned
    # overrides. The 0.4.0 v1->v2 migration re-seeds categories/shops from default_map.json
    # (replace) while preserving learned corrections (decision OQ-A).
    hass_storage["alexa_shopping_categoriser.entry2"] = {
        "version": 1,
        "data": {
            "schema_version": 1,
            "categories": [{"name": "Produce", "keywords": ["apple"]}],
            "overrides": {"birthday candles": "Household"},
            "shops": [{"name": "OldShop", "keywords": []}],
            "shop_overrides": {"oat milk": "Aldi"},
        },
    }
    store = CategoryStore(hass, "entry2")
    category_map = await store.async_load()

    # Categories/shops replaced by the shipped defaults (Produce/OldShop gone).
    cat_names = [c.name for c in category_map.categories]
    assert "Produce" not in cat_names
    assert "Fruit & Veg" in cat_names and "Sauces" in cat_names
    assert {s.name for s in category_map.shops} == {
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
    }
    # Learned overrides preserved verbatim.
    assert category_map.overrides == {"birthday candles": "Household"}
    assert category_map.shop_overrides == {"oat milk": "Aldi"}
    assert category_map.schema_version == STORE_SCHEMA_VERSION
    assert category_map.seed_version >= 1


async def test_v1_migration_is_idempotent(hass: HomeAssistant, hass_storage: dict) -> None:
    hass_storage["alexa_shopping_categoriser.entry_idem"] = {
        "version": 1,
        "data": {
            "schema_version": 1,
            "categories": [{"name": "Produce", "keywords": ["apple"]}],
            "overrides": {},
        },
    }
    store = CategoryStore(hass, "entry_idem")
    first = await store.async_load()
    first_names = [c.name for c in first.categories]

    # Reload from the now-migrated store: no further change.
    store2 = CategoryStore(hass, "entry_idem")
    second = await store2.async_load()
    assert [c.name for c in second.categories] == first_names
    assert second.schema_version == STORE_SCHEMA_VERSION


async def test_fresh_install_records_seed_version(hass: HomeAssistant) -> None:
    store = CategoryStore(hass, "entry_fresh")
    category_map = await store.async_load()
    assert category_map.seed_version >= 1
    assert category_map.schema_version == STORE_SCHEMA_VERSION


async def test_reload_defaults_replaces_and_keeps_overrides(hass: HomeAssistant) -> None:
    store = CategoryStore(hass, "entry_reload")
    category_map = await store.async_load()
    # Simulate user edits: add a custom category + learned override.
    from custom_components.alexa_shopping_categoriser.models import Category

    category_map.categories.append(Category(name="MyCustom", keywords=["widget"]))
    category_map.overrides["widget"] = "MyCustom"
    await store.async_replace(category_map)

    reseeded = await store.async_reload_defaults()
    # Custom category gone (replaced by defaults); override preserved (self-heals later).
    assert not any(c.name == "MyCustom" for c in reseeded.categories)
    assert reseeded.overrides == {"widget": "MyCustom"}
    assert any(c.name == "Fruit & Veg" for c in reseeded.categories)


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
