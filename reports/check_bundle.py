"""Audit the collected Windows release using only the Python standard library.

Usage: python reports/check_bundle.py [path/to/Hindi Sounds]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import wave


def audit(bundle: Path) -> dict:
    bundle = bundle.resolve()
    internal = bundle / "_internal"
    assets = internal / "assets"
    result = {
        "bundle": str(bundle),
        "success": False,
        "recordings_checked": 0,
        "bundled_icu_dlls": [],
        "errors": [],
    }
    errors = result["errors"]
    if not internal.is_dir():
        errors.append(f"Missing collected runtime directory: {internal}")
        return result
    icu_files = sorted(path for path in bundle.rglob("*") if path.is_file() and path.name.lower().startswith("icu") and path.suffix.lower() == ".dll")
    result["bundled_icu_dlls"] = [str(path.relative_to(bundle)) for path in icu_files]
    if icu_files:
        errors.append("Bundled ICU DLLs would shadow Windows system ICU: " + ", ".join(result["bundled_icu_dlls"]))
    manifest = assets / "letters.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        items = data if isinstance(data, list) else data.get("letters")
        if not isinstance(items, list):
            raise ValueError("Expected a letter list")
    except (OSError, ValueError, AttributeError) as exc:
        errors.append(f"Cannot read the letter collection: {exc}")
        return result
    if len(items) != 46:
        errors.append(f"Expected 46 letters, found {len(items)}")
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(ids) != len(items) or len(set(ids)) != len(items) or any(not ident for ident in ids):
        errors.append("Each letter must have a unique, nonempty id")
    audio_paths = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("audio"), str) or not item.get("letter"):
            errors.append(f"Letter {index + 1} lacks a glyph or audio path")
            continue
        path = (assets / item["audio"]).resolve()
        if not path.is_relative_to(assets.resolve()):
            errors.append(f"Audio path escapes the asset directory: {item['audio']}")
            continue
        audio_paths.append(path)
        if not path.is_file():
            errors.append(f"Missing recording for {item.get('id', index + 1)}: {item['audio']}")
            continue
        try:
            with wave.open(str(path), "rb") as recording:
                if recording.getnframes() <= 0 or recording.getframerate() <= 0:
                    raise ValueError("Empty audio stream")
                if len(recording.readframes(recording.getnframes())) == 0:
                    raise ValueError("Missing audio samples")
        except (OSError, EOFError, wave.Error, ValueError) as exc:
            errors.append(f"Invalid recording {item['audio']}: {exc}")
            continue
        result["recordings_checked"] += 1
    if len(set(audio_paths)) != len(audio_paths):
        errors.append("Letter entries must reference distinct recording files")
    result["success"] = not errors and result["recordings_checked"] == 46
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check packaged ICU isolation and all 46 Hindi audio assets")
    parser.add_argument("bundle", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent / "release" / "Hindi Sounds")
    args = parser.parse_args()
    result = audit(args.bundle)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
