#!/usr/bin/env python3
"""Generate the deterministic Micro Reactions Orbit layered 2.5D proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTLINE = "#203654"
PRIMARY = "#9B7CF6"
SECONDARY = "#6D55D8"
LIGHT = "#D7C9FF"
ACCENT = "#FFD166"
WHITE = "#FFFDF8"
BLUSH = "#FF6F91"


def svg(content: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        f'viewBox="0 0 512 512">{content}</svg>\n'
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def pack_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pack_id": "micro-orbit-004-2_5d-proof",
        "canvas": {"width": 512, "height": 512},
        "layers": [
            {
                "id": "shadow",
                "source": "layers/00-shadow.svg",
                "z": 0,
                "depth": -0.65,
                "pivot": "shadow",
            },
            {
                "id": "ring-back",
                "source": "layers/10-ring-back.svg",
                "z": 10,
                "depth": -0.10,
                "parent": "body",
                "pivot": "orbit",
            },
            {
                "id": "body",
                "source": "layers/20-body.svg",
                "z": 20,
                "depth": 0.12,
                "pivot": "body",
                "collision_bounds": {"x": 99, "y": 100, "width": 314, "height": 320},
            },
            {
                "id": "antenna",
                "source": "layers/25-antenna.svg",
                "z": 25,
                "depth": 0.22,
                "parent": "body",
                "pivot": "antenna",
            },
            {
                "id": "ring-front",
                "source": "layers/30-ring-front.svg",
                "z": 30,
                "depth": 0.38,
                "parent": "body",
                "pivot": "orbit",
            },
            {
                "id": "face-shading",
                "source": "layers/35-face-shading.svg",
                "z": 35,
                "depth": 0.26,
                "parent": "body",
                "pivot": "face",
            },
            {
                "id": "face",
                "source": "layers/40-face-proud.svg",
                "z": 40,
                "depth": 0.31,
                "parent": "body",
                "pivot": "face",
            },
            {
                "id": "rim-light",
                "source": "layers/45-rim-light.svg",
                "z": 45,
                "depth": 0.34,
                "parent": "body",
                "pivot": "body",
            },
            {
                "id": "stars",
                "source": "layers/50-stars.svg",
                "z": 50,
                "depth": 0.46,
                "pivot": "orbit",
            },
        ],
        "base_layers": [
            "shadow",
            "ring-back",
            "body",
            "antenna",
            "ring-front",
            "face",
            "stars",
        ],
        "expressions": {"proud": []},
        "poses": {
            "front": [],
            "dimensional": ["face-shading", "rim-light"],
        },
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT",
            "source": "generate_micro_orbit_2_5d_proof.py; original deterministic SVG",
            "production_use": "forbidden-until-selected-glb-and-final-pack-review",
        },
        "anchors": {
            "face_center": {"x": 256, "y": 258},
            "ground_contact": {"x": 256, "y": 420},
        },
        "pivots": {
            "shadow": {"x": 256, "y": 420},
            "body": {"x": 256, "y": 260},
            "face": {"x": 256, "y": 255},
            "antenna": {"x": 257, "y": 112},
            "orbit": {"x": 256, "y": 270},
        },
        "avoid_regions": [],
        "text_clearance": 16,
    }


def sticker_document(
    sticker_id: str,
    *,
    pose: str,
    view: tuple[int, int] | None = None,
    animated: bool = False,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": 1,
        "sticker_id": sticker_id,
        "pack_id": "micro-orbit-004-2_5d-proof",
        "alt_text": "Orbit showing a confident proud reaction with layered orbital depth",
        "expression": "proud",
        "pose": pose,
        "seed": 1,
    }
    if view is not None:
        value["view"] = {"x": view[0], "y": view[1]}
    if animated:
        value["animation"] = {
            "duration_ms": 1200,
            "fps": 12,
            "loop": "loop",
            "tracks": [
                {
                    "target": "body",
                    "property": "rotation_degrees",
                    "keyframes": [
                        {"at_ms": 0, "value": 0, "easing": "ease_in_out"},
                        {"at_ms": 300, "value": -3, "easing": "ease_out"},
                        {"at_ms": 600, "value": 2, "easing": "ease_in_out"},
                        {"at_ms": 900, "value": -1, "easing": "ease_in_out"},
                        {"at_ms": 1200, "value": 0, "easing": "ease_in_out"},
                    ],
                },
                {
                    "target": "ring-front",
                    "property": "rotation_degrees",
                    "keyframes": [
                        {"at_ms": 0, "value": 0, "easing": "ease_in_out"},
                        {"at_ms": 600, "value": 5, "easing": "ease_in_out"},
                        {"at_ms": 1200, "value": 0, "easing": "ease_in_out"},
                    ],
                },
                {
                    "target": "antenna",
                    "property": "rotation_degrees",
                    "keyframes": [
                        {"at_ms": 0, "value": 0, "easing": "ease_in_out"},
                        {"at_ms": 300, "value": 5, "easing": "ease_out"},
                        {"at_ms": 600, "value": -3, "easing": "ease_in_out"},
                        {"at_ms": 1200, "value": 0, "easing": "ease_in_out"},
                    ],
                },
                {
                    "target": "shadow",
                    "property": "scale_x",
                    "keyframes": [
                        {"at_ms": 0, "value": 1, "easing": "ease_in_out"},
                        {"at_ms": 600, "value": 0.93, "easing": "ease_in_out"},
                        {"at_ms": 1200, "value": 1, "easing": "ease_in_out"},
                    ],
                },
            ],
        }
    return value


def author(root: Path) -> None:
    write_json(root / "pack.json", pack_document())
    write(
        root / "layers/00-shadow.svg",
        svg(f'<ellipse cx="256" cy="420" rx="118" ry="21" fill="{OUTLINE}" fill-opacity=".18"/>'),
    )
    write(
        root / "layers/10-ring-back.svg",
        svg(
            f'<path d="M64 270 Q256 116 448 270" fill="none" '
            f'stroke="{ACCENT}" stroke-width="22" stroke-linecap="round"/>'
        ),
    )
    write(
        root / "layers/20-body.svg",
        svg(
            f'<circle cx="256" cy="259" r="151" fill="{PRIMARY}" stroke="{OUTLINE}" '
            'stroke-width="12"/>'
            f'<path d="M132 315 Q256 382 380 315 Q357 398 256 413 Q155 398 132 315 Z" '
            f'fill="{SECONDARY}" fill-opacity=".50"/>'
            f'<ellipse cx="216" cy="178" rx="54" ry="36" fill="{LIGHT}" fill-opacity=".30"/>'
        ),
    )
    write(
        root / "layers/25-antenna.svg",
        svg(
            f'<path d="M257 112 Q245 75 278 55" fill="none" stroke="{OUTLINE}" '
            'stroke-width="12" stroke-linecap="round"/>'
            f'<circle cx="286" cy="48" r="20" fill="{ACCENT}" stroke="{OUTLINE}" stroke-width="12"/>'
        ),
    )
    write(
        root / "layers/30-ring-front.svg",
        svg(
            f'<path d="M64 270 Q256 424 448 270" fill="none" '
            f'stroke="{ACCENT}" stroke-width="22" stroke-linecap="round"/>'
        ),
    )
    write(
        root / "layers/35-face-shading.svg",
        svg(
            f'<path d="M125 260 Q256 379 387 260 Q380 405 256 414 Q132 405 125 260 Z" '
            f'fill="{OUTLINE}" fill-opacity=".08"/>'
        ),
    )
    write(
        root / "layers/40-face-proud.svg",
        svg(
            f'<path d="M174 205 Q208 181 242 203 M270 203 Q304 181 338 205" '
            f'fill="none" stroke="{OUTLINE}" stroke-width="11" stroke-linecap="round"/>'
            f'<path d="M180 239 Q207 217 234 239 Q207 257 180 239 Z" fill="{WHITE}" '
            f'stroke="{OUTLINE}" stroke-width="8"/>'
            f'<path d="M278 239 Q305 217 332 239 Q305 257 278 239 Z" fill="{WHITE}" '
            f'stroke="{OUTLINE}" stroke-width="8"/>'
            f'<circle cx="211" cy="235" r="9" fill="{OUTLINE}"/>'
            f'<circle cx="309" cy="235" r="9" fill="{OUTLINE}"/>'
            f'<path d="M180 283 Q201 270 222 283 M290 283 Q311 270 332 283" '
            f'fill="none" stroke="{BLUSH}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M211 306 Q250 342 304 296" fill="none" stroke="{OUTLINE}" '
            'stroke-width="13" stroke-linecap="round"/>'
            f'<circle cx="256" cy="372" r="28" fill="{ACCENT}" stroke="{OUTLINE}" stroke-width="7"/>'
            f'<path d="M256 355 L261 367 L274 368 L264 377 L267 390 L256 383 '
            f'L245 390 L248 377 L238 368 L251 367 Z" fill="{WHITE}"/>'
        ),
    )
    write(
        root / "layers/45-rim-light.svg",
        svg(
            f'<path d="M145 230 Q151 150 223 122" fill="none" stroke="{LIGHT}" '
            'stroke-opacity=".72" stroke-width="11" stroke-linecap="round"/>'
        ),
    )
    write(
        root / "layers/50-stars.svg",
        svg(
            f'<path d="M84 179 L90 193 L105 198 L90 203 L84 218 L78 203 L63 198 '
            f'L78 193 Z" fill="{ACCENT}" stroke="{OUTLINE}" stroke-width="5"/>'
            f'<circle cx="433" cy="335" r="10" fill="{LIGHT}" stroke="{OUTLINE}" stroke-width="5"/>'
        ),
    )
    write_json(
        root / "stickers/front.json",
        sticker_document("micro-orbit-004-2_5d-front", pose="front"),
    )
    write_json(
        root / "stickers/dimensional.json",
        sticker_document("micro-orbit-004-2_5d-dimensional", pose="dimensional"),
    )
    write_json(
        root / "stickers/parallax-left.json",
        sticker_document(
            "micro-orbit-004-2_5d-parallax-left",
            pose="dimensional",
            view=(-36, 10),
        ),
    )
    write_json(
        root / "stickers/parallax-right.json",
        sticker_document(
            "micro-orbit-004-2_5d-parallax-right",
            pose="dimensional",
            view=(36, -10),
        ),
    )
    write_json(
        root / "stickers/orbital-tilt.json",
        sticker_document(
            "micro-orbit-004-2_5d-orbital-tilt",
            pose="dimensional",
            animated=True,
        ),
    )


def render(cli: Path, root: Path, sticker_name: str, output: Path, reduced: bool) -> None:
    sticker = root / "stickers" / sticker_name
    run([str(cli), "validate", "--pack", str(root / "pack.json"), "--sticker", str(sticker)])
    command = [
        str(cli),
        "render",
        "--pack",
        str(root / "pack.json"),
        "--sticker",
        str(sticker),
        "--output",
        str(output),
        "--width",
        "512",
        "--height",
        "512",
        "--quality",
        "100",
        "--lossless",
    ]
    if reduced:
        command.append("--first-frame-only")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(command)


def image_difference(first: Path, second: Path) -> int:
    with Image.open(first) as left, Image.open(second) as right:
        difference = ImageChops.difference(left.convert("RGBA"), right.convert("RGBA"))
        return sum(channel[1] for channel in difference.getextrema())


def animated_metrics(path: Path) -> dict[str, Any]:
    hashes: list[str] = []
    with Image.open(path) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            hashes.append(hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest())
        return {
            "frame_count": len(hashes),
            "animated_webp": len(hashes) > 1,
            "visible_mid_cycle_change": len(set(hashes)) > 1,
            "loop_closure": hashes[0] == hashes[-1],
        }


def contact_sheet(paths: list[tuple[str, Path]], output: Path) -> None:
    tile = 300
    label_height = 38
    sheet = Image.new("RGB", (tile * len(paths), tile + label_height), "#EEF3F8")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, path) in enumerate(paths):
        with Image.open(path) as source:
            frame = source.convert("RGBA")
        frame = frame.resize((tile, tile), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (tile, tile), "#FFFFFF")
        cell.alpha_composite(frame)
        sheet.paste(cell.convert("RGB"), (index * tile, 0))
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (index * tile + (tile - (bounds[2] - bounds[0])) // 2, tile + 12),
            label,
            fill=OUTLINE,
            font=font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


def build_review(source: Path, review: Path, cli: Path) -> None:
    rendered: list[tuple[str, Path]] = []
    for label, sticker in (
        ("front", "front.json"),
        ("dimensional", "dimensional.json"),
        ("parallax left", "parallax-left.json"),
        ("parallax right", "parallax-right.json"),
    ):
        path = review / f"{sticker.removesuffix('.json')}.webp"
        render(cli, source, sticker, path, True)
        rendered.append((label, path))
    animation = review / "orbital-tilt-animated.webp"
    reduced = review / "orbital-tilt-reduced-motion.webp"
    render(cli, source, "orbital-tilt.json", animation, False)
    render(cli, source, "orbital-tilt.json", reduced, True)
    rendered.append(("orbital tilt poster", reduced))
    sheet = review / "contact-sheet.png"
    contact_sheet(rendered, sheet)
    metrics = animated_metrics(animation)
    if not metrics["animated_webp"] or not metrics["visible_mid_cycle_change"]:
        raise RuntimeError("Orbit orbital-tilt proof is not visibly animated")
    left_right_delta = image_difference(
        review / "parallax-left.webp",
        review / "parallax-right.webp",
    )
    flat_dimensional_delta = image_difference(
        review / "front.webp",
        review / "dimensional.webp",
    )
    if left_right_delta <= 0 or flat_dimensional_delta <= 0:
        raise RuntimeError("Orbit 2.5D proof does not visibly separate depth states")
    artifacts = {
        path.name: sha256(path)
        for path in (
            sheet,
            review / "front.webp",
            review / "dimensional.webp",
            review / "parallax-left.webp",
            review / "parallax-right.webp",
            animation,
            reduced,
        )
    }
    write_json(
        review / "review.json",
        {
            "schema_version": 1,
            "review_id": "micro-orbit-004-layered-2_5d-proof-v1",
            "review_status": "owner-approved",
            "production_use": "forbidden-until-selected-glb-and-final-pack-review",
            "owner_approval": (
                "contracts/"
                "micro-reactions-reaction-and-orbit-2_5d-owner-approval-v1.json"
            ),
            "identity_id": "micro-orbit-004",
            "semantic": "proud",
            "layer_count": len(pack_document()["layers"]),
            "parented_layer_count": sum(
                "parent" in layer for layer in pack_document()["layers"]
            ),
            "distinct_depth_count": len(
                {layer["depth"] for layer in pack_document()["layers"]}
            ),
            "parallax_left_right_meaningful_delta": left_right_delta,
            "flat_dimensional_meaningful_delta": flat_dimensional_delta,
            "animation": metrics,
            "artifacts": artifacts,
        },
    )


def replace(staging: Path, destination: Path, force: bool) -> None:
    if destination.exists():
        if not force:
            raise FileExistsError(f"output exists (use --force): {destination}")
        shutil.rmtree(destination)
    staging.rename(destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-output",
        type=Path,
        default=ROOT / "art" / "micro-reactions-v1" / "orbit-2_5d-proof",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=ROOT / "generated" / "micro-orbit-2_5d-review",
    )
    parser.add_argument(
        "--mascotrender",
        type=Path,
        default=ROOT / "build" / "Release" / "mascotrender",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    cli = args.mascotrender.resolve()
    if not cli.is_file() or not os.access(cli, os.X_OK):
        raise FileNotFoundError(f"MascotRender CLI is unavailable: {cli}")
    source = args.source_output.resolve()
    review = args.review_output.resolve()
    source.parent.mkdir(parents=True, exist_ok=True)
    review.parent.mkdir(parents=True, exist_ok=True)
    source_staging = Path(tempfile.mkdtemp(prefix="micro-orbit-2_5d-source-", dir=source.parent))
    review_staging = Path(tempfile.mkdtemp(prefix="micro-orbit-2_5d-review-", dir=review.parent))
    try:
        author(source_staging)
        build_review(source_staging, review_staging, cli)
        replace(source_staging, source, args.force)
        replace(review_staging, review, args.force)
    finally:
        if source_staging.exists():
            shutil.rmtree(source_staging)
        if review_staging.exists():
            shutil.rmtree(review_staging)
    print(f"generated Orbit layered 2.5D proof at {review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
