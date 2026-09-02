"""Diagnostics tests: item-text redaction and summary counts."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import (
    CONF_REDACT_ITEMS_IN_DIAGNOSTICS,
)
from custom_components.alexa_shopping_categoriser.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.helpers import SourceListMock, make_items, set_source_state


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, src: SourceListMock) -> None:
    set_source_state(hass)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_diagnostics_redacts_item_text_by_default(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        await _setup(hass, mock_config_entry, src)
        diag = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Summary counts present.
    assert diag["map_summary"]["category_count"] > 0
    assert diag["map_summary"]["shop_count"] == 3
    # Item text is redacted (default option true) - the literal must not appear.
    dumped = str(diag)
    assert "oat milk" not in dumped


async def test_diagnostics_includes_item_text_when_disabled(
    hass: HomeAssistant,
) -> None:
    from custom_components.alexa_shopping_categoriser.const import (
        CONF_SOURCE_ENTITY_ID,
        DOMAIN,
    )
    from tests.conftest import SOURCE_ENTITY_ID

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SOURCE_ENTITY_ID: SOURCE_ENTITY_ID},
        options={CONF_REDACT_ITEMS_IN_DIAGNOSTICS: False},
        unique_id=SOURCE_ENTITY_ID,
        version=1,
    )
    src = SourceListMock(make_items(("u1", "oat milk", False)))
    with src:
        await _setup(hass, entry, src)
        diag = await async_get_config_entry_diagnostics(hass, entry)

    dumped = str(diag)
    assert "oat milk" in dumped
