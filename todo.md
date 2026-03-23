# AgroPortál — souhrn stavu a co zbývá

## Co je hotové ✅

**Infrastruktura:**

- `docker-compose.yml` s PostgreSQL + FastAPI backendem
- Healthcheck — backend čeká na DB
- `.env` konfigurace
- GitHub repo: `KubiikSvK/agroportal`

**Backend:**

- FastAPI kostra (`main.py`, `database.py`, `config.py`)
- SQLAlchemy DB modely (`models.py`) — všechny tabulky: `saves`, `fields`, `field_snapshots`, `crop_rotation`, `harvests`, `finance_snapshots`, `vehicles`, `weather_log`, `sync_history`
- Fields router (`/fields/`) — GET, POST, PATCH, GET by ID
- Tabulky se automaticky vytvoří při startu

---

## Co zbývá udělat

### 1. Backend routery (přidat do `backend/app/routers/`)

**`saves.py`** — `/saves/`

- GET všechny saves
- POST nový save

**`snapshots.py`** — `/snapshots/`

- POST field snapshot (stav pole v čase)
- GET snapshots pro pole

**`finance.py`** — `/finance/`

- GET finanční přehled
- POST finance snapshot

**`vehicles.py`** — `/vehicles/`

- GET seznam strojů
- POST nový stroj

**`sync.py`** — `/sync/` ← nejdůležitější

- `POST /sync/push` — přijme ZIP savegame, parsuje XML, uloží do DB
- `GET /sync/pull` — vrátí aktuální ZIP ke stažení
- `GET /sync/status` — metadata posledního save

**`harvests.py`** — `/harvests/`

- GET výnosy per pole/rok

**`weather.py`** — `/weather/`

- GET předpověď počasí

Každý router přidat do `main.py`:

```python
from app.routers import saves, snapshots, finance, vehicles, sync, harvests, weather
app.include_router(saves.router)
# atd.
```

---

### 2. Sync endpoint — XML parser (`backend/app/`)

Soubor `parser.py` — parsuje tyto XML soubory ze savegame ZIP:

```python
# careerSavegame.xml → herní den, rok, mapa, balance, loan, mody
# environment.xml   → sezóna, počasí forecast
# fields.xml        → stav polí (fruitType, growthState, weedState, sprayLevel, limeLevel)
# farms.xml         → finance per den (harvestIncome, missionIncome, purchaseSeeds atd.)
# farmland.xml      → která pole vlastníme (farmId=1)
# precisionFarming.xml → yield, yieldBestPrice, usedFertilizer, usedLime per farmland
# vehicles.xml      → stroje (name, operatingTime, damage, wear, price, isLeased)
```

Mapování herního dne na sezónu:

```python
DAY_TO_SEASON = {
    1: ("SPRING", "Early Spring", "březen"),
    2: ("SPRING", "Mid Spring", "duben"),
    3: ("SPRING", "Late Spring", "květen"),
    4: ("SUMMER", "Early Summer", "červen"),
    5: ("SUMMER", "Mid Summer", "červenec"),
    6: ("SUMMER", "Late Summer", "srpen"),
    7: ("AUTUMN", "Early Autumn", "září"),
    8: ("AUTUMN", "Mid Autumn", "říjen"),
    9: ("AUTUMN", "Late Autumn", "listopad"),
    10: ("WINTER", "Early Winter", "prosinec"),
    11: ("WINTER", "Mid Winter", "leden"),
    12: ("WINTER", "Late Winter", "únor"),
}
```

---

### 3. API Key middleware

Soubor `backend/app/middleware.py`:

```python
# Endpoint /sync/push a /sync/pull ověřuje X-API-Key header
# Ostatní endpointy jsou volné (Basic Auth řeší Nginx)
```

---

### 4. Frontend (React + Vite)

Složka `frontend/` — zatím prázdná, Dockerfile chybí.

**Setup:**

```bash
npm create vite@latest . -- --template react-ts
npm install axios react-router-dom leaflet react-leaflet recharts
```

**`frontend/Dockerfile`:**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

**Stránky k vytvoření (`frontend/src/pages/`):**

- `Dashboard.tsx` — úvodní přehled
- `MapPage.tsx` — mapa polí (Leaflet)
- `RotationPage.tsx` — osevní plán
- `FinancePage.tsx` — finance + grafy (Recharts)
- `PrecisionPage.tsx` — precision farming
- `VehiclesPage.tsx` — stroje
- `WeatherPage.tsx` — počasí

---

### 5. Sync skript (Windows/Mac GUI)

Složka `sync-script/` — zatím prázdná.

**`sync-script/fs25sync.py`** — Python GUI aplikace:

- `customtkinter` pro GUI
- Tlačítka Push / Pull
- Progress bar s kroky
- Konfigurace: cesta k savegame, server URL, API klíč

**`sync-script/requirements.txt`:**

```txt
customtkinter
requests
```

**Workflow Push:**

1. Najde savegame složku
2. Zkopíruje XML soubory do temp/
3. Zazipuje celý savegame
4. POST na `/sync/push` s ZIP souborem
5. Uklidí temp/

