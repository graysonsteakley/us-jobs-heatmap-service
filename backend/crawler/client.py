from __future__ import annotations

import time
import requests
from typing import Any, Dict, Optional

JSON = Dict[str, Any]


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://hiring.cafe/",
    "Origin": "https://hiring.cafe",
}


class HiringCafeClient:
    def __init__(
        self,
        base_url: str = "https://hiring.cafe",
        timeout_s: int = 30,
        min_delay_s: float = 0.35,  # be polite; prevents hammering
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.min_delay_s = min_delay_s
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        self._last_request_ts = 0.0

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.min_delay_s:
            time.sleep(self.min_delay_s - elapsed)

    def post_json(self, path: str, payload: JSON) -> JSON:
        self._throttle()
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, json=payload, timeout=self.timeout_s)
        self._last_request_ts = time.time()

        # Raise useful error
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # Attach response text for debugging
            raise requests.HTTPError(
                f"{e} | status={resp.status_code} | body={resp.text[:400]}"
            ) from e

        return resp.json()

    def get_total_count(self, search_state: JSON) -> JSON:
        return self.post_json(
            "/api/search-jobs/get-total-count",
            {"searchState": search_state},
        )
