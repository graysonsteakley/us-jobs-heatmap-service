from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict, List

from .cities import City


JSON = Dict[str, Any]


@dataclass(frozen=True)
class CountResult:
    query: str
    total: int
    raw: JSON | None = None
    error: str | None = None


@dataclass(frozen=True)
class CityCountResult:
    city: City
    total: int
    raw: JSON | None = None
    error: str | None = None
    radius_miles: float = 0.0


class Location(TypedDict, total=False):
    id: str
    types: List[str]
    formatted_address: str
    address_components: List[JSON]
    geometry: JSON
    population: int
    workplace_types: List[str]
    options: JSON
