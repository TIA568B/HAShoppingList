"""Shared test helpers for mocking the source todo entity and its services."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from tests.conftest import SOURCE_ENTITY_ID


def register_source_entity(hass: HomeAssistant) -> str:
    """Register the source todo entity in the entity registry on the alexa_devices platform.

    Returns the entity_id. Registering (not just a state) makes service target validation
    pass, mirroring a real alexa_devices todo entity.
    """
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        domain="todo",
        platform="alexa_devices",
        unique_id="david_carson_shopping",
        suggested_object_id="david_carson_amazon_gmail_com_shopping_list",
    )
    return entry.entity_id


def set_source_state(hass: HomeAssistant, state: str = "3") -> None:
    """Register a fake source todo entity in the registry and state machine."""
    register_source_entity(hass)
    hass.states.async_set(
        SOURCE_ENTITY_ID,
        state,
        {"friendly_name": "David Carson Shopping List", "supported_features": 7},
    )


class SourceListMock:
    """Context manager that intercepts todo.get_items / update_item / add_item.

    Patches ``ServiceRegistry.async_call`` at the class level so the coordinator's
    ``todo.get_items`` returns the configured items (bypassing HA's entity-service target
    validation), and records write calls. All other service calls pass through.
    """

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.recorded: list[dict[str, Any]] = []
        self._patcher: Any = None

    def __enter__(self) -> SourceListMock:
        from unittest.mock import patch

        from homeassistant.core import ServiceRegistry

        real = ServiceRegistry.async_call

        async def _patched(
            registry: ServiceRegistry,
            domain: str,
            service: str,
            service_data: dict[str, Any] | None = None,
            blocking: bool = False,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            if domain == "todo" and service == "get_items":
                return {SOURCE_ENTITY_ID: {"items": list(self.items)}}
            if domain == "todo" and service in ("update_item", "add_item"):
                self.recorded.append(
                    {
                        "service": service,
                        "data": dict(service_data or {}),
                        "target": dict(kwargs.get("target") or {}),
                    }
                )
                return None
            return await real(registry, domain, service, service_data, blocking, *args, **kwargs)

        self._patcher = patch.object(ServiceRegistry, "async_call", _patched)
        self._patcher.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._patcher is not None:
            self._patcher.stop()


def make_items(*specs: tuple[str, str, bool]) -> list[dict[str, Any]]:
    """Build get_items-style item dicts from (uid, summary, completed) tuples."""
    return [
        {
            "uid": uid,
            "summary": summary,
            "status": "completed" if completed else "needs_action",
        }
        for uid, summary, completed in specs
    ]
