"""Shared dataclasses for the Alexa Shopping List Categoriser.

These types cross module boundaries (categoriser, store, coordinator). They carry no
Home Assistant dependency so the pure categoriser can import them standalone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class SourceItem:
    """A single item read from the source `todo` list."""

    uid: str
    name: str
    completed: bool


@dataclass(slots=True, frozen=True)
class CategorisedItem:
    """A source item with its resolved category and shop preference."""

    uid: str
    name: str
    checked: bool
    category: str
    shop: str


@dataclass(slots=True)
class Category:
    """A display category with its matching keywords."""

    name: str
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Shop:
    """A user-managed shop with its keyword rules (Req 7.3)."""

    name: str
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CategoryMap:
    """The full persisted map: categories, shops, and learned overrides."""

    schema_version: int
    categories: list[Category] = field(default_factory=list)
    overrides: dict[str, str] = field(default_factory=dict)
    shops: list[Shop] = field(default_factory=list)
    shop_overrides: dict[str, str] = field(default_factory=dict)