**Workflow Pull:**

1. GET `/sync/pull` — stáhne ZIP
2. Rozbalí do savegame složky
3. Uklidí temp/

---

### 6. NPM konfigurace na serveru

V Nginx Proxy Manager nastavit:

- `agro.vanekgroup.eu` → `http://localhost:3001` (frontend)
- Basic Auth: jakub / ondra
- Výjimka pro `/api/sync/` → bez Basic Auth, jen API klíč

---

## Checklist (prioritní)

### 1. Backend routery
- [ ] `saves.py`: GET všechny saves, POST nový save
- [ ] `snapshots.py`: POST field snapshot, GET snapshots pro pole
- [ ] `finance.py`: GET finanční přehled, POST finance snapshot
- [ ] `vehicles.py`: GET seznam strojů, POST nový stroj
- [ ] `harvests.py`: GET výnosy per pole/rok
- [ ] `weather.py`: GET předpověď počasí
- [ ] `sync.py`: `POST /sync/push`, `GET /sync/pull`, `GET /sync/status`
- [ ] Přidat routery do `backend/app/main.py`

### 2. Sync (server)
- [ ] `backend/app/parser.py`: parsování XML (viz seznam níže)
- [ ] `/sync/push`: přijmout ZIP, rozbalit do temp, parsovat, uložit do DB
- [ ] `/sync/pull`: vracet aktuální ZIP savegame ke stažení
- [ ] `/sync/status`: metadata posledního save (mapa, den, rok, money, timestamp)
- [ ] Zálohování pushů: držet poslední 3 ZIPy, 4. a další mazat kvůli místu
- [ ] Podpora jediného multiplayer save (jeden aktivní savegame)

### 3. API Key middleware
- [ ] `backend/app/middleware.py`: chránit `/sync/push` a `/sync/pull` přes `X-API-Key`
- [ ] API key v `.env` a použít v middleware

### 4. Frontend
- [ ] `frontend/` init (React + Vite + TS)
- [ ] Základní routing stránek
- [ ] Stránky: Dashboard, Map, Rotation, Finance, Precision, Vehicles, Weather
- [ ] `frontend/Dockerfile`

### 5. Sync klient (PC)
- [ ] `sync-script/` vytvořit
- [ ] Skript/program, který:
- [ ] Načte všechny savy v PC
- [ ] Vypíše u každého mapu + peníze
- [ ] Umožní vybrat save, zazipovat a poslat na server
- [ ] Pracuje s celým savegame ZIPem (pushuje se celý save)
- [ ] Pull: stáhne ZIP a rozbalí do vybraného save slotu
- [ ] GUI: `customtkinter` + progress + konfigurace (URL, API key, save path)

### 6. Nasazení
- [ ] Nginx Proxy Manager: frontend host, Basic Auth
- [ ] Výjimka `/api/sync/` bez Basic Auth, pouze API key
 
## Poznámky k rozsahu
- Multiplayer: počítáme s jedním aktivním savegame.
- Chceme začít na nové mapě "od nuly".
- Na server pushujeme celý savegame ZIP.
- Dočasný save na testy, později nahradíme ostrým.

## Nové požadavky (mapa + výměna save)
### 1. Práce s mapou z PDF
- [ ] Server umí stáhnout PDF mapu (URL nebo soubor)
- [ ] Vytáhnout z PDF hranice polí (polygony)
- [ ] Překlopit do klikatelných vrstev nad mapou
- [ ] Klik na pole → detail (aktuální plodina, poslední sklizeň, další metadata)

### 2. Výměna aktuálního save
- [ ] Endpoint pro „Replace Save“ (např. `/sync/replace`)
- [ ] Při výměně: zazálohovat starou mapu + všechna data
- [ ] Vygenerovat nový dataset podle nové mapy/savegame

---

## Důležité technické detaily

**Savegame XML struktura** — klíčové atributy:

```xml
<!-- careerSavegame.xml -->
<statistics><money>50046</money></statistics>
<settings><mapId>FS25_Valachy</mapId><currentDay>7</currentDay></settings>

<!-- fields.xml -->
<field id="1" fruitType="WHEAT" growthState="4" weedState="2"
       sprayLevel="2" limeLevel="1" groundType="SOWN"/>

<!-- farms.xml -->
<farm farmId="1" money="50046" loan="100000">
  <finances>
    <stats day="1">
      <harvestIncome>66233</harvestIncome>
      <missionIncome>211094</missionIncome>
      <newVehiclesCost>-246738</newVehiclesCost>
    </stats>
  </finances>
</farm>

<!-- precisionFarming.xml -->
<farmlandStatistic farmlandId="15">
  <totalCounter yield="7955" yieldBestPrice="23598"
                usedLime="4805" usedFuel="328"/>
</farmlandStatistic>
```

**DB tabulky jsou vytvořené** — přidat `__init__.py` do `models/`:

```python
# backend/app/models/__init__.py — prázdný soubor
```
