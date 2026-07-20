#!/usr/bin/env python3
"""Render and validate the five-identity Micro Reactions styled GLB expansion."""

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
FRAME_COUNT = 13
CLIP_DURATION = {"idle": 1.2, "proud": 1.0}


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


def read_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or not isinstance(value.get("identities"), list):
        raise ValueError(f"invalid styled GLB identity contract: {path}")
    return value


def glb_document(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"not a binary glTF file: {path}")
    version, total = struct.unpack_from("<II", data, 4)
    if version != 2 or total != len(data):
        raise RuntimeError(f"invalid GLB header: {path}")
    json_length, json_kind = struct.unpack_from("<I4s", data, 12)
    if json_kind != b"JSON":
        raise RuntimeError(f"missing GLB JSON chunk: {path}")
    value = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"GLB document is not an object: {path}")
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
        "animated_webp": True,
        "visible_mid_cycle_change": len(set(hashes)) > 1,
        "loop_closure": hashes[0] == hashes[-1],
        "first_frame_sha256": hashes[0],
        "last_frame_sha256": hashes[-1],
    }


def alpha_bounds(path: Path) -> list[int]:
    with Image.open(path) as image:
        bounds = image.convert("RGBA").getchannel("A").getbbox()
    if bounds is None:
        raise RuntimeError(f"empty render: {path}")
    return list(bounds)


def image_delta(first: Path, second: Path) -> int:
    with Image.open(first) as left, Image.open(second) as right:
        difference = ImageChops.difference(left.convert("RGBA"), right.convert("RGBA"))
        return sum(extreme[1] for extreme in difference.getextrema())


def palette_pixel_counts(path: Path, palette: dict[str, str]) -> dict[str, int]:
    with Image.open(path) as image:
        pixels = list(image.convert("RGBA").getdata())
    counts: dict[str, int] = {}
    for name, value in palette.items():
        target = tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))
        counts[name] = sum(
            alpha > 200
            and all(abs(actual - expected) <= 3 for actual, expected in zip(rgb, target))
            for *rgb, alpha in pixels
        )
    required = ("outline", "primary", "secondary", "light", "accent", "white", "blush")
    missing = [name for name in required if counts.get(name, 0) < 12]
    if missing:
        raise RuntimeError(f"{path.name} lost required palette colors: {missing}")
    return counts


