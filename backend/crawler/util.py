from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict

JSON = Dict[str, Any]


def parse_search_state_from_url(url: str) -> JSON:
    """
    Extract and decode the `searchState` param from a hiring.cafe URL.
    Works for URLs like: https://hiring.cafe/?searchState=<urlencoded json>
    """
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    raw = qs.get("searchState", [None])[0]
    if not raw:
        raise ValueError("URL does not contain a searchState query param")

    decoded = urllib.parse.unquote(raw)
    obj = json.loads(decoded)
    if not isinstance(obj, dict):
        raise ValueError("searchState JSON was not an object")
    return obj


def normalize_place_name(name: str) -> str:
    """
    Normalize place names so they align across datasets (drop suffixes like 'city').
    """
    n = name.strip().lower()
    suffixes = [
        " city and borough",
        " city and county",
        " consolidated city",
        " consolidated government",
        " metropolitan government",
        " census designated place",
        " cdp",
        " municipality",
        " charter township",
        " township",
        " plantation",
        " village",
        " borough",
        " town",
        " city",
    ]
    for suf in suffixes:
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
            break
    return " ".join(n.split())
