import { useEffect, useRef, useState } from "react";
import { api } from "../api";

function formatMoney(value?: number | null) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("cs-CZ", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function friendlyMapName(mapId?: string | null, mapTitle?: string | null) {
  if (mapTitle) return mapTitle;
  if (!mapId) return "-";
  const name = mapId.split(".")[0]?.replace(/_/g, " ") ?? mapId;
  return name;
}

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null);
  const [apiKey, setApiKey] = useState(localStorage.getItem("agro_api_key") || "");
  const [saveFile, setSaveFile] = useState<File | null>(null);
  const [mapFile, setMapFile] = useState<File | null>(null);
  const [mapZip, setMapZip] = useState<File | null>(null);
  const [saveZip, setSaveZip] = useState<File | null>(null);
  const [mapId, setMapId] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [progressSteps, setProgressSteps] = useState<{ label: string; state: "pending" | "active" | "done" }[] | null>(null);
  const progressTimer = useRef<number | null>(null);
  const pollTimer = useRef<number | null>(null);
  const [notices, setNotices] = useState<{ id: number; type: "ok" | "error" | "info"; message: string }[]>([]);
  const [deployMode, setDeployMode] = useState<"push" | "replace">("replace");

  useEffect(() => {
    const load = () => api.get("/sync/status").then((res) => setStatus(res.data)).catch(() => setStatus(null));
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const persistKey = (value: string) => {
    setApiKey(value);
    localStorage.setItem("agro_api_key", value);
  };

  const pushNotice = (type: "ok" | "error" | "info", message: string) => {
    setNotices((prev) => [{ id: Date.now(), type, message }, ...prev].slice(0, 4));
  };

  const stopProgress = () => {
    if (progressTimer.current) {
      window.clearInterval(progressTimer.current);
      progressTimer.current = null;
    }
    if (pollTimer.current) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setProgress(null);
  };

  const startStep = (label: string, speedMs = 140, auto = true) => {
    setStatusLine(label);
    setProgress(0);
    if (progressTimer.current) {
      window.clearInterval(progressTimer.current);
      progressTimer.current = null;
    }
    if (auto) {
      progressTimer.current = window.setInterval(() => {
        setProgress((prev) => {
          if (prev === null) return 0;
          const next = Math.min(prev + 4, 90);
          return next;
        });
      }, speedMs);
    }
  };

  const errorMessage = (err: any, fallback: string) => {
    const detail = err?.response?.data?.detail;
    if (detail) return typeof detail === "string" ? detail : JSON.stringify(detail);
    return fallback;
  };

  const setStepState = (index: number) => {
    setProgressSteps((prev) => {
      if (!prev) return prev;
      return prev.map((s, i) => ({
        ...s,
        state: i < index ? "done" : i === index ? "active" : "pending",
      }));
    });
  };

  const forceSync = async () => {
    setBusy(true);
    startStep("Synchronizuji uložený savegame…");
    try {
      await api.post("/sync/reingest");
      setProgress(100);
      const res = await api.get("/sync/status");
      setStatus(res.data);
      pushNotice("ok", "Synchronizace dokončena.");
    } finally {
      setStatusLine(null);
      stopProgress();
      setProgressSteps(null);
      setBusy(false);
    }
  };

  const uploadSave = async (mode: "push" | "replace") => {
    if (!saveFile) return;
    setBusy(true);
    startStep(mode === "replace" ? "Nahrávám a nahrazuji savegame…" : "Nahrávám savegame…");
    try {
      const data = new FormData();
      data.append("file", saveFile);
      const headers: Record<string, string> = { "Content-Type": "multipart/form-data" };
      if (apiKey) headers["x-api-key"] = apiKey;
      await api.post(`/sync/${mode}`, data, { headers });
      setProgress(100);
      const res = await api.get("/sync/status");
      setStatus(res.data);
      pushNotice("ok", mode === "replace" ? "Savegame nahrazen." : "Savegame nahrán.");
    } catch (err) {
      pushNotice("error", errorMessage(err, "Nahrání savegame selhalo."));
    } finally {
      setStatusLine(null);
      stopProgress();
      setProgressSteps(null);
      setBusy(false);
    }
  };

  const uploadMap = async () => {
    if (!mapFile) return;
    setBusy(true);
    startStep("Nahrávám mapu…");
    try {
      const data = new FormData();
      data.append("file", mapFile);
      const query = mapId ? `?map_id=${encodeURIComponent(mapId)}` : "";
      await api.post(`/maps/image/upload${query}`, data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setProgress(100);
      pushNotice("ok", "Mapa nahrána.");
    } catch (err) {
      pushNotice("error", errorMessage(err, "Nahrání mapy selhalo."));
    } finally {
      setStatusLine(null);
      stopProgress();
      setProgressSteps(null);
      setBusy(false);
    }
  };

  const deployBundle = async () => {
    if (!mapZip || !saveZip) return;
    setBusy(true);
    startStep("Nahrávám bundle mapy + savegame…", 140, false);
    setProgressSteps([
      { label: "Upload bundle", state: "active" },
      { label: "Ingest savegame", state: "pending" },
      { label: "Import I3D", state: "pending" },
    ]);
    try {
      const data = new FormData();
      data.append("map_zip", mapZip);
      data.append("save_zip", saveZip);
      data.append("mode", deployMode);
      if (mapId) data.append("map_id", mapId);
      data.append("import_i3d", "true");

      const headers: Record<string, string> = { "Content-Type": "multipart/form-data" };
      if (apiKey) headers["x-api-key"] = apiKey;
      const response = await api.post("/sync/deploy", data, {
        headers,
        onUploadProgress: (evt) => {
          if (!evt.total) return;
          const percent = Math.round((evt.loaded / evt.total) * 100);
          setProgress(percent);
        },
      });
      setProgress(100);
      setStepState(1);

      const jobId = response.data?.job_id;
      if (!jobId) {
        throw new Error("Chybí job_id");
      }

      startStep("Zpracování savegame…", 400, false);
      pollTimer.current = window.setInterval(async () => {
        try {
          const res = await api.get(`/sync/deploy-status/${jobId}`);
          const job = res.data;
          if (job.step === "ingest") {
            setStatusLine(job.message || "Zpracování savegame…");
            setProgress(job.progress ?? 0);
          }
          if (job.step === "import") {
            setStepState(2);
            setStatusLine(job.message || "Import I3D…");
            setProgress(job.progress ?? 0);
          }
          if (job.status === "done") {
            setProgress(100);
            const statusRes = await api.get("/sync/status");
            setStatus(statusRes.data);
            pushNotice("ok", "Bundle úspěšně nasazen.");
            if (job.result?.warning || job.warning) {
              pushNotice("info", job.result?.warning || job.warning);
            }
            stopProgress();
            setProgressSteps(null);
            setBusy(false);
          }
          if (job.status === "error") {
            pushNotice("error", job.error || "Deploy bundle selhal.");
            stopProgress();
            setProgressSteps(null);
            setBusy(false);
          }
        } catch (err) {
          pushNotice("error", errorMessage(err, "Deploy bundle selhal."));
          stopProgress();
          setProgressSteps(null);
          setBusy(false);
        }
      }, 1000);
    } catch (err) {
      pushNotice("error", errorMessage(err, "Deploy bundle selhal."));
    } finally {
      if (!pollTimer.current) {
        setStatusLine(null);
        stopProgress();
        setProgressSteps(null);
        setBusy(false);
      }
    }
  };

  return (
    <section className="page">
      <header className="page__header">
        <h1>Velín farmy</h1>
        <p>Řídicí přehled posledního syncu a stavu ekonomiky.</p>
      </header>
      <div className="grid">
        <article className="card card--primary">
          <h3>Poslední sync</h3>
          {status?.status === "ok" ? (
            <p>
              Den {status.game_day}, rok {status.game_year}<br />
              Mapa: {friendlyMapName(status.map_id, status.map_title)}<br />
              Balance: {formatMoney(status.balance)}
            </p>
          ) : (
            <p>Žádná data.</p>
          )}
        </article>
        <article className="card">
          <h3>Sezóna</h3>
          <p>{status?.season || "-"}</p>
        </article>
        <article className="card">
          <h3>Dluh</h3>
          <p>{formatMoney(status?.loan)}</p>
        </article>
      </div>
      {notices.length > 0 && (
        <div className="notice-stack">
          {notices.map((n) => (
            <div key={n.id} className={`notice notice--${n.type}`}>
              {n.message}
            </div>
          ))}
        </div>
      )}
      {statusLine && (
        <div className="progress-box">
          <div className="progress-box__label">{statusLine}</div>
          {progress !== null && (
            <div className="progress">
              <div className="progress__bar" style={{ width: `${progress}%` }} />
            </div>
          )}
        </div>
      )}
      {progressSteps && (
        <div className="progress-steps">
          {progressSteps.map((step) => (
            <div key={step.label} className={`progress-step progress-step--${step.state}`}>
              <span className="progress-step__dot" />
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      )}
      <div className="card">
        <h3>Rychlá synchronizace</h3>
        <p className="muted">Vynucení načtení dat ze současného savegame.zip na serveru.</p>
        <div className="controls">
          <button className="button" onClick={forceSync} disabled={busy}>
            {busy ? "Synchronizuji…" : "Vynutit sync"}
          </button>
        </div>
      </div>
      <div className="cards-grid">
        <article className="card">
          <h3>Výměna savegame</h3>
          <div className="form-grid">
            <label className="field">
              API klíč (volitelné)
              <input
                type="password"
                value={apiKey}
                placeholder="pokud je zapnutý"
                onChange={(e) => persistKey(e.target.value)}
              />
            </label>
            <label className="field">
              Savegame ZIP
              <input type="file" accept=".zip" onChange={(e) => setSaveFile(e.target.files?.[0] || null)} />
            </label>
          </div>
          <div className="controls">
            <button className="button" onClick={() => uploadSave("push")} disabled={!saveFile || busy}>
              Nahrát (push)
            </button>
            <button className="button" onClick={() => uploadSave("replace")} disabled={!saveFile || busy}>
              Nahradit (replace)
            </button>
          </div>
          <p className="muted small">Replace uloží předchozí save do archivu a přepíše DB.</p>
        </article>
        <article className="card">
          <h3>Mapový obrázek (PNG)</h3>
          <div className="form-grid">
            <label className="field">
              Map ID (volitelné)
              <input
                type="text"
                value={mapId}
                placeholder="FS25_4bruecken.SampleModMap"
                onChange={(e) => setMapId(e.target.value)}
              />
            </label>
            <label className="field">
              Obrázek mapy (PNG)
              <input type="file" accept="image/png" onChange={(e) => setMapFile(e.target.files?.[0] || null)} />
            </label>
          </div>
          <div className="controls">
            <button className="button" onClick={uploadMap} disabled={!mapFile || busy}>
              Nahrát mapu
            </button>
          </div>
          <p className="muted small">Použij, když nechceš uploadovat celý map ZIP.</p>
        </article>
        <article className="card">
          <h3>Deploy bundle (map ZIP + save ZIP)</h3>
          <p className="muted">Komplexní import mapy, I3D a savegame v jednom kroku.</p>
          <div className="form-grid">
            <label className="field">
              Režim
              <select value={deployMode} onChange={(e) => setDeployMode(e.target.value as "push" | "replace")}>
                <option value="replace">Replace</option>
                <option value="push">Push</option>
              </select>
            </label>
            <label className="field">
              Map ZIP
              <input type="file" accept=".zip" onChange={(e) => setMapZip(e.target.files?.[0] || null)} />
            </label>
            <label className="field">
              Savegame ZIP
              <input type="file" accept=".zip" onChange={(e) => setSaveZip(e.target.files?.[0] || null)} />
            </label>
          </div>
          <div className="controls">
            <button className="button" onClick={deployBundle} disabled={!mapZip || !saveZip || busy}>
              Spustit deploy
            </button>
          </div>
          <p className="muted small">
            Z map ZIPu se pokusíme vytáhnout overview (PNG/DDS) a I3D. DDS převádíme na PNG.
          </p>
        </article>
      </div>
    </section>
  );
}
