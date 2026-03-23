import "react-leaflet";
import type { CRS, LatLngBoundsExpression } from "leaflet";

declare module "react-leaflet" {
  interface MapContainerProps {
    crs?: CRS;
    bounds?: LatLngBoundsExpression;
    maxBounds?: LatLngBoundsExpression;
  }
}
