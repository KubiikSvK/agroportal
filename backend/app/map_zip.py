from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image
import xml.etree.ElementTree as ET


@dataclass
class MapZipResult:
    image_path: Optional[Path]
    i3d_path: Optional[Path]
    map_xml_path: Optional[Path]
    warning: Optional[str] = None
    map_id: Optional[str] = None
    map_xml_copy: Optional[Path] = None


def _pick_i3d(candidates: list[Path]) -> Optional[Path]:
    if not candidates:
        return None

    def score(path: Path) -> tuple[int, int]:
        lower = path.as_posix().lower()
        score = 0
        if "/config/" in lower:
            score -= 3
        if "/map" in lower or "map" in lower:
            score += 2
        if path.name.lower().startswith("map") or path.parent.name.lower().startswith("map"):
            score += 2
        return (-score, len(path.as_posix().split("/")))

    return sorted(candidates, key=score)[0]


def _pick_overview(candidates: list[Path]) -> Optional[Path]:
    if not candidates:
        return None
    def score(path: Path) -> tuple[int, int]:
        lower = path.as_posix().lower()
        score = 0
        if "overview" in lower:
            score += 3
        if "map" in lower:
            score += 1
        if path.suffix.lower() == ".png":
            score += 2
        if path.suffix.lower() == ".dds":
            score -= 1
        return (-score, len(path.as_posix().split("/")))
    return sorted(candidates, key=score)[0]


def _is_dark_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img = img.convert("L").resize((128, 128))
            pixels = list(img.getdata())
            avg = sum(pixels) / max(len(pixels), 1)
            return avg < 5
    except Exception:
        return True


def _read_image_filename(map_xml: Path) -> Optional[str]:
    try:
        tree = ET.parse(map_xml)
        root = tree.getroot()
        return root.get("imageFilename")
    except Exception:
        return None


def _is_map_xml(path: Path) -> bool:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        tag = root.tag.lower()
        if tag.endswith("map"):
            return True
        if root.get("imageFilename") or root.get("width") or root.get("height"):
            return True
    except Exception:
        return False
    return False


def _pick_map_xml(candidates: list[Path]) -> Optional[Path]:
    if not candidates:
        return None
    for cand in candidates:
        if _is_map_xml(cand):
            return cand
    for cand in candidates:
        if cand.name.lower().startswith("map") and cand.name.lower().endswith(".xml"):
            return cand
    return candidates[0]


def _map_id_from_xml(map_xml: Path) -> Optional[str]:
    return map_xml.stem if map_xml else None


def extract_map_zip(zip_path: Path, extract_dir: Path, map_dir: Path, timestamp: str) -> MapZipResult:
    extract_dir.mkdir(parents=True, exist_ok=True)
    map_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    i3d_candidates = list(extract_dir.rglob("*.i3d"))
    map_xml_candidates = list(extract_dir.rglob("*.xml"))
    image_candidates = list(extract_dir.rglob("*.png")) + list(extract_dir.rglob("*.jpg")) + list(extract_dir.rglob("*.jpeg")) + list(extract_dir.rglob("*.dds"))

    i3d_path = _pick_i3d(i3d_candidates)
    map_xml_path = _pick_map_xml(map_xml_candidates)

    map_id = _map_id_from_xml(map_xml_path) if map_xml_path else None
    map_xml_copy = None
    if map_xml_path and map_xml_path.exists():
        map_xml_copy = map_dir / f"map_{timestamp}.xml"
        map_xml_copy.write_bytes(map_xml_path.read_bytes())

    image_path = None
    warning = None
    overview = None
    if map_xml_path:
        image_filename = _read_image_filename(map_xml_path)
        if image_filename:
            target = (map_xml_path.parent / image_filename).resolve()
            if target.exists():
                overview = target
            else:
                stem = Path(image_filename).stem
                for ext in [".png", ".dds", ".jpg", ".jpeg"]:
                    candidate = (map_xml_path.parent / f"{stem}{ext}").resolve()
                    if candidate.exists():
                        overview = candidate
                        break
    if overview is None:
        overview = _pick_overview(image_candidates)
    if overview:
        if overview.suffix.lower() == ".dds":
            try:
                with Image.open(overview) as img:
                    target = map_dir / f"map_{timestamp}.png"
                    img.save(target)
                    image_path = target
                if image_path and _is_dark_image(image_path):
                    image_path.unlink(missing_ok=True)
                    image_path = None
                    warning = "DDS převod selhal (obrázek je černý). Nahraj PNG mapy ručně."
            except Exception:
                image_path = None
                warning = "DDS převod selhal. Nahraj PNG mapy ručně."
        else:
            target = map_dir / f"map_{timestamp}{overview.suffix.lower()}"
            target.write_bytes(overview.read_bytes())
            image_path = target

    return MapZipResult(
        image_path=image_path,
        i3d_path=i3d_path,
        map_xml_path=map_xml_path,
        warning=warning,
        map_id=map_id,
        map_xml_copy=map_xml_copy,
    )
