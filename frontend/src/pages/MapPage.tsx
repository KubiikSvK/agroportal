import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ImageOverlay, MapContainer, Polygon, Popup, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, API_BASE_URL } from "../api";

const cropColors: Record<string, string> = {
  WHEAT: "#e4b83c",
  BARLEY: "#d2b55b",
  CANOLA: "#c9ce4b",
  CORN: "#e1a84d",
  SOYBEAN: "#a6c36f",
  POTATO: "#b08a6f",
  SUGARBEET: "#d79aa2",
};

const MAP_CONFIG = {
  sizeMeters: 2048,
  offsetX: 0,
  offsetY: 0,
  flipX: false,
  flipY: false,
};

type GeometryItem = {
  field_id: string;
  geometry_geojson: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
};

type Field = {
  id: string;
  fs_field_id: number;
  name: string;
  area_ha?: number | null;
  owned: boolean;
};

type Snapshot = {
  field_id: string;
  crop_type?: string | null;
  growth_state?: number | null;
  ground_type?: string | null;
  weed_state?: number | null;
  spray_level?: number | null;
  lime_level?: number | null;
  recorded_at?: string | null;
};

type Crop = {
  id: string;
  code: string;
  name: string;
  color?: string | null;
};

type Harvest = {
  id: string;
  field_id: string;
  crop_type?: string | null;
  amount_kg?: number | null;
  yield_per_ha?: number | null;
  game_year?: number | null;
  game_day?: number | null;
};

function loadImageSize(url: string): Promise<{ w: number; h: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => reject(new Error("image load failed"));
    img.src = url;
  });
}

