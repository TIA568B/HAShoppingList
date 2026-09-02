"""Repair issues surfaced to the user.

The only repairable condition is a missing/unavailable source todo entity, which points
the user at the Alexa Devices integration. This integration owns no credentials, so there
is no reauth flow.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_SOURCE_MISSING


def _issue_id(entry_id: str) -> str:
    return f"{ISSUE_SOURCE_MISSING}_{entry_id}"


def async_raise_source_missing(hass: HomeAssistant, entry_id: str, source_entity_id: str) -> None:
    """Raise a repair issue when the source todo entity is missing/unavailable."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_SOURCE_MISSING,
        translation_placeholders={"entity_id": source_entity_id},
    )


def async_clear_source_missing(hass: HomeAssistant, entry_id: str) -> None:
    """Clear the source-missing repair issue once the source is healthy again."""
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id))
