from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from flask import jsonify, request

from crawler.client import HiringCafeClient
from crawler.db import fetch_heatmap_points
from .settings import Settings
from crawler.search_state import default_search_state, merge_overrides


def register_routes(app, settings: Settings) -> None:
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/heatmap", methods=["GET"])
    def heatmap():
        query = request.args.get("query") or None
        min_total = int(request.args.get("min_total", settings.min_total_default))
        limit = int(request.args.get("limit", settings.limit_default))
        rows = fetch_heatmap_points(settings.pg_url, settings.pg_table, query=query, min_total=min_total, limit=limit)
        return jsonify({"points": rows})

    @app.route("/cluster-count", methods=["POST", "OPTIONS"])
    def cluster_count():
        """
        Compute a combined hiring.cafe count for a cluster of locations.
        Body: { "query": "...", "members": [{ city,state,lat,lon,radius_miles }] }
        """
        if request.method == "OPTIONS":
            return ("", 204)
        data = request.get_json(silent=True) or {}
        members = data.get("members") or []
        query = data.get("query") or ""
        if not members:
            return jsonify({"error": "members required"}), 400

        search_state = default_search_state()
        search_state["searchQuery"] = query
        locations = []
        for m in members:
            try:
                city = m["city"]
                state = m["state"]
                lat = float(m["lat"])
                lon = float(m["lon"])
                radius = float(m.get("radius_miles") or 25)
            except Exception:
                continue
            locations.append(
                {
                    "formatted_address": f"{city}, {state}, United States",
                    "types": ["locality", "political"],
                    "geometry": {"location": {"lat": lat, "lon": lon}},
                    "id": f"city_{str(city).lower().replace(' ','_')}_{str(state).lower()}",
                    "address_components": [
                        {"long_name": city, "short_name": city, "types": ["locality", "political"]},
                        {"long_name": state, "short_name": state, "types": ["administrative_area_level_1", "political"]},
                        {"long_name": "United States", "short_name": "US", "types": ["country", "political"]},
                    ],
                    "options": {"radius_miles": radius, "ignore_radius": False, "radius": radius},
                }
            )
        if not locations:
            return jsonify({"error": "no valid members"}), 400

        search_state["locations"] = locations
        client = HiringCafeClient(min_delay_s=0.5)
        try:
            raw = client.get_total_count(search_state)
            total = raw.get("total") or raw.get("count")
            return jsonify({"total": total, "raw": raw})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/refresh", methods=["POST"])
    def refresh():
        """
        Kick off the hiring.cafe city sweep via a shell command (non-blocking).
        Configure JOBS_REFRESH_CMD in env, e.g.:
        JOBS_REFRESH_CMD="python main.py --mode cities --query 'react developer' --pg-url ... --pg-table city_counts --pg-areas-table city_areas --pg-create-table --pg-load-gazetteer-to-pg --gazetteer-path ../data/2023_Gaz_place_national.txt --min-population 50000 --city-limit 0"
        """
        if not settings.refresh_cmd:
            return jsonify({"error": "Set JOBS_REFRESH_CMD to enable refresh endpoint"}), 400

        cmd = settings.refresh_cmd
        workdir = Path(__file__).resolve().parents[1]

        def run_cmd():
            try:
                subprocess.run(cmd, shell=True, cwd=workdir, check=True)
            except subprocess.CalledProcessError as exc:
                print(f"Refresh command failed: {exc}")

        threading.Thread(target=run_cmd, daemon=True).start()
        return jsonify({"status": "started", "cmd": cmd})
