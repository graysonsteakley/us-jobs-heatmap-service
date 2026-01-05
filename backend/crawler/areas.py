from __future__ import annotations

import math
from typing import Dict, Tuple
from pathlib import Path

from .db import load_area_lookup_from_pg, upsert_areas_to_pg
from .util import normalize_place_name
from .search_state import round_radius_miles
from .gazetteer import load_gazetteer_area_sqmi


def radius_from_lookup(area_lookup: Dict[Tuple[str, str], float], city, default_radius, min_radius, max_radius, map_boroughs: bool):
    state = city.state_code.upper()
    candidates = [
        (city.name.lower(), state),
        (normalize_place_name(city.name), state),
    ]
    if map_boroughs:
        borough_alias = state == "NY" and normalize_place_name(city.name) in {
            "brooklyn",
            "queens",
            "manhattan",
            "bronx",
            "staten island",
        }
        if borough_alias:
            candidates.append(("new york city", "NY"))
            candidates.append(("new york", "NY"))

    area_sqmi = None
    for key in candidates:
        if key in area_lookup:
            area_sqmi = area_lookup[key]
            break
    if area_sqmi and area_sqmi > 0:
        radius = math.sqrt(area_sqmi / math.pi)
        return round_radius_miles(max(min_radius, min(max_radius, radius)))
    return default_radius


def build_area_lookup(args, cities=None) -> Dict[Tuple[str, str], float]:
    """
    Prefer Postgres cache; if empty and instructed, load Gazetteer and cache.
    """
    area_lookup: Dict[Tuple[str, str], float] = {}

    if args.pg_url and args.pg_areas_table:
        try:
            area_lookup = load_area_lookup_from_pg(args.pg_url, args.pg_areas_table, args.pg_create_table)
            if area_lookup:
                print(f"Loaded {len(area_lookup)} areas from Postgres table {args.pg_areas_table}")
            elif args.pg_load_gazetteer_to_pg and args.gazetteer_path:
                area_lookup = load_gazetteer_area_sqmi(Path(args.gazetteer_path))
                if area_lookup:
                    saved = upsert_areas_to_pg(area_lookup, args.pg_url, args.pg_areas_table, args.pg_create_table)
                    print(f"Cached {saved} Gazetteer areas into {args.pg_areas_table}")
        except Exception as exc:
            print(f"Warning: failed to load areas from Postgres; Error: {exc}")
            area_lookup = {}

    return area_lookup
