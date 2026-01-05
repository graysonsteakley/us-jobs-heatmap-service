import { useMapEvents } from "react-leaflet";
import type { LatLngBounds } from "leaflet";

type MapEventsProps = {
  onChange: (state: { bounds: LatLngBounds | null; zoom: number }) => void;
};

export function MapEventsHandler({ onChange }: MapEventsProps) {
  useMapEvents({
    moveend(e) {
      onChange({ bounds: e.target.getBounds(), zoom: e.target.getZoom() });
    },
    zoomend(e) {
      onChange({ bounds: e.target.getBounds(), zoom: e.target.getZoom() });
    },
  });
  return null;
}
