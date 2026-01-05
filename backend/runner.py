from __future__ import annotations

import argparse
import sys
from datetime import date
import math
from typing import Iterable, List

from crawler.areas import build_area_lookup, radius_from_lookup
from crawler.cities import load_us_cities
from crawler.client import HiringCafeClient
from crawler.config import (
    QUERIES_BY_CATEGORY,
    env_bool,
    env_float,
    env_int,
    load_env_file,
)
from crawler.db import save_city_results_to_pg
from crawler.search_state import default_search_state
from crawler.service import get_counts_for_cities


def parse_args() -> argparse.Namespace:
    load_env_file()
    parser = argparse.ArgumentParser(description="Run city jobs for one or more query categories.")
    parser.add_argument(
        "--categories",
        default="frontend,backend,fullstack,devops,data,mobile,levels",
        help="Comma-separated categories from QUERIES_BY_CATEGORY to run sequentially.",
    )
    parser.add_argument("--city-limit", type=int, default=env_int("JOBS_CITY_LIMIT", 0))
    parser.add_argument("--min-population", type=int, default=env_int("JOBS_MIN_POPULATION", 50000))
    parser.add_argument("--concurrency", type=int, default=env_int("JOBS_CONCURRENCY", 3))
    parser.add_argument("--radius-miles", type=int, default=env_int("JOBS_RADIUS_MILES", 25))
    parser.add_argument("--pg-url", default=None, help="Postgres connection URL (required).")
    parser.add_argument("--pg-table", default="city_counts")
    parser.add_argument("--pg-create-table", action="store_true", default=env_bool("JOBS_PG_CREATE_TABLE", True))
    parser.add_argument("--gazetteer-path", default=None, help="Optional Gazetteer path override.")
    parser.add_argument(
        "--auto-radius-from-population",
        action="store_true",
        default=env_bool("JOBS_AUTO_RADIUS_FROM_POPULATION", False),
        help="Derive radius when Gazetteer is absent.",
    )
    parser.add_argument("--density-per-sq-mile", type=float, default=env_float("JOBS_DENSITY_PER_SQ_MILE", 3000.0))
    parser.add_argument("--min-radius", type=float, default=env_float("JOBS_MIN_RADIUS", 5.0))
    parser.add_argument("--max-radius", type=float, default=env_float("JOBS_MAX_RADIUS", 50.0))
    return parser.parse_args()


def run_category(
    category: str,
    queries: Iterable[str],
    client: HiringCafeClient,
    city_limit: int,
    min_population: int,
    concurrency: int,
    radius_miles: float,
    pg_url: str,
    pg_table: str,
    pg_create_table: bool,
    gazetteer_path: str | None,
    auto_radius_from_population: bool,
    density_per_sq_mile: float,
    min_radius: float,
    max_radius: float,
    map_boroughs: bool,
) -> None:
    limit = city_limit or None
    cities = load_us_cities(min_population=min_population, limit=limit)
    area_lookup = build_area_lookup(
        argparse.Namespace(
            gazetteer_path=gazetteer_path,
            pg_url=pg_url,
            pg_areas_table="city_areas",
            pg_create_table=pg_create_table,
            pg_load_gazetteer_to_pg=False,
        ),
        cities=cities,
    )

    def radius_selector(city):
        return radius_from_lookup(
            area_lookup,
            city,
            default_radius=radius_miles,
            min_radius=min_radius,
            max_radius=max_radius,
            map_boroughs=map_boroughs,
        )

    def radius_from_population(city):
        if city.population and city.population > 0 and density_per_sq_mile > 0:
            area = city.population / density_per_sq_mile
            radius = math.sqrt(area / math.pi)
            return max(min_radius, min(max_radius, radius))
        return radius_miles

    for query in queries:
        print(f"[{category}] Running query '{query}' across {len(cities)} cities...")
        results = get_counts_for_cities(
            client=client,
            cities=cities,
            radius_miles=radius_miles,
            radius_selector=radius_selector
            if area_lookup
            else (radius_from_population if auto_radius_from_population else None),
            concurrency=max(1, concurrency),
            base_search_state=default_search_state(),
            query=query,
        )
        save_city_results_to_pg(
            results=results,
            pg_url=pg_url,
            table=pg_table,
            create_table=pg_create_table,
            query=query,
            radius_miles=radius_miles,
            run_date=date.today(),
        )


def main() -> None:
    args = parse_args()
    if not args.pg_url:
        print("--pg-url is required.")
        sys.exit(1)

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    client = HiringCafeClient(min_delay_s=0.5)

    for category in categories:
        if category not in QUERIES_BY_CATEGORY:
            print(f"Skipping unknown category '{category}'.")
            continue
        run_category(
            category=category,
            queries=QUERIES_BY_CATEGORY[category],
            client=client,
            city_limit=args.city_limit,
            min_population=args.min_population,
            concurrency=args.concurrency,
            radius_miles=args.radius_miles,
            pg_url=args.pg_url,
            pg_table=args.pg_table,
            pg_create_table=args.pg_create_table,
            gazetteer_path=args.gazetteer_path,
            auto_radius_from_population=args.auto_radius_from_population,
            density_per_sq_mile=args.density_per_sq_mile,
            min_radius=args.min_radius,
            max_radius=args.max_radius,
            map_boroughs=args.map_nyc_boroughs,
        )


if __name__ == "__main__":
    main()
