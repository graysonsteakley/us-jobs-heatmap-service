import { useRef } from "react";
import { useMapEvents } from "react-leaflet";
import type { LatLngBounds } from "leaflet";

type MapEventsProps = {
  onChange: (state: { bounds: LatLngBounds | null; zoom: number }) => void;
};

export function MapEventsHandler({ onChange }: MapEventsProps) {
  const last = useRef<{ b?: string; z?: number }>({});
  useMapEvents({
    moveend(e) {
      const b = e.target.getBounds();
      const z = e.target.getZoom();
      const key = `${b.getSouthWest().lat.toFixed(4)},${b.getSouthWest().lng.toFixed(4)},${b.getNorthEast().lat.toFixed(4)},${b.getNorthEast().lng.toFixed(4)}`;
      if (last.current.b !== key || last.current.z !== z) {
        last.current = { b: key, z };
        onChange({ bounds: b, zoom: z });
      }
    },
    zoomend(e) {
      const b = e.target.getBounds();
      const z = e.target.getZoom();
      const key = `${b.getSouthWest().lat.toFixed(4)},${b.getSouthWest().lng.toFixed(4)},${b.getNorthEast().lat.toFixed(4)},${b.getNorthEast().lng.toFixed(4)}`;
      if (last.current.b !== key || last.current.z !== z) {
        last.current = { b: key, z };
        onChange({ bounds: b, zoom: z });
      }
    },
  });
  return null;
}
