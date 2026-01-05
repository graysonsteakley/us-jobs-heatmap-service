export type HeatPoint = {
  city: string;
  state: string;
  state_name: string;
  lat: number;
  lon: number;
  radius_miles: number | null;
  total: number;
  query: string | null;
  seniority_level?: string | null;
  run_at: string | null;
  hiring_cafe_url?: string;
  perRoles?: { role: string; query: string; total: number; url?: string }[];
};

export type ClusterMember = {
  city: string;
  state: string;
  lat: number;
  lon: number;
  radius_miles: number;
  total: number;
  query: string | null;
  seniority_level?: string | null;
  run_at: string | null;
  hiring_cafe_url?: string;
  perRoles?: { role: string; query: string; total: number; url?: string }[];
};

export type ClusteredPoint = {
  lat: number;
  lon: number;
  total: number; // max member total
  sum: number; // sum of member totals
  radius_miles: number | null;
  query: string | null;
  seniority_level?: string | null;
  run_at: string | null;
  cities: string[];
  states: string[];
  hiring_cafe_url?: string;
  members?: ClusterMember[];
  perRoles?: { role: string; query: string; total: number; url?: string }[];
};
