import type { PropsWithChildren } from "react";
import { API_BASE } from "../utils";

type SidebarProps = PropsWithChildren<{
  minTotalInput: number;
  isFetching: boolean;
  error: unknown;
  pointsCount: number;
  onMinTotalChange: (val: number) => void;
  onSubmit: () => void;
  roleOptions: { key: string; label: string }[];
  seniorityOptions: string[];
  selectedRoles: string[];
  selectedSeniorities: string[];
  onToggleRole: (role: string) => void;
  onToggleSeniority: (level: string) => void;
  onClearRoles: () => void;
  onClearSeniorities: () => void;
}>;

export function Sidebar({
  minTotalInput,
  isFetching,
  error,
  pointsCount,
  onMinTotalChange,
  onSubmit,
  children,
  roleOptions,
  seniorityOptions,
  selectedRoles,
  selectedSeniorities,
  onToggleRole,
  onToggleSeniority,
  onClearRoles,
  onClearSeniorities,
}: SidebarProps) {
  return (
    <div className='sidebar'>
      <h3>Jobs Heatmap</h3>
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
      <div className='section'>
        <div className='section-header'>
          <span>Roles</span>
          <button className='link-btn' onClick={onClearRoles}>
            clear
          </button>
        </div>
        <div className='chip-row'>
          {roleOptions.map((role) => {
            const active = selectedRoles.includes(role.key);
            return (
              <button
                key={role.key}
                className={`chip ${active ? "chip-active" : ""}`}
                onClick={() => onToggleRole(role.key)}
              >
                {role.label}
              </button>
            );
          })}
        </div>
      </div>
      <div className='section'>
        <div className='section-header'>
          <span>Seniority</span>
          <button className='link-btn' onClick={onClearSeniorities}>
            clear
          </button>
        </div>
        <div className='chip-row'>
          {seniorityOptions.map((level) => {
            const active = selectedSeniorities.includes(level);
            return (
              <button
                key={level}
                className={`chip ${active ? "chip-active" : ""}`}
                onClick={() => onToggleSeniority(level)}
              >
                {level}
              </button>
            );
          })}
        </div>
      </div>
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
