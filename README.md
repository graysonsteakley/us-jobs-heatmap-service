# Jobs Crawler

CLI + API to fetch hiring.cafe job counts across US cities, derive radii from the Census Gazetteer, cache results in Postgres, and visualize via a React/Leaflet heatmap.

## Prereqs

- Python 3.11+
- Node 18+
- Postgres (see `backend/docker-compose.yml`, default host port 5433)
- Gazetteer places file (example 2023):
  ```
  mkdir -p data
  curl -L -o data/2023_Gaz_place_national.zip https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_place_national.zip
  unzip -o data/2023_Gaz_place_national.zip -d data
  ```

## Backend: seed counts and serve API

```
cd backend
pip install -r requirements.txt
docker compose up -d
python main.py --mode cities --query "react developer" \
  --pg-url "postgresql://jobs_user:jobs_pw@localhost:5433/jobs_db" \
  --pg-table city_counts --pg-areas-table city_areas --pg-create-table \
  --pg-load-gazetteer-to-pg --gazetteer-path ../data/2023_Gaz_place_national.txt \
  --min-population 50000 --city-limit 150
```

- First run caches Gazetteer areas into `city_areas`; later runs can drop the `pg-load-gazetteer-to-pg`/`gazetteer-path` flags.

Run API:

```
JOBS_PG_URL=postgresql://jobs_user:jobs_pw@localhost:5433/jobs_db \
JOBS_PG_TABLE=city_counts \
python server.py
```

Heatmap endpoint:

- GET `/heatmap` with optional `query`, `min_total`, `limit`.

## Frontend: React + Vite + Leaflet

```
cd frontend
npm install
npm run dev -- --host
```

- If API is not on `http://localhost:8000`, set `frontend/.env` with `VITE_API_BASE=http://<api-host>:<port>`.
- Open the dev URL (default http://localhost:5173) and use the sidebar to load heatmap circles from the API.

## UI Preview

![Jobs Heatmap UI](frontend/docs/ui-example.png)

## Layout

- `backend/` – Python CLI + API + Postgres helpers + Gazetteer loader.
  - `main.py` – CLI entrypoint.
  - `crawler/` – hiring.cafe client, search state helpers, Gazetteer loader, Postgres helpers, area lookup.
  - `api/` – Flask app factory + routes/settings for `/heatmap`.
  - `server.py` – API entrypoint wiring `api.create_app()`.
  - `docker-compose.yml` – local Postgres.
- `frontend/` – React/Vite/Leaflet heatmap UI.
