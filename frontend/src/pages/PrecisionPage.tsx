import { useEffect, useState } from "react";
import { api } from "../api";

type Precision = {
  id: string;
  amount_kg?: number | null;
  best_price?: number | null;
  game_year?: number | null;
  game_day?: number | null;
  source?: string | null;
};

export default function PrecisionPage() {
  const [rows, setRows] = useState<Precision[]>([]);

  useEffect(() => {
    api.get("/harvests")
      .then((res) => setRows((res.data || []).filter((r: Precision) => r.source === "precision")))
      .catch(() => setRows([]));
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Precision Farming</h1>
        <p>Výnosy a metriky z precision modulu.</p>
      </header>
      <div className="cards-grid">
        {rows.length === 0 ? (
          <article className="card">
            <h3>Data nejsou v savegame</h3>
            <p className="muted">Zatím nejsou uložené precision statistiky.</p>
          </article>
        ) : (
          rows.slice(0, 6).map((row) => (
            <article key={row.id} className="card">
              <h3>Rok {row.game_year ?? "-"}</h3>
              <p>Den: {row.game_day ?? "-"}</p>
              <p>Výnos: {row.amount_kg ? `${Math.round(row.amount_kg)} kg` : "-"}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
