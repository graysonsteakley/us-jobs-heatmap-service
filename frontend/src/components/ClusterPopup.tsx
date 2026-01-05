import { Popup } from "react-leaflet";
import type { ClusteredPoint } from "../types";

type ClusterPopupProps = {
  point: ClusteredPoint;
  totalText: string;
  combineState?: { loading: boolean; total?: number; error?: string };
};

export function ClusterPopup({ point: p, totalText, combineState }: ClusterPopupProps) {
  const hasRange = (p.members?.length || 0) > 1 && p.sum !== p.total;
  return (
    <Popup>
      <div>
        <strong>
          {p.cities.join(", ")} ({p.states.join(", ")})
        </strong>
        <div>Total: {totalText}</div>
        {combineState?.error && <div className='error'>Err: {combineState.error}</div>}
        <div>
          Radius: {p.radius_miles?.toFixed ? p.radius_miles.toFixed(1) : p.radius_miles} mi
        </div>
        {p.query && <div>Query: {p.query}</div>}
        {p.hiring_cafe_url && (
          <div>
            <a href={p.hiring_cafe_url} target='_blank' rel='noreferrer'>
              Open on hiring.cafe
            </a>
          </div>
        )}
        {hasRange && (
          <div style={{ marginTop: 6 }}>
            <small>(Range shown while fetching; combined de-duped total loads automatically)</small>
          </div>
        )}
        {p.run_at && <div>Run: {p.run_at}</div>}
      </div>
    </Popup>
  );
}
