import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import customtkinter as ctk
import requests
from tkinter import filedialog, messagebox

DEFAULT_ROOTS = [
    Path.home() / "Documents" / "My Games" / "FarmingSimulator25",
    Path.home() / "Documents" / "My Games" / "FarmingSimulator2025",
]


def parse_save_meta(save_dir: Path) -> dict:
    meta = {
        "map_id": "unknown",
        "money": "-",
        "day": "-",
        "year": "-",
    }
    xml_path = save_dir / "careerSavegame.xml"
    if not xml_path.exists():
        return meta
    try:
        root = ET.parse(xml_path).getroot()
        settings = root.find("./settings")
        stats = root.find("./statistics")
        if settings is not None:
            meta["map_id"] = settings.findtext("mapId") or meta["map_id"]
            meta["day"] = settings.findtext("currentDay") or meta["day"]
            meta["year"] = settings.findtext("currentYear") or meta["year"]
        if stats is not None:
            meta["money"] = stats.findtext("money") or meta["money"]
    except ET.ParseError:
        return meta
    return meta


def list_saves(root: Path) -> list[dict]:
    if not root.exists():
        return []
    saves = []
    for item in sorted(root.iterdir()):
        if item.is_dir() and item.name.startswith("savegame"):
            meta = parse_save_meta(item)
            saves.append({
                "name": item.name,
                "path": item,
                **meta,
            })
    return saves


def zip_folder(folder: Path, target_zip: Path):
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = Path(root) / file
                rel = file_path.relative_to(folder)
                zf.write(file_path, rel.as_posix())


class SyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AgroPortál Sync")
        self.geometry("900x620")

        self.server_url = ctk.StringVar(value="http://localhost:8000")
        self.api_key = ctk.StringVar(value="")
        self.save_root = ctk.StringVar(value=str(self._default_root()))
        self.selected_save = ctk.StringVar(value="")
        self.status_text = ctk.StringVar(value="Připraveno")

        self._build_ui()
        self.refresh_saves()

    def _default_root(self) -> Path:
        for root in DEFAULT_ROOTS:
            if root.exists():
                return root
        return DEFAULT_ROOTS[0]

    def _build_ui(self):
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(header, text="Server URL").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(header, textvariable=self.server_url, width=320).grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkLabel(header, text="API Key").grid(row=0, column=2, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(header, textvariable=self.api_key, width=240, show="*").grid(row=0, column=3, padx=8, pady=4)

        ctk.CTkLabel(header, text="Save folder").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(header, textvariable=self.save_root, width=320).grid(row=1, column=1, padx=8, pady=4)
        ctk.CTkButton(header, text="Vybrat", command=self.pick_root).grid(row=1, column=2, padx=8, pady=4)
        ctk.CTkButton(header, text="Refresh", command=self.refresh_saves).grid(row=1, column=3, padx=8, pady=4)

        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        ctk.CTkLabel(list_frame, text="Savegame list", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=8)

        self.scroll = ctk.CTkScrollableFrame(list_frame)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=8)

        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(action_frame, text="Push", command=self.push_selected).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(action_frame, text="Pull", command=self.pull_selected).pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(action_frame, textvariable=self.status_text).pack(side="right", padx=8, pady=8)

    def pick_root(self):
        path = filedialog.askdirectory(title="Vyberte složku se savy")
        if path:
            self.save_root.set(path)
            self.refresh_saves()

    def refresh_saves(self):
        for child in self.scroll.winfo_children():
            child.destroy()
        root = Path(self.save_root.get())
        saves = list_saves(root)
        if not saves:
            ctk.CTkLabel(self.scroll, text="Žádné savy nenalezeny.").pack(anchor="w", padx=8, pady=6)
            return
        for item in saves:
            label = f"{item['name']} | mapa: {item['map_id']} | peníze: {item['money']} | den: {item['day']} | rok: {item['year']}"
            ctk.CTkRadioButton(self.scroll, text=label, variable=self.selected_save, value=str(item["path"])).pack(anchor="w", padx=8, pady=6)

    def push_selected(self):
        if not self.selected_save.get():
            messagebox.showwarning("Sync", "Vyberte savegame.")
            return
        save_path = Path(self.selected_save.get())
        if not save_path.exists():
            messagebox.showerror("Sync", "Savegame neexistuje.")
            return
        self.status_text.set("Zazipovávám...")
        self.update_idletasks()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "savegame.zip"
            zip_folder(save_path, zip_path)
            self.status_text.set("Odesílám na server...")
            self.update_idletasks()
            try:
                with open(zip_path, "rb") as f:
                    resp = requests.post(
                        f"{self.server_url.get().rstrip('/')}/sync/push",
                        files={"file": f},
                        headers={"X-API-Key": self.api_key.get()},
                        timeout=120,
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(resp.text)
                self.status_text.set("Push OK")
            except Exception as exc:
                messagebox.showerror("Sync", f"Push failed: {exc}")
                self.status_text.set("Push failed")

    def pull_selected(self):
        if not self.selected_save.get():
            messagebox.showwarning("Sync", "Vyberte cílový savegame.")
            return
        save_path = Path(self.selected_save.get())
        self.status_text.set("Stahuji...")
        self.update_idletasks()
        try:
            resp = requests.get(
                f"{self.server_url.get().rstrip('/')}/sync/pull",
                headers={"X-API-Key": self.api_key.get()},
                timeout=120,
            )
            resp.raise_for_status()
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / "savegame.zip"
                zip_path.write_bytes(resp.content)
                if save_path.exists():
                    shutil.rmtree(save_path)
                save_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(save_path)
            self.status_text.set("Pull OK")
        except Exception as exc:
            messagebox.showerror("Sync", f"Pull failed: {exc}")
            self.status_text.set("Pull failed")


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    app = SyncApp()
    app.mainloop()
