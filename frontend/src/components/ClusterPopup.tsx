import { Popup } from "react-leaflet";
import type { ClusteredPoint } from "../types";

type ClusterPopupProps = {
  point: ClusteredPoint;
  totalText: string;
  combineState?: { loading: boolean; total?: number; error?: string; perRoles?: { role: string; query: string; total: number; url?: string }[] };
};

export function ClusterPopup({ point: p, totalText, combineState }: ClusterPopupProps) {
  const hasRange = (p.members?.length || 0) > 1 && p.sum !== p.total;
  const perRoles = combineState?.perRoles || p.perRoles || [];
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
        {p.seniority_level && <div>Seniority: {p.seniority_level}</div>}
        {p.query && <div>Query: {p.query}</div>}
        {perRoles && perRoles.length > 0 && (
          <div style={{ marginTop: 6 }}>
            <div>Role links:</div>
            <ul style={{ paddingLeft: 16, margin: 4 }}>
              {perRoles.map((r) => (
                <li key={`${r.role}-${r.query}`}>
                  {r.role}: {r.total}
                  {r.url && (
                    <>
                      {" "}
                      <a href={r.url} target='_blank' rel='noreferrer'>
                        open
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
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
