from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional, List

from .cities import City

JSON = Dict[str, Any]


def default_search_state() -> JSON:
    # Minimal defaults for count-based usage.
    # Add more fields only when you need them.
    return {
        "locations": [
            {
                "formatted_address": "United States",
                "types": ["country"],
                "geometry": {"location": {"lat": "39.8283", "lon": "-98.5795"}},
                "id": "user_country",
                "address_components": [
                    {"long_name": "United States", "short_name": "US", "types": ["country"]}
                ],
                "options": {"flexible_regions": ["anywhere_in_continent", "anywhere_in_world"]},
            }
        ],
        "workplaceTypes": ["Remote", "Hybrid", "Onsite"],
        "defaultToUserLocation": False,
        "searchQuery": "",
        "dateFetchedPastNDays": 61,
        "sortBy": "default",
    }


def with_query(base: JSON, query: str) -> JSON:
    st = deepcopy(base)
    st["searchQuery"] = query
    return st


def with_locations(base: JSON, locations: List[JSON]) -> JSON:
    st = deepcopy(base)
    st["locations"] = locations
    return st


def merge_overrides(base: JSON, overrides: JSON) -> JSON:
    """
    Shallow merge at top-level (good enough for swapping query/locations/etc.).
    If you want deep merge later, we can add it.
    """
    st = deepcopy(base)
    st.update(overrides)
    return st


def location_from_city(city: City, radius_miles: int = 25) -> JSON:
    """
    Build a hiring.cafe location payload for a given city.
    Radius is expressed in miles because that is what the API expects.
    """
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in city.name).strip("_")
    return {
        "formatted_address": f"{city.name}, {city.state_code}, United States",
        "types": ["locality", "political"],
        "geometry": {"location": {"lat": city.latitude, "lon": city.longitude}},
        "id": f"city_{slug}_{city.state_code.lower()}",
        "address_components": [
            {"long_name": city.name, "short_name": city.name, "types": ["locality", "political"]},
            {
                "long_name": city.state_name,
                "short_name": city.state_code,
                "types": ["administrative_area_level_1", "political"],
            },
            {"long_name": "United States", "short_name": "US", "types": ["country", "political"]},
        ],
        "population": city.population,
        "options": {"radius_miles": radius_miles},
    }


def search_state_for_city(
    city: City,
    base: Optional[JSON] = None,
    radius_miles: int = 25,
    query: Optional[str] = None,
) -> JSON:
    """
    Create a search state scoped to a city and radius, optionally overriding query.
    """
    st = deepcopy(base or default_search_state())
    st["locations"] = [location_from_city(city, radius_miles)]
    if query is not None:
        st["searchQuery"] = query
    return st


def search_states_for_cities(
    cities: List[City],
    base: Optional[JSON] = None,
    radius_miles: int = 25,
    query: Optional[str] = None,
) -> List[JSON]:
    """
    Build one search state per city. Useful for iterating and collecting totals.
    """
    base_state = base or default_search_state()
    return [search_state_for_city(city, base_state, radius_miles, query) for city in cities]
