#!/usr/bin/env python3
"""Render deterministic poster contact sheets for human representation review."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}\n{completed.stderr}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def color_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def render_poster(executable: Path, pack: Path, sticker: Path, output: Path, size: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(executable), "render", "--pack", str(pack), "--sticker", str(sticker),
        "--output", str(output), "--width", str(size), "--height", str(size),
        "--lossless", "--first-frame-only",
    ])


def contact_sheet(records: list[dict[str, Any]], output: Path, size: int) -> None:
    columns = min(4, max(1, len(records)))
    rows = math.ceil(len(records) / columns)
    cell_width = size + 28
    cell_height = size + 48
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), (238, 242, 247))
    draw = ImageDraw.Draw(sheet)
    for index, record in enumerate(records):
        x = (index % columns) * cell_width + 14
        y = (index // columns) * cell_height + 4
        image = Image.open(record["poster"]).convert("RGBA")
        sheet.paste(image, (x, y), image)
        draw.text((x + 4, y + size + 4), record["display_name"], fill=(38, 52, 81))
        draw.text((x + 4, y + size + 20), record["mascot_id"], fill=(92, 102, 122))
    sheet.save(output)


def replace_directory(staging: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        raise FileExistsError(f"review output exists (use --force): {destination}")
    if destination.exists():
        shutil.rmtree(destination)
    staging.rename(destination)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "generated/human-pilots")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mascotrender", type=Path, default=root / "build/Release/mascotrender")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    destination = (args.output or source / "review").resolve()
    if args.size < 128 or args.size > 1024:
        raise ValueError("--size must be between 128 and 1024")
    manifest = read_json(source / "generation-manifest.json")
    pack_roots = sorted(path.parent for path in source.glob("human-*/pack.json"))
    if len(pack_roots) != manifest.get("pack_count"):
        raise ValueError("generation manifest pack_count does not match source packs")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        by_phrase: dict[str, list[dict[str, Any]]] = {}
        validations: list[dict[str, Any]] = []
        for pack_root in pack_roots:
            identity = read_json(pack_root / "identity.json")
            pack = read_json(pack_root / "pack.json")
            skin_rgb = color_tuple(identity["appearance"]["skin"]["base_color"])
            for sticker_path in sorted((pack_root / "stickers").glob("*.json")):
                sticker = read_json(sticker_path)
                phrase_id = sticker["phrase_id"]
                poster = staging / "posters" / identity["mascot_id"] / f"{phrase_id}.webp"
                render_poster(args.mascotrender.resolve(), pack_root / "pack.json", sticker_path, poster, args.size)
                image = Image.open(poster).convert("RGBA")
                bounds = image.getbbox()
                if bounds is None:
                    raise RuntimeError(f"empty poster: {poster}")
                scaled_skin = tuple(round(channel) for channel in skin_rgb)
                skin_pixels = sum(
                    1 for pixel in image.getdata()
                    if pixel[3] > 240 and all(abs(pixel[index] - scaled_skin[index]) <= 3 for index in range(3))
                )
                if skin_pixels < max(30, args.size * args.size // 400):
                    raise RuntimeError(f"identity complexion is not visible in {poster}")
                record = {
                    "mascot_id": identity["mascot_id"],
                    "display_name": identity["display_name"],
                    "phrase_id": phrase_id,
                    "caption": sticker["text"]["content"],
                    "camera_framing": sticker["camera"]["framing"],
                    "poster": poster,
                    "alpha_bounds": list(bounds),
                    "skin_pixel_count": skin_pixels,
                    "sha256": sha256(poster),
                }
                by_phrase.setdefault(phrase_id, []).append(record)
                validations.append({key: value for key, value in record.items() if key != "poster"})
        expected_per_phrase = len(pack_roots)
        sheets: list[dict[str, Any]] = []
        for phrase_id, records in sorted(by_phrase.items()):
            if len(records) != expected_per_phrase:
                raise RuntimeError(f"phrase {phrase_id} is missing a pilot rendition")
            path = staging / "sheets" / f"{phrase_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            contact_sheet(records, path, args.size)
            sheets.append({"phrase_id": phrase_id, "path": path.relative_to(staging).as_posix(), "sha256": sha256(path)})

        cards = "\n".join(
            f'<article><h2>{html.escape(item["phrase_id"])}</h2><a href="{html.escape(item["path"])}"><img src="{html.escape(item["path"])}" alt="{html.escape(item["phrase_id"])} pilot contact sheet"></a></article>'
            for item in sheets
        )
        (staging / "index.html").write_text(
            "<!doctype html><meta charset=\"utf-8\"><title>Human mascot pilot review</title>"
            "<style>body{font:16px system-ui;background:#eef2f7;color:#263451;margin:24px}article{margin:0 0 36px}img{max-width:100%;height:auto;border-radius:16px;background:white}h1,h2{margin:0 0 12px}</style>"
            f"<h1>Human technical fixtures</h1><p>{len(pack_roots)} identities × {len(sheets)} semantic phrases. These simplified procedural assets verify the engine only and are forbidden from production use. Heritage metadata is audit-only; rendered geometry comes from appearance contracts.</p>{cards}\n",
            encoding="utf-8",
            newline="\n",
        )
        write_json(staging / "review.json", {
            "schema_version": 1,
            "verification_status": "success",
            "asset_class": "technical-fixture",
            "production_use": "forbidden",
            "review_status": "not-a-production-review-candidate",
            "pack_count": len(pack_roots),
            "phrase_count": len(sheets),
            "poster_count": len(validations),
            "expected_poster_count": manifest["sticker_count"],
            "contact_sheets": sheets,
            "validations": validations,
        })
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    print(f"built {len(sheets)} human pilot contact sheets in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
