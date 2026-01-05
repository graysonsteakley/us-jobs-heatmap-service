from __future__ import annotations

import os
from dataclasses import dataclass

from crawler.config import load_env_file


@dataclass(frozen=True)
class Settings:
    pg_url: str
    pg_table: str
    min_total_default: int = 0
    limit_default: int = 1000
    refresh_cmd: str | None = None


def load_settings() -> Settings:
    load_env_file()
    pg_url = os.getenv("JOBS_PG_URL")
    if not pg_url:
        raise RuntimeError("JOBS_PG_URL must be set (e.g., in .env)")
    pg_table = os.getenv("JOBS_PG_TABLE", "city_counts")
    min_total = int(os.getenv("JOBS_HEATMAP_MIN_TOTAL", "0"))
    limit = int(os.getenv("JOBS_HEATMAP_LIMIT", "1000"))
    refresh_cmd = os.getenv("JOBS_REFRESH_CMD")
    return Settings(
        pg_url=pg_url,
        pg_table=pg_table,
        min_total_default=min_total,
        limit_default=limit,
        refresh_cmd=refresh_cmd,
    )
