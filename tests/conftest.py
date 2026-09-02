"""Shared fixtures for the Alexa Shopping List Categoriser tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alexa_shopping_categoriser.const import (
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
)

SOURCE_ENTITY_ID = "todo.david_carson_amazon_gmail_com_shopping_list"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def source_list() -> Generator[object]:
    """Provide a patched source todo list (get_items/update_item/add_item).

    Default items: one unchecked 'oat milk'. Mutate ``.items`` in the test to change what
    get_items returns; read ``.recorded`` for write-call assertions.
    """
    from tests.helpers import SourceListMock, make_items

    mock = SourceListMock(make_items(("u1", "oat milk", False)))
    with mock:
        yield mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Alexa Shopping List Categoriser",
        data={CONF_SOURCE_ENTITY_ID: SOURCE_ENTITY_ID},
        options={},
        unique_id=SOURCE_ENTITY_ID,
        version=1,
    )
