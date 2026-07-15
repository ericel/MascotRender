#!/usr/bin/env python3
"""Render review-only sheets for the five canonical layered human masters."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw


MASTER_IDS = ("H01", "H04", "H07", "H12", "H13")
FRAMINGS = ("face-closeup", "bust", "three-quarter", "full-body", "dynamic-full-body")
DEVICE_PROFILES = {
    "H01": "device.none",
    "H04": "prosthesis.lower-leg.right",
    "H07": "wheelchair.manual",
    "H12": "hearing-aid.behind-ear.right",
    "H13": "rollator.four-wheel",
}
DEVICE_CONTACTS = {
    "H04": ("knee_right", "ankle_right", "foot_right", "ground_contact"),
    "H07": ("hand_left", "hand_right", "foot_left", "foot_right", "ground_contact"),
    "H12": ("ear_right",),
    "H13": ("hand_left", "hand_right", "ground_contact"),
}
BACKGROUND = (239, 243, 248)
INK = (22, 43, 69)
MUTED = (88, 103, 122)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def render(executable: Path, pack: Path, sticker: Path, output: Path, size: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
    run([
        str(executable), "render", "--pack", str(pack), "--sticker", str(sticker),
        "--output", str(output), "--width", str(size), "--height", str(size),
        "--lossless", "--first-frame-only",
    ])


def render_animation(executable: Path, pack: Path, sticker: Path, output: Path, size: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
    run([
        str(executable), "render", "--pack", str(pack), "--sticker", str(sticker),
        "--output", str(output), "--width", str(size), "--height", str(size), "--lossless",
    ])


def resolve_point(pack: dict[str, Any], name: str) -> tuple[float, float]:
    if name in pack["pivots"]:
        point = pack["pivots"][name]
    elif name in pack["anchors"]:
        point = pack["anchors"][name]
    else:
        raise ValueError(f"pack lacks semantic point {name}")
    return float(point["x"]), float(point["y"])


def full_body_screen_point(pack: dict[str, Any], name: str) -> tuple[float, float]:
    source_x, source_y = resolve_point(pack, name)
    target_x, target_y = resolve_point(pack, "body_center")
    return ((source_x - target_x) * .91 + 256, (source_y - target_y) * .91 + 256 + 18)


def paste_contained(sheet: Image.Image, source: Path, box: tuple[int, int, int, int]) -> None:
    image = Image.open(source).convert("RGBA")
    width, height = box[2] - box[0], box[3] - box[1]
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    x = box[0] + (width - image.width) // 2
    y = box[1] + (height - image.height) // 2
    sheet.paste(image, (x, y), image)


def build_framing_matrix(posters: dict[tuple[str, str], Path], output: Path) -> None:
    cell, header, label = 250, 52, 32
    sheet = Image.new("RGB", (cell * len(FRAMINGS) + 110, header + (cell + label) * len(MASTER_IDS)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for column, framing in enumerate(FRAMINGS):
        draw.text((110 + column * cell + 10, 18), framing, fill=INK)
    for row, master_id in enumerate(MASTER_IDS):
        y = header + row * (cell + label)
        draw.text((25, y + cell // 2 - 8), master_id, fill=INK)
        for column, framing in enumerate(FRAMINGS):
            x = 110 + column * cell
            draw.rounded_rectangle((x + 5, y + 5, x + cell - 5, y + cell - 5), 18, fill=(255, 255, 255))
            paste_contained(sheet, posters[(master_id, framing)], (x + 8, y + 8, x + cell - 8, y + cell - 8))
            draw.text((x + 10, y + cell + 5), f"{master_id} · {framing}", fill=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_lineup(posters: dict[tuple[str, str], Path], output: Path, framing: str = "full-body") -> None:
    cell, art_height = 300, 300
    sheet = Image.new("RGB", (cell * len(MASTER_IDS), art_height + 66), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for column, master_id in enumerate(MASTER_IDS):
        x = column * cell
        draw.rounded_rectangle((x + 10, 10, x + cell - 10, art_height - 4), 18, fill=(255, 255, 255))
        paste_contained(sheet, posters[(master_id, framing)], (x + 12, 12, x + cell - 12, art_height - 6))
        draw.text((x + 16, art_height + 5), master_id, fill=INK)
        draw.text((x + 16, art_height + 25), DEVICE_PROFILES[master_id], fill=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_readability(posters: dict[tuple[str, int], Path], output: Path) -> None:
    sizes = (80, 96, 100)
    cell_width, row_height = 150, 126
    sheet = Image.new("RGB", (110 + cell_width * len(MASTER_IDS), 44 + row_height * len(sizes)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for column, master_id in enumerate(MASTER_IDS):
        draw.text((110 + column * cell_width + 45, 16), master_id, fill=INK)
    for row, size in enumerate(sizes):
        y = 44 + row * row_height
        draw.text((24, y + 45), f"{size}px", fill=INK)
        for column, master_id in enumerate(MASTER_IDS):
            source = Image.open(posters[(master_id, size)]).convert("RGBA")
            if source.size != (size, size):
                raise RuntimeError(f"small-size render for {master_id} is not {size}px")
            x = 110 + column * cell_width + (cell_width - size) // 2
            sheet.paste(source, (x, y + (112 - size) // 2), source)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_semantic_parts(
    records: list[dict[str, str]], rsvg_convert: Path, staging: Path, output: Path
) -> None:
    columns, cell_width, cell_height = 4, 260, 190
    rows = (len(records) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for index, record in enumerate(records):
        x, y = (index % columns) * cell_width, (index // columns) * cell_height
        draw.rounded_rectangle((x + 6, y + 6, x + cell_width - 6, y + cell_height - 6), 14, fill=(255, 255, 255))
        raster = staging / "semantic-parts" / f"{index:02d}.png"
        raster.parent.mkdir(parents=True, exist_ok=True)
        run([str(rsvg_convert), record["svg"], "-o", str(raster)])
        image = Image.open(raster).convert("RGBA")
        bounds = image.getbbox()
        if bounds is None:
            raise RuntimeError(f"empty semantic device part: {record['svg']}")
        image = image.crop(bounds)
        image.thumbnail((170, 125), Image.Resampling.LANCZOS)
        px = x + (cell_width - image.width) // 2
        py = y + 12 + (125 - image.height) // 2
        sheet.paste(image, (px, py), image)
        draw.text((x + 12, y + 142), f"{record['master_id']} · {record['part']}", fill=INK)
        draw.text((x + 12, y + 160), record["layer"], fill=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_point_sheet(
    posters: dict[tuple[str, str], Path], packs: dict[str, dict[str, Any]],
    points: dict[str, tuple[str, ...]], output: Path, title: str,
) -> None:
    cell, art_height = 300, 300
    sheet = Image.new("RGB", (cell * len(MASTER_IDS), art_height + 80), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    palette = ((229, 78, 100), (35, 182, 166), (245, 184, 46), (100, 58, 120), (40, 121, 168))
    for column, master_id in enumerate(MASTER_IDS):
        x = column * cell
        draw.rounded_rectangle((x + 10, 10, x + cell - 10, art_height - 4), 18, fill=(255, 255, 255))
        paste_contained(sheet, posters[(master_id, "full-body")], (x + 12, 12, x + cell - 12, art_height - 6))
        for index, name in enumerate(points.get(master_id, ())):
            px, py = full_body_screen_point(packs[master_id], name)
            sx = x + 12 + px * 276 / 512
            sy = 12 + py * 276 / 512
            color = palette[index % len(palette)]
            draw.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), fill=color, outline=INK, width=2)
            draw.text((sx + 6, sy - 7), name, fill=color, stroke_width=2, stroke_fill=(255, 255, 255))
        draw.text((x + 14, art_height + 5), master_id, fill=INK)
    draw.text((14, art_height + 46), title, fill=MUTED)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def build_motion_sheet(
    animations: dict[str, Path], output: Path
) -> list[dict[str, Any]]:
    masters = tuple(master_id for master_id in MASTER_IDS if master_id in animations)
    cell, label_width = 240, 90
    sheet = Image.new("RGB", (label_width + 3 * cell, len(masters) * (cell + 28)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    records: list[dict[str, Any]] = []
    for row, master_id in enumerate(masters):
        animation = Image.open(animations[master_id])
        frame_count = getattr(animation, "n_frames", 1)
        if frame_count < 3 or b"ANIM" not in animations[master_id].read_bytes():
            raise RuntimeError(f"{master_id} device motion output is not genuinely animated")
        indices = (0, frame_count // 2, frame_count - 1)
        frames = []
        for index in indices:
            animation.seek(index)
            frames.append(animation.convert("RGBA").copy())
        if ImageChops.difference(frames[0], frames[1]).getbbox() is None:
            raise RuntimeError(f"{master_id} device motion has no visible mid-cycle change")
        y = row * (cell + 28)
        draw.text((18, y + cell // 2), master_id, fill=INK)
        for column, (label, frame) in enumerate(zip(("start", "motion", "end"), frames, strict=True)):
            frame.thumbnail((cell - 16, cell - 16), Image.Resampling.LANCZOS)
            x = label_width + column * cell
            sheet.paste(frame, (x + 8, y + 8), frame)
            draw.text((x + 10, y + cell + 4), label, fill=MUTED)
        records.append({
            "master_id": master_id,
            "frame_count": frame_count,
            "animated_webp": True,
            "visible_mid_cycle_change": True,
            "sha256": sha256(animations[master_id]),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return records


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=root / "art/human-pack-v1/masters")
    parser.add_argument("--output", type=Path, default=root / "generated/canonical-human-vector-review")
    parser.add_argument("--mascotrender", type=Path, default=root / "build/Release/mascotrender")
    parser.add_argument("--rig-contract", type=Path, default=root / "contracts/humanoid-production-v2.json")
    parser.add_argument("--rsvg-convert", type=Path)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    destination = args.output.resolve()
    executable = args.mascotrender.resolve()
    rsvg_convert_value = args.rsvg_convert or shutil.which("rsvg-convert")
    if not rsvg_convert_value:
        raise RuntimeError("rsvg-convert is required for semantic device-part proof sheets")
    rsvg_convert = Path(rsvg_convert_value).resolve()
    if args.size != 512:
        raise ValueError("canonical review posters must use the 512x512 production canvas")
    generation = read_json(source / "generation-manifest.json")
    rig_contract = read_json(args.rig_contract.resolve())
    if generation.get("master_count") != 5 or generation.get("status") != "owner-vector-parity-approved":
        raise ValueError("canonical generation manifest is incomplete or overstates approval")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        posters: dict[tuple[str, str], Path] = {}
        small_posters: dict[tuple[str, int], Path] = {}
        packs: dict[str, dict[str, Any]] = {}
        semantic_parts: list[dict[str, str]] = []
        animations: dict[str, Path] = {}
        lod_records: list[dict[str, Any]] = []
        validations: list[dict[str, Any]] = []
        for master_id in MASTER_IDS:
            master = source / master_id
            identity = read_json(master / "identity.json")
            pack = read_json(master / "pack.json")
            packs[master_id] = pack
            manifest = read_json(master / "source-manifest.json")
            if identity.get("status") != "owner-vector-parity-approved" or identity.get("production_use") != "forbidden":
                raise ValueError(f"{master_id} identity approval state is inconsistent")
            if identity.get("device_profile") != DEVICE_PROFILES[master_id]:
                raise ValueError(f"{master_id} device profile drift")
            if pack.get("rig", {}).get("contract_id") != "humanoid-production-v2":
                raise ValueError(f"{master_id} is not bound to the production rig")
            profile = rig_contract.get("device_profiles", {}).get(DEVICE_PROFILES[master_id])
            bindings = pack.get("rig", {}).get("device_bindings")
            if not isinstance(profile, dict) or not isinstance(bindings, dict):
                raise ValueError(f"{master_id} lacks a valid semantic device profile")
            if set(bindings) != set(profile.get("required_parts", [])):
                raise ValueError(f"{master_id} device bindings do not satisfy the rig contract")
            layer_ids = {layer.get("id") for layer in pack.get("layers", [])}
            if not set(bindings.values()).issubset(layer_ids):
                raise ValueError(f"{master_id} device binding references a missing layer")
            layers_by_id = {layer["id"]: layer for layer in pack["layers"]}
            for part, layer_id in sorted(bindings.items()):
                semantic_parts.append({
                    "master_id": master_id,
                    "part": part,
                    "layer": layer_id,
                    "svg": str(master / layers_by_id[layer_id]["source"]),
                })
            if manifest.get("master_sha256") != sha256(master / "master.svg"):
                raise ValueError(f"{master_id} master SVG hash mismatch")
            if manifest.get("layer_count", 0) < 11:
                raise ValueError(f"{master_id} lacks semantic source layers")
            for framing in FRAMINGS:
                sticker = master / "stickers" / f"{framing}.json"
                poster = staging / "posters" / master_id / f"{framing}.webp"
                render(executable, master / "pack.json", sticker, poster, args.size)
                image = Image.open(poster).convert("RGBA")
                if image.size != (512, 512):
                    raise RuntimeError(f"{poster} has a noncanonical canvas")
                bounds = image.getbbox()
                if bounds is None or bounds[2] - bounds[0] < 40 or bounds[3] - bounds[1] < 40:
                    raise RuntimeError(f"{poster} is empty or implausibly small")
                if framing in {"three-quarter", "full-body", "dynamic-full-body"} and bounds[1] < 8:
                    raise RuntimeError(f"{master_id} {framing} violates the 8px minimum top safe margin")
                posters[(master_id, framing)] = poster
                validations.append({
                    "master_id": master_id,
                    "framing": framing,
                    "canvas": [512, 512],
                    "alpha_bounds": list(bounds),
                    "sha256": sha256(poster),
                })
            scale_sticker = master / "stickers" / "canonical-scale.json"
            scale_poster = staging / "posters" / master_id / "canonical-scale.webp"
            render(executable, master / "pack.json", scale_sticker, scale_poster, args.size)
            posters[(master_id, "canonical-scale")] = scale_poster
            for small_size in (80, 96, 100):
                small_poster = staging / "small" / str(small_size) / f"{master_id}.webp"
                render(executable, master / "pack.json", master / "stickers" / "full-body.json", small_poster, small_size)
                small_posters[(master_id, small_size)] = small_poster
                lod_records.append({
                    "master_id": master_id,
                    "size": small_size,
                    "authored_lod_selected": small_size <= 100 and manifest.get("lod_layer_count", 0) > 0,
                    "lod_layer_count": manifest.get("lod_layer_count", 0),
                    "sha256": sha256(small_poster),
                })
            motion_sticker = master / "stickers" / "device-motion-check.json"
            if motion_sticker.exists():
                motion_document = read_json(motion_sticker)
                for track in motion_document["animation"]["tracks"]:
                    if track["keyframes"][0]["value"] != track["keyframes"][-1]["value"]:
                        raise ValueError(f"{master_id} device motion track does not close")
                animation = staging / "animations" / f"{master_id}-device-motion.webp"
                render_animation(executable, master / "pack.json", motion_sticker, animation, args.size)
                animations[master_id] = animation
        sheets = {
            "framing_matrix": staging / "framing-matrix.png",
            "full_body_lineup": staging / "full-body-lineup.png",
            "canonical_scale_lineup": staging / "canonical-scale-lineup.png",
            "small_size_readability": staging / "small-size-readability.png",
            "device_semantic_parts": staging / "device-semantic-parts.png",
            "device_anchors": staging / "device-anchors.png",
            "device_pivots": staging / "device-pivots.png",
            "device_contact_points": staging / "device-contact-points.png",
            "device_motion": staging / "device-motion.png",
        }
        build_framing_matrix(posters, sheets["framing_matrix"])
        build_lineup(posters, sheets["full_body_lineup"])
        build_lineup(posters, sheets["canonical_scale_lineup"], "canonical-scale")
        build_readability(small_posters, sheets["small_size_readability"])
        build_semantic_parts(semantic_parts, rsvg_convert, staging, sheets["device_semantic_parts"])
        anchor_points = {
            master_id: tuple(rig_contract["device_profiles"][DEVICE_PROFILES[master_id]]["required_anchors"])
            for master_id in MASTER_IDS
        }
        build_point_sheet(posters, packs, anchor_points, sheets["device_anchors"], "Rig-contract required anchors")
        pivot_points = {
            master_id: ("shoulder_right", "shoulder_left", "wrist_right", "wrist_left", "hip_right", "hip_left", "knee_right", "knee_left", "ankle_right", "ankle_left")
            for master_id in MASTER_IDS
        }
        build_point_sheet(posters, packs, pivot_points, sheets["device_pivots"], "Anatomical pivots: character-right projects to screen-left")
        build_point_sheet(posters, packs, DEVICE_CONTACTS, sheets["device_contact_points"], "Authored device and ground contact points")
        motion_records = build_motion_sheet(animations, sheets["device_motion"])
        write_json(staging / "review.json", {
            "schema_version": 1,
            "verification_status": "success",
            "asset_class": "owner-approved-vector-art",
            "review_status": "owner-vector-parity-approved",
            "production_use": "forbidden",
            "concept_reference_sha256": generation["concept_reference_sha256"],
            "master_count": len(MASTER_IDS),
            "framing_count": len(FRAMINGS),
            "poster_count": len(validations),
            "comparison_poster_count": len(MASTER_IDS),
            "semantic_device_part_count": len(semantic_parts),
            "device_motion_count": len(motion_records),
            "small_size_render_count": len(lod_records),
            "authored_lod_master_count": len({record["master_id"] for record in lod_records if record["authored_lod_selected"]}),
            "canvas": [512, 512],
            "device_profiles": DEVICE_PROFILES,
            "coordinate_convention": rig_contract["coordinate_convention"],
            "resolved_review_items": [
                "H12 is authored as naturally greying straight hair, not a head covering",
                "anatomical right projects to screen-left in the unmirrored front view",
                "project owner approved H07 seated geometry and footrest relationship",
                "project owner approved vector identity parity for H01, H04, H07, H12, and H13",
            ],
            "open_review_items": [
                "replace detached and partial side/back turnaround construction",
                "author true whole-character three-quarter rotations",
                "prove farewell and disagreement pose semantics",
                "prove dimensional 2.5D behavior",
                "replace technical-prototype GLBs with identity- and device-parity production models",
                "obtain a new owner production-design decision bound to regenerated review sheets",
            ],
            "release_gate": "generated/canonical-human-production-review/release-review.json",
            "release_note": "Front-facing vector identity remains an approved foundation. The current turnaround and GLB candidate is owner-rejected; automated technical validation cannot grant public-release status.",
            "production_rig_sha256": sha256(args.rig_contract.resolve()),
            "sheets": {
                name: {"path": path.relative_to(staging).as_posix(), "sha256": sha256(path)}
                for name, path in sheets.items()
            },
            "validations": validations,
            "semantic_device_parts": [
                {key: value for key, value in record.items() if key != "svg"}
                for record in semantic_parts
            ],
            "device_motion_validations": motion_records,
            "small_size_lod_validations": lod_records,
        })
        if destination.exists():
            if not args.force:
                raise FileExistsError(f"review output exists (use --force): {destination}")
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"built 25 canonical vector review posters and {len(sheets)} sheets in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
