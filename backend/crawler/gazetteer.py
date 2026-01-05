from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

from .util import normalize_place_name
from .cities import load_us_states


def load_gazetteer_area_sqmi(path: Path) -> Dict[Tuple[str, str], float]:
    """
    Load land area (sq mi) from a Census Gazetteer places CSV/TSV file.
    Expected columns: NAME, ALAND_SQMI (preferred) or ALAND (meters^2).
    Returns mapping of (city_lower, state_code) -> land area in square miles.
    """
    if not path.exists():
        raise FileNotFoundError(f"Gazetteer file not found: {path}")

    state_lookup = load_us_states()  # code -> metadata
    states_by_name = {v["name"].lower(): k for k, v in state_lookup.items()}

    def state_to_code(state_str: str, usps: str) -> str:
        if usps and len(usps.strip()) == 2:
            return usps.strip().upper()
        state_str = state_str.strip().lower()
        if len(state_str) == 2:
            return state_str.upper()
        return states_by_name.get(state_str, state_str.upper())

    area_by_city: Dict[Tuple[str, str], float] = {}
    with path.open(newline="") as fh:
        sample = fh.read(1024)
        fh.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(fh, delimiter=delimiter)

        for row in reader:
            name_raw = row.get("NAME", "") or ""
            if not name_raw:
                continue
            parts = [p.strip() for p in name_raw.split(",")]
            city_name = parts[0]
            state_raw = parts[1] if len(parts) > 1 else ""
            state_code = state_to_code(state_raw, row.get("USPS", ""))
            if not state_code:
                continue

            area_sqmi_str = row.get("ALAND_SQMI") or ""
            area_sqmi = float(area_sqmi_str) if area_sqmi_str else 0.0

            if not area_sqmi:
                area_m2_str = row.get("ALAND") or ""
                if area_m2_str:
                    try:
                        area_m2 = float(area_m2_str)
                        area_sqmi = area_m2 / 1609.344 / 1609.344
                    except ValueError:
                        pass

            if area_sqmi <= 0:
                continue

            key_raw = (city_name.lower(), state_code.upper())
            key_norm = (normalize_place_name(city_name), state_code.upper())
            area_by_city[key_raw] = area_sqmi
            area_by_city[key_norm] = area_sqmi

    return area_by_city
