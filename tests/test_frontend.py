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
