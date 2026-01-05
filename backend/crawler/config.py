from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List


QUERIES_BY_CATEGORY = {
    "frontend": [
        "frontend engineer",
        "frontend developer",
        "react developer",
        "javascript developer",
        "typescript developer",
        "ui engineer",
    ],
    "fullstack": [
        "full stack engineer",
        "full stack developer",
        "software engineer",
        "software developer",
    ],
    "backend": [
        "backend engineer",
        "backend developer",
        "python developer",
        "java developer",
        "golang developer",
        "ruby developer",
        "node.js developer",
    ],
    "mobile": [
        "ios engineer",
        "android engineer",
        "mobile developer",
    ],
    "devops": [
        "devops engineer",
        "site reliability engineer",
        "platform engineer",
        "cloud engineer",
    ],
    "levels": [
        "junior software engineer",
        "junior developer",
        "mid level software engineer",
        "mid-level software engineer",
        "software engineer ii",
        "software engineer 2",
        "senior software engineer",
        "lead engineer",
        "staff engineer",
        "principal engineer",
        "engineering manager",
        "tech lead",
    ],
    "data": [
        "data engineer",
        "ml engineer",
        "machine learning engineer",
        "ml ops",
    ],
}

SENIORITY_LEVELS = {
    "entry": ["No Prior Experience Required", "Entry Level"],
    "mid": ["Associate", "Mid-Senior Level"],
    "senior": ["Senior Level", "Director"],
    "all": [],
}

# Backwards-compatible default set for simple runs.
JOB_QUERIES = [
    "software engineer",
    "frontend engineer",
    "backend engineer",
    "react developer",
    "full stack engineer",
]


def load_env_file(env_path: str = ".env") -> None:
    """Lightweight .env loader (no external deps)."""
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Remove inline comments starting with # after some spacing
        if " #" in value:
            value = value.split(" #", 1)[0]
        value = value.strip().strip('"').strip("'")
        if key and value:
            # Later entries override earlier ones in the file; external env still wins if set after load_env_file.
            os.environ[key] = value


def env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "y", "on"}


