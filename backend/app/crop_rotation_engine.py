from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET


@dataclass
class CropRotationSettings:
    monoculture_penalty: float = -0.05
    break_periods_penalty: float = -0.1
    fore_crops_penalties: List[float] = field(default_factory=list)
    fore_crops_very_good_bonuses: List[float] = field(default_factory=list)
    fore_crops_good_bonuses: List[float] = field(default_factory=list)
    fallow_state_bonus: float = 0.05
    very_good_catch_crop_bonus: float = 0.15
    good_catch_crop_bonus: float = 0.1
    bad_catch_crop_penalty: float = -0.1


@dataclass
class CropRotationCrop:
    code: str
    break_periods: int
    very_good: List[str]
    good: List[str]
    bad: List[str]
    ignore_in_planner: bool = False
    ignore_fallow: bool = False


@dataclass
class CatchCrop:
    code: str
    very_good: List[str]
    good: List[str]
    bad: List[str]


class CropRotationEngine:
    def __init__(self, settings: CropRotationSettings, crops: Dict[str, CropRotationCrop], catch_crops: Dict[str, CatchCrop]):
        self.settings = settings
        self.crops = crops
        self.catch_crops = catch_crops

        # Derive history length from config arrays; fallback to 2 (mod default)
        self.num_history_maps = max(
            len(settings.fore_crops_good_bonuses),
            len(settings.fore_crops_very_good_bonuses),
            len(settings.fore_crops_penalties),
            2,
        )

    def calculate_multiplier(
        self,
        history: List[str],
        crop_code: str,
        catch_crop_code: Optional[str] = None,
    ) -> tuple[float, Dict[str, float]]:
        if crop_code not in self.crops:
            return 1.0, {}

        crop = self.crops[crop_code]
        history = history[: self.num_history_maps]

        monoculture = 0.0
        if crop.break_periods > 0 and history and all(h == crop_code for h in history):
            monoculture = self.settings.monoculture_penalty

        break_periods = 0.0
        for i, h in enumerate(history):
            if i < crop.break_periods and h == crop_code:
                break_periods += self.settings.break_periods_penalty

        fore_crops = 0.0
        for i, h in enumerate(history):
            if h in crop.very_good and i < len(self.settings.fore_crops_very_good_bonuses):
                fore_crops += self.settings.fore_crops_very_good_bonuses[i]
            if h in crop.good and i < len(self.settings.fore_crops_good_bonuses):
                fore_crops += self.settings.fore_crops_good_bonuses[i]
            if h in crop.bad and i < len(self.settings.fore_crops_penalties):
                fore_crops += self.settings.fore_crops_penalties[i]

        fallow = 0.0
        for h in history:
            if h == "FALLOW":
                fallow += self.settings.fallow_state_bonus

        catch_crop = 0.0
        if catch_crop_code and catch_crop_code in self.catch_crops:
            catch = self.catch_crops[catch_crop_code]
            if crop_code in catch.very_good:
                catch_crop = self.settings.very_good_catch_crop_bonus
            if crop_code in catch.good:
                catch_crop = self.settings.good_catch_crop_bonus
            if crop_code in catch.bad:
                catch_crop = self.settings.bad_catch_crop_penalty

        multiplier = 1.0 + monoculture + break_periods + fore_crops + fallow + catch_crop
        detail = {
            "monoculture": monoculture,
            "break_periods": break_periods,
            "fore_crops": fore_crops,
            "fallow": fallow,
            "catch_crop": catch_crop,
        }
        return multiplier, detail


_ENGINE: CropRotationEngine | None = None


def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item for item in value.split() if item]


def _parse_float_list(value: Optional[str]) -> List[float]:
    if not value:
        return []
    return [float(item) for item in value.split() if item]


def _load_settings(xml_path: Path) -> CropRotationSettings:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    settings_node = root.find("settings")
    settings = CropRotationSettings()
    if settings_node is None:
        return settings

    settings.monoculture_penalty = float(settings_node.get("monoculturePenalty", settings.monoculture_penalty))
    settings.break_periods_penalty = float(settings_node.get("breakPeriodsPenalty", settings.break_periods_penalty))
    settings.fore_crops_penalties = _parse_float_list(settings_node.get("foreCropsPenalties"))
    settings.fore_crops_very_good_bonuses = _parse_float_list(settings_node.get("foreCropsVeryGoodBonuses"))
    settings.fore_crops_good_bonuses = _parse_float_list(settings_node.get("foreCropsGoodBonuses"))
    settings.fallow_state_bonus = float(settings_node.get("fallowStateBonus", settings.fallow_state_bonus))
    settings.very_good_catch_crop_bonus = float(settings_node.get("veryGoodCatchCropBonus", settings.very_good_catch_crop_bonus))
    settings.good_catch_crop_bonus = float(settings_node.get("goodCatchCropBonus", settings.good_catch_crop_bonus))
    settings.bad_catch_crop_penalty = float(settings_node.get("badCatchCropPenalty", settings.bad_catch_crop_penalty))
    return settings


def _load_crops(xml_path: Path) -> tuple[Dict[str, CropRotationCrop], Dict[str, CatchCrop]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    crops: Dict[str, CropRotationCrop] = {}
    catch_crops: Dict[str, CatchCrop] = {}

    for crop_node in root.findall("crop"):
        code = crop_node.get("fruitName")
        if not code:
            continue
        crops[code] = CropRotationCrop(
            code=code,
            break_periods=int(crop_node.get("breakPeriods", "0")),
            very_good=_parse_list(crop_node.get("veryGoodCrops")),
            good=_parse_list(crop_node.get("goodCrops")),
            bad=_parse_list(crop_node.get("badCrops")),
            ignore_in_planner=crop_node.get("ignoreInPlanner", "false").lower() == "true",
            ignore_fallow=crop_node.get("ignoreFallow", "false").lower() == "true",
        )

    catch_root = root.find("catchCrops")
    if catch_root is not None:
        for catch_node in catch_root.findall("catchCrop"):
            code = catch_node.get("fruitName")
            if not code:
                continue
            catch_crops[code] = CatchCrop(
                code=code,
                very_good=_parse_list(catch_node.get("veryGoodCrops")),
                good=_parse_list(catch_node.get("goodCrops")),
                bad=_parse_list(catch_node.get("badCrops")),
            )

    return crops, catch_crops


def get_crop_rotation_engine() -> CropRotationEngine:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    base = Path("source-data") / "_cropRotation" / "xmls"
    settings_path = base / "cropRotation.xml"
    crops_path = base / "crops.xml"

    if settings_path.exists() and crops_path.exists():
        settings = _load_settings(settings_path)
        crops, catch_crops = _load_crops(crops_path)
    else:
        settings = CropRotationSettings()
        crops, catch_crops = {}, {}

    _ENGINE = CropRotationEngine(settings, crops, catch_crops)
    return _ENGINE
