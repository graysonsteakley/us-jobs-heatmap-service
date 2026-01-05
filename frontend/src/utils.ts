import type { ClusterMember, ClusteredPoint, HeatPoint } from "./types";
import Supercluster from "supercluster";
import type { LatLngBounds } from "leaflet";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const MI_TO_METERS = 1609.344;

export function getColor(total: number, maxTotal: number): string {
  if (total <= 0 || maxTotal <= 0) return "rgba(180,180,180,0.25)";
  const t = Math.min(1, total / maxTotal);
  const stops = [
    { t: 0, color: [0, 120, 255] },
    { t: 0.2, color: [0, 200, 255] },
    { t: 0.4, color: [0, 200, 120] },
    { t: 0.6, color: [200, 200, 60] },
    { t: 0.8, color: [255, 140, 40] },
    { t: 1, color: [255, 0, 40] },
  ];
  let i = stops.findIndex((s) => t <= s.t);
  if (i <= 0) i = 1;
  const prev = stops[i - 1];
  const next = stops[i];
  const span = next.t - prev.t || 1;
  const ratio = (t - prev.t) / span;
  const interp = (a: number, b: number) => Math.round(a + (b - a) * ratio);
  const [r, g, b] = [
    interp(prev.color[0], next.color[0]),
    interp(prev.color[1], next.color[1]),
    interp(prev.color[2], next.color[2]),
  ];
  return `rgba(${r},${g},${b},0.55)`;
}

function buildClusterIndex(points: HeatPoint[]) {
  const features = points
    .filter((p) => (p.total || 0) > 0)
    .map((p) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] },
      properties: {
        members: [
          {
            city: p.city,
            state: p.state,
            lat: p.lat,
            lon: p.lon,
            radius_miles: p.radius_miles || 0,
            total: p.total || 0,
            query: p.query,
            run_at: p.run_at,
            hiring_cafe_url: p.hiring_cafe_url,
          },
        ],
      },
    }));

  const index = new Supercluster({
    radius: 80,
    maxZoom: 12,
    map: (props) => props,
    reduce: (accum: any, props: any) => {
      accum.members = [...(accum.members || []), ...(props.members || [])];
    },
  });
  index.load(features as any);
  return index;
}

export function clusterPoints(points: HeatPoint[], bounds: LatLngBounds | null, zoom: number): ClusteredPoint[] {
  const index = buildClusterIndex(points);
  const z = Math.max(0, Math.round(zoom || 0));
  const bbox = bounds
    ? [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]
    : [-180, -85, 180, 85];
  const clusters = index.getClusters(bbox as [number, number, number, number], z);
  return clusters.map((c: any) => {
    const [lon, lat] = c.geometry.coordinates;
    const props = c.properties || {};
    const members: ClusterMember[] = props.members || [];
    const total = members.reduce((m, mbr) => Math.max(m, mbr.total || 0), 0);
    const sum = members.reduce((s, mbr) => s + (mbr.total || 0), 0);
    const radius_miles = members.reduce((m, mbr) => Math.max(m, mbr.radius_miles || 0), 0);
    const cities = Array.from(new Set(members.map((m) => m.city)));
    const states = Array.from(new Set(members.map((m) => m.state)));
    const query = members[0]?.query || null;
    const run_at = members[0]?.run_at || null;
    const url = buildCombinedUrl(members, query);
    return {
      lat,
      lon,
      total,
      sum,
      radius_miles,
      query,
      run_at,
      cities: Array.from(new Set(cities)),
      states: Array.from(new Set(states)),
      hiring_cafe_url: url,
      members,
    };
  });
}

export function buildCombinedUrl(members: ClusterMember[], query: string | null) {
  if (!members.length) return undefined;
  const locations = members.map((m) => ({
    formatted_address: `${m.city}, ${m.state}, United States`,
    types: ["locality", "political"],
    geometry: { location: { lat: m.lat, lon: m.lon } },
    id: `city_${m.city.toLowerCase().replace(/\s+/g, "_")}_${m.state.toLowerCase()}`,
    address_components: [
      { long_name: m.city, short_name: m.city, types: ["locality", "political"] },
      { long_name: m.state, short_name: m.state, types: ["administrative_area_level_1", "political"] },
      { long_name: "United States", short_name: "US", types: ["country", "political"] },
    ],
    options: { radius_miles: m.radius_miles || 25, ignore_radius: false, radius: m.radius_miles || 25 },
  }));
  const searchState = {
    locations,
    workplaceTypes: ["Remote", "Hybrid", "Onsite"],
    defaultToUserLocation: false,
    searchQuery: query || "",
    dateFetchedPastNDays: 61,
    sortBy: "default",
  };
  const encoded = encodeURIComponent(JSON.stringify(searchState));
  return `https://hiring.cafe/?searchState=${encoded}`;
}
