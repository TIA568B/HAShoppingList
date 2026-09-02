"""Service tests: category + shop CRUD, learning, delete-reassign, rename-migrate."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import (
    ATTR_CATEGORY,
    ATTR_ITEM_TEXT,
    ATTR_KEYWORDS,
    ATTR_NAME,
    ATTR_NEW_NAME,
    ATTR_SHOP,
    DOMAIN,
    NO_PREFERENCE,
    SERVICE_ADD_CATEGORY,
    SERVICE_ADD_SHOP,
    SERVICE_ASSIGN_SHOP,
    SERVICE_DELETE_CATEGORY,
    SERVICE_DELETE_SHOP,
    SERVICE_EDIT_CATEGORY,
    SERVICE_EDIT_SHOP,
    SERVICE_RECATEGORISE_ITEM,
    UNCATEGORISED,
)
from tests.helpers import SourceListMock, make_items, set_source_state


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry]:
    """Set up a loaded entry with a small source list and keep get_items patched."""
    set_source_state(hass)
    src = SourceListMock(
        make_items(
            ("u1", "oat milk", False),
            ("u2", "birthday candles", False),
        )
    )
    with src:
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        yield mock_config_entry


def _map(entry: MockConfigEntry):  # type: ignore[no-untyped-def]
    return entry.runtime_data.store.category_map


async def _call(hass: HomeAssistant, service: str, data: dict) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)
    await hass.async_block_till_done()


# --- category services ----------------------------------------------------


async def test_recategorise_item_learns(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    await _call(
        hass,
        SERVICE_RECATEGORISE_ITEM,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_CATEGORY: "Household"},
    )
    assert _map(loaded_entry).overrides["birthday candles"] == "Household"


async def test_recategorise_uncategorised_clears(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(
        hass,
        SERVICE_RECATEGORISE_ITEM,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_CATEGORY: "Household"},
    )
    await _call(
        hass,
        SERVICE_RECATEGORISE_ITEM,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_CATEGORY: UNCATEGORISED},
    )
    assert "birthday candles" not in _map(loaded_entry).overrides


async def test_recategorise_unknown_category_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            SERVICE_RECATEGORISE_ITEM,
            {ATTR_ITEM_TEXT: "oat milk", ATTR_CATEGORY: "Nonexistent"},
        )


async def test_add_category_and_duplicate(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(hass, SERVICE_ADD_CATEGORY, {ATTR_NAME: "Snacks", ATTR_KEYWORDS: ["crisps"]})
    assert any(c.name == "Snacks" for c in _map(loaded_entry).categories)
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ADD_CATEGORY, {ATTR_NAME: "snacks"})  # case-insensitive dup


async def test_edit_category_rename_migrates_overrides(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(
        hass,
        SERVICE_RECATEGORISE_ITEM,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_CATEGORY: "Household"},
    )
    await _call(
        hass,
        SERVICE_EDIT_CATEGORY,
        {ATTR_NAME: "Household", ATTR_NEW_NAME: "Home"},
    )
    cmap = _map(loaded_entry)
    assert any(c.name == "Home" for c in cmap.categories)
    assert not any(c.name == "Household" for c in cmap.categories)
    # Learned override migrated to the new name.
    assert cmap.overrides["birthday candles"] == "Home"


async def test_delete_category_reassigns_not_deletes_items(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    # oat milk is in Milk; delete Milk -> item falls to Uncategorised, still present.
    await _call(hass, SERVICE_DELETE_CATEGORY, {ATTR_NAME: "Milk"})
    cmap = _map(loaded_entry)
    assert not any(c.name == "Milk" for c in cmap.categories)
    coord = loaded_entry.runtime_data.coordinator
    # The oat milk item still appears (now Uncategorised), so nothing was deleted.
    all_items = [
        item
        for shop in coord.data["shop_groups"]
        for cat in shop["categories"]
        for item in cat["items"]
    ]
    assert any(i["name"] == "oat milk" for i in all_items)
    assert any(i["category"] == UNCATEGORISED for i in all_items)


# --- shop services --------------------------------------------------------


async def test_assign_shop_learns_and_clears(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(hass, SERVICE_ASSIGN_SHOP, {ATTR_ITEM_TEXT: "birthday candles", ATTR_SHOP: "Tesco"})
    assert _map(loaded_entry).shop_overrides["birthday candles"] == "Tesco"
    # No Preference clears it.
    await _call(
        hass,
        SERVICE_ASSIGN_SHOP,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_SHOP: NO_PREFERENCE},
    )
    assert "birthday candles" not in _map(loaded_entry).shop_overrides


async def test_assign_unknown_shop_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ASSIGN_SHOP, {ATTR_ITEM_TEXT: "oat milk", ATTR_SHOP: "Nowhere"})


async def test_add_shop_reserved_and_duplicate(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ADD_SHOP, {ATTR_NAME: NO_PREFERENCE})
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ADD_SHOP, {ATTR_NAME: "aldi"})  # case-insensitive dup


async def test_add_shop_with_keywords(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    await _call(hass, SERVICE_ADD_SHOP, {ATTR_NAME: "Lidl", ATTR_KEYWORDS: ["bratwurst"]})
    shop = next(s for s in _map(loaded_entry).shops if s.name == "Lidl")
    assert shop.keywords == ["bratwurst"]


async def test_edit_shop_rename_migrates_shop_overrides(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(hass, SERVICE_ASSIGN_SHOP, {ATTR_ITEM_TEXT: "oat milk", ATTR_SHOP: "Tesco"})
    await _call(hass, SERVICE_EDIT_SHOP, {ATTR_NAME: "Tesco", ATTR_NEW_NAME: "Tesco Extra"})
    cmap = _map(loaded_entry)
    assert any(s.name == "Tesco Extra" for s in cmap.shops)
    assert cmap.shop_overrides["oat milk"] == "Tesco Extra"


async def test_delete_shop_reassigns_not_deletes_items(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    # oat milk resolves to Aldi via keyword; delete Aldi -> No Preference, item kept.
    await _call(hass, SERVICE_DELETE_SHOP, {ATTR_NAME: "Aldi"})
    cmap = _map(loaded_entry)
    assert not any(s.name == "Aldi" for s in cmap.shops)
    coord = loaded_entry.runtime_data.coordinator
    all_items = [
        item
        for shop in coord.data["shop_groups"]
        for cat in shop["categories"]
        for item in cat["items"]
    ]
    oat = next(i for i in all_items if i["name"] == "oat milk")
    assert oat["shop"] == NO_PREFERENCE


async def test_delete_no_preference_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_DELETE_SHOP, {ATTR_NAME: NO_PREFERENCE})


async def test_add_shop_dictionary_word_warns_not_blocks(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, caplog
) -> None:
    await _call(hass, SERVICE_ADD_SHOP, {ATTR_NAME: "Fresh"})
    assert any(s.name == "Fresh" for s in _map(loaded_entry).shops)
    assert "common word" in caplog.text.lower()


# --- validation + remaining branches --------------------------------------


@pytest.mark.parametrize(
    "bad_name",
    ["", "   ", "x" * 100, "bad\x01name"],
)
async def test_add_category_invalid_names_raise(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, bad_name: str
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ADD_CATEGORY, {ATTR_NAME: bad_name})


async def test_add_category_reserved_uncategorised_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ADD_CATEGORY, {ATTR_NAME: UNCATEGORISED})


async def test_edit_category_keywords_only(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    await _call(
        hass,
        SERVICE_EDIT_CATEGORY,
        {ATTR_NAME: "Milk", ATTR_KEYWORDS: ["milk", "kefir"]},
    )
    milk = next(c for c in _map(loaded_entry).categories if c.name == "Milk")
    assert "kefir" in milk.keywords


async def test_edit_category_unknown_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_EDIT_CATEGORY, {ATTR_NAME: "Ghost", ATTR_NEW_NAME: "X"})


async def test_edit_category_rename_to_existing_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_EDIT_CATEGORY, {ATTR_NAME: "Milk", ATTR_NEW_NAME: "Chilled"})


async def test_delete_category_unknown_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_DELETE_CATEGORY, {ATTR_NAME: "Ghost"})


async def test_edit_shop_keywords_only(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    await _call(hass, SERVICE_EDIT_SHOP, {ATTR_NAME: "Tesco", ATTR_KEYWORDS: ["fish"]})
    tesco = next(s for s in _map(loaded_entry).shops if s.name == "Tesco")
    assert tesco.keywords == ["fish"]


async def test_edit_shop_rename_to_reserved_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_EDIT_SHOP, {ATTR_NAME: "Tesco", ATTR_NEW_NAME: NO_PREFERENCE})


async def test_edit_shop_unknown_raises(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_EDIT_SHOP, {ATTR_NAME: "Ghost", ATTR_NEW_NAME: "X"})


async def test_delete_shop_unknown_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_DELETE_SHOP, {ATTR_NAME: "Ghost"})


async def test_reload_maps(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    from custom_components.alexa_shopping_categoriser.const import SERVICE_RELOAD_MAPS

    # Should not raise and should keep the map loaded.
    await _call(hass, SERVICE_RELOAD_MAPS, {})
    assert _map(loaded_entry).categories


async def test_recategorise_empty_item_text_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_RECATEGORISE_ITEM, {ATTR_ITEM_TEXT: "  ", ATTR_CATEGORY: "Milk"})


async def test_unknown_entry_id_raises(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    from custom_components.alexa_shopping_categoriser.const import ATTR_ENTRY_ID

    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            SERVICE_ADD_CATEGORY,
            {ATTR_ENTRY_ID: "does-not-exist", ATTR_NAME: "X"},
        )


async def test_apply_to_uid_moves_item_now(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    from custom_components.alexa_shopping_categoriser.const import ATTR_APPLY_TO_UID

    await _call(
        hass,
        SERVICE_RECATEGORISE_ITEM,
        {
            ATTR_ITEM_TEXT: "birthday candles",
            ATTR_CATEGORY: "Household",
            ATTR_APPLY_TO_UID: "u2",
        },
    )
    coord = loaded_entry.runtime_data.coordinator
    all_items = [
        item
        for shop in coord.data["shop_groups"]
        for cat in shop["categories"]
        for item in cat["items"]
    ]
    candles = next(i for i in all_items if i["uid"] == "u2")
    assert candles["category"] == "Household"


async def test_assign_shop_apply_to_uid(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    from custom_components.alexa_shopping_categoriser.const import ATTR_APPLY_TO_UID

    await _call(
        hass,
        SERVICE_ASSIGN_SHOP,
        {ATTR_ITEM_TEXT: "birthday candles", ATTR_SHOP: "Tesco", ATTR_APPLY_TO_UID: "u2"},
    )
    coord = loaded_entry.runtime_data.coordinator
    all_items = [
        item
        for shop in coord.data["shop_groups"]
        for cat in shop["categories"]
        for item in cat["items"]
    ]
    candles = next(i for i in all_items if i["uid"] == "u2")
    assert candles["shop"] == "Tesco"


async def test_assign_shop_empty_item_text_raises(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_ASSIGN_SHOP, {ATTR_ITEM_TEXT: "  ", ATTR_SHOP: "Tesco"})


async def test_no_loaded_entries_raises(hass: HomeAssistant) -> None:
    # No config entry set up at all -> resolver raises.
    with pytest.raises(ServiceValidationError):
        await _resolve_coordinator_directly(hass)


async def _resolve_coordinator_directly(hass: HomeAssistant) -> None:
    from types import SimpleNamespace

    from custom_components.alexa_shopping_categoriser.services import _resolve_coordinator

    _resolve_coordinator(hass, SimpleNamespace(data={}))  # type: ignore[arg-type]
