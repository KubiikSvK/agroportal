import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _load_xml(path: Path) -> ET.Element | None:
    if not path.exists():
        return None
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def _to_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _resolve_save_root(folder: Path) -> Path:
    if (folder / "careerSavegame.xml").exists():
        return folder
    # Common case: zip contains a single savegameX/ directory
    subdirs = [p for p in folder.iterdir() if p.is_dir()]
    for sub in subdirs:
        if (sub / "careerSavegame.xml").exists():
            return sub
    return folder


def parse_save_folder(folder: Path) -> dict[str, Any]:
    root = _resolve_save_root(folder)
    career = _load_xml(root / "careerSavegame.xml")
    environment = _load_xml(root / "environment.xml")
    fields = _load_xml(root / "fields.xml")
    farms = _load_xml(root / "farms.xml")
    farmland = _load_xml(root / "farmland.xml")
    precision = _load_xml(root / "precisionFarming.xml")
    vehicles = _load_xml(root / "vehicles.xml")

    meta = {
        "game_day": None,
        "game_year": None,
        "season": None,
        "time_scale": None,
        "balance": None,
        "loan": None,
        "map_id": None,
        "map_title": None,
    }

    if career is not None:
        stats = career.find("./statistics")
        if stats is not None:
            money = stats.findtext("money")
            if money is not None:
                meta["balance"] = _to_float(money)
        settings = career.find("./settings")
        if settings is not None:
            map_id = settings.findtext("mapId")
            if map_id:
                meta["map_id"] = map_id
            map_title = settings.findtext("mapTitle")
            if map_title:
                meta["map_title"] = map_title
            day = settings.findtext("currentDay")
            year = settings.findtext("currentYear")
            if day:
                meta["game_day"] = _to_int(day)
            if year:
                meta["game_year"] = _to_int(year)
            time_scale = settings.findtext("timeScale")
            if time_scale:
                meta["time_scale"] = _to_float(time_scale)

    if environment is not None:
        season = environment.findtext("./season")
        if season:
            meta["season"] = season

    farm_finance = None
    if farms is not None:
        farm = farms.find("./farm")
        if farm is not None:
            money = farm.get("money")
            loan = farm.get("loan")
            if money is not None:
                meta["balance"] = _to_float(money)
            if loan is not None:
                meta["loan"] = _to_float(loan)
            finance_stats = farm.find("./finances/stats")
            if finance_stats is not None:
                farm_finance = {
                    "day": _to_int(finance_stats.get("day", "0")),
                    "harvest_income": _to_float(finance_stats.findtext("harvestIncome") or "0"),
                    "mission_income": _to_float(finance_stats.findtext("missionIncome") or "0"),
                    "new_vehicles_cost": _to_float(finance_stats.findtext("newVehiclesCost") or "0"),
                    "construction_cost": _to_float(finance_stats.findtext("constructionCost") or "0"),
                    "field_purchase": _to_float(finance_stats.findtext("fieldPurchase") or "0"),
                    "purchase_seeds": _to_float(finance_stats.findtext("purchaseSeeds") or "0"),
                    "purchase_fertilizer": _to_float(finance_stats.findtext("purchaseFertilizer") or "0"),
                    "purchase_fuel": _to_float(finance_stats.findtext("purchaseFuel") or "0"),
                    "vehicle_running_cost": _to_float(finance_stats.findtext("vehicleRunningCost") or "0"),
                    "loan_interest": _to_float(finance_stats.findtext("loanInterest") or "0"),
                    "other": _to_float(finance_stats.findtext("other") or "0"),
                }

    owned_farmlands = set()
    if farmland is not None:
        for farm_land in farmland.findall("./farmland"):
            if farm_land.get("farmId") == "1":
                fid = farm_land.get("id")
                if fid is not None:
                    owned_farmlands.add(_to_int(fid))

    field_rows = []
    if fields is not None:
        for field in fields.findall("./field"):
            field_rows.append({
                "fs_field_id": _to_int(field.get("id", "0")),
                "fs_farmland_id": _to_int(field.get("farmlandId", "0")) if field.get("farmlandId") else None,
                "crop_type": field.get("fruitType"),
                "growth_state": _to_int(field.get("growthState", "0")) if field.get("growthState") else None,
                "ground_type": field.get("groundType"),
                "weed_state": _to_int(field.get("weedState", "0")) if field.get("weedState") else None,
                "spray_level": _to_int(field.get("sprayLevel", "0")) if field.get("sprayLevel") else None,
                "lime_level": _to_int(field.get("limeLevel", "0")) if field.get("limeLevel") else None,
            })

    vehicle_rows = []
    if vehicles is not None:
        for veh in vehicles.findall("./vehicle"):
            vehicle_rows.append({
                "name": veh.get("name") or veh.get("filename"),
                "vehicle_type": veh.get("type"),
                "brand": veh.get("brand"),
                "purchase_price": _to_float(veh.get("price", "0")),
                "age_days": _to_int(veh.get("age", "0")),
                "damage": _to_float(veh.get("damage", "0")),
                "wear": _to_float(veh.get("wear", "0")),
                "operating_time": _to_float(veh.get("operatingTime", "0")),
                "is_leased": (veh.get("isLeased") == "true"),
                "property_state": veh.get("propertyState"),
            })

    precision_rows = []
    if precision is not None:
        for row in precision.findall(".//farmlandStatistic"):
            period = row.find("./periodCounter")
            total = row.find("./totalCounter")
            source = period or total
            precision_rows.append({
                "farmland_id": _to_int(row.get("farmlandId", "0")),
                "yield": _to_float(source.get("yield", "0")) if source is not None else 0.0,
                "yield_best_price": _to_float(source.get("yieldBestPrice", "0")) if source is not None else 0.0,
                "used_fertilizer": _to_float(source.get("usedMineralFertilizer", "0")) if source is not None else 0.0,
                "used_lime": _to_float(source.get("usedLime", "0")) if source is not None else 0.0,
                "used_fuel": _to_float(source.get("usedFuel", "0")) if source is not None else 0.0,
            })

    return {
        "meta": meta,
        "finance": farm_finance,
        "owned_farmlands": owned_farmlands,
        "fields": field_rows,
        "vehicles": vehicle_rows,
        "precision": precision_rows,
    }
