#!/usr/bin/env bash
set -eo pipefail

# Sweep all US cities for predefined role queries (searchQuery) and seniority filters.
# Usage:
#   ./run_all.sh
# Required env:
#   JOBS_PG_URL="postgresql://user:pass@host:5432/db"
# Optional env overrides:
#   JOBS_SENIORITY_LEVELS="entry,mid,senior,all"   # comma-separated list
#   JOBS_CITY_LIMIT=0        # 0 = all (~1,700 cities)
#   JOBS_MIN_POPULATION=50000
#   JOBS_CONCURRENCY=4
#   JOBS_RADIUS_MILES=25
#   JOBS_PG_TABLE=city_counts
#   JOBS_GAZETTEER_PATH="data/2023_Gaz_place_national.txt"
#   JOBS_AUTO_RADIUS_FROM_POPULATION=0

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# Load .env if present so JOBS_PG_URL and other settings come from it
if [[ -f ".env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source ".env"
  set +a
fi

: "${JOBS_PG_URL:?Set JOBS_PG_URL to your Postgres URL}"

ROLE_PAIRS=(
  "software|Software Engineer"
  "frontend|Frontend Engineer"
  "backend|Backend Engineer"
  "fullstack|Full Stack Engineer"
  "devops|DevOps Engineer"
  "data|Data Engineer"
  "mobile|Mobile Developer"
)
QUERY="${JOBS_QUERY:-}"
SENIORITY_LEVELS="${JOBS_SENIORITY_LEVELS:-entry,mid,senior,all}"
CITY_LIMIT="${JOBS_CITY_LIMIT:-10}"
MIN_POP="${JOBS_MIN_POPULATION:-50000}"
CONCURRENCY="${JOBS_CONCURRENCY:-4}"
RADIUS="${JOBS_RADIUS_MILES:-25}"
TABLE="${JOBS_PG_TABLE:-city_counts}"
GAZ_PATH="${JOBS_GAZETTEER_PATH:-}"
AUTO_RADIUS="${JOBS_AUTO_RADIUS_FROM_POPULATION:-0}"

ARGS=(
  --pg-url "$JOBS_PG_URL"
  --pg-table "$TABLE"
  --city-limit "$CITY_LIMIT"
  --min-population "$MIN_POP"
  --concurrency "$CONCURRENCY"
  --radius-miles "$RADIUS"
  --pg-create-table
)

if [[ -n "$GAZ_PATH" ]]; then
  ARGS+=(--gazetteer-path "$GAZ_PATH")
fi

if [[ "$AUTO_RADIUS" == "1" || "$AUTO_RADIUS" == "true" ]]; then
  ARGS+=(--auto-radius-from-population)
fi

echo "Role queries: ${ROLE_PAIRS[*]}"
echo "Seniority sets: $SENIORITY_LEVELS"
echo "City limit: $CITY_LIMIT  Min pop: $MIN_POP  Concurrency: $CONCURRENCY"
echo "Radius: $RADIUS mi  Table: $TABLE"
if [[ -n "$GAZ_PATH" ]]; then
  echo "Using Gazetteer: $GAZ_PATH"
fi

IFS=',' read -r -a LEVEL_LIST <<< "$SENIORITY_LEVELS"

for pair in "${ROLE_PAIRS[@]}"; do
  role="${pair%%|*}"
  role_query="${pair#*|}"
  for level in "${LEVEL_LIST[@]}"; do
    level_trimmed="$(echo "$level" | xargs)"
    [[ -z "$level_trimmed" ]] && continue
    echo "---- Role: $role  Query: ${role_query} (seniority=$level_trimmed) ----"
    python main.py \
      --mode cities \
      --query "$role_query" \
      --seniority-level "$level_trimmed" \
      "${ARGS[@]}"
  done
done
