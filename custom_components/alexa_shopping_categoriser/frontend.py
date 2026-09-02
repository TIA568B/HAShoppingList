"""Register and serve the bundled Lovelace card.

Serves the built card asset from the integration so users do not hand-install JS, and
adds it as an extra module URL cache-busted by the integration version (finding
REVIEW2-004). Registration is idempotent across entries.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "alexa-shopping-categoriser-card.js"
_CARD_URL_BASE = f"/{DOMAIN}/{CARD_FILENAME}"
_WWW_DIR = Path(__file__).parent / "www"

_REGISTERED = "frontend_card_registered"


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