export default function MapPage() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ w: number; h: number } | null>(null);
  const [mapMeters, setMapMeters] = useState<{ w: number; h: number } | null>(null);
  const [geometry, setGeometry] = useState<GeometryItem[]>([]);
  const [fields, setFields] = useState<Field[]>([]);
  const [snapshots, setSnapshots] = useState<Record<string, Snapshot>>({});
  const [snapshotsAll, setSnapshotsAll] = useState<Snapshot[]>([]);
  const [crops, setCrops] = useState<Record<string, Crop>>({});
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [cropFilter, setCropFilter] = useState<string>("ALL");
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedField, setSelectedField] = useState<Field | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);
  const [selectedHarvests, setSelectedHarvests] = useState<Harvest[]>([]);
  const imageRef = useRef<string | null>(null);
  const sizeRef = useRef<{ w: number; h: number } | null>(null);

  const load = useCallback(async (initial = false) => {
    if (initial) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    const [imgRes, fieldRes, snapRes, cropsRes, statusRes, geomRes] = await Promise.all([
      api.get("/maps/active-image"),
      api.get("/fields"),
      api.get("/snapshots"),
      api.get("/crops"),
      api.get("/sync/status"),
      api.get("/maps/geometry"),
    ]);

    const rawUrl = imgRes.data.url as string;
    const widthMeters = imgRes.data.map_width as number | null | undefined;
    const heightMeters = imgRes.data.map_height as number | null | undefined;
    if (typeof widthMeters === "number" && typeof heightMeters === "number") {
      setMapMeters({ w: widthMeters, h: heightMeters });
    } else {
      setMapMeters(null);
    }
    const imgUrl = rawUrl.startsWith("http") ? rawUrl : `${API_BASE_URL}${rawUrl}`;
    if (imageRef.current !== imgUrl) {
      imageRef.current = imgUrl;
      setImageUrl(imgUrl);
      const size = await loadImageSize(imgUrl);
      sizeRef.current = size;
      setImageSize(size);
    } else if (sizeRef.current) {
      setImageSize(sizeRef.current);
    }

    setGeometry(geomRes.data);
    setFields(fieldRes.data);
    setSyncStatus(statusRes.data);

    const latest: Record<string, Snapshot> = {};
    const all = snapRes.data as Snapshot[];
    for (const item of all) {
      if (!latest[item.field_id]) {
        latest[item.field_id] = item;
      }
    }
    setSnapshots(latest);
    setSnapshotsAll(all);

    const cropMap: Record<string, Crop> = {};
    for (const crop of cropsRes.data as Crop[]) {
      cropMap[crop.code] = crop;
    }
    setCrops(cropMap);
    if (initial) {
      setLoading(false);
    } else {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const guardedLoad = async () => {
      if (!isMounted) return;
      try {
        await load(true);
      } catch {
        if (isMounted) setLoading(false);
      }
    };
    guardedLoad();
    return () => {
      isMounted = false;
    };
  }, [load, refreshKey]);

  const bounds = useMemo(() => {
    if (!imageSize) return null;
    const sizeX = mapMeters?.w ?? MAP_CONFIG.sizeMeters;
    const sizeY = mapMeters?.h ?? MAP_CONFIG.sizeMeters;
    const padX = Math.max((imageSize.w - sizeX) / 2, 0);
    const padY = Math.max((imageSize.h - sizeY) / 2, 0);
    const halfX = sizeX / 2;
    const halfY = sizeY / 2;
    return new L.LatLngBounds([
      [-(halfY + padY), -(halfX + padX)],
      [halfY + padY, halfX + padX],
    ]);
  }, [imageSize, mapMeters]);

  const toMapCoords = useCallback(
    (x: number, y: number) => {
      let mx = x + MAP_CONFIG.offsetX;
      let my = y + MAP_CONFIG.offsetY;
      if (MAP_CONFIG.flipX) mx = -mx;
      if (MAP_CONFIG.flipY) my = -my;
      return [-my, mx] as [number, number];
    },
    []
  );

  const fieldById = useMemo(() => {
    const map: Record<string, Field> = {};
    fields.forEach((f) => {
      map[f.id] = f;
    });
    return map;
  }, [fields]);

  const cropOptions = useMemo(() => {
    const set = new Set<string>();
    Object.values(snapshots).forEach((s) => {
      if (s.crop_type) set.add(s.crop_type);
    });
    return ["ALL", ...Array.from(set)];
  }, [snapshots]);

  const openFieldDetail = async (field: Field | undefined) => {
    if (!field) return;
    setSelectedField(field);
    try {
      const [planRes, harvestRes] = await Promise.all([
        api.get(`/rotation/plan?years=3&field_id=${field.id}`),
        api.get(`/harvests?field_id=${field.id}`),
      ]);
      setSelectedPlan(planRes.data?.[0] || null);
      setSelectedHarvests(harvestRes.data || []);
    } catch {
      setSelectedPlan(null);
      setSelectedHarvests([]);
    }
  };


  if (loading) {
    return (
      <section className="page">
        <header className="page__header">
          <h1>Mapa polí</h1>
          <p>Načítám mapu a vrstvy…</p>
        </header>
      </section>
    );
  }

  if (!imageUrl || !bounds) {
    return (
      <section className="page">
        <header className="page__header">
          <h1>Mapa polí</h1>
          <p>Mapa není k dispozici. Nahraj mapový obrázek do backendu.</p>
        </header>
        <div className="panel">
          <p className="muted">
            Tip: spusť import mapy do API a pak se sem vrať.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <header className="page__header">
        <h1>Mapa polí</h1>
        <p>
          Klikni na pole pro detail aktuálního stavu.
          {syncStatus?.status === "ok" && (
            <span className="muted"> Poslední sync: den {syncStatus.game_day}, rok {syncStatus.game_year}</span>
          )}
          {refreshing && <span className="muted"> · Aktualizuji data…</span>}
        </p>
      </header>
      <div className="controls">
        <label className="control">
          <input type="checkbox" checked={ownedOnly} onChange={(e) => setOwnedOnly(e.target.checked)} />
          Pouze vlastněná pole
        </label>
        <label className="control">
          Plodina:
          <select value={cropFilter} onChange={(e) => setCropFilter(e.target.value)}>
            {cropOptions.map((opt) => (
              <option key={opt} value={opt}>
                {crops[opt]?.name || opt}
              </option>
            ))}
          </select>
        </label>
        <button className="button" onClick={() => setRefreshKey((v) => v + 1)}>Refresh</button>
      </div>
      <div className="legend">
        {Object.values(crops).map((crop) => (
          <span key={crop.id} className="legend__item">
            <span className="legend__swatch" style={{ background: crop.color || cropColors[crop.code] || "#999" }} />
            {crop.name}
          </span>
        ))}
      </div>
      <div className="map-container">
        <MapContainer
          crs={L.CRS.Simple}
          bounds={bounds}
          maxBounds={bounds}
          zoom={-1}
          minZoom={-3}
          maxZoom={2}
          style={{ height: "100%", width: "100%" }}
        >
          <ImageOverlay url={imageUrl} bounds={bounds} />
          {geometry.flatMap((item) => {
            const field = fieldById[item.field_id];
            const snapshot = snapshots[item.field_id];
            const crop = snapshot?.crop_type || "UNKNOWN";
            const color = crops[crop]?.color || cropColors[crop] || "#6c757d";

            if (ownedOnly && field && !field.owned) return [];
            if (cropFilter !== "ALL" && crop !== cropFilter) return [];

            const polygons: [number, number][][] = [];
            if (item.geometry_geojson.type === "Polygon") {
              polygons.push(
                (item.geometry_geojson.coordinates[0] as [number, number][])
                  .map(([x, y]) => toMapCoords(x, y))
              );
            }
            if (item.geometry_geojson.type === "MultiPolygon") {
              for (const poly of item.geometry_geojson.coordinates as [number, number][][][]) {
                polygons.push(poly[0].map(([x, y]) => toMapCoords(x, y)));
              }
            }

            return polygons.map((positions, idx) => (
              <Polygon
                key={`${item.field_id}-${idx}`}
                positions={positions}
                pathOptions={{ color, weight: 2, fillOpacity: 0.35 }}
                eventHandlers={{
                  click: () => openFieldDetail(field),
                }}
              >
                <Tooltip sticky>
                  <strong>{field?.name || `Pole ${field?.fs_field_id ?? ""}`}</strong>
                  <div>Plodina: {crops[crop]?.name || crop}</div>
                </Tooltip>
                <Popup>
                  <strong>{field?.name || `Pole ${field?.fs_field_id ?? ""}`}</strong>
                  <div>Plodina: {crops[crop]?.name || crop}</div>
                  <div>Growth: {snapshot?.growth_state ?? "-"}</div>
                  <div>Weed: {snapshot?.weed_state ?? "-"}</div>
                  <div>Lime: {snapshot?.lime_level ?? "-"}</div>
                </Popup>
              </Polygon>
            ));
          })}
        </MapContainer>
      </div>
      {selectedField && (
        <aside className="detail-panel">
          <div className="detail-panel__header">
            <div>
              <h2>{selectedField.name || `Pole ${selectedField.fs_field_id}`}</h2>
              <p className="muted">Aktuální stav a historie</p>
            </div>
            <button className="button" onClick={() => setSelectedField(null)}>Zavřít</button>
          </div>
          <div className="detail-panel__section">
            <h3>Aktuální stav</h3>
            <div className="detail-grid">
              <span>Plodina</span>
              <strong>{crops[snapshots[selectedField.id]?.crop_type || ""]?.name || snapshots[selectedField.id]?.crop_type || "-"}</strong>
              <span>Růst</span>
              <strong>{snapshots[selectedField.id]?.growth_state ?? "-"}</strong>
              <span>Plevel</span>
              <strong>{snapshots[selectedField.id]?.weed_state ?? "-"}</strong>
              <span>Hnojení</span>
              <strong>{snapshots[selectedField.id]?.spray_level ?? "-"}</strong>
              <span>Vápno</span>
              <strong>{snapshots[selectedField.id]?.lime_level ?? "-"}</strong>
            </div>
          </div>
          <div className="detail-panel__section">
            <h3>Historie sadby</h3>
            {snapshotsAll.filter((s) => s.field_id === selectedField.id).slice(0, 5).length ? (
              <div className="detail-list">
                {snapshotsAll
                  .filter((s) => s.field_id === selectedField.id)
                  .slice(0, 5)
                  .map((s, idx) => (
                    <div key={`${s.field_id}-${idx}`} className="detail-row">
                      <span>{s.recorded_at ? new Date(s.recorded_at).toLocaleDateString("cs-CZ") : "-"}</span>
                      <strong>{crops[s.crop_type || ""]?.name || s.crop_type || "Neznámá"}</strong>
                      <span className="muted">Růst {s.growth_state ?? "-"}</span>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="muted">Zatím bez historie sadby.</p>
            )}
          </div>
          <div className="detail-panel__section">
            <h3>Crop rotation plán</h3>
            {selectedPlan?.plan?.length ? (
              <div className="detail-list">
                {selectedPlan.plan.map((p: any) => (
                  <div key={p.year} className="detail-row">
                    <span>Rok {p.year}</span>
                    <strong>{p.name}</strong>
                    <span className="muted">x{p.multiplier.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">Zatím bez plánu.</p>
            )}
          </div>
          <div className="detail-panel__section">
            <h3>Sklizně</h3>
            {selectedHarvests.length ? (
              <div className="detail-list">
                {selectedHarvests.slice(0, 5).map((h) => (
                  <div key={h.id} className="detail-row">
                    <span>Rok {h.game_year ?? "-"}</span>
                    <strong>{crops[h.crop_type || ""]?.name || h.crop_type || "Neznámá"}</strong>
                    <span className="muted">{h.amount_kg ? `${Math.round(h.amount_kg)} kg` : "-"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">Žádné záznamy sklizně.</p>
            )}
          </div>
        </aside>
      )}
    </section>
  );
}
