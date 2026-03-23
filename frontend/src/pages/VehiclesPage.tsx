import { useEffect, useMemo, useState } from "react";
import { api, API_BASE_URL } from "../api";

type Vehicle = {
  id: string;
  name?: string;
  brand?: string;
  damage?: number | null;
  wear?: number | null;
  operating_time?: number | null;
  is_leased?: boolean;
  property_state?: string | null;
  display_name?: string | null;
  ownership?: string | null;
  icon_url?: string | null;
};

function formatHours(value?: number | null) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(1);
}

function ownershipLabel(state?: string | null) {
  if (!state) return "Vlastněné";
  if (state === "MISSION") return "Zakázka";
  if (state === "LEASED") return "Leasing";
  return "Vlastněné";
}

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [leasedOnly, setLeasedOnly] = useState(false);
  const [hideDamaged, setHideDamaged] = useState(false);

  useEffect(() => {
    api.get("/vehicles").then((res) => setVehicles(res.data)).catch(() => setVehicles([]));
  }, []);

  const filtered = useMemo(() => {
    return vehicles.filter((v) => {
      if (leasedOnly && v.property_state !== "LEASED") return false;
      if (hideDamaged && (v.damage ?? 0) > 0.2) return false;
      return true;
    });
  }, [vehicles, leasedOnly, hideDamaged]);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Technika</h1>
        <p>Přehled strojů s přehledem opotřebení a hodin.</p>
      </header>
      <div className="controls">
        <label className="control">
          <input type="checkbox" checked={leasedOnly} onChange={(e) => setLeasedOnly(e.target.checked)} />
          Pouze leasing
        </label>
        <label className="control">
          <input type="checkbox" checked={hideDamaged} onChange={(e) => setHideDamaged(e.target.checked)} />
          Skrýt poškozené (damage &gt; 0.2)
        </label>
      </div>
      <div className="cards-grid">
        {filtered.length === 0 ? (
          <div className="panel">Žádná data o strojích.</div>
        ) : (
          filtered.map((v) => (
            <article key={v.id} className="card card--vehicle">
              <div className="card__icon" aria-hidden>
                {v.icon_url ? (
                  <img src={v.icon_url.startsWith("http") ? v.icon_url : `${API_BASE_URL}${v.icon_url}`} alt="" />
                ) : (
                  <span className="muted">🚜</span>
                )}
              </div>
              <div className="card__body">
                <h3>{v.display_name || v.name || "Neznámý stroj"}</h3>
                <p className="muted">{v.brand || ""}</p>
                <div className="card__meta">
                  <span>Hours: {formatHours(v.operating_time)}</span>
                  <span>Damage: {(v.damage ?? 0).toFixed(2)}</span>
                  <span>Wear: {(v.wear ?? 0).toFixed(2)}</span>
                  <span>{ownershipLabel(v.property_state)}</span>
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
