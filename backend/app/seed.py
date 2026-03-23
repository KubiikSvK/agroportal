from sqlalchemy import inspect, text
from app.models.models import Crop

DEFAULT_CROPS = [
    {"code": "WHEAT", "name": "Pšenice", "color": "#e4b83c"},
    {"code": "BARLEY", "name": "Ječmen", "color": "#d2b55b"},
    {"code": "CANOLA", "name": "Řepka", "color": "#c9ce4b"},
    {"code": "CORN", "name": "Kukuřice", "color": "#e1a84d"},
    {"code": "MAIZE", "name": "Kukuřice (zrno)", "color": "#e1a84d"},
    {"code": "SILAGEMAIZE", "name": "Kukuřice (siláž)", "color": "#d9a14a"},
    {"code": "SOYBEAN", "name": "Sója", "color": "#a6c36f"},
    {"code": "POTATO", "name": "Brambory", "color": "#b08a6f"},
    {"code": "SUGARBEET", "name": "Cukrovka", "color": "#d79aa2"},
    {"code": "OAT", "name": "Oves", "color": "#cbb89b"},
    {"code": "SUNFLOWER", "name": "Slunečnice", "color": "#e3c655"},
    {"code": "GRASS", "name": "Tráva", "color": "#7fb36a"},
    {"code": "SORGHUM", "name": "Čirok", "color": "#c7834a"},
    {"code": "RYE", "name": "Žito", "color": "#c2a46f"},
    {"code": "TRITICALE", "name": "Triticale", "color": "#c9b57d"},
    {"code": "SPELT", "name": "Špalda", "color": "#c6b48c"},
    {"code": "LINSEED", "name": "Len", "color": "#b2b89a"},
    {"code": "CLOVER", "name": "Jetel", "color": "#73b073"},
    {"code": "ALFALFA", "name": "Vojtěška", "color": "#6fa66f"},
    {"code": "RICE", "name": "Rýže", "color": "#b7c7c9"},
    {"code": "RICELONGGRAIN", "name": "Rýže (dlouhozrnná)", "color": "#aabcc0"},
    {"code": "WINTERWHEAT", "name": "Pšenice ozimá", "color": "#e1b74c"},
    {"code": "SUMMERWHEAT", "name": "Pšenice jarní", "color": "#e6c15f"},
    {"code": "WINTERBARLEY", "name": "Ječmen ozimý", "color": "#d9ba6d"},
    {"code": "SUMMERBARLEY", "name": "Ječmen jarní", "color": "#d8b474"},
    {"code": "GREENRYE", "name": "Zelené žito", "color": "#9fb57a"},
    {"code": "VETCHRYE", "name": "Vikev + žito", "color": "#8fb07a"},
    {"code": "BUCKWHEAT", "name": "Pohanka", "color": "#c1a07a"},
    {"code": "GREENBEAN", "name": "Zelené fazole", "color": "#7bb36a"},
    {"code": "PEA", "name": "Hrách", "color": "#9fc57a"},
    {"code": "PEAS", "name": "Hrách", "color": "#9fc57a"},
    {"code": "BEANS", "name": "Fazole", "color": "#8bbd6a"},
    {"code": "LENTILS", "name": "Čočka", "color": "#c2a47a"},
    {"code": "HEMP", "name": "Konopí", "color": "#7ca86a"},
    {"code": "POPPY", "name": "Mák", "color": "#c97f5d"},
    {"code": "TOBACCO", "name": "Tabák", "color": "#b8824a"},
    {"code": "LAVENDER", "name": "Levandule", "color": "#a57bc1"},
    {"code": "ONION", "name": "Cibule", "color": "#d7b59a"},
    {"code": "BEETROOT", "name": "Červená řepa", "color": "#c0657a"},
    {"code": "CARROT", "name": "Mrkev", "color": "#d58a4c"},
    {"code": "PARSNIP", "name": "Pasternák", "color": "#d2b48c"},
    {"code": "SPINACH", "name": "Špenát", "color": "#6ea66a"},
    {"code": "SUGARCANE", "name": "Cukrová třtina", "color": "#b8d27f"},
    {"code": "COTTON", "name": "Bavlna", "color": "#e0d7c7"},
    {"code": "GRAPE", "name": "Hrozny", "color": "#6c4c8a"},
    {"code": "OLIVE", "name": "Olivy", "color": "#8ca46a"},
    {"code": "POPLAR", "name": "Topol", "color": "#7a9b6a"},
    {"code": "OILSEEDRADISH", "name": "Ředkev olejná", "color": "#a4c36a"},
    {"code": "HUMUSACTIVE", "name": "Humus aktiv", "color": "#8c7a5a"},
    {"code": "MUSTARD", "name": "Hořčice", "color": "#d6c14c"},
    {"code": "FLOWERINGCATCHCROP", "name": "Medonosná meziplodina", "color": "#dcbf7a"},
]


def ensure_crops(session) -> None:
    for crop in DEFAULT_CROPS:
        existing = session.query(Crop).filter(Crop.code == crop["code"]).first()
        if existing:
            existing.name = crop["name"]
            existing.color = crop["color"]
        else:
            session.add(Crop(**crop))
    session.commit()


def ensure_vehicle_property_state(engine) -> None:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("vehicles")]
    if "property_state" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE vehicles ADD COLUMN property_state VARCHAR"))
