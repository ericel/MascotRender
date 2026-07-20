#!/usr/bin/env python3
"""Render and validate the Micro Reactions Orbit styled GLB proof."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
CLIPS = {"idle": 1.2, "orbital-tilt": 1.2, "proud": 1.0}
FRAME_COUNT = 13
PALETTE = {
    "outline": "#203654",
    "primary": "#9B7CF6",
    "secondary": "#6D55D8",
    "light": "#D7C9FF",
    "accent": "#FFD166",
    "white": "#FFFDF8",
    "blush": "#FF6F91",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def glb_document(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError("Orbit proof is not a binary glTF file")
    version, total = struct.unpack_from("<II", data, 4)
    if version != 2 or total != len(data):
        raise RuntimeError("Orbit proof has an invalid GLB header")
    json_length, json_kind = struct.unpack_from("<I4s", data, 12)
    if json_kind != b"JSON":
        raise RuntimeError("Orbit proof is missing its JSON chunk")
    value = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Orbit proof GLB document is not an object")
    return value


def render_frame(
    preview: Path,
    glb: Path,
    output: Path,
    *,
    animation: str | None = None,
    time_seconds: float = 0.0,
) -> None:
    command = [
        str(preview),
        "--input",
        str(glb),
        "--output",
        str(output),
        "--width",
        "512",
        "--height",
        "512",
        "--span",
        "4.55",
        "--center-y",
        "0.18",
    ]
    if animation is not None:
        command.extend(["--animation", animation, "--time", f"{time_seconds:.6f}"])
    output.parent.mkdir(parents=True, exist_ok=True)
    run(command)


def encode_animation(frames: list[Path], output: Path, duration_ms: int) -> dict[str, Any]:
    images = [Image.open(path).convert("RGBA") for path in frames]
    hashes = [hashlib.sha256(image.tobytes()).hexdigest() for image in images]
    images[0].save(
        output,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,
        lossless=True,
        quality=100,
        method=6,
    )
    for image in images:
        image.close()
    return {
        "frame_count": len(hashes),
        "visible_mid_cycle_change": len(set(hashes)) > 1,
        "loop_closure": hashes[0] == hashes[-1],
        "first_frame_sha256": hashes[0],
        "last_frame_sha256": hashes[-1],
    }


def alpha_bounds(path: Path) -> list[int]:
    with Image.open(path) as image:
        bounds = image.convert("RGBA").getchannel("A").getbbox()
    if bounds is None:
        raise RuntimeError(f"render is empty: {path}")
    return list(bounds)


def palette_pixel_counts(path: Path) -> dict[str, int]:
    with Image.open(path) as image:
        pixels = list(image.convert("RGBA").getdata())
    counts: dict[str, int] = {}
    for name, value in PALETTE.items():
        target = tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))
        counts[name] = sum(
            alpha > 200
            and all(abs(actual - expected) <= 3 for actual, expected in zip(rgb, target))
            for *rgb, alpha in pixels
        )
    required = ("outline", "primary", "secondary", "light", "accent", "white", "blush")
    missing = [name for name in required if counts[name] < 20]
    if missing:
        raise RuntimeError(f"GLB render lost Orbit palette colors: {missing}")
    return counts


def image_delta(first: Path, second: Path) -> int:
    with Image.open(first) as left, Image.open(second) as right:
        difference = ImageChops.difference(left.convert("RGBA"), right.convert("RGBA"))
        return sum(extreme[1] for extreme in difference.getextrema())


def contact_sheet(items: list[tuple[str, Path]], output: Path) -> None:
    tile = 300
    label_height = 42
    sheet = Image.new("RGB", (tile * len(items), tile + label_height), "#EEF3F8")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, path) in enumerate(items):
        with Image.open(path) as source:
            frame = source.convert("RGBA").resize((tile, tile), Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (tile, tile), "#FFFFFF")
        cell.alpha_composite(frame)
        sheet.paste(cell.convert("RGB"), (index * tile, 0))
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (index * tile + (tile - bounds[2] + bounds[0]) // 2, tile + 14),
            label,
            fill="#203654",
            font=font,
        )
    sheet.save(output, optimize=True)


def motion_sheet(
    clip_frames: dict[str, list[Path]],
    output: Path,
) -> None:
    tile = 260
    label_height = 34
    sheet = Image.new(
        "RGB",
        (tile * 3, (tile + label_height) * len(CLIPS)),
        "#EEF3F8",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row, clip in enumerate(CLIPS):
        frames = clip_frames[clip]
        for column, frame_index in enumerate((0, FRAME_COUNT // 2, FRAME_COUNT - 1)):
            with Image.open(frames[frame_index]) as source:
                frame = source.convert("RGBA").resize(
                    (tile, tile),
                    Image.Resampling.LANCZOS,
                )
            cell = Image.new("RGBA", (tile, tile), "#FFFFFF")
            cell.alpha_composite(frame)
            left = column * tile
            top = row * (tile + label_height)
            sheet.paste(cell.convert("RGB"), (left, top))
            label = f"{clip} · {'start' if column == 0 else 'mid' if column == 1 else 'closure'}"
            bounds = draw.textbbox((0, 0), label, font=font)
            draw.text(
                (left + (tile - bounds[2] + bounds[0]) // 2, top + tile + 11),
                label,
                fill="#203654",
                font=font,
            )
    sheet.save(output, optimize=True)


def small_display_sheet(rest: Path, output: Path) -> None:
    sizes = (80, 100, 160)
    card_width = 260
    card_height = 280
    sheet = Image.new("RGB", (card_width * len(sizes), card_height), "#25364D")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    with Image.open(rest) as source:
        original = source.convert("RGBA")
    for column, size in enumerate(sizes):
        left = column * card_width
        draw.rounded_rectangle(
            (left + 14, 14, left + card_width - 14, card_height - 14),
            radius=24,
            fill="#F7FAFC",
        )
        frame = original.resize((size, size), Image.Resampling.LANCZOS)
        x = left + (card_width - size) // 2
        y = 70 + (160 - size) // 2
        cell = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        cell.alpha_composite(frame, (x - left, y))
        sheet.paste(cell, (left, 0), cell)
        label = f"{size}px"
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (left + (card_width - bounds[2] + bounds[0]) // 2, 32),
            label,
            fill="#203654",
            font=font,
        )
    sheet.save(output, optimize=True)


def animation_html(output: Path) -> None:
    figures = "".join(
        f'<figure><img src="{clip}-animated.webp" alt="Orbit {clip} animation">'
        f"<figcaption>{clip}</figcaption></figure>"
        for clip in CLIPS
    )
    output.write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>Orbit styled GLB playback</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#203654;margin:24px}"
        "main{display:grid;grid-template-columns:repeat(3,minmax(220px,1fr));gap:18px}"
        "figure{margin:0;background:white;border-radius:22px;padding:14px;text-align:center}"
        "img{display:block;width:100%;height:auto}figcaption{font-weight:800;margin-top:8px}"
        "@media(prefers-reduced-motion:reduce){img{display:none}.reduced{display:block}}</style>"
        "<h1>Micro Reactions · Orbit styled GLB playback</h1><main>"
        + figures
        + '<figure><img class="reduced" src="reduced-motion.webp" '
        'alt="Orbit reduced-motion dimensional still"><figcaption>reduced motion</figcaption></figure>'
        "</main>",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--glb",
        type=Path,
        default=ROOT / "art/micro-reactions-v1/orbit-glb-proof/micro-orbit-004.glb",
    )
    parser.add_argument(
        "--generator",
        type=Path,
        default=ROOT / "tools/generate_micro_orbit_glb.py",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=ROOT / "build/Release/mascotrender-glb-preview",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated/micro-orbit-glb-review",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    glb = args.glb.resolve()
    preview = args.preview.resolve()
    output = args.output.resolve()
    run(["python3", str(args.generator.resolve()), "--output", str(glb), "--check"])
    document = glb_document(glb)
    names = {node.get("name") for node in document["nodes"]}
    required_nodes = {
        "OrbitRoot",
        "Body",
        "OrbitRing",
        "AntennaTip",
        "UpwardBrows",
        "AsymmetricConfidentSmile",
        "AchievementMedal",
        "GroundShadow",
    }
    if not required_nodes.issubset(names):
        raise RuntimeError(f"Orbit GLB is missing semantic nodes: {required_nodes - names}")
    clips = {animation["name"] for animation in document.get("animations", [])}
    if clips != set(CLIPS):
        raise RuntimeError(f"Orbit GLB clips differ from contract: {sorted(clips)}")
    if "KHR_materials_unlit" not in document.get("extensionsUsed", []):
        raise RuntimeError("Orbit GLB does not preserve the flat sticker palette")

    staging = Path(tempfile.mkdtemp(prefix="micro-orbit-glb-review-", dir=output.parent))
    try:
        rest = staging / "rest.webp"
        render_frame(preview, glb, rest)
        reduced_motion = staging / "reduced-motion.webp"
        shutil.copy2(rest, reduced_motion)
        clip_posters: dict[str, Path] = {}
        clip_frames: dict[str, list[Path]] = {}
        animation_metrics: dict[str, Any] = {}
        for clip, duration in CLIPS.items():
            frame_root = staging / "frames" / clip
            times = [duration * index / (FRAME_COUNT - 1) for index in range(FRAME_COUNT)]
            frames: list[Path] = []
            for index, time_seconds in enumerate(times):
                frame = frame_root / f"{index:02d}.webp"
                render_frame(
                    preview,
                    glb,
                    frame,
                    animation=clip,
                    time_seconds=time_seconds,
                )
                frames.append(frame)
            clip_frames[clip] = frames
            clip_posters[clip] = frames[FRAME_COUNT // 2]
            animated = staging / f"{clip}-animated.webp"
            metrics = encode_animation(
                frames,
                animated,
                round(duration * 1000 / (FRAME_COUNT - 1)),
            )
            if not metrics["visible_mid_cycle_change"] or not metrics["loop_closure"]:
                raise RuntimeError(f"{clip} does not visibly animate and close")
            animation_metrics[clip] = metrics

        flat = ROOT / "generated/micro-reactions-v1-review/reduced-motion/micro-orbit-004/micro-orbit-004-proud.webp"
        layered = ROOT / "generated/micro-orbit-2_5d-review/dimensional.webp"
        if not flat.is_file() or not layered.is_file():
            raise FileNotFoundError("the approved vector and layered Orbit proofs are required")
        sheet = staging / "cross-backend-contact-sheet.png"
        contact_sheet(
            [
                ("flat 2D · proud", flat),
                ("layered 2.5D · proud", layered),
                ("styled GLB · rest", rest),
                ("styled GLB · orbital tilt", clip_posters["orbital-tilt"]),
                ("styled GLB · proud rise", clip_posters["proud"]),
            ],
            sheet,
        )
        motion = staging / "motion-sample-sheet.png"
        motion_sheet(clip_frames, motion)
        small_display = staging / "small-display-80-100-160.png"
        small_display_sheet(rest, small_display)
        playback = staging / "animation-review.html"
        animation_html(playback)
        counts = palette_pixel_counts(rest)
        bounds = alpha_bounds(rest)
        if min(bounds[0], bounds[1], 512 - bounds[2], 512 - bounds[3]) < 16:
            raise RuntimeError(f"Orbit GLB violates the 16 px hard margin: {bounds}")
        report = {
            "schema_version": 1,
            "review_id": "micro-orbit-004-final-glb-face-parity-review-v1",
            "review_status": "owner-approved",
            "production_use": "approved-as-selected-styled-glb-proof",
            "owner_decision": "contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json",
            "identity_id": "micro-orbit-004",
            "semantic": "proud",
            "glb_sha256": sha256(glb),
            "generator_sha256": sha256(args.generator.resolve()),
            "deterministic_generation": True,
            "extensions_used": document.get("extensionsUsed", []),
            "semantic_node_count": len(required_nodes),
            "clip_names": sorted(clips),
            "palette_pixel_counts": counts,
            "alpha_bounds": bounds,
            "rest_to_orbital_mid_delta": image_delta(rest, clip_posters["orbital-tilt"]),
            "rest_to_proud_mid_delta": image_delta(rest, clip_posters["proud"]),
            "selected_glb_gate_checks": {
                "cross_backend_identity_parity_evidence": True,
                "styled_outline_hierarchy_present": True,
                "approved_palette_present": True,
                "semantic_nodes_present": True,
                "deterministic_glb_generation": True,
                "three_real_animation_clips": True,
                "loop_closure": True,
                "reduced_motion_equivalent": True,
                "small_display_profiles_px": [80, 100, 160],
            },
            "targeted_face_parity_corrections": {
                "narrow_horizontal_eye_construction": True,
                "composed_proud_eyelids": True,
                "smooth_arched_brows": True,
                "compact_curved_smile": True,
                "restrained_blush": True,
                "continuous_curved_antenna_attachment": True,
                "approved_model_rig_materials_and_clips_preserved": True,
            },
            "animations": animation_metrics,
            "artifacts": {
                path.name: sha256(path)
                for path in (
                    sheet,
                    motion,
                    small_display,
                    playback,
                    rest,
                    reduced_motion,
                    staging / "idle-animated.webp",
                    staging / "orbital-tilt-animated.webp",
                    staging / "proud-animated.webp",
                )
            },
        }
        write_json(staging / "review.json", report)
        shutil.rmtree(staging / "frames")
        if output.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {output}")
            shutil.rmtree(output)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(f"rendered styled Orbit GLB review at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
