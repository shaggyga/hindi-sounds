from __future__ import annotations
import json
import os
import sys
from pathlib import Path

DEFAULTS = {"group": "all", "gap_ms": 1400, "volume": 0.85, "window_mode": "windowed", "letter_id": "01"}
GAPS = (700, 1000, 1400, 2000, 2500, 3500, 5000)

def asset_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"

def state_root() -> Path:
    override = os.environ.get("HINDI_SOUNDS_APPDATA_DIR")
    return Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HindiSoundsApp"

def load_settings() -> dict:
    result = dict(DEFAULTS)
    try:
        data = json.loads((state_root() / "settings.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict): return result
        if data.get("group") in ("all", "vowels", "consonants"): result["group"] = data["group"]
        if data.get("gap_ms") in GAPS: result["gap_ms"] = data["gap_ms"]
        if isinstance(data.get("volume"), (int, float)) and 0 <= data["volume"] <= 1: result["volume"] = data["volume"]
        if data.get("window_mode") in ("windowed", "fullscreen", "borderless"): result["window_mode"] = data["window_mode"]
        if isinstance(data.get("letter_id"), str): result["letter_id"] = data["letter_id"]
    except (OSError, ValueError): pass
    return result

def save_settings(data: dict) -> None:
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / "settings.tmp"
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(root / "settings.json")