def env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def parse_args() -> argparse.Namespace:
    load_env_file()
    parser = argparse.ArgumentParser(description="Fetch hiring.cafe job counts.")
    parser.add_argument(
        "--mode",
        choices=["queries", "cities"],
        default=os.getenv("JOBS_MODE", "queries"),
        help="queries=use JOB_QUERIES list, cities=iterate US cities with radius",
    )
    parser.add_argument(
        "--radius-miles",
        type=int,
        default=env_int("JOBS_RADIUS_MILES", 25),
        help="Radius (miles) to search around each city.",
    )
    parser.add_argument(
        "--min-population",
        type=int,
        default=env_int("JOBS_MIN_POPULATION", 50000),
        help="Only include cities with at least this population.",
    )
    parser.add_argument(
        "--city-limit",
        type=int,
        default=env_int("JOBS_CITY_LIMIT", 150),
        help="Max number of cities to process (sorted by population). Use 0 for all.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=env_int("JOBS_CONCURRENCY", 1),
        help="Number of parallel requests for city mode (be polite; 3-5 is reasonable).",
    )
    parser.add_argument(
        "--query",
        default=os.getenv("JOBS_QUERY", ""),
        help="Single search query to use (blank = all jobs).",
    )
    parser.add_argument(
        "--seniority-level",
        choices=sorted(SENIORITY_LEVELS.keys()),
        default=os.getenv("JOBS_SENIORITY_LEVEL", "all"),
        help="Filter by seniority (entry includes 'No Prior Experience').",
    )
    parser.add_argument(
        "--query-set",
        choices=sorted(QUERIES_BY_CATEGORY.keys()),
        default=os.getenv("JOBS_QUERY_SET"),
        help="Use a predefined category of queries (queries mode only).",
    )
    parser.add_argument(
        "--query-list",
        default=os.getenv("JOBS_QUERY_LIST"),
        help="Comma-separated list of queries to run (queries mode only).",
    )
    parser.add_argument(
        "--use-url-search-state",
        default=os.getenv("JOBS_USE_URL_SEARCH_STATE"),
        help="Optional hiring.cafe URL to seed searchState (locations/radius will be replaced per-city).",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("JOBS_OUTPUT"),
        help="Optional file path to write city-mode results (json or csv).",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "csv"],
        default=os.getenv("JOBS_OUTPUT_FORMAT", "json"),
        help="Format for --output when in city mode.",
    )
    parser.add_argument(
        "--pg-url",
        default=os.getenv("JOBS_PG_URL"),
        help="Postgres connection URL to store city results (city mode only).",
    )
    parser.add_argument(
        "--pg-table",
        default=os.getenv("JOBS_PG_TABLE", "city_counts"),
        help="Postgres table name for city results.",
    )
    parser.add_argument(
        "--pg-areas-table",
        default=os.getenv("JOBS_PG_AREAS_TABLE", "city_areas"),
        help="Postgres table name for city areas (cached Gazetteer areas).",
    )
    parser.add_argument(
        "--pg-create-table",
        action="store_true",
        default=env_bool("JOBS_PG_CREATE_TABLE", False),
        help="Create the Postgres table if it does not exist.",
    )
    parser.add_argument(
        "--pg-load-gazetteer-to-pg",
        action="store_true",
        default=env_bool("JOBS_PG_LOAD_GAZETTEER_TO_PG", False),
        help="If areas table is empty, load Gazetteer file into Postgres once.",
    )
    parser.add_argument(
        "--gazetteer-path",
        default=os.getenv("JOBS_GAZETTEER_PATH"),
        help="Path to Census Gazetteer places file to derive city area/radius.",
    )
    parser.add_argument(
        "--auto-radius-from-population",
        action="store_true",
        default=env_bool("JOBS_AUTO_RADIUS_FROM_POPULATION", False),
        help="Derive city radius from population (fallback to --radius-miles).",
    )
    parser.add_argument(
        "--density-per-sq-mile",
        type=float,
        default=env_float("JOBS_DENSITY_PER_SQ_MILE", 3000.0),
        help="Population density assumption when deriving radius.",
    )
    parser.add_argument(
        "--min-radius",
        type=float,
        default=env_float("JOBS_MIN_RADIUS", 5.0),
        help="Minimum radius when auto-calculating.",
    )
    parser.add_argument(
        "--max-radius",
        type=float,
        default=env_float("JOBS_MAX_RADIUS", 50.0),
        help="Maximum radius when auto-calculating.",
    )
    parser.add_argument(
        "--map-nyc-boroughs",
        action="store_true",
        default=env_bool("JOBS_MAP_NYC_BORO_TO_CITY", True),
        help="Map NYC borough names to New York City for radius lookup.",
    )
    return parser.parse_args()


def resolve_queries(args: argparse.Namespace) -> List[str]:
    """
    Priority:
    1) --query-list (comma-separated)
    2) --query-set (predefined category)
    3) --query (single)
    4) default JOB_QUERIES
    """
    if args.query_list:
        qs = [q.strip() for q in args.query_list.split(",") if q.strip()]
        if not qs:
            raise ValueError("No queries found in --query-list")
        return qs

    if args.query_set:
        return QUERIES_BY_CATEGORY[args.query_set]

    if args.query:
        return [args.query]

    return JOB_QUERIES


def resolve_role(args: argparse.Namespace) -> tuple[str | None, List[str]]:
    """
    Determine searchQuery and seniorityLevel list.
    Returns (search_query, seniority_levels).
    """
    search_query = args.query.strip() if args.query else None
    if args.seniority_level == "all":
        seniority_levels: List[str] = []
    else:
        seniority_levels = SENIORITY_LEVELS.get(args.seniority_level, [])
    return search_query, seniority_levels
