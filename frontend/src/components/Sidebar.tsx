import type { PropsWithChildren } from "react";
import { API_BASE } from "../utils";

type SidebarProps = PropsWithChildren<{
  queryInput: string;
  minTotalInput: number;
  isFetching: boolean;
  error: unknown;
  pointsCount: number;
  onQueryChange: (val: string) => void;
  onMinTotalChange: (val: number) => void;
  onSubmit: () => void;
}>;

export function Sidebar({
  queryInput,
  minTotalInput,
  isFetching,
  error,
  pointsCount,
  onQueryChange,
  onMinTotalChange,
  onSubmit,
  children,
}: SidebarProps) {
  return (
    <div className='sidebar'>
      <h3>Jobs Heatmap</h3>
      <label>Query</label>
      <input
        value={queryInput}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder='react developer'
      />
      <label>Min total</label>
      <input
        type='number'
        value={minTotalInput}
        onChange={(e) => onMinTotalChange(Number(e.target.value) || 0)}
      />
      <button onClick={onSubmit} disabled={isFetching}>
        {isFetching ? "Loading..." : "Load"}
      </button>
      {error && <div className='error'>{String((error as any)?.message || error)}</div>}
      <div className='summary'>Points: {pointsCount}</div>
      <div className='summary'>API: {API_BASE}</div>
      <div className='legend'>
        <div className='legend-row'>
          <span className='legend-swatch low' /> Low
        </div>
        <div className='legend-row'>
          <span className='legend-swatch mid' /> Mid
        </div>
        <div className='legend-row'>
          <span className='legend-swatch high' /> High
        </div>
      </div>
      {children}
    </div>
  );
}
