from __future__ import annotations

from typing import Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import HiringCafeClient
from .cities import City
from .types import CityCountResult, CountResult, JSON
from .search_state import default_search_state, search_state_for_city, with_query


def extract_total(count_response: JSON) -> int:
    if isinstance(count_response, dict):
        if "total" in count_response and isinstance(count_response["total"], int):
            return count_response["total"]
        if "count" in count_response and isinstance(count_response["count"], int):
            return count_response["count"]
    raise ValueError(f"Unexpected count response shape: {count_response}")


def get_count_for_query(
    client: HiringCafeClient,
    query: str,
    base_search_state: Optional[JSON] = None,
) -> CountResult:
    st = with_query(base_search_state or default_search_state(), query)
    try:
        raw = client.get_total_count(st)
        total = extract_total(raw)
        return CountResult(query=query, total=total, raw=raw)
    except Exception as e:
        return CountResult(query=query, total=0, raw=None, error=str(e))


def get_counts_for_queries(
    client: HiringCafeClient,
    queries: List[str],
    base_search_state: Optional[JSON] = None,
) -> List[CountResult]:
    base = base_search_state or default_search_state()
    results: List[CountResult] = []
    for q in queries:
        results.append(get_count_for_query(client, q, base))
    return results


def get_count_for_city(
    client: HiringCafeClient,
    city: City,
    radius_miles: float = 25,
    base_search_state: Optional[JSON] = None,
    query: Optional[str] = None,
) -> CityCountResult:
    st = search_state_for_city(city, base_search_state or default_search_state(), radius_miles, query)
    try:
        raw = client.get_total_count(st)
        total = extract_total(raw)
        return CityCountResult(city=city, total=total, raw=raw, radius_miles=radius_miles)
    except Exception as e:
        return CityCountResult(city=city, total=0, raw=None, error=str(e), radius_miles=radius_miles)


def get_counts_for_cities(
    client: HiringCafeClient,
    cities: List[City],
    radius_miles: float = 25,
    radius_selector: Optional[Callable[[City], float]] = None,
    concurrency: int = 1,
    base_search_state: Optional[JSON] = None,
    query: Optional[str] = None,
) -> List[CityCountResult]:
    base = base_search_state or default_search_state()
    results: List[CityCountResult] = []
    if concurrency <= 1:
        for city in cities:
            radius = radius_selector(city) if radius_selector else radius_miles
            results.append(get_count_for_city(client, city, radius, base, query))
        return results

    def task(city: City) -> CityCountResult:
        radius = radius_selector(city) if radius_selector else radius_miles
        return get_count_for_city(client, city, radius, base, query)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {executor.submit(task, city): city for city in cities}
        for fut in as_completed(future_map):
            try:
                results.append(fut.result())
            except Exception as exc:
                city = future_map[fut]
                results.append(CityCountResult(city=city, total=0, raw=None, error=str(exc), radius_miles=radius_miles))

    return results
