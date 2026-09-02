"""Register and serve the bundled Lovelace card and sidebar panel.

Serves the built card asset from the integration so users do not hand-install JS, and
adds it as an extra module URL cache-busted by the integration version (finding
REVIEW2-004). Also registers a dedicated sidebar panel ("Shopping List") that hosts the
card so the categorised view has a first-class left-nav entry without a Lovelace
dashboard. Registration is idempotent across entries.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "alexa-shopping-categoriser-card.js"
PANEL_FILENAME = "alexa-shopping-categoriser-panel.js"
_CARD_URL_BASE = f"/{DOMAIN}/{CARD_FILENAME}"
_PANEL_URL_BASE = f"/{DOMAIN}/{PANEL_FILENAME}"
_WWW_DIR = Path(__file__).parent / "www"

_REGISTERED = "frontend_card_registered"
_PANEL_REGISTERED = "frontend_panel_registered"

# Sidebar panel identity.
PANEL_URL_PATH = "alexa-shopping-list"
PANEL_TITLE = "Shopping List"
PANEL_ICON = "mdi:cart"
PANEL_COMPONENT_NAME = "alexa-shopping-categoriser-panel"


async def async_register_card(hass: HomeAssistant, version: str) -> None:
    """Register the static card asset and add it as a frontend resource (once)."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_REGISTERED):
        return

    card_path = _WWW_DIR / CARD_FILENAME
    if not card_path.is_file():
        _LOGGER.warning(
            "Bundled card asset not found at %s; build the card (npm run build) and copy "
            "it into the integration's www/ directory. The integration still works; only "
            "the custom card resource is unavailable.",
            card_path,
        )
        return

    # Card serving is best-effort: a failure here (e.g. frontend/http not loaded) must
    # never block integration setup.
    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    _CARD_URL_BASE,
                    str(card_path),
                    cache_headers=False,
                )
            ]
        )

        # Cache-bust with the integration version so card updates aren't masked by caching.
        url = f"{_CARD_URL_BASE}?v={version}"
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, url)
    except Exception as err:
        _LOGGER.warning("Could not register the bundled card resource: %s", err)
        return

    domain_data[_REGISTERED] = True
    _LOGGER.debug("Registered card resource at %s", url)


async def async_register_panel(hass: HomeAssistant, version: str) -> None:
    """Serve the panel module and register the sidebar panel (once).

    Best-effort: any failure here must never block integration setup. The panel hosts the
    card element and discovers the categorised sensor by its attribute contract.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_PANEL_REGISTERED):
        return

    panel_path = _WWW_DIR / PANEL_FILENAME
    if not panel_path.is_file():
        _LOGGER.warning(
            "Panel asset not found at %s; the sidebar entry will be unavailable. The "
            "integration and card still work.",
            panel_path,
        )
        return

    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    _PANEL_URL_BASE,
                    str(panel_path),
                    cache_headers=False,
                )
            ]
        )

        # Ensure panel_custom is available. In a real HA instance frontend/panel_custom
        # are part of default_config; this is a safety net if setup ordering left it out.
        # It is a no-op if already set up.
        if not await async_setup_component(hass, "panel_custom", {}):
            _LOGGER.warning(
                "panel_custom component unavailable; sidebar panel not registered. "
                "The integration and card still work."
            )
            return

        from homeassistant.components import panel_custom

        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_COMPONENT_NAME,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            # Cache-bust with the integration version so panel updates land.
            module_url=f"{_PANEL_URL_BASE}?v={version}",
            embed_iframe=False,
            require_admin=False,
        )
    except Exception as err:
        _LOGGER.warning("Could not register the sidebar panel: %s", err)
        return

    domain_data[_PANEL_REGISTERED] = True
    _LOGGER.debug("Registered sidebar panel at /%s", PANEL_URL_PATH)


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel when the last entry unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get(_PANEL_REGISTERED):
        return
    try:
        from homeassistant.components import frontend

        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    except Exception as err:
        _LOGGER.debug("Could not remove sidebar panel: %s", err)
        return
    domain_data[_PANEL_REGISTERED] = False
