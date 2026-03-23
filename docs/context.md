# Agroportal Kontext / Context

## CZ
Tento repozitář je plánování + raná implementace FS25 (Farming Simulator 25) portálu pro správu farmy ("Agroportál") určeného pro agro.vanekgroup.eu.

### Cíl
Webová aplikace pro správu virtuální farmy na mapě FS25 "Karpatský Venkov" – plánování a přehled stavu.

### MVP moduly
- Interaktivní mapa polí (klikací pole nad screenshotem PDA)
- Crop rotation planner (tabulka pole × sezóna)
- Herní kalendář (FS25 den/sezóna)
- Precision Farming doporučení (nejdřív ruční zadávání, později auto sync)
- Produkce/výnosy (per pole/sezóna)

### Vstup dat
- Začít ručním zadáváním
- Později: automatický import ze savegame XML (ZIP s XML soubory)

### Plánovaný savegame import (v2)
- Parsovat: `careerSavegame.xml`, `fields.xml` a mapový `crops.xml`
- Sync skript na hostitelském PC čte savegame a posílá JSON na backend
- Endpoint chráněný `X-API-Key`

### Tech stack
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React (Vite) plánovaný, zatím neimplementován
- Docker Compose orchestrace
- Nginx Proxy Manager pro reverse proxy
- Auth: Basic Auth v NPM; Authelia volitelně později

### Aktuální stav repa
- Backend skeleton existuje (`/backend`) s health endpointem
- Docker Compose s Postgres + backend (frontend je zakomentovaný)
- Frontend složka existuje, ale je prázdná

### Poznámky
- Repo začalo jako čistá kostra; nepočítá se s citlivými daty
- Tento soubor je stručný sdílený kontext pro spolupracující AI

---

## EN
This repo is a planning + early implementation for an FS25 (Farming Simulator 25) farm management portal ("Agroportál") intended for agro.vanekgroup.eu.

### Goal
A web app to manage a virtual farm on the FS25 map "Karpatský Venkov" with planning and status overview.

### MVP Modules
- Interactive field map (clickable fields over a PDA screenshot)
- Crop rotation planner (field x season table)
- In‑game calendar (FS25 day/season tracking)
- Precision Farming recommendations (manual data entry first; later auto sync)
- Production tracking (yields per field/season)

### Data Input
- Start with manual input
- Later: automated import from FS25 savegame XML (ZIP with XML files)

### Planned Savegame Import (v2)
- Parse: `careerSavegame.xml`, `fields.xml`, and map `crops.xml`
- Sync script on host PC reads savegame and POSTs JSON to backend
- Endpoint protected with `X-API-Key`

### Tech Stack
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React (Vite) planned, not implemented yet
- Docker Compose orchestration
- Nginx Proxy Manager for reverse proxy
- Auth: Basic Auth at NPM; Authelia optional later

### Current Repo State
- Backend skeleton exists (`/backend`) with health endpoint
- Docker Compose with Postgres + backend (frontend commented)
- Frontend folder exists but empty

### Notes
- Repo started as a clean skeleton; no sensitive data intended
- This file is meant as a concise, shareable context for collaborating AIs
