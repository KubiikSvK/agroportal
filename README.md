# AgroPortal (FS25 Farm Management)

Portál pro správu FS25 map a savegame s důrazem na **multiplayer**, **rychlé nasazování** a **přehledný agrární dashboard**.  
Obsahuje mapu polí s overlayi, rotaci plodin, finance, stroje a nástroje pro synchronizaci.

---

## Rychlý start

1. Zkopíruj env soubor:
   - `copy .env.example .env`
2. Spusť build a kontejnery:
   - `docker compose up --build`
3. Otevři:
   - Frontend: `http://localhost:3001`
   - Backend API: `http://localhost:8001`

> Porty jsou definované v `docker-compose.yml` (frontend 3001, backend 8001).

---

## Co AgroPortal umí

- Mapa polí s přesným polygonovým overlayem
- Ingest a re‑ingest savegame
- Crop rotation doporučení + víceletý plán
- Přehled strojů (karty, stav, opotřebení)
- Finance + historie syncu
- Deploy mapy + savegame v jednom kroku

---

## Deploy mapy a savegame

Použij formulář ve frontendu nebo API:

- `POST /sync/deploy` (multipart: `map_zip`, `save_zip`)
- Průběh: `GET /sync/deploy-status/{job_id}`

Backend při deployi:
- rozbalí map ZIP
- najde mapový XML (`<map ...>` s `imageFilename/width/height`)
- uloží mapový obrázek jako `MapAsset` typu `image`
- uloží mapový XML jako `MapAsset` typu `config`
- importuje I3D polygony (volitelné)

---

## Měřítko mapy (2048 m vs 4096 px)

FS25 používá **hratelnou plochu 2048 × 2048 metrů**, ale PDA obrázek bývá **4096 × 4096 px**.  
Frontend počítá s tím, že:

- **polygony jsou v metrech** (2048)
- **obrázek je větší plátno** (4096) a hratelná plocha je vycentrovaná

Pokud se mapa nezobrazuje:
- Zkontroluj `GET /maps/active-image`
- Zkontroluj `GET /maps/assets` pro `asset_type: image` a `config`

---

## Ruční refresh mapy

Mapa je **ručně obnovovaná**, aby se neresetovalo přiblížení. Použij tlačítko `Refresh` na stránce mapy.

---

## Prostředí (.env)

Všechny tajné hodnoty jsou v `.env`:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `AGRO_API_KEY` (fallback `API_KEY`)

---

## Kontext projektu

- Kontext: `docs/context.md`

