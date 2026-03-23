import { useEffect, useState } from "react";
import { api } from "../api";

export default function WeatherPage() {
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    api.get("/weather").then((res) => setRows(res.data)).catch(() => setRows([]));
  }, []);

  return (
    <section className="page">
      <header className="page__header">
        <h1>Počasí</h1>
        <p>Výhled podle posledního syncu a sezóny.</p>
      </header>
      <div className="cards-grid">
        {rows.length === 0 ? (
          <article className="card">
            <h3>Data nejsou v savegame</h3>
            <p className="muted">V aktuálním save nejsou uložené záznamy počasí.</p>
          </article>
        ) : (
          rows.map((row) => (
            <article key={row.id} className="card">
              <h3>{row.condition || "Unknown"}</h3>
              <p>Sezóna: {row.season || "-"}</p>
              <p>Den: {row.game_day ?? "-"}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
