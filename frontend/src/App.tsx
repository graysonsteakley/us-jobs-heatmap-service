import { useCallback, useEffect, useMemo, useState } from "react";
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
  { loading: boolean; total?: number; error?: string; perRoles?: { role: string; query: string; total: number; url?: string }[] }
>;

const SENIORITY_OPTIONS = ["entry", "mid", "senior", "all"];
const ROLE_PRESETS: { key: string; label: string; query: string }[] = [
  { key: "software", label: "Software", query: "Software Engineer" },
  { key: "frontend", label: "Frontend", query: "Frontend Engineer" },
  { key: "backend", label: "Backend", query: "Backend Engineer" },
  { key: "fullstack", label: "Fullstack", query: "Full Stack Engineer" },
  { key: "devops", label: "DevOps", query: "DevOps Engineer" },
  { key: "data", label: "Data", query: "Data Engineer" },
  { key: "mobile", label: "Mobile", query: "Mobile Developer" },
];

export default function App() {
  const queryClient = useQueryClient();
  const [minTotalInput, setMinTotalInput] = useState(0);
  const [selectedSeniorities, setSelectedSeniorities] = useState<string[]>(["all"]);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [params, setParams] = useState({
    minTotal: 0,
    roles: [] as string[],
    seniorities: ["all"] as string[],
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
      const rolesToFetch = selectedRoles.length ? selectedRoles : ROLE_PRESETS.map((p) => p.key);
      const seniorities = params.seniorities || [];
      const pointsByCity: Record<string, any> = {};

      for (const roleKey of rolesToFetch) {
        const preset = ROLE_PRESETS.find((p) => p.key === roleKey);
        if (!preset) continue;
        const qs = new URLSearchParams();
        qs.set("query", preset.query);
        if (!(seniorities.length === 1 && seniorities[0] === "all")) {
          seniorities.forEach((s) => qs.append("seniority", s));
        }
        qs.set("min_total", String(params.minTotal));
        qs.set("limit", "1000");
        const res = await fetch(`${API_BASE}/heatmap?${qs.toString()}`);
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        const pts: HeatPoint[] = json.points || [];
        pts.forEach((p) => {
          const key = `${p.city}|${p.state}`;
          const existing = pointsByCity[key];
          const roleLink = {
            role: preset.label,
            query: preset.query,
            total: p.total,
            url: p.hiring_cafe_url,
          };
          if (!existing) {
            pointsByCity[key] = {
              ...p,
              total: p.total,
              perRoles: [roleLink],
            };
          } else {
            const perMap = new Map(existing.perRoles?.map((r: any) => [r.role, r]));
            const prev = perMap.get(roleLink.role);
            if (!prev || (roleLink.total ?? 0) > (prev.total ?? 0)) {
              perMap.set(roleLink.role, roleLink);
            }
            const merged = Array.from(perMap.values());
            existing.perRoles = merged;
            existing.total = merged.reduce((sum, r) => sum + (r.total || 0), 0);
          }
        });
      }
      return Object.values(pointsByCity) as HeatPoint[];
    },
    placeholderData: (prev) => prev,
  });

  const points = data || [];
  const clusters: ClusteredPoint[] = useMemo(
    () => clusterPoints(points, mapState.bounds, mapState.zoom),
    [points, mapState]
  );
  const maxTotal = clusters.reduce((m, p) => Math.max(m, p.total || 0), 0);

  // Reset combined cache when filters change
  useEffect(() => {
    setCombined({});
  }, [params.minTotal, params.seniorities, params.roles]);

  const clusterCacheKey = useCallback(
    (cluster: ClusteredPoint) => [
      "cluster-combined",
      cluster.query || "",
      cluster.seniority_level || "",
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
                  queries: cluster.perRoles?.map((r) => r.query).filter(Boolean),
                  seniority_level: cluster.seniority_level,
                  members: cluster.members,
                }),
              }
            );
            if (!res.ok) throw new Error(await res.text());
            return res.json() as Promise<{ total?: number }>;
          },
          staleTime: 5 * 60 * 1000,
        });
        const perMap = new Map(
          (cluster.perRoles || []).map((r) => [r.query, { ...r }])
        );
        if (json.breakdown) {
          json.breakdown.forEach((b: any) => {
            const entry = perMap.get(b.query);
            if (entry) entry.total = b.total;
          });
        }
        const perRoles = Array.from(perMap.values());
        setCombined((s) => ({
          ...s,
          [key]: { loading: false, total: json.total, perRoles },
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
        minTotalInput={minTotalInput}
        isFetching={isFetching}
        error={error}
        pointsCount={points.length}
        onMinTotalChange={setMinTotalInput}
        onSubmit={() => {
          setParams({
            minTotal: minTotalInput,
            roles: selectedRoles,
            seniorities: selectedSeniorities,
          });
          refetch();
        }}
        roleOptions={ROLE_PRESETS}
        seniorityOptions={SENIORITY_OPTIONS}
        selectedRoles={selectedRoles}
        selectedSeniorities={selectedSeniorities}
        onToggleRole={(roleKey) => {
          setSelectedRoles((prev) =>
            prev.includes(roleKey) ? prev.filter((r) => r !== roleKey) : [...prev, roleKey]
          );
        }}
        onToggleSeniority={(level) => {
          setSelectedSeniorities((prev) => {
            if (level === "all") return ["all"];
            const next = prev.filter((l) => l !== "all");
            let updated = next.includes(level) ? next.filter((l) => l !== level) : [...next, level];
            // If all three granular levels are selected, collapse to "all"
            const hasAllGranular =
              updated.includes("entry") && updated.includes("mid") && updated.includes("senior");
            if (hasAllGranular || updated.length === 0) {
              updated = ["all"];
            }
            return updated;
          });
        }}
        onClearRoles={() => setSelectedRoles([])}
        onClearSeniorities={() => setSelectedSeniorities(["all"])}
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
            const key = `${p.lat}-${p.lon}-${idx}-${p.seniority_level || "na"}-${p.query || ""}`;
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
