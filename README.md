# AgroPortal (FS25 Farm Management)

Web dashboard for managing FS25 savegames, fields, machinery, weather, and crop rotation. Designed for multiplayer HQ workflows and rapid map/sav e swaps.

## Quick Start

1. Copy env file and adjust values if needed:
   - `copy .env.example .env`
2. Build and start containers:
   - `docker compose up --build`
3. Open:
   - Frontend: `http://localhost:3001`
   - Backend API: `http://localhost:8001`

> Ports are defined in `docker-compose.yml` (frontend 3001, backend 8001).

## Core Features

- Map overview with field overlays
- Savegame ingest + re-ingest
- Crop rotation recommendations and multi-year plan
- Vehicles inventory cards
- Sync history & finance snapshots
- Map bundle deploy (map ZIP + save ZIP)

## Map & Save Deployment

Use the frontend “Deploy bundle” form or call the API directly:

- `POST /sync/deploy` (multipart: `map_zip`, `save_zip`)
- Progress: `GET /sync/deploy-status/{job_id}`

The backend:
- Extracts the map ZIP
- Detects map XML (`<map ...>` with `imageFilename/width/height`)
- Stores map image as `MapAsset` type `image`
- Stores XML as `MapAsset` type `config`
- Imports I3D polygons (optional)

## Map Scaling (2048m vs 4096px)

FS25 maps typically use a **2048 x 2048 meter** playable area, while PDA images can be **4096 x 4096 px**. The frontend treats the image as a larger canvas and centers the 2048m playable area inside it. Field polygons are plotted in **map meters**; the image provides the visual background.

If the map does not show:
- Check `GET /maps/active-image`
- Check `GET /maps/assets` for `asset_type: image` and `config`

## Manual Refresh

Map data is **manual refresh only** to avoid auto-zoom resets. Use the `Refresh` button in the map page to reload layers.

## Environment Variables

All secrets live in `.env`:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `AGRO_API_KEY` (or `API_KEY` fallback)

## Project Notes

- Detailed context: `docs/context.md`
- Map workflow notes: `PDAmap.md`

