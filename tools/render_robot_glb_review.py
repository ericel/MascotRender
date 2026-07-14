#!/usr/bin/env python3
"""Render the rest pose and four MR-112 clips for visual review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


SAMPLES = [
    ("rest", "", 0.0),
    ("idle", "idle", 0.5),
    ("hello", "hello", 0.3),
    ("hop", "hop", 0.3),
    ("celebrate", "celebrate", 0.5),
]

PALETTE = {
    "gold": (255, 209, 102),
    "orange": (228, 155, 54),
    "mint": (122, 225, 210),
    "ink": (60, 48, 66),
}


def matching_pixels(image: Image.Image, target: tuple[int, int, int], tolerance=3):
    matches = []
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.getpixel((x, y))
            if alpha > 200 and all(
                abs(actual - expected) <= tolerance
                for actual, expected in zip((red, green, blue), target)
            ):
                matches.append((x, y))
    return matches


def validate_rest_frame(image: Image.Image) -> dict[str, object]:
    counts = {name: len(matching_pixels(image, color)) for name, color in PALETTE.items()}
    missing = [name for name, count in counts.items() if count < 100]
    if missing:
        raise RuntimeError(f"rest frame is missing approved palette colors: {missing}")

    mint_pixels = matching_pixels(image, PALETTE["mint"])
    top_mint = sum(y < image.height * 0.2 for _, y in mint_pixels)
    bottom_mint = sum(y > image.height * 0.8 for _, y in mint_pixels)
    if top_mint < 100 or top_mint <= bottom_mint:
        raise RuntimeError("rest frame orientation guard failed: mint antenna is not on top")

    alpha_bounds = image.getchannel("A").getbbox()
    if alpha_bounds is None or alpha_bounds[1] >= image.height * 0.3:
        raise RuntimeError("rest frame orientation/visibility guard failed")
    return {"palette_pixel_counts": counts, "alpha_bounds": list(alpha_bounds)}


def write_review_images(output: Path, rendered: list[tuple[str, Path]]) -> dict[str, object]:
    frames = [(label, Image.open(path).convert("RGBA")) for label, path in rendered]
    rest_validation = validate_rest_frame(frames[0][1])

    white = Image.new("RGBA", frames[0][1].size, (255, 255, 255, 255))
    white.alpha_composite(frames[0][1])
    white_path = output / "robot-004-rest-white.png"
    white.convert("RGB").save(white_path, optimize=True)

    tile_size = 320
    label_height = 38
    sheet = Image.new(
        "RGB", (tile_size * len(frames), tile_size + label_height), (244, 247, 251)
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, frame) in enumerate(frames):
        tile = Image.new("RGBA", (tile_size, tile_size), (244, 247, 251, 255))
        resized = frame.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
        tile.alpha_composite(resized)
        sheet.paste(tile.convert("RGB"), (index * tile_size, 0))
        text_bounds = draw.textbbox((0, 0), label)
        text_width = text_bounds[2] - text_bounds[0]
        draw.text(
            (index * tile_size + (tile_size - text_width) * 0.5, tile_size + 10),
            label,
            fill=PALETTE["ink"],
        )
    sheet_path = output / "robot-004-contact-sheet.png"
    sheet.save(sheet_path, optimize=True)

    def file_record(path: Path) -> dict[str, object]:
        payload = path.read_bytes()
        return {
            "file": path.name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    return {
        "rest_validation": rest_validation,
        "white_background": file_record(white_path),
        "contact_sheet": file_record(sheet_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    # Review directories are reproducible outputs. Remove current and legacy
    # names so an obsolete debug render cannot be mistaken for a deliverable.
    for pattern in ("robot-004-*", "review.json", "rest-white.png", "contact-sheet.png"):
        for stale in args.output.glob(pattern):
            if stale.is_file():
                stale.unlink()

    manifest = {"asset": str(args.input), "samples": []}
    rendered: list[tuple[str, Path]] = []
    for label, animation, time in SAMPLES:
        destination = args.output / f"robot-004-{label}.webp"
        command = [
            str(args.renderer),
            "--input",
            str(args.input),
            "--output",
            str(destination),
            "--width",
            "512",
            "--height",
            "512",
            "--span",
            "4.4",
            "--center-y",
            "0.35",
        ]
        if animation:
            command.extend(["--animation", animation, "--time", str(time)])
        subprocess.run(command, check=True)
        rendered.append((label, destination))
        payload = destination.read_bytes()
        manifest["samples"].append(
            {
                "label": label,
                "animation": animation or None,
                "time_seconds": time,
                "file": destination.name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    manifest["review_images"] = write_review_images(args.output, rendered)

    (args.output / "review.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(SAMPLES)} robot review frames to {args.output}")


if __name__ == "__main__":
    main()
