"""Config flow, options flow, and reconfigure flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import (
    CONF_GRACE_PERIOD_SECONDS,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
)
from tests.conftest import SOURCE_ENTITY_ID
from tests.helpers import SourceListMock, make_items, register_source_entity, set_source_state


def _register_two_todo_entities(hass: HomeAssistant) -> None:
    """Register one alexa_devices todo list and one native shopping_list todo list."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="todo",
        platform="alexa_devices",
        unique_id="david_carson_shopping",
        suggested_object_id="david_carson_amazon_gmail_com_shopping_list",
    )
    registry.async_get_or_create(
        domain="todo",
        platform="shopping_list",
        unique_id="native_shopping",
        suggested_object_id="shopping_list",
    )


async def test_user_flow_selects_alexa_devices_platform(hass: HomeAssistant) -> None:
    # Regression (M-8): only alexa_devices-platform todo lists are offered, never the
    # native shopping_list platform entity.
    _register_two_todo_entities(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"].schema
    field = next(iter(schema.values()))
    choices = list(field.container)
    assert SOURCE_ENTITY_ID in choices
    assert "todo.shopping_list" not in choices  # native list never offered

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SOURCE_ENTITY_ID: SOURCE_ENTITY_ID}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_SOURCE_ENTITY_ID: SOURCE_ENTITY_ID}
    assert result2["result"].unique_id == SOURCE_ENTITY_ID


async def test_user_flow_abort_no_alexa_lists(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_alexa_lists"


async def test_user_flow_abort_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    register_source_entity(hass)
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SOURCE_ENTITY_ID: SOURCE_ENTITY_ID}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow_grace_range(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    src = SourceListMock(make_items(("u1", "oat milk", False)))
    set_source_state(hass)
    with src:
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # init is now a menu; navigate to Display options.
        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        assert result["type"] is FlowResultType.MENU
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "display_options"}
        )
        assert result["type"] is FlowResultType.FORM
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_GRACE_PERIOD_SECONDS: 12,
                "show_completed": False,
                "collapse_empty_categories": True,
                "redact_items_in_diagnostics": True,
            },
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert mock_config_entry.options[CONF_GRACE_PERIOD_SECONDS] == 12


async def test_options_flow_grace_out_of_range_rejected(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    set_source_state(hass)
    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "display_options"}
        )
        try:
            await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_GRACE_PERIOD_SECONDS: 3,  # below the 8 floor
                    "show_completed": False,
                    "collapse_empty_categories": True,
                    "redact_items_in_diagnostics": True,
                },
            )
            raised = False
        except Exception:
            raised = True
        assert raised


async def test_reconfigure_changes_source_atomically(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    # A second alexa_devices list exists to switch to.
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="todo",
        platform="alexa_devices",
        unique_id="second_list",
        suggested_object_id="second_alexa_list",
    )
    set_source_state(hass)
    new_source = "todo.second_alexa_list"
    hass.states.async_set(new_source, "0", {"supported_features": 7})

    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await mock_config_entry.start_reconfigure_flow(hass)
        assert result["type"] is FlowResultType.FORM
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SOURCE_ENTITY_ID: new_source}
        )
        await hass.async_block_till_done()
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "reconfigure_successful"

    assert mock_config_entry.data[CONF_SOURCE_ENTITY_ID] == new_source
    assert mock_config_entry.unique_id == new_source
