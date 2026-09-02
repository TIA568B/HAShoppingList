"""Tests for the bundled-card resource registration.

The real `frontend` component requires the `hass_frontend` package (not installed in the
test harness), so we inject seams for the static-path registration and the JS-URL add and
assert our own behaviour: versioned cache-buster, idempotency, and missing-asset no-op.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.alexa_shopping_categoriser.const import DOMAIN
from custom_components.alexa_shopping_categoriser.frontend import (
    CARD_FILENAME,
    async_register_card,
)


@pytest.fixture(autouse=True)
async def _http(hass: HomeAssistant) -> None:
    """Set up the lightweight http component so hass.http exists."""
    assert await async_setup_component(hass, "http", {})
    await hass.async_block_till_done()


async def test_register_card_adds_versioned_js_url(hass: HomeAssistant) -> None:
    added: list[str] = []

    with (
        patch.object(hass.http, "async_register_static_paths", AsyncMock()),
        patch(
            "homeassistant.components.frontend.add_extra_js_url",
            side_effect=lambda _hass, url: added.append(url),
        ),
    ):
        await async_register_card(hass, "1.2.3")

    assert len(added) == 1
    assert CARD_FILENAME in added[0]
    assert "v=1.2.3" in added[0]
    assert hass.data[DOMAIN]["frontend_card_registered"] is True


async def test_register_card_is_idempotent(hass: HomeAssistant) -> None:
    register = AsyncMock()
    with (
        patch.object(hass.http, "async_register_static_paths", register),
        patch("homeassistant.components.frontend.add_extra_js_url"),
    ):
        await async_register_card(hass, "1.0.0")
        await async_register_card(hass, "1.0.0")

    # Static path registered only once despite two calls.
    assert register.await_count == 1


async def test_register_card_missing_asset_is_noop(
    hass: HomeAssistant, tmp_path, monkeypatch
) -> None:
    import custom_components.alexa_shopping_categoriser.frontend as fe

    # Point the www dir at an empty temp dir so the asset is missing.
    monkeypatch.setattr(fe, "_WWW_DIR", tmp_path)
    register = AsyncMock()
    with patch.object(hass.http, "async_register_static_paths", register):
        await async_register_card(hass, "1.0.0")

    register.assert_not_awaited()
    assert not hass.data.get(DOMAIN, {}).get("frontend_card_registered")


async def test_register_panel_registers_sidebar_panel(hass: HomeAssistant) -> None:
    from custom_components.alexa_shopping_categoriser.frontend import (
        PANEL_TITLE,
        PANEL_URL_PATH,
        async_register_panel,
    )

    registered: list[dict] = []

    async def _fake_register(_hass, **kwargs):
        registered.append(kwargs)

    with (
        patch.object(hass.http, "async_register_static_paths", AsyncMock()),
        patch(
            "custom_components.alexa_shopping_categoriser.frontend.async_setup_component",
            AsyncMock(return_value=True),
        ),
        patch(
            "homeassistant.components.panel_custom.async_register_panel",
            side_effect=_fake_register,
        ),
    ):
        await async_register_panel(hass, "1.2.3")

    assert len(registered) == 1
    kwargs = registered[0]
    assert kwargs["frontend_url_path"] == PANEL_URL_PATH
    assert kwargs["sidebar_title"] == PANEL_TITLE
    assert kwargs["webcomponent_name"] == "alexa-shopping-categoriser-panel"
    assert kwargs["embed_iframe"] is False
    assert "v=1.2.3" in kwargs["module_url"]
    assert hass.data[DOMAIN]["frontend_panel_registered"] is True


async def test_register_panel_is_idempotent(hass: HomeAssistant) -> None:
    from custom_components.alexa_shopping_categoriser.frontend import async_register_panel

    register = AsyncMock()
    with (
        patch.object(hass.http, "async_register_static_paths", register),
        patch(
            "custom_components.alexa_shopping_categoriser.frontend.async_setup_component",
            AsyncMock(return_value=True),
        ),
        patch("homeassistant.components.panel_custom.async_register_panel", AsyncMock()),
    ):
        await async_register_panel(hass, "1.0.0")
        await async_register_panel(hass, "1.0.0")

    assert register.await_count == 1


async def test_register_panel_missing_asset_is_noop(
    hass: HomeAssistant, tmp_path, monkeypatch
) -> None:
    import custom_components.alexa_shopping_categoriser.frontend as fe

    monkeypatch.setattr(fe, "_WWW_DIR", tmp_path)
    register = AsyncMock()
    with patch.object(hass.http, "async_register_static_paths", register):
        await fe.async_register_panel(hass, "1.0.0")

    register.assert_not_awaited()
    assert not hass.data.get(DOMAIN, {}).get("frontend_panel_registered")


async def test_remove_panel_calls_frontend_remove(hass: HomeAssistant) -> None:
    from custom_components.alexa_shopping_categoriser.frontend import (
        PANEL_URL_PATH,
        async_register_panel,
        async_remove_panel,
    )

    with (
        patch.object(hass.http, "async_register_static_paths", AsyncMock()),
        patch(
            "custom_components.alexa_shopping_categoriser.frontend.async_setup_component",
            AsyncMock(return_value=True),
        ),
        patch("homeassistant.components.panel_custom.async_register_panel", AsyncMock()),
    ):
        await async_register_panel(hass, "1.0.0")

    with patch("homeassistant.components.frontend.async_remove_panel") as remove:
        async_remove_panel(hass)

    remove.assert_called_once_with(hass, PANEL_URL_PATH)
    assert hass.data[DOMAIN]["frontend_panel_registered"] is False
