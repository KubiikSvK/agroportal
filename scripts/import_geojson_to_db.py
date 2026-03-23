import json
from pathlib import Path
import sys

sys.path.append('backend')
from app.database import SessionLocal, Base, engine
from app.models.models import Field, FieldGeometry

geo_path = Path('source-data/fields_4bruecken.geojson')
if not geo_path.exists():
    raise SystemExit('GeoJSON not found')

Base.metadata.create_all(bind=engine)

geo = json.loads(geo_path.read_text(encoding='utf-8'))

session = SessionLocal()
try:
    count = 0
    for feat in geo.get('features', []):
        field_id = feat.get('properties', {}).get('fieldId') or feat.get('id')
        if field_id is None:
            continue
        field = session.query(Field).filter(Field.fs_field_id == int(field_id)).first()
        if not field:
            field = Field(fs_field_id=int(field_id), name=f'Field {field_id}')
            session.add(field)
            session.commit()
            session.refresh(field)
        existing = session.query(FieldGeometry).filter(FieldGeometry.field_id == field.id).first()
        geometry = feat.get('geometry')
        if not geometry:
            continue
        payload = json.dumps(geometry)
        if existing:
            existing.geometry_geojson = payload
        else:
            session.add(FieldGeometry(field_id=field.id, geometry_geojson=payload))
        count += 1
    session.commit()
    print(f'Imported geometry for {count} fields')
finally:
    session.close()
