# PDA map workflow

## Co očekáváme
- Statická mapová data z modové mapy (map.xml, map.i3d, overview.dds)
- Dynamická data ze savegame (fields.xml, farms.xml, vehicles.xml)

## Co je připravené v projektu
- `/maps/pdf/upload` a `/maps/pdf/from-url` pro uložení PDF mapy
- `/maps/image/upload` pro uložení obrázku mapy (PNG)
- `/maps/import-geometry` pro import polygonů (JSON/GeoJSON)
- `/maps/import-i3d` pro přímé zpracování map `.i3d`
- `/maps/geometry` pro vrácení uložených polygonů
- `MapAsset` a `FieldGeometry` tabulky v DB

## Jak importovat polygony
Doporučená cesta je export z GIANTS Editoru (Field Exporter) do JSON.
Endpoint `/maps/import-geometry` přijímá:
- GeoJSON FeatureCollection s `properties.fieldId`
- nebo list položek `{ fieldId, points: [{x,z}, ...] }`

Volitelné query parametry:
- `scale` (default 1.0)
- `offset_x` a `offset_y` (default 0)
- `invert_y` (default false, hodí se pro převrácení osy v UI)

## Co ještě chybí (a čeká na doladění)
- PDF → polygon extrakce (připraven stub `/maps/extract`)
- Definice měřítka mapy a offsetu pro přesné překreslení na obraz mapy

## Doporučené nastavení pro 4bruecken (mapa 2048x2048)
- `scale=1`
- `offset_x=1024`
- `offset_y=1024`
- `invert_y=true`

Tím dostaneš souřadnice do pixelového prostoru (0..2048) pro Leaflet `CRS.Simple`.

## Testovací data (source-data)
- `FS25_4bruecken.zip` obsahuje `mapUS/mapUS.i3d` a `mapUS/mapUS.xml`
- `savegame3.zip` obsahuje `fields.xml` se stavem polí
- `scripts/extract_i3d_fields.py` umí vyrobit GeoJSON z `.i3d`
- Vygenerované soubory:
- `source-data/fields_4bruecken.geojson`
- `source-data/map_overview.png`