def draw_labeled_sheet(
    rows: list[list[tuple[str, Path]]],
    output: Path,
    *,
    tile: int = 250,
) -> None:
    label_height = 38
    columns = max(len(row) for row in rows)
    sheet = Image.new(
        "RGB",
        (tile * columns, (tile + label_height) * len(rows)),
        "#EEF3F8",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row_index, row in enumerate(rows):
        for column, (label, path) in enumerate(row):
            with Image.open(path) as source:
                frame = source.convert("RGBA").resize(
                    (tile, tile),
                    Image.Resampling.LANCZOS,
                )
            cell = Image.new("RGBA", (tile, tile), "#FFFFFF")
            cell.alpha_composite(frame)
            left = column * tile
            top = row_index * (tile + label_height)
            sheet.paste(cell.convert("RGB"), (left, top))
            bounds = draw.textbbox((0, 0), label, font=font)
            draw.text(
                (left + (tile - bounds[2] + bounds[0]) // 2, top + tile + 12),
                label,
                fill="#20324B",
                font=font,
            )
    sheet.save(output, optimize=True)


def small_display_family_sheet(
    identities: list[tuple[str, Path]],
    output: Path,
) -> None:
    sizes = (80, 100, 160)
    tile = 220
    row_height = 225
    sheet = Image.new("RGB", (tile * len(sizes), row_height * len(identities)), "#25364D")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row, (name, rest) in enumerate(identities):
        with Image.open(rest) as source:
            original = source.convert("RGBA")
        for column, size in enumerate(sizes):
            left = column * tile
            top = row * row_height
            draw.rounded_rectangle(
                (left + 10, top + 10, left + tile - 10, top + row_height - 10),
                radius=20,
                fill="#F7FAFC",
            )
            frame = original.resize((size, size), Image.Resampling.LANCZOS)
            x = left + (tile - size) // 2
            y = top + 45 + (160 - size) // 2
            sheet.paste(frame, (x, y), frame)
            label = f"{name} · {size}px"
            bounds = draw.textbbox((0, 0), label, font=font)
            draw.text(
                (left + (tile - bounds[2] + bounds[0]) // 2, top + 24),
                label,
                fill="#20324B",
                font=font,
            )
    sheet.save(output, optimize=True)


def animation_html(
    specs: list[dict[str, Any]],
    output: Path,
) -> None:
    figures: list[str] = []
    for spec in specs:
        identity_id = spec["identity_id"]
        for clip in ("idle", spec["signature_clip"], "proud"):
            figures.append(
                f'<figure><img src="{identity_id}/{clip}-animated.webp" '
                f'alt="{spec["display_name"]} {clip} animation">'
                f"<figcaption>{spec['display_name']} · {clip}</figcaption></figure>"
            )
    output.write_text(
        "<!doctype html><meta charset=\"utf-8\">"
        "<title>Micro Reactions styled GLB family playback</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#20324b;margin:24px}"
        "main{display:grid;grid-template-columns:repeat(3,minmax(220px,1fr));gap:18px}"
        "figure{margin:0;background:white;border-radius:22px;padding:14px;text-align:center}"
        "img{display:block;width:100%;height:auto}figcaption{font-weight:800;margin-top:8px}"
        "</style><h1>Micro Reactions · styled GLB family playback</h1><main>"
        + "".join(figures)
        + "</main>",
        encoding="utf-8",
    )


def extract_animation_frame(source: Path, output: Path, frame_index: int) -> None:
    with Image.open(source) as image:
        image.seek(frame_index)
        frame = image.convert("RGBA")
        frame.save(output, format="WEBP", lossless=True, quality=100, method=6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "content/micro-styled-glb-identities-v1.json",
    )
    parser.add_argument(
        "--generator",
        type=Path,
        default=ROOT / "tools/generate_micro_styled_glbs.py",
    )
    parser.add_argument(
        "--glb-root",
        type=Path,
        default=ROOT / "art/micro-reactions-v1/styled-glb-proofs",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=ROOT / "build/Release/mascotrender-glb-preview",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated/micro-styled-glb-family-review",
    )
    parser.add_argument(
        "--owner-approval",
        type=Path,
        default=ROOT
        / "contracts/micro-reactions-styled-glb-family-owner-approval-v1.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    contract = read_contract(args.contract.resolve())
    specs: list[dict[str, Any]] = contract["identities"]
    owner_approval_path = args.owner_approval.resolve()
    owner_approval = json.loads(owner_approval_path.read_text(encoding="utf-8"))
    if (
        owner_approval.get("authority") != "project-owner"
        or owner_approval.get("decision") != "approved"
        or owner_approval.get("gate")
        != "micro-reactions-styled-glb-family-expansion-v1"
    ):
        raise RuntimeError(f"invalid family owner approval: {owner_approval_path}")
    output = args.output.resolve()
    preview = args.preview.resolve()
    glb_root = args.glb_root.resolve()
    run(
        [
            "python3",
            str(args.generator.resolve()),
            "--contract",
            str(args.contract.resolve()),
            "--output-root",
            str(glb_root),
            "--check",
        ]
    )

    staging = Path(tempfile.mkdtemp(prefix="micro-styled-glb-review-", dir=output.parent))
    identity_reports: dict[str, Any] = {}
    family_rows: list[list[tuple[str, Path]]] = []
    signature_motion_rows: list[list[tuple[str, Path]]] = []
    small_display_items: list[tuple[str, Path]] = []
    try:
        for spec in specs:
            identity_id = spec["identity_id"]
            name = spec["display_name"]
            signature_clip = spec["signature_clip"]
            glb = glb_root / f"{identity_id}.glb"
            document = glb_document(glb)
            node_names = {node.get("name") for node in document.get("nodes", [])}
            required_nodes = {
                "MascotRoot",
                "Body",
                "Face",
                "ProudEyeShapes",
                "CompactProudSmile",
                spec["signature_node"],
                "AchievementMedal",
                "GroundShadow",
            }
            if not required_nodes.issubset(node_names):
                raise RuntimeError(
                    f"{identity_id} is missing semantic nodes: {required_nodes - node_names}"
                )
            clips = {animation["name"] for animation in document.get("animations", [])}
            expected_clips = {"idle", signature_clip, "proud"}
            if clips != expected_clips:
                raise RuntimeError(f"{identity_id} clips differ: {sorted(clips)}")
            if document["asset"]["extras"]["mascot"] != identity_id:
                raise RuntimeError(f"{identity_id} GLB metadata identity drift")
            if document.get("extensionsUsed") != ["KHR_materials_unlit"]:
                raise RuntimeError(f"{identity_id} lost the styled unlit material contract")

            identity_root = staging / identity_id
            rest = identity_root / "rest.webp"
            reduced = identity_root / "reduced-motion.webp"
            render_frame(preview, glb, rest)
            shutil.copy2(rest, reduced)
            clip_frames: dict[str, list[Path]] = {}
            clip_posters: dict[str, Path] = {}
            animations: dict[str, Any] = {}
            durations = {"idle": 1.2, signature_clip: 1.2, "proud": 1.0}
            for clip in ("idle", signature_clip, "proud"):
                duration = durations[clip]
                frames: list[Path] = []
                for index in range(FRAME_COUNT):
                    frame = identity_root / "frames" / clip / f"{index:02d}.webp"
                    render_frame(
                        preview,
                        glb,
                        frame,
                        animation=clip,
                        time_seconds=duration * index / (FRAME_COUNT - 1),
                    )
                    frames.append(frame)
                clip_frames[clip] = frames
                clip_posters[clip] = frames[FRAME_COUNT // 2]
                metrics = encode_animation(
                    frames,
                    identity_root / f"{clip}-animated.webp",
                    round(duration * 1000 / (FRAME_COUNT - 1)),
                )
                if not metrics["visible_mid_cycle_change"] or not metrics["loop_closure"]:
                    raise RuntimeError(f"{identity_id}/{clip} does not visibly animate and close")
                animations[clip] = metrics

            flat = (
                ROOT
                / "generated/micro-reactions-v1-review/reduced-motion"
                / identity_id
                / f"{identity_id}-proud.webp"
            )
            if not flat.is_file():
                raise FileNotFoundError(f"missing approved vector proud reference: {flat}")
            per_identity_sheet = identity_root / "cross-backend-contact-sheet.png"
            draw_labeled_sheet(
                [
                    [
                        (f"{name} · flat proud", flat),
                        (f"{name} · GLB rest", rest),
                        (f"{name} · {signature_clip}", clip_posters[signature_clip]),
                        (f"{name} · GLB proud", clip_posters["proud"]),
                    ]
                ],
                per_identity_sheet,
            )
            per_identity_motion = identity_root / "motion-sample-sheet.png"
            draw_labeled_sheet(
                [
                    [
                        (f"{clip} · start", frames[0]),
                        (f"{clip} · mid", frames[FRAME_COUNT // 2]),
                        (f"{clip} · closure", frames[-1]),
                    ]
                    for clip, frames in clip_frames.items()
                ],
                per_identity_motion,
            )
            family_rows.append(
                [
                    (f"{name} · flat proud", flat),
                    (f"{name} · GLB rest", rest),
                    (f"{name} · {signature_clip}", clip_posters[signature_clip]),
                    (f"{name} · GLB proud", clip_posters["proud"]),
                ]
            )
            signature_motion_rows.append(
                [
                    (f"{name} · start", clip_frames[signature_clip][0]),
                    (f"{name} · {signature_clip}", clip_posters[signature_clip]),
                    (f"{name} · closure", clip_frames[signature_clip][-1]),
                ]
            )
            small_display_items.append((name, rest))
            bounds = alpha_bounds(rest)
            if min(bounds[0], bounds[1], 512 - bounds[2], 512 - bounds[3]) < 16:
                raise RuntimeError(f"{identity_id} violates the 16 px hard margin: {bounds}")
            counts = palette_pixel_counts(rest, spec["palette"])
            if rest.read_bytes() != reduced.read_bytes():
                raise RuntimeError(f"{identity_id} reduced motion differs from rest")
            glb_hash = sha256(glb)
            if owner_approval["approved_glbs"].get(identity_id) != glb_hash:
                raise RuntimeError(f"owner-approved GLB hash drift: {identity_id}")
            identity_reports[identity_id] = {
                "display_name": name,
                "glb_sha256": glb_hash,
                "semantic_node_count": len(required_nodes),
                "semantic_nodes": sorted(required_nodes),
                "clip_names": sorted(clips),
                "palette_pixel_counts": counts,
                "alpha_bounds": bounds,
                "rest_to_signature_mid_delta": image_delta(
                    rest,
                    clip_posters[signature_clip],
                ),
                "rest_to_proud_mid_delta": image_delta(rest, clip_posters["proud"]),
                "animations": animations,
                "artifacts": {
                    path.name: sha256(path)
                    for path in (
                        per_identity_sheet,
                        per_identity_motion,
                        rest,
                        reduced,
                        identity_root / "idle-animated.webp",
                        identity_root / f"{signature_clip}-animated.webp",
                        identity_root / "proud-animated.webp",
                    )
                },
            }
        orbit_review = ROOT / "generated/micro-orbit-glb-review"
        orbit_owner_decision_path = (
            ROOT / "contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json"
        )
        orbit_owner_decision = json.loads(
            orbit_owner_decision_path.read_text(encoding="utf-8")
        )
        orbit_root = staging / "micro-orbit-004"
        orbit_root.mkdir(parents=True, exist_ok=True)
        for filename in (
            "rest.webp",
            "reduced-motion.webp",
            "idle-animated.webp",
            "orbital-tilt-animated.webp",
            "proud-animated.webp",
        ):
            source = orbit_review / filename
            if not source.is_file():
                raise FileNotFoundError(f"missing approved Orbit review artifact: {source}")
            expected = orbit_owner_decision["reviewed_artifacts"].get(filename)
            if expected is not None and sha256(source) != expected:
                raise RuntimeError(f"approved Orbit artifact hash drift: {filename}")
            shutil.copy2(source, orbit_root / filename)
        orbit_signature_mid = orbit_root / "orbital-tilt-mid.webp"
        orbit_proud_mid = orbit_root / "proud-mid.webp"
        extract_animation_frame(
            orbit_root / "orbital-tilt-animated.webp",
            orbit_signature_mid,
            FRAME_COUNT // 2,
        )
        extract_animation_frame(
            orbit_root / "proud-animated.webp",
            orbit_proud_mid,
            FRAME_COUNT // 2,
        )
        orbit_flat = (
            ROOT
            / "generated/micro-reactions-v1-review/reduced-motion"
            / "micro-orbit-004/micro-orbit-004-proud.webp"
        )
        family_rows.insert(
            3,
            [
                ("Orbit · flat proud", orbit_flat),
                ("Orbit · approved GLB", orbit_root / "rest.webp"),
                ("Orbit · orbital-tilt", orbit_signature_mid),
                ("Orbit · GLB proud", orbit_proud_mid),
            ],
        )
        signature_motion_rows.insert(
            3,
            [
                ("Orbit · start", orbit_root / "rest.webp"),
                ("Orbit · orbital-tilt", orbit_signature_mid),
                ("Orbit · closure", orbit_root / "rest.webp"),
            ],
        )
        small_display_items.insert(3, ("Orbit", orbit_root / "rest.webp"))

        family_sheet = staging / "family-cross-backend-contact-sheet.png"
        draw_labeled_sheet(family_rows, family_sheet, tile=240)
        family_motion = staging / "family-signature-motion-sheet.png"
        draw_labeled_sheet(signature_motion_rows, family_motion, tile=240)
        small_display = staging / "family-small-display-80-100-160.png"
        small_display_family_sheet(small_display_items, small_display)
        playback = staging / "animation-review.html"
        playback_specs = [
            *specs[:3],
            {
                "identity_id": "micro-orbit-004",
                "display_name": "Orbit",
                "signature_clip": "orbital-tilt",
            },
            *specs[3:],
        ]
        animation_html(playback_specs, playback)
        family_artifacts = {
            family_sheet.name: sha256(family_sheet),
            family_motion.name: sha256(family_motion),
            small_display.name: sha256(small_display),
            playback.name: sha256(playback),
        }
        if owner_approval["reviewed_artifacts"] != family_artifacts:
            raise RuntimeError("owner-approved family review artifact hash drift")
        report = {
            "schema_version": 1,
            "review_id": "micro-reactions-styled-glb-family-expansion-v1",
            "review_status": "owner-approved",
            "production_use": "approved-for-styled-glb-family-expansion",
            "owner_approval": {
                "path": "contracts/micro-reactions-styled-glb-family-owner-approval-v1.json",
                "sha256": sha256(owner_approval_path),
            },
            "reference_identity": "micro-orbit-004",
            "reference_gate": "micro-orbit-final-glb-face-parity-v1",
            "identity_count": len(specs) + 1,
            "new_glb_count": len(specs),
            "approved_reference_glb_count": 1,
            "deterministic_generation": True,
            "family_gate_checks": {
                "identity_specific_anatomy": True,
                "six_identity_family_coherence_evidence": True,
                "shared_proud_face_contract": True,
                "semantic_nodes_present": True,
                "three_real_clips_per_identity": True,
                "visible_signature_motion": True,
                "loop_closure": True,
                "reduced_motion_byte_identity": True,
                "small_display_profiles_px": [80, 100, 160],
                "hard_margin_px": 16,
            },
            "approved_reference": {
                "identity_id": "micro-orbit-004",
                "owner_gate": orbit_owner_decision["gate"],
                "owner_decision_sha256": sha256(orbit_owner_decision_path),
                "production_use": orbit_owner_decision["production_use"],
            },
            "identities": identity_reports,
            "artifacts": family_artifacts,
        }
        write_json(staging / "review.json", report)
        for spec in specs:
            shutil.rmtree(staging / spec["identity_id"] / "frames")
        if output.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {output}")
            shutil.rmtree(output)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(f"rendered Micro Reactions styled GLB family review at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
