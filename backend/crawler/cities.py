from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import geonamescache


@dataclass(frozen=True)
class City:
    name: str
    state_code: str
    state_name: str
    latitude: float
    longitude: float
    population: int


def load_us_cities(
    min_population: int = 25000,
    limit: Optional[int] = None,
) -> List[City]:
    """
    Load US cities from the public geonames cache dataset.
    Requires the `geonamescache` package (public domain data).
    """
    gc = _import_geonamescache()

    states_by_code = gc.get_us_states()
    states_by_fips = {v.get("fips"): v for v in states_by_code.values() if v.get("fips")}
    cities: List[City] = []
    for city in gc.get_cities().values():
        if city.get("countrycode") != "US":
            continue

        population = int(city.get("population") or 0)
        if population < min_population:
            continue

        state_code_raw = city.get("admin1code") or ""
        state_meta = states_by_code.get(state_code_raw, {}) or states_by_fips.get(state_code_raw, {})
        state_code = (state_meta.get("code") or state_code_raw or "").upper()
        state_name = state_meta.get("name", state_code) or state_code

        if not state_code or state_code.isdigit():
            # If we still don't have a 2-letter code, try resolving numeric FIPS -> code
            fips_code = state_code_raw or state_meta.get("fips")
            if fips_code and fips_code in states_by_fips:
                state_meta = states_by_fips[fips_code]
                state_code = (state_meta.get("code") or "").upper()
                state_name = state_meta.get("name", state_code) or state_code

        if not state_code or len(state_code) != 2:
            # Skip entries with no usable 2-letter state code; keeps downstream IDs clean.
            continue

        cities.append(
            City(
                name=city.get("name", ""),
                state_code=state_code,
                state_name=state_name,
                latitude=float(city.get("latitude")),
                longitude=float(city.get("longitude")),
                population=population,
            )
        )

    cities.sort(key=lambda c: c.population, reverse=True)
    if limit:
        cities = cities[:limit]
    return cities


def load_us_states():
    gc = _import_geonamescache()
    return gc.get_us_states()


def _import_geonamescache():
    try:
        return geonamescache.GeonamesCache()
    except Exception as exc:
        raise RuntimeError(
            "The `geonamescache` package is required for loading city data. "
            "Install it with `pip install geonamescache`."
        ) from exc
