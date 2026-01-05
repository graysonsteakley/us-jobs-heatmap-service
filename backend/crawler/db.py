from __future__ import annotations

import json
import urllib.parse
from datetime import date
from typing import Dict, Tuple, Optional

from .util import normalize_place_name
SENIORITY_MAP = {
    "entry": ["No Prior Experience Required", "Entry Level"],
    "mid": ["Associate", "Mid-Senior Level"],
    "senior": ["Senior Level", "Director"],
}


def ensure_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for Postgres output. Install with `pip install psycopg[binary]`.") from exc
    return psycopg


def load_area_lookup_from_pg(pg_url: str, table: str, create_table: bool) -> Dict[Tuple[str, str], float]:
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql
    area_lookup: Dict[Tuple[str, str], float] = {}
    with connect(pg_url) as conn:
        with conn.cursor() as cur:
            if create_table:
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            city TEXT NOT NULL,
                            state_code TEXT NOT NULL,
                            area_sqmi DOUBLE PRECISION NOT NULL,
                            PRIMARY KEY (city, state_code)
                        )
                        """
                    ).format(table_name=sql.Identifier(table))
                )
            cur.execute(
                sql.SQL(
                    """
                    SELECT city, state_code, area_sqmi FROM {table_name}
                    """
                ).format(table_name=sql.Identifier(table))
            )
            for city, state_code, area_sqmi in cur.fetchall():
                if not state_code or len(state_code.strip()) != 2:
                    continue
                state = state_code.strip().upper()
                raw_key = (city.lower(), state)
                norm_key = (normalize_place_name(city), state)
                area_lookup[raw_key] = area_sqmi
                area_lookup[norm_key] = area_sqmi
    return area_lookup


def upsert_areas_to_pg(area_lookup: Dict[Tuple[str, str], float], pg_url: str, table: str, create_table: bool) -> int:
    if not area_lookup:
        return 0
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql
    count = 0
    with connect(pg_url) as conn:
        with conn.cursor() as cur:
            if create_table:
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            city TEXT NOT NULL,
                            state_code TEXT NOT NULL,
                            area_sqmi DOUBLE PRECISION NOT NULL,
                            PRIMARY KEY (city, state_code)
                        )
                        """
                    ).format(table_name=sql.Identifier(table))
                )

            insert_sql = sql.SQL(
                """
                INSERT INTO {table_name} (city, state_code, area_sqmi)
                VALUES (%s, %s, %s)
                ON CONFLICT (city, state_code) DO UPDATE SET area_sqmi = EXCLUDED.area_sqmi
                """
            ).format(table_name=sql.Identifier(table))

            payload = [(city, state, area) for (city, state), area in area_lookup.items() if state and len(state) == 2]
            cur.executemany(insert_sql, payload)
            count = len(payload)
        conn.commit()
    return count


