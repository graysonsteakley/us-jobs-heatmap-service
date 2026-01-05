from __future__ import annotations

import json
import urllib.parse
from typing import Dict, Tuple

from .util import normalize_place_name


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
) -> None:
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql

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
                            total INTEGER,
                            error TEXT,
                            run_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(table_name=sql.Identifier(table))
                )

            insert_sql = sql.SQL(
                """
                INSERT INTO {table_name} (
                    city, state_code, state_name, lat, lon, population,
                    radius_miles, query, total, error
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
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
                    r.total,
                    r.error,
                )
                for r in results
            ]
            cur.executemany(insert_sql, payload)
        conn.commit()


def fetch_heatmap_points(pg_url: str, table: str, query: str | None = None, min_total: int = 0, limit: int = 1000):
    psycopg = ensure_psycopg()
    connect = psycopg.connect
    sql = psycopg.sql
    with connect(pg_url) as conn:
        with conn.cursor() as cur:
            base = sql.SQL(
                """
                SELECT DISTINCT ON (city, state_code)
                    city, state_code, state_name, lat, lon, radius_miles, total, query, run_at
                FROM {table_name}
                {where}
                ORDER BY city, state_code, run_at DESC
                LIMIT %s
                """
            )
            clauses = []
            params = []
            if query:
                clauses.append("query = %s")
                params.append(query)
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
    def hiring_cafe_url(city: str, state: str, lat: float, lon: float, radius_miles: float, search_query: str | None):
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
            "run_at": r[8].isoformat() if r[8] else None,
        }
        entry["hiring_cafe_url"] = hiring_cafe_url(entry["city"], entry["state"], lat, lon, radius_val, entry["query"])
        result.append(entry)
    return result
