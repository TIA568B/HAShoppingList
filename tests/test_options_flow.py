"""Options-flow taxonomy management tests (menu-style, 0.5.0)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.helpers import SourceListMock, make_items, set_source_state


@pytest.fixture
async def loaded(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry]:
    set_source_state(hass)
    with SourceListMock(make_items(("u1", "oat milk", False))):
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        yield mock_config_entry


def _map(entry: MockConfigEntry):  # type: ignore[no-untyped-def]
    return entry.runtime_data.coordinator.store.category_map


async def _menu_to(hass: HomeAssistant, entry: MockConfigEntry, step: str, data: dict):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.options.async_configure(result["flow_id"], data)


async def test_init_is_a_menu(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {
        "display_options",
        "manage_categories",
        "manage_shops",
        "reload_defaults",
    }


async def test_add_category_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    # init -> manage_categories (select "add new") -> edit_category form
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_categories"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "__add_new__"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Snacks", "keywords": "crisps, nuts"}
    )
    # Returns to the menu after applying.
    assert result["type"] is FlowResultType.MENU
    cat = next(c for c in _map(loaded).categories if c.name == "Snacks")
    assert cat.keywords == ["crisps", "nuts"]


async def test_edit_category_rename_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_categories"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "Milk"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Dairy-free", "keywords": "milk, oat milk", "delete": False}
    )
    assert result["type"] is FlowResultType.MENU
    names = [c.name for c in _map(loaded).categories]
    assert "Dairy-free" in names and "Milk" not in names


async def test_delete_category_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_categories"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "Bakery"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Bakery", "keywords": "", "delete": True}
    )
    assert result["type"] is FlowResultType.MENU
    assert not any(c.name == "Bakery" for c in _map(loaded).categories)


async def test_add_duplicate_category_shows_error(
    hass: HomeAssistant, loaded: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_categories"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "__add_new__"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"name": "Milk", "keywords": ""},  # dup
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid"}


async def test_add_shop_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_shops"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "__add_new__"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Coop", "keywords": "bratwurst"}
    )
    assert result["type"] is FlowResultType.MENU
    assert any(s.name == "Coop" for s in _map(loaded).shops)


async def test_delete_shop_reassigns_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "manage_shops"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"selection": "Aldi"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Aldi", "keywords": "", "delete": True}
    )
    assert result["type"] is FlowResultType.MENU
    assert not any(s.name == "Aldi" for s in _map(loaded).shops)


async def test_reload_defaults_via_flow(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    from custom_components.alexa_shopping_categoriser.models import Category

    cmap = _map(loaded)
    cmap.categories.append(Category(name="Custom", keywords=["x"]))
    await loaded.runtime_data.coordinator.store.async_replace(cmap)

    result = await hass.config_entries.options.async_init(loaded.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "reload_defaults"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"confirm": True})
    assert result["type"] is FlowResultType.MENU
    assert not any(c.name == "Custom" for c in _map(loaded).categories)
    assert any(c.name == "Fruit & Veg" for c in _map(loaded).categories)
