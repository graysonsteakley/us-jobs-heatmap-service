from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from crawler.config import parse_args, resolve_queries
from crawler.areas import build_area_lookup, radius_from_lookup
from crawler.db import save_city_results_to_pg
from crawler.cities import load_us_cities
from crawler.client import HiringCafeClient
from crawler.service import get_counts_for_cities, get_counts_for_queries
from crawler.search_state import default_search_state, merge_overrides
from crawler.util import parse_search_state_from_url


def build_base_state(args):
    base_state = default_search_state()
    if args.use_url_search_state:
        try:
            url_state = parse_search_state_from_url(args.use_url_search_state)
            base_state = merge_overrides(base_state, url_state)
        except Exception as exc:
            print(f"Warning: failed to parse --use-url-search-state; using defaults. Error: {exc}")
    return base_state


def estimate_radius_from_population(population: int, density_per_sq_mile: float, min_radius: float, max_radius: float) -> float:
    if population <= 0 or density_per_sq_mile <= 0:
        return min_radius
    area = population / density_per_sq_mile
    radius = math.sqrt(area / math.pi)
    return max(min_radius, min(max_radius, radius))


def run_query_mode(client: HiringCafeClient, args, base_state, queries) -> None:
    if args.pg_url:
        print("--pg-url is only supported in cities mode.")
        sys.exit(1)
    results = get_counts_for_queries(client, queries, base_state)
    for r in results:
        if r.error:
            print(f"{r.query:20} -> ERROR: {r.error}")
        else:
            print(f"{r.query:20} -> {r.total}")


def run_city_mode(client: HiringCafeClient, args, base_state) -> None:
    if args.query_list or args.query_set:
        print("--query-list/--query-set provided but cities mode uses a single --query; ignoring those values.")

    limit = args.city_limit or None
    try:
        cities = load_us_cities(min_population=args.min_population, limit=limit)
    except RuntimeError as exc:
        print(f"City lookup failed: {exc}")
        sys.exit(1)
    print(f"Loaded {len(cities)} cities (min_pop={args.min_population}, limit={limit or 'all'})")

    area_lookup = build_area_lookup(args, cities=cities)
    radius_selector = None
    if area_lookup:
        def radius_selector(city):
            return radius_from_lookup(
                area_lookup,
                city,
                default_radius=args.radius_miles,
                min_radius=args.min_radius,
                max_radius=args.max_radius,
                map_boroughs=args.map_nyc_boroughs,
            )
    elif args.auto_radius_from_population:
        def radius_selector(city):
            return estimate_radius_from_population(
                city.population,
                args.density_per_sq_mile,
                args.min_radius,
                args.max_radius,
            )

    results = get_counts_for_cities(
        client=client,
        cities=cities,
        radius_miles=args.radius_miles,
        radius_selector=radius_selector,
        concurrency=max(1, args.concurrency),
        base_search_state=base_state,
        query=args.query,
    )

    for r in results:
        label = f"{r.city.name}, {r.city.state_code}"
        if r.error:
            print(f"{label:30} -> ERROR: {r.error}")
        else:
            print(f"{label:30} -> {r.total} (radius={r.radius_miles:.1f} mi)")

    if args.output:
        save_city_results(
            results=results,
            path=Path(args.output),
            fmt=args.output_format,
            query=args.query,
            radius_miles=args.radius_miles,
        )
    if args.pg_url:
        try:
            save_city_results_to_pg(
                results=results,
                pg_url=args.pg_url,
                table=args.pg_table,
                create_table=args.pg_create_table,
                query=args.query,
                radius_miles=args.radius_miles,
            )
        except RuntimeError as exc:
            print(f"Postgres save failed: {exc}")
            sys.exit(1)


def save_city_results(
    results,
    path: Path,
    fmt: str,
    query: str,
    radius_miles: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        payload = [
            {
                "city": r.city.name,
                "state": r.city.state_code,
                "state_name": r.city.state_name,
                "lat": r.city.latitude,
                "lon": r.city.longitude,
                "population": r.city.population,
                "radius_miles": r.radius_miles or radius_miles,
                "query": query,
                "total": r.total,
                "error": r.error,
            }
            for r in results
        ]
        path.write_text(json.dumps(payload, indent=2))
        print(f"Wrote {len(results)} records to {path} (json)")
        return

    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "city",
                "state",
                "state_name",
                "lat",
                "lon",
                "population",
                "radius_miles",
                "query",
                "total",
                "error",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "city": r.city.name,
                    "state": r.city.state_code,
                    "state_name": r.city.state_name,
                    "lat": r.city.latitude,
                    "lon": r.city.longitude,
                    "population": r.city.population,
                    "radius_miles": r.radius_miles or radius_miles,
                    "query": query,
                    "total": r.total,
                    "error": r.error or "",
                }
            )
    print(f"Wrote {len(results)} records to {path} (csv)")


def main() -> None:
    args = parse_args()
    client = HiringCafeClient(min_delay_s=0.5)
    base_state = build_base_state(args)

    if args.mode == "cities":
        run_city_mode(client, args, base_state)
    else:
        try:
            queries = resolve_queries(args)
        except ValueError as exc:
            print(exc)
            sys.exit(1)
        run_query_mode(client, args, base_state, queries)


if __name__ == "__main__":
    main()