def save_city_results_to_pg(
    results,
    pg_url: str,
    table: str,
    create_table: bool,
    query: str,
    radius_miles: float,
    role: Optional[str] = None,
    seniority_level: Optional[str] = None,
    job_title_query: Optional[str] = None,
    run_date: Optional[date] = None,
) -> None:
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql

    run_dt = run_date or date.today()

    with connect(pg_url) as conn:
        with conn.cursor() as cur:
            if create_table:
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id BIGSERIAL PRIMARY KEY,
                            city TEXT NOT NULL,
                            state_code TEXT NOT NULL,
                            state_name TEXT NOT NULL,
                            lat DOUBLE PRECISION NOT NULL,
                            lon DOUBLE PRECISION NOT NULL,
                            population INTEGER,
                            radius_miles INTEGER,
                            query TEXT,
                            job_title_query TEXT,
                            role TEXT,
                            seniority_level TEXT,
                            total INTEGER,
                            error TEXT,
                            run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            run_date DATE NOT NULL DEFAULT CURRENT_DATE,
                            UNIQUE (city, state_code, query, seniority_level, run_date)
                        )
                        """
                    ).format(table_name=sql.Identifier(table))
                )
                cur.execute(
                    sql.SQL(
                        "CREATE INDEX IF NOT EXISTS {idx} ON {table_name} (query, seniority_level, run_date)"
                    ).format(
                        idx=sql.Identifier(f"{table}_query_level_date_idx"),
                        table_name=sql.Identifier(table),
                    )
                )

            insert_sql = sql.SQL(
                """
                INSERT INTO {table_name} (
                    city, state_code, state_name, lat, lon, population,
                    radius_miles, query, job_title_query, role, seniority_level,
                    total, error, run_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (city, state_code, query, seniority_level, run_date)
                DO UPDATE SET
                    total = EXCLUDED.total,
                    error = EXCLUDED.error,
                    population = EXCLUDED.population,
                    radius_miles = EXCLUDED.radius_miles,
                    lat = EXCLUDED.lat,
                    lon = EXCLUDED.lon,
                    state_name = EXCLUDED.state_name,
                    query = EXCLUDED.query,
                    job_title_query = EXCLUDED.job_title_query,
                    run_at = NOW()
                """
            ).format(table_name=sql.Identifier(table))

            payload = [
                (
                    r.city.name,
                    r.city.state_code,
                    r.city.state_name,
                    r.city.latitude,
                    r.city.longitude,
                    r.city.population,
                    r.radius_miles or radius_miles,
                    query,
                    job_title_query,
                    role,
                    seniority_level,
                    r.total,
                    r.error,
                    run_dt,
                )
                for r in results
            ]
            cur.executemany(insert_sql, payload)
        conn.commit()


def fetch_heatmap_points(
    pg_url: str,
    table: str,
    query: str | None = None,
    roles: list[str] | None = None,
    seniority_level: str | None = None,
    seniority_levels: list[str] | None = None,
    min_total: int = 0,
    limit: int = 1000,
):
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql
    with connect(pg_url) as conn:
        with conn.cursor() as cur:
            base = sql.SQL(
                """
                SELECT DISTINCT ON (city, state_code, query, seniority_level)
                    city, state_code, state_name, lat, lon, radius_miles,
                    total, query, job_title_query, role, seniority_level, run_at
                FROM {table_name}
                {where}
                ORDER BY city, state_code, query, seniority_level, run_at DESC
                LIMIT %s
                """
            )
            clauses = []
            params = []
            if query:
                clauses.append("query = %s")
                params.append(query)
            if roles:
                clauses.append("role = ANY(%s)")
                params.append(roles)
            levels = seniority_levels or ([seniority_level] if seniority_level else None)
            if levels:
                clauses.append("seniority_level = ANY(%s)")
                params.append(levels)
            if min_total > 0:
                clauses.append("total >= %s")
                params.append(min_total)
            where_sql = sql.SQL("")
            if clauses:
                where_sql = sql.SQL("WHERE " + " AND ".join(clauses))
            cur.execute(
                base.format(table_name=sql.Identifier(table), where=where_sql),
                (*params, limit),
            )
            rows = cur.fetchall()
    def hiring_cafe_url(
        city: str,
        state: str,
        lat: float,
        lon: float,
        radius_miles: float,
        search_query: str | None,
        job_title_query: str | None,
        seniority_level: str | None,
    ):
        search_state = {
            "locations": [
                {
                    "formatted_address": f"{city}, {state}, United States",
                    "types": ["locality", "political"],
                    "geometry": {"location": {"lat": lat, "lon": lon}},
                    "id": f"city_{city.lower().replace(' ','_')}_{state.lower()}",
                    "address_components": [
                        {"long_name": city, "short_name": city, "types": ["locality", "political"]},
                        {
                            "long_name": state,
                            "short_name": state,
                            "types": ["administrative_area_level_1", "political"],
                        },
                        {"long_name": "United States", "short_name": "US", "types": ["country", "political"]},
                    ],
                    "options": {"radius_miles": radius_miles, "ignore_radius": False, "radius": radius_miles},
                }
            ],
            "workplaceTypes": ["Remote", "Hybrid", "Onsite"],
            "defaultToUserLocation": False,
            "searchQuery": search_query or "",
            "dateFetchedPastNDays": 61,
            "sortBy": "default",
        }
        # Prefer jobTitleQuery when present (role-based queries)
        if job_title_query:
            search_state["jobTitleQuery"] = job_title_query
        if seniority_level and seniority_level != "all":
            search_state["seniorityLevel"] = SENIORITY_MAP.get(seniority_level, [seniority_level])
        encoded = urllib.parse.quote(json.dumps(search_state))
        return f"https://hiring.cafe/?searchState={encoded}"

    result = []
    for r in rows:
        lat = float(r[3])
        lon = float(r[4])
        radius_val = float(r[5]) if r[5] is not None else 25.0
        entry = {
            "city": r[0],
            "state": r[1],
            "state_name": r[2],
            "lat": lat,
            "lon": lon,
            "radius_miles": radius_val,
            "total": r[6],
            "query": r[7],
            "job_title_query": r[8],
            "role": r[9],
            "seniority_level": r[10],
            "run_at": r[11].isoformat() if r[11] else None,
        }
        entry["hiring_cafe_url"] = hiring_cafe_url(
            entry["city"],
            entry["state"],
            lat,
            lon,
            radius_val,
            entry["query"],
            entry["job_title_query"],
            entry["seniority_level"],
        )
        result.append(entry)
    return result
