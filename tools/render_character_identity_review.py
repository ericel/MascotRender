#!/usr/bin/env python3
"""Generate the robot-004 identity and dimensional 2.5D acceptance review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageChops

from render_caption_backend_review import (
    caption_pixel_count,
    record,
    run,
    write_contact_sheet,
)


def changed_pixel_count(left: Path, right: Path) -> int:
    difference = ImageChops.difference(
        Image.open(left).convert("RGBA"), Image.open(right).convert("RGBA")
    )
    return sum(
        any(channel != 0 for channel in difference.getpixel((x, y)))
        for y in range(difference.height)
        for x in range(difference.width)
    )


def color_channels(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))


def sparkle_bounds(path: Path, color: tuple[int, int, int]) -> tuple[int, int, int, int]:
    image = Image.open(path).convert("RGBA")
    points = [
        (x, y)
        for y in range(image.height)
        for x in range(round(image.width * 0.32))
        if image.getpixel((x, y))[3] > 240
        and all(
            abs(actual - expected) <= 3
            for actual, expected in zip(image.getpixel((x, y))[:3], color)
        )
    ]
    if not points:
        raise RuntimeError(f"screen-space sparkle is missing from {path}")
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points) + 1,
        max(y for _, y in points) + 1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renderer-2d", type=Path, required=True)
    parser.add_argument("--renderer-3d", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    pack_root = root / "examples" / "robot-2_5d"
    robot_root = root / "examples" / "robot-004"
    flat_sticker = pack_root / "stickers" / "caption-proof.json"
    dimensional_sticker = (
        pack_root / "stickers" / "dimensional-caption-proof.json"
    )
    outputs = {
        "flat_2d": args.output / "robot-flat-identity.webp",
        "dimensional_2_5d": args.output / "robot-dimensional-identity.webp",
        "filament_3d": args.output / "robot-glb-identity.webp",
    }
    args.output.mkdir(parents=True, exist_ok=True)

    for pack, sticker, destination in (
        (pack_root / "pack-flat.json", flat_sticker, outputs["flat_2d"]),
        (pack_root / "pack.json", dimensional_sticker, outputs["dimensional_2_5d"]),
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
            str(robot_root / "robot-004.glb"),
            "--output",
            str(outputs["filament_3d"]),
            "--width",
            "512",
            "--height",
            "512",
            "--span",
            "3.85",
            "--center-y",
            "0.15",
            "--screen-effects-pack",
            str(pack_root / "pack.json"),
            "--screen-effects-sticker",
            str(flat_sticker),
            "--caption-pack",
            str(pack_root / "pack.json"),
            "--caption-sticker",
            str(flat_sticker),
        ]
    )

    camera_proofs = {
        "near": args.output / "robot-glb-sparkle-near.webp",
        "far": args.output / "robot-glb-sparkle-far.webp",
    }
    for span, destination in (("3.3", camera_proofs["near"]), ("4.6", camera_proofs["far"])):
        run(
            [
                str(args.renderer_3d),
                "--input",
                str(robot_root / "robot-004.glb"),
                "--output",
                str(destination),
                "--width",
                "512",
                "--height",
                "512",
                "--span",
                span,
                "--center-y",
                "0.15",
                "--screen-effects-pack",
                str(pack_root / "pack.json"),
                "--screen-effects-sticker",
                str(flat_sticker),
            ]
        )

    identity_report = args.output / "identity-validation.json"
    validator = root / "tools" / "validate_character_identity.py"
    completed = subprocess.run(
        [
            "python3",
            str(validator),
            "--contract",
            str(robot_root / "identity.json"),
            "--pack",
            str(pack_root / "pack.json"),
            "--flat-pack",
            str(pack_root / "pack-flat.json"),
            "--glb",
            str(robot_root / "robot-004.glb"),
            "--report",
            str(identity_report),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"identity validation failed:\n{completed.stdout}")

    changed_pixels = changed_pixel_count(
        outputs["flat_2d"], outputs["dimensional_2_5d"]
    )
    if changed_pixels < 10000:
        raise RuntimeError(
            f"2.5D dimensional separation is too subtle: {changed_pixels} pixels"
        )
    caption_counts = {
        name: caption_pixel_count(Image.open(path)) for name, path in outputs.items()
    }
    if any(count < 200 for count in caption_counts.values()):
        raise RuntimeError(f"caption validation failed: {caption_counts}")

    sheet = args.output / "contact-sheet.png"
    write_contact_sheet(
        [
            ("2D identity", outputs["flat_2d"]),
            ("2.5D dimensional identity", outputs["dimensional_2_5d"]),
            ("3D identity + shared caption", outputs["filament_3d"]),
        ],
        sheet,
        pack_root / "fonts" / "changa-one" / "ChangaOne-Regular.ttf",
    )
    contract = robot_root / "identity.json"
    identity = json.loads(contract.read_text(encoding="utf-8"))["identity"]
    sparkle_color = color_channels(identity["sparkle"]["color"])
    all_sparkle_bounds = {
        name: sparkle_bounds(path, sparkle_color) for name, path in outputs.items()
    }
    camera_sparkle_bounds = {
        name: sparkle_bounds(path, sparkle_color)
        for name, path in camera_proofs.items()
    }
    expected_size = round(512 * float(identity["sparkle"]["screenSizeRatio"]))
    if len(set(all_sparkle_bounds.values())) != 1:
        raise RuntimeError(f"backends disagree on sparkle bounds: {all_sparkle_bounds}")
    if len(set(camera_sparkle_bounds.values())) != 1:
        raise RuntimeError(
            f"sparkle size changed with camera span: {camera_sparkle_bounds}"
        )
    sparkle_box = next(iter(all_sparkle_bounds.values()))
    rasterized_size = max(
        sparkle_box[2] - sparkle_box[0], sparkle_box[3] - sparkle_box[1]
    )
    if abs(rasterized_size - expected_size) > 5:
        raise RuntimeError(
            f"sparkle is not approximately {expected_size}px at 512px output: "
            f"{sparkle_box}"
        )
    manifest = {
        "milestone": "MR-115",
        "characterId": "robot-004",
        "identityContract": str(contract.relative_to(root)),
        "identitySha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "dimensionalChangedPixels": changed_pixels,
        "captionWhitePixelCounts": caption_counts,
        "sparkleBounds": all_sparkle_bounds,
        "sparkleCameraSpanProof": {
            "bounds": camera_sparkle_bounds,
            "outputs": {name: record(path) for name, path in camera_proofs.items()},
        },
        "outputs": {name: record(path) for name, path in outputs.items()},
        "identityValidation": record(identity_report),
        "contactSheet": record(sheet),
    }
    (args.output / "review.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote robot-004 identity review to {args.output}")


if __name__ == "__main__":
    main()
