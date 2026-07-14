#!/usr/bin/env python3
"""Generate the MR-113 same-recipe 2D/2.5D/3D caption review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont


def run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command exited with {completed.returncode}:\n"
            f"{' '.join(command)}\n{completed.stdout}"
        )


def record(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "file": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def caption_pixel_count(image: Image.Image) -> int:
    rgba = image.convert("RGBA")
    first_row = round(rgba.height * 438 / 512)
    return sum(
        alpha > 245 and red > 245 and green > 245 and blue > 245
        for red, green, blue, alpha in (
            rgba.getpixel((x, y))
            for y in range(first_row, rgba.height)
            for x in range(rgba.width)
        )
    )


def write_contact_sheet(
    sources: list[tuple[str, Path]], destination: Path, font_path: Path
) -> None:
    tile_size = 512
    label_height = 48
    background = (238, 242, 247, 255)
    sheet = Image.new(
        "RGBA", (tile_size * len(sources), tile_size + label_height), background
    )
    font = ImageFont.truetype(str(font_path), 24)
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(sources):
        tile = Image.new("RGBA", (tile_size, tile_size), background)
        tile.alpha_composite(Image.open(path).convert("RGBA"))
        sheet.alpha_composite(tile, (index * tile_size, 0))
        bounds = draw.textbbox((0, 0), label, font=font)
        width = bounds[2] - bounds[0]
        draw.text(
            (index * tile_size + (tile_size - width) / 2, tile_size + 8),
            label,
            font=font,
            fill=(39, 52, 81, 255),
        )
    sheet.convert("RGB").save(destination, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer-2d", type=Path, required=True)
    parser.add_argument("--renderer-3d", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    pack_root = root / "examples" / "robot-2_5d"
    layered_pack = pack_root / "pack.json"
    flat_pack = pack_root / "pack-flat.json"
    sticker = pack_root / "stickers" / "caption-proof.json"
    model = root / "examples" / "robot-004" / "robot-004.glb"
    args.output.mkdir(parents=True, exist_ok=True)

    outputs = {
        "flat_2d": args.output / "robot-flat-caption.webp",
        "layered_2_5d": args.output / "robot-layered-caption.webp",
        "filament_3d": args.output / "robot-glb-caption.webp",
    }
    for pack, destination in (
        (flat_pack, outputs["flat_2d"]),
        (layered_pack, outputs["layered_2_5d"]),
    ):
        run(
            [
                str(args.renderer_2d),
                "render",
                "--pack",
                str(pack),
                "--sticker",
                str(sticker),
                "--output",
                str(destination),
                "--lossless",
            ]
        )
    run(
        [
            str(args.renderer_3d),
            "--input",
            str(model),
            "--output",
            str(outputs["filament_3d"]),
            "--width",
            "512",
            "--height",
            "512",
            "--span",
            "4.4",
            "--center-y",
            "0.35",
            "--screen-effects-pack",
            str(layered_pack),
            "--screen-effects-sticker",
            str(sticker),
            "--caption-pack",
            str(layered_pack),
            "--caption-sticker",
            str(sticker),
        ]
    )

    records = {name: record(path) for name, path in outputs.items()}
    if records["flat_2d"]["sha256"] != records["layered_2_5d"]["sha256"]:
        raise RuntimeError("flat and layered captioned t=0 renders differ")
    counts = {
        name: caption_pixel_count(Image.open(path)) for name, path in outputs.items()
    }
    if any(count < 200 for count in counts.values()):
        raise RuntimeError(f"caption safe-area validation failed: {counts}")

    sheet = args.output / "contact-sheet.png"
    write_contact_sheet(
        [
            ("2D flat", outputs["flat_2d"]),
            ("2.5D layered", outputs["layered_2_5d"]),
            ("3D GLB + shared 2D caption", outputs["filament_3d"]),
        ],
        sheet,
        pack_root / "fonts" / "changa-one" / "ChangaOne-Regular.ttf",
    )
    manifest = {
        "milestone": "MR-113",
        "recipe": str(sticker.relative_to(root)),
        "caption": "NICE ONE!",
        "placement": "collision-aware auto: top preference rejected, bottom selected",
        "flat_layered_identical": True,
        "caption_white_pixel_counts": counts,
        "outputs": records,
        "contact_sheet": record(sheet),
    }
    (args.output / "review.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote MR-113 review to {args.output}")


if __name__ == "__main__":
    main()
