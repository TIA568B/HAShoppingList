"""Typed runtime data stored on the config entry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .coordinator import AlexaShoppingCoordinator
from .store import CategoryStore


@dataclass(slots=True)
class AlexaShoppingRuntimeData:
    """Runtime objects attached to ``entry.runtime_data``."""

    coordinator: AlexaShoppingCoordinator
    store: CategoryStore
    unsub_state: Callable[[], None]
