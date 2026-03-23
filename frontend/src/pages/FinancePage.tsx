import { useEffect, useState } from "react";
import { api } from "../api";

export default function FinancePage() {
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    api.get("/finance").then((res) => setRows(res.data)).catch(() => setRows([]));
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Finance</h1>
        <p>Cashflow, výnosy a náklady v čase.</p>
      </header>
      <div className="cards-grid">
        {rows.length === 0 ? (
          <article className="card">
            <h3>Žádná data</h3>
            <p className="muted">Po prvním syncu se zobrazí finance.</p>
          </article>
        ) : (
          rows.slice(0, 6).map((row) => (
            <article key={row.id} className="card">
              <h3>Den {row.game_day ?? "-"}</h3>
              <p>Balance: {row.balance ?? "-"}</p>
              <p>Harvest: {row.harvest_income ?? "-"}</p>
              <p>Seeds: {row.purchase_seeds ?? "-"}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
