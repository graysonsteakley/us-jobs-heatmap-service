import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Circle, MapContainer, TileLayer } from "react-leaflet";
import type { LatLngBounds } from "leaflet";
import "leaflet/dist/leaflet.css";
import "./index.css";
import { Sidebar } from "./components/Sidebar";
import { ClusterPopup } from "./components/ClusterPopup";
import { MapEventsHandler } from "./components/MapEventsHandler";
import { API_BASE, MI_TO_METERS, clusterPoints, getColor } from "./utils";
import type { ClusteredPoint, HeatPoint } from "./types";

type CombinedState = Record<
  string,
  { loading: boolean; total?: number; error?: string }
>;

export default function App() {
  const queryClient = useQueryClient();
  const [queryInput, setQueryInput] = useState("react developer");
  const [minTotalInput, setMinTotalInput] = useState(0);
  const [params, setParams] = useState({
    query: "react developer",
    minTotal: 0,
  });
  const [mapState, setMapState] = useState<{
    bounds: LatLngBounds | null;
    zoom: number;
  }>({
    bounds: null,
    zoom: 4,
  });
  const [combined, setCombined] = useState<CombinedState>({});

  const mapCenter = useMemo(() => ({ lat: 39.8283, lng: -98.5795 }), []);

  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["heatmap", params],
    queryFn: async (): Promise<HeatPoint[]> => {
      const qs = new URLSearchParams();
      if (params.query.trim()) qs.set("query", params.query.trim());
      qs.set("min_total", String(params.minTotal));
      qs.set("limit", "1000");
      const res = await fetch(`${API_BASE}/heatmap?${qs.toString()}`);
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      return json.points || [];
    },
    placeholderData: (prev) => prev,
  });

  const points = data || [];
  const clusters: ClusteredPoint[] = useMemo(
    () => clusterPoints(points, mapState.bounds, mapState.zoom),
    [points, mapState]
  );
  const maxTotal = clusters.reduce((m, p) => Math.max(m, p.total || 0), 0);

  const clusterCacheKey = useCallback(
    (cluster: ClusteredPoint) => [
      "cluster-combined",
      cluster.query || "",
      cluster.members
        ?.map((m) => `${m.city}-${m.state}-${m.lat}-${m.lon}-${m.radius_miles}`)
        .join("|"),
    ],
    []
  );

  const fetchCombined = useCallback(
    async (key: string, cluster: ClusteredPoint) => {
      if (!cluster.members || cluster.members.length <= 1) return;
      if (combined[key]?.total !== undefined || combined[key]?.loading) return;

      const cacheKey = clusterCacheKey(cluster);
      const cached = queryClient.getQueryData<{ total?: number }>(cacheKey);
      if (cached && cached.total !== undefined) {
        setCombined((s) => ({
          ...s,
          [key]: { loading: false, total: cached.total },
        }));
        return;
      }

      setCombined((s) => ({ ...s, [key]: { loading: true } }));
      try {
        const json = await queryClient.fetchQuery({
          queryKey: cacheKey,
          queryFn: async () => {
            const res = await fetch(
              `${API_BASE.replace(/\/$/, "")}/cluster-count`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  query: cluster.query,
                  members: cluster.members,
                }),
              }
            );
            if (!res.ok) throw new Error(await res.text());
            return res.json() as Promise<{ total?: number }>;
          },
          staleTime: 5 * 60 * 1000,
        });
        setCombined((s) => ({
          ...s,
          [key]: { loading: false, total: json.total },
        }));
      } catch (e: any) {
        setCombined((s) => ({
          ...s,
          [key]: { loading: false, error: e?.message || "error" },
        }));
      }
    },
    [clusterCacheKey, combined, queryClient]
  );

  return (
    <div className='layout'>
      <Sidebar
        queryInput={queryInput}
        minTotalInput={minTotalInput}
        isFetching={isFetching}
        error={error}
        pointsCount={points.length}
        onQueryChange={setQueryInput}
        onMinTotalChange={setMinTotalInput}
        onSubmit={() => {
          setParams({ query: queryInput, minTotal: minTotalInput });
          refetch();
        }}
      />
      <div className='map-wrap'>
        <MapContainer
          center={mapCenter}
          zoom={4}
          zoomControl
          scrollWheelZoom
          style={{ height: "100vh", width: "100%" }}
        >
          <TileLayer
            url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
            attribution='&copy; OpenStreetMap contributors'
          />
          <MapEventsHandler onChange={(state) => setMapState(state)} />
          {clusters.map((p, idx) => {
            if (!p.total || p.total <= 0) return null;
            const radiusMeters = (p.radius_miles || 10) * MI_TO_METERS;
            const color = getColor(p.total || 0, maxTotal);
            const key = `${p.lat}-${p.lon}-${idx}`;
            const combineState = combined[key];
            const hasRange = (p.members?.length || 0) > 1 && p.sum !== p.total;
            const totalText = combineState?.loading
              ? hasRange
                ? `${p.total}–${p.sum} (fetching...)`
                : `${p.total} (fetching...)`
              : combineState?.total !== undefined
              ? `${combineState.total}`
              : hasRange
              ? `${p.total}–${p.sum}`
              : `${p.total}`;

            return (
              <Circle
                key={key}
                center={[p.lat, p.lon]}
                radius={radiusMeters}
                pathOptions={{
                  color,
                  weight: 1,
                  fillColor: color,
                  fillOpacity: 0.6,
                }}
                eventHandlers={{ popupopen: () => fetchCombined(key, p) }}
              >
                <ClusterPopup
                  point={p}
                  totalText={totalText}
                  combineState={combineState}
                />
              </Circle>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
