import { useEffect, useState } from "react";
import { api } from "../api";
import cropTranslations from "../i18n/crops.cs.json";

type Recommendation = {
  code: string;
  name: string;
  multiplier: number;
  detail: Record<string, number>;
};

type RotationRow = {
  field_id: string;
  fs_field_id: number;
  name: string;
  current_crop?: string | null;
  history: string[];
  recommendations: Recommendation[];
};

type RotationPlan = {
  field_id: string;
  fs_field_id: number;
  name: string;
  history: string[];
  plan: { year: number; code: string; name: string; multiplier: number }[];
};

export default function RotationPage() {
  const cropNames = cropTranslations as Record<string, string>;
  const [data, setData] = useState<RotationRow[]>([]);
  const [plans, setPlans] = useState<Record<string, RotationPlan>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [recRes, planRes] = await Promise.all([
          api.get("/rotation/recommendations?limit=5"),
          api.get("/rotation/plan?years=3"),
        ]);
        if (mounted) {
          setData(recRes.data);
          const map: Record<string, RotationPlan> = {};
          (planRes.data as RotationPlan[]).forEach((p) => {
            map[p.field_id] = p;
          });
          setPlans(map);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Osevní plán</h1>
        <p>Rotace plodin podle modifikace Crop Rotation a maximální výnosnosti.</p>
      </header>
      {loading ? (
        <div className="cards-grid">
          <article className="card">
            <h3>Načítám data</h3>
            <p className="muted">Zpracovávám historii polí a doporučení plodin.</p>
          </article>
        </div>
      ) : (
        <div className="cards-grid">
          {data.map((row) => (
            <article key={row.field_id} className="card">
              <div className="card__title-row">
                <div>
                  <h3>{row.name || `Pole ${row.fs_field_id}`}</h3>
                  <p className="muted">
                    Aktuálně: {cropNames[row.current_crop || ""] || row.current_crop || "Neznámé"} · Historie:{" "}
                    {row.history.map((h) => cropNames[h] || h).join(" → ") || "—"}
                  </p>
                </div>
                <span className="badge">Max výnos</span>
              </div>
              <div className="list">
                {row.recommendations.map((rec) => (
                  <div key={rec.code} className="list__row">
                    <div>
                      <strong>{cropNames[rec.code] || rec.name}</strong>
                      <div className="muted">Koeficient: {rec.multiplier.toFixed(2)}</div>
                    </div>
                    <div className="pill">{rec.code}</div>
                  </div>
                ))}
              </div>
              {plans[row.field_id]?.plan?.length ? (
                <div className="plan">
                  <div className="plan__title">Plán další 3 roky</div>
                  <div className="plan__rows">
                    {plans[row.field_id].plan.map((item) => (
                      <div key={item.year} className="plan__row">
                        <span>Rok {item.year}</span>
                        <strong>{cropNames[item.code] || item.name}</strong>
                        <span className="muted">x{item.multiplier.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              <p className="muted small">
                Kombinujeme přestávky v rotaci, předplodiny a mono-kulturu. Výnos je predikovaný pro další sezónu.
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
