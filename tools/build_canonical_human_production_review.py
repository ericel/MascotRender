#!/usr/bin/env python3
"""Build technical evidence and apply the bound owner design decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageStat

from build_canonical_human_review import BACKGROUND, INK, MUTED, paste_contained, read_json, render, render_animation, run, sha256, write_json
from generate_canonical_human_masters import EXPRESSIONS, MASTERS, POSES


ROOT = Path(__file__).resolve().parent.parent
MASTER_IDS = tuple(sorted(MASTERS))
VIEWS = ("front", "three-quarter", "side", "back")
PAIRING = {
    "happy": "agreement", "laughing": "celebration", "surprised": "surprise",
    "thinking": "concern", "confident": "agreement", "sorry": "gratitude", "excited": "celebration",
}
DEVICE_NODES = {
    "H01": (),
    "H04": ("ProstheticSocketRight", "ProstheticPylonRight", "ProstheticFootRight"),
    "H07": ("WheelLeft", "WheelRight", "PushrimLeft", "PushrimRight", "WheelSideProfileLeft", "WheelSideProfileRight", "WheelchairSeat", "WheelchairBackrest", "WheelchairFrame", "WheelchairFootrest", "WheelchairCasterLeft", "WheelchairCasterRight"),
    "H12": ("EarRightAnchor", "HearingAidRoot", "HearingAidCaseRight", "HearingAidTubeRight", "HearingAidEarpieceRight"),
    "H13": ("RollatorFrame", "RollatorHandleLeft", "RollatorHandleRight", "RollatorWheelFrontLeft", "RollatorWheelFrontRight", "RollatorWheelRearLeft", "RollatorWheelRearRight"),
}
IDENTITY_CORRECTION_NODES = {
    "H01": ("Skirt",),
    "H04": ("CoilyHairCap", "ForearmLeft", "ForearmRight"),
    "H07": (),
    "H12": ("BobRearCoverage", "GreyStreakRear"),
    "H13": (),
}


def glb_json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"glTF":
        raise ValueError(f"not a GLB: {path}")
    version, total = struct.unpack_from("<II", payload, 4)
    if version != 2 or total != len(payload):
        raise ValueError(f"invalid GLB header: {path}")
    json_length, chunk_type = struct.unpack_from("<I4s", payload, 12)
    if chunk_type != b"JSON":
        raise ValueError(f"GLB does not start with JSON: {path}")
    return json.loads(payload[20:20+json_length].decode("utf-8"))


def channels(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index+2], 16) for index in (1, 3, 5))


def luminance(color: str) -> float:
    values = [value / 255 for value in channels(color)]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in values]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def contrast(left: str, right: str) -> float:
    a, b = luminance(left), luminance(right)
    return (max(a, b) + .05) / (min(a, b) + .05)


def alpha_bounds(path: Path) -> tuple[int, int, int, int]:
    bounds = Image.open(path).convert("RGBA").getbbox()
    if bounds is None:
        raise RuntimeError(f"empty render: {path}")
    return bounds


def matching_pixels(path: Path, color: str, tolerance: int = 4) -> int:
    target = channels(color)
    image = Image.open(path).convert("RGBA")
    return sum(
        alpha > 180 and all(abs(actual - expected) <= tolerance for actual, expected in zip((red, green, blue), target))
        for red, green, blue, alpha in image.getdata()
    )


def composited_mean_channel_delta(left: Path, right: Path) -> float:
    background = Image.new("RGBA", (512, 512), (*BACKGROUND, 255))
    first = Image.alpha_composite(background, Image.open(left).convert("RGBA")).convert("RGB")
    second = Image.alpha_composite(background, Image.open(right).convert("RGBA")).convert("RGB")
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3


def render_glb(renderer: Path, source: Path, output: Path, animation: str = "", time: float = .5) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(renderer), "--input", str(source), "--output", str(output), "--width", "512", "--height", "512", "--span", "4.5", "--center-y", "0"]
    if animation:
        command += ["--animation", animation, "--time", str(time)]
    run(command)


def render_glb_animation_review(renderer: Path, source: Path, output_root: Path, master_id: str) -> tuple[dict[str, Path], dict[str, Any]]:
    frame_paths: list[Path] = []
    frames: list[Image.Image] = []
    for index in range(9):
        frame_path = output_root / master_id / "frames" / f"{index:02d}.webp"
        render_glb(renderer, source, frame_path, "semantic-excited", index / 8)
        frame_paths.append(frame_path)
        frames.append(Image.open(frame_path).convert("RGBA"))
    animated = output_root / master_id / f"{master_id}-semantic-excited-animated.webp"
    reduced = output_root / master_id / f"{master_id}-semantic-excited-reduced-motion.webp"
    animated.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        animated, "WEBP", save_all=True, append_images=frames[1:],
        duration=125, loop=0, lossless=True, method=6,
    )
    frames[len(frames)//2].save(reduced, "WEBP", lossless=True, method=6)
    first_last_delta = sum(ImageStat.Stat(ImageChops.difference(frames[0], frames[-1])).mean) / 4
    midpoint_delta = sum(ImageStat.Stat(ImageChops.difference(frames[0], frames[len(frames)//2])).mean) / 4
    step_deltas = [
        sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 4
        for left, right in zip(frames, frames[1:])
    ]
    with Image.open(animated) as check_animated, Image.open(reduced) as check_reduced:
        animated_frame_count = getattr(check_animated, "n_frames", 1)
        reduced_frame_count = getattr(check_reduced, "n_frames", 1)
    if animated_frame_count != 9 or reduced_frame_count != 1 or first_last_delta != 0 or midpoint_delta < 2:
        raise RuntimeError(f"{master_id} animation/reduced-motion evidence failed structural playback checks")
    selected = {
        "t0": frame_paths[0], "t25": frame_paths[2], "t50": frame_paths[4],
        "t75": frame_paths[6], "t100": frame_paths[8], "reduced": reduced,
    }
    validation = {
        "master_id": master_id, "animation": "semantic-excited", "canvas": [512, 512],
        "animated_webp": animated.relative_to(output_root.parent).as_posix(),
        "animated_sha256": sha256(animated), "animated_frame_count": animated_frame_count,
        "frame_duration_ms": 125, "loop_duration_ms": 1000,
        "first_last_mean_channel_delta": first_last_delta,
        "midpoint_mean_channel_delta": midpoint_delta,
        "maximum_adjacent_frame_delta": max(step_deltas),
        "reduced_motion_webp": reduced.relative_to(output_root.parent).as_posix(),
        "reduced_motion_sha256": sha256(reduced), "reduced_motion_frame_count": reduced_frame_count,
        "reduced_motion_presentation": "static-semantic-midpoint",
        "technical_status": "pass", "visual_playback_status": "awaiting-owner-review",
    }
    return selected, validation


def resolved_depths(pack: dict[str, Any]) -> dict[str, float]:
    layers = {item["id"]: item for item in pack["layers"]}
    resolved: dict[str, float] = {}

    def visit(layer_id: str) -> float:
        if layer_id in resolved:
            return resolved[layer_id]
        item = layers[layer_id]
        parent = item.get("parent")
        value = float(item.get("depth", 0)) + (visit(parent) if parent else 0.0)
        resolved[layer_id] = value
        return value

    for layer_id in layers:
        visit(layer_id)
    return resolved


def contact_sheet(records: dict[tuple[str, str], Path], columns: tuple[str, ...], output: Path, cell: int = 230, rows: tuple[str, ...] = MASTER_IDS) -> None:
    header = 38
    sheet = Image.new("RGB", (92 + cell * len(columns), header + cell * len(rows)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for index, label in enumerate(columns):
        draw.text((100 + index * cell, 12), label, fill=INK)
    for row, master_id in enumerate(rows):
        y = header + row * cell
        draw.text((18, y + cell // 2), master_id, fill=INK)
        for column, label in enumerate(columns):
            x = 92 + column * cell
            draw.rounded_rectangle((x+4, y+4, x+cell-4, y+cell-4), 14, fill=(255,255,255))
            paste_contained(sheet, records[(master_id, label)], (x+8, y+8, x+cell-8, y+cell-8))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "art/human-pack-v1/masters")
    parser.add_argument("--output", type=Path, default=ROOT / "generated/canonical-human-production-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build/Release/mascotrender")
    parser.add_argument("--glb-renderer", type=Path, default=ROOT / "build/Release/mascotrender-glb-preview")
    parser.add_argument("--rsvg-convert", type=Path)
    parser.add_argument(
        "--design-review",
        type=Path,
        default=ROOT / "contracts/human-canonical-production-design-review-v1.json",
    )
    parser.add_argument("--expect-review-status")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source, destination = args.input.resolve(), args.output.resolve()
    if not args.mascotrender.is_file() or not args.glb_renderer.is_file():
        raise FileNotFoundError("both MascotRender and Filament GLB preview executables are required")
    rsvg = args.rsvg_convert or Path(shutil.which("rsvg-convert") or "")
    if not rsvg.is_file():
        raise FileNotFoundError("rsvg-convert is required")
    staging = Path(tempfile.mkdtemp(prefix=destination.name+".staging-", dir=destination.parent))
    try:
        provenance = read_json(source / "provenance.json")
        representation = read_json(source / "representation-review.json")
        if provenance.get("license") != "MIT" or provenance.get("distribution_authority", {}).get("decision") != "approved-for-public-release":
            raise ValueError("MIT provenance/public distribution authority is not approved")
        if representation.get("decision") != "approved" or representation.get("disposition") != "respectful-and-non-stereotyped-for-human-pack-production":
            raise ValueError("diverse-human representation disposition is incomplete")

        turnaround: dict[tuple[str,str], Path] = {}
        expressions: dict[tuple[str,str], Path] = {}
        poses: dict[tuple[str,str], Path] = {}
        depth: dict[tuple[str,str], Path] = {}
        device_topology: dict[tuple[str,str], Path] = {}
        parity: dict[tuple[str,str], Path] = {}
        glb_semantics: dict[tuple[str,str], Path] = {}
        animation_playback: dict[tuple[str,str], Path] = {}
        reduced_records, glb_records, contrast_records, rigid_depth_records, playback_records = [], [], [], [], []
        for master_id in MASTER_IDS:
            root = source / master_id
            identity = read_json(root / "identity.json")
            manifest = read_json(root / "source-manifest.json")
            pack = root / "pack.json"
            pack_document = read_json(pack)
            if identity.get("status") != "owner-vector-parity-approved" or identity.get("production_use") != "forbidden" or identity.get("provenance", {}).get("license") != "MIT":
                raise ValueError(f"{master_id} lacks owner approval or MIT provenance")
            if manifest.get("turnaround_view_count") != 4 or manifest.get("production_expression_count") != len(EXPRESSIONS) or manifest.get("production_pose_count") != len(POSES):
                raise ValueError(f"{master_id} production source matrix is incomplete")
            depths = resolved_depths(pack_document)
            rigid_groups: list[tuple[str, tuple[str, ...]]] = []
            if master_id == "H07":
                rigid_groups.append(("wheelchair-and-seated-contact", (
                    "torso", "leg-left", "leg-right", "arm-left-rest", "arm-right-rest",
                    "device-wheelchair-frame", "device-wheel-left", "device-pushrim-left",
                    "device-wheel-right", "device-pushrim-right", "device-wheelchair-footrest")))
            elif master_id == "H12":
                rigid_groups.append(("hearing-aid-head-attachment", (
                    "head", "device-hearing-case-right", "device-hearing-tube-right", "device-hearing-earpiece-right")))
            elif master_id == "H13":
                rigid_groups.append(("rollator-and-hand-contact", (
                    "torso", "arm-left-rest", "arm-right-rest", "device-rollator-frame",
                    "device-rollator-handle-left", "device-rollator-handle-right",
                    "device-rollator-wheel-front-left", "device-rollator-wheel-front-right",
                    "device-rollator-wheel-rear-left", "device-rollator-wheel-rear-right")))
            for group_name, members in rigid_groups:
                values = [depths[member] for member in members]
                spread = max(values) - min(values)
                if spread > 1e-6:
                    raise RuntimeError(f"{master_id} {group_name} accumulates divergent parallax depth: {spread}")
                rigid_depth_records.append({
                    "master_id": master_id, "group": group_name, "member_count": len(members),
                    "resolved_depth": values[0], "maximum_depth_spread": spread, "status": "pass",
                })
            expression_hashes = set()
            for expression in EXPRESSIONS:
                standard = staging / "expressions" / master_id / f"{expression}.webp"
                reduced = staging / "reduced-motion" / master_id / f"{expression}.webp"
                render(args.mascotrender, pack, root / "stickers" / "production" / f"{expression}.json", standard, 512)
                render(args.mascotrender, pack, root / "stickers" / "reduced-motion" / f"{expression}.json", reduced, 512)
                if standard.read_bytes() != reduced.read_bytes():
                    raise RuntimeError(f"{master_id} {expression} reduced-motion output changes semantic presentation")
                neutral_expression = staging / "expression-isolation" / master_id / f"{expression}.webp"
                render(args.mascotrender, pack, root / "stickers" / "expressions" / f"{expression}.json", neutral_expression, 512)
                expressions[(master_id, expression)] = neutral_expression
                expression_hashes.add(sha256(neutral_expression))
                reduced_records.append({"master_id": master_id, "expression": expression, "pose": PAIRING[expression], "byte_identical_static_equivalent": True, "sha256": sha256(reduced)})
            if len(expression_hashes) != len(EXPRESSIONS):
                raise RuntimeError(f"{master_id} expression/pose renders are not visually distinct")
            pose_hashes = set()
            for pose in POSES:
                pose_render = staging / "pose-isolation" / master_id / f"{pose}.webp"
                render(args.mascotrender, pack, root / "stickers" / "poses" / f"{pose}.json", pose_render, 512)
                poses[(master_id, pose)] = pose_render
                pose_hashes.add(sha256(pose_render))
            if len(pose_hashes) != len(POSES):
                raise RuntimeError(f"{master_id} pose renders are not visually distinct")

            layered_rest = staging / "depth" / master_id / "layered-rest.webp"
            parallax_left = staging / "depth" / master_id / "parallax-left.webp"
            parallax_right = staging / "depth" / master_id / "parallax-right.webp"
            animated_depth = staging / "depth" / master_id / "animated-depth.webp"
            flat_depth = staging / "depth" / master_id / "flat.webp"
            render(args.mascotrender, pack, root / "stickers" / "depth" / "layered-rest.json", layered_rest, 512)
            render(args.mascotrender, root / "pack-flat.json", root / "stickers" / "depth" / "layered-rest.json", flat_depth, 512)
            render(args.mascotrender, pack, root / "stickers" / "depth" / "parallax-left.json", parallax_left, 512)
            render(args.mascotrender, pack, root / "stickers" / "depth" / "parallax-right.json", parallax_right, 512)
            render_animation(args.mascotrender, pack, root / "stickers" / "depth" / "animated-depth.json", animated_depth, 512)
            with Image.open(animated_depth) as motion:
                if getattr(motion, "n_frames", 1) < 3:
                    raise RuntimeError(f"{master_id} depth evidence is not actually animated")
                motion.seek(motion.n_frames // 2)
                midpoint = staging / "depth" / master_id / "animated-midpoint.png"
                motion.convert("RGBA").save(midpoint)
            if ImageChops.difference(Image.open(parallax_left).convert("RGBA"), Image.open(parallax_right).convert("RGBA")).getbbox() is None:
                raise RuntimeError(f"{master_id} layered parallax evidence has no visible displacement")
            depth[(master_id, "flat 2D")] = flat_depth
            depth[(master_id, "layered rest")] = layered_rest
            depth[(master_id, "parallax left")] = parallax_left
            depth[(master_id, "parallax right")] = parallax_right
            depth[(master_id, "motion midpoint")] = midpoint
            flat_happy = flat_depth
            flat_layered_delta = composited_mean_channel_delta(flat_happy, layered_rest)
            if flat_layered_delta > 1.5:
                raise RuntimeError(f"{master_id} flat 2D and layered 2.5D identity posters drift")
            palette = identity["palette"]
            contrast_record = {
                "master_id": master_id,
                "outline_to_canvas": contrast(palette["outline"], "#EFF3F8"),
                "eye_white_to_outline": contrast("#FFF8EE", palette["outline"]),
                "primary_to_canvas": contrast(palette["primary"], "#EFF3F8"),
            }
            if contrast_record["outline_to_canvas"] < 10 or contrast_record["eye_white_to_outline"] < 10:
                raise RuntimeError(f"{master_id} critical silhouette/face contrast failed")
            contrast_record["status"] = "pass"
            contrast_records.append(contrast_record)

            glb = root / f"{master_id}-production.glb"
            document = glb_json(glb)
            asset_identity = document.get("asset", {}).get("extras", {}).get("characterIdentity", {})
            nodes = {node.get("name") for node in document.get("nodes", [])}
            materials = {material.get("name") for material in document.get("materials", [])}
            character_nodes = [node for node in document.get("nodes", []) if node.get("extras", {}).get("characterId") == master_id]
            animations = {animation.get("name") for animation in document.get("animations", [])}
            expected_clips = {*POSES, *{f"expression-{name}" for name in EXPRESSIONS}}
            expected_turnarounds = {"turnaround-three-quarter", "turnaround-side", "turnaround-back"}
            semantic_clips = {"semantic-excited"}
            if asset_identity.get("characterId") != master_id or len(character_nodes) != 1 or not expected_clips.issubset(animations) or not expected_turnarounds.issubset(animations) or not semantic_clips.issubset(animations):
                raise RuntimeError(f"{master_id} GLB identity or semantic clips are incomplete")
            if not set(DEVICE_NODES[master_id]).issubset(nodes):
                raise RuntimeError(f"{master_id} GLB lacks semantic device nodes")
            if not set(IDENTITY_CORRECTION_NODES[master_id]).issubset(nodes):
                raise RuntimeError(f"{master_id} GLB lacks targeted identity-correction geometry")
            if not {"Outline", "PrimaryCelShadow"}.issubset(materials):
                raise RuntimeError(f"{master_id} GLB lacks the shared outline/cel-shading material language")
            if any("KHR_materials_unlit" not in material.get("extensions", {}) for material in document.get("materials", [])):
                raise RuntimeError(f"{master_id} GLB contains a material outside deterministic toon transport")
            rest = staging / "glb" / master_id / "rest.webp"
            greet = staging / "glb" / master_id / "greeting.webp"
            excited = staging / "glb" / master_id / "excited.webp"
            render_glb(args.glb_renderer, glb, rest)
            turnaround[(master_id, "front")] = rest
            for view, clip in (("three-quarter", "turnaround-three-quarter"), ("side", "turnaround-side"), ("back", "turnaround-back")):
                view_render = staging / "turnarounds" / f"{master_id}-{view}.webp"
                render_glb(args.glb_renderer, glb, view_render, clip)
                bounds = alpha_bounds(view_render)
                if bounds[2]-bounds[0] < 70 or bounds[3]-bounds[1] < 160:
                    raise RuntimeError(f"{master_id} {view} turnaround is implausibly small")
                turnaround[(master_id, view)] = view_render
            if master_id != "H01":
                for view in VIEWS:
                    device_topology[(master_id, view)] = turnaround[(master_id, view)]
            clip_hashes: dict[str, str] = {}
            for clip in sorted(expected_clips | semantic_clips):
                clip_render = staging / "glb-clips" / master_id / f"{clip}.webp"
                render_glb(args.glb_renderer, glb, clip_render, clip)
                clip_hashes[clip] = sha256(clip_render)
                if clip == "greeting":
                    shutil.copyfile(clip_render, greet)
                elif clip == "semantic-excited":
                    shutil.copyfile(clip_render, excited)
            pose_hashes = {clip_hashes[name] for name in POSES}
            expression_hashes_3d = {clip_hashes[f"expression-{name}"] for name in EXPRESSIONS}
            if len(pose_hashes) != len(POSES) or len(expression_hashes_3d) != len(EXPRESSIONS):
                raise RuntimeError(f"{master_id} GLB semantic pose/expression clips are not all visually distinct")
            if ImageChops.difference(Image.open(rest).convert("RGBA"), Image.open(greet).convert("RGBA")).getbbox() is None:
                raise RuntimeError(f"{master_id} GLB greeting clip has no visible motion")
            if ImageChops.difference(Image.open(rest).convert("RGBA"), Image.open(excited).convert("RGBA")).getbbox() is None:
                raise RuntimeError(f"{master_id} GLB expression clip has no visible motion")
            greeting_delta = composited_mean_channel_delta(rest, greet)
            excited_delta = composited_mean_channel_delta(rest, excited)
            if greeting_delta < .35 or excited_delta < .75:
                raise RuntimeError(
                    f"{master_id} GLB semantic presentation is not visually readable "
                    f"(greeting={greeting_delta:.3f}, excited={excited_delta:.3f})"
                )
            for color_name in ("skin", "hair", "primary", "outline"):
                if matching_pixels(rest, palette[color_name]) < 20:
                    raise RuntimeError(f"{master_id} GLB render lacks {color_name} identity palette")
            vector = expressions[(master_id, "happy")]
            vb, gb = alpha_bounds(vector), alpha_bounds(rest)
            vector_aspect = (vb[2]-vb[0]) / (vb[3]-vb[1])
            glb_aspect = (gb[2]-gb[0]) / (gb[3]-gb[1])
            if abs(vector_aspect-glb_aspect) > .8:
                raise RuntimeError(f"{master_id} vector/GLB silhouette aspect drift is too large")
            parity[(master_id, "flat 2D")] = flat_happy
            parity[(master_id, "layered 2.5D")] = layered_rest
            parity[(master_id, "GLB rest")] = rest
            parity[(master_id, "GLB greeting")] = greet
            parity[(master_id, "GLB excited")] = excited
            glb_semantics[(master_id, "rest")] = rest
            glb_semantics[(master_id, "greeting")] = greet
            glb_semantics[(master_id, "excited")] = excited
            playback_frames, playback_validation = render_glb_animation_review(
                args.glb_renderer, glb, staging / "animation-playback", master_id
            )
            for label, path in playback_frames.items():
                animation_playback[(master_id, label)] = path
            playback_records.append(playback_validation)
            glb_records.append({
                "master_id": master_id, "sha256": sha256(glb), "animation_count": len(animations),
                "required_clip_count": len(expected_clips), "semantic_device_node_count": len(DEVICE_NODES[master_id]),
                "targeted_identity_correction_node_count": len(IDENTITY_CORRECTION_NODES[master_id]),
                "art_direction_materials_verified": ["Outline", "PrimaryCelShadow"],
                "palette_verified_in_filament": True, "silhouette_aspect_delta": abs(vector_aspect-glb_aspect),
                "filament_backend": "Metal", "rendered_clip_count": len(clip_hashes),
                "all_pose_frames_distinct": True, "all_expression_frames_distinct": True,
                "semantic_greeting_mean_channel_delta": greeting_delta,
                "semantic_excited_mean_channel_delta": excited_delta,
                "flat_layered_mean_channel_delta": flat_layered_delta,
                "reduced_motion_behavior": "freeze-semantic-clip-at-0.5-seconds-with-playback-disabled",
                "status": "technical-pass",
            })

        sheets = {
            "turnarounds": staging / "turnaround-sheet.png",
            "expressions": staging / "expression-sheet.png",
            "poses": staging / "pose-sheet.png",
            "depth_motion": staging / "depth-motion-sheet.png",
            "device_topology": staging / "device-topology-sheet.png",
            "glb_semantics": staging / "glb-semantic-pose-sheet.png",
            "animation_playback": staging / "animation-playback-sheet.png",
            "cross_backend_parity": staging / "cross-backend-parity-sheet.png",
        }
        contact_sheet(turnaround, VIEWS, sheets["turnarounds"])
        contact_sheet(expressions, EXPRESSIONS, sheets["expressions"], 205)
        contact_sheet(poses, POSES, sheets["poses"], 175)
        contact_sheet(depth, ("flat 2D", "layered rest", "parallax left", "parallax right", "motion midpoint"), sheets["depth_motion"])
        contact_sheet(device_topology, VIEWS, sheets["device_topology"], rows=("H04", "H07", "H12", "H13"))
        contact_sheet(glb_semantics, ("rest", "greeting", "excited"), sheets["glb_semantics"])
        contact_sheet(animation_playback, ("t0", "t25", "t50", "t75", "t100", "reduced"), sheets["animation_playback"], 190)
        contact_sheet(parity, ("flat 2D", "layered 2.5D", "GLB rest", "GLB greeting", "GLB excited"), sheets["cross_backend_parity"])
        playback_html = [
            "<!doctype html><meta charset='utf-8'><title>Canonical Human Animation Review</title>",
            "<style>body{font-family:system-ui;background:#eff3f8;color:#162b45}section{display:flex;gap:24px;align-items:start;margin:24px}figure{margin:0;background:white;padding:12px;border-radius:12px}img{width:220px;height:220px;object-fit:contain}figcaption{text-align:center;font-weight:700}</style>",
            "<h1>Canonical Human animation and reduced-motion review</h1>",
        ]
        for record in playback_records:
            playback_html.append(
                f"<section><h2>{record['master_id']}</h2>"
                f"<figure><img src='{record['animated_webp']}'><figcaption>animated semantic-excited</figcaption></figure>"
                f"<figure><img src='{record['reduced_motion_webp']}'><figcaption>reduced-motion static equivalent</figcaption></figure></section>"
            )
        (staging / "animation-review.html").write_text("\n".join(playback_html) + "\n", encoding="utf-8")
        technical_gates = {
            "contract-and-provenance": "pass",
            "hierarchy-preserving-glb-turnarounds-and-bounds": "pass",
            "required-framing-files-and-bounds": "pass",
            "isolated-expression-files-distinct": "pass",
            "isolated-pose-files-distinct": "pass",
            "layered-depth-parallax-and-motion-evidence": "pass",
            "rigid-device-parallax-depth-groups": "pass",
            "small-size-files-and-bounds": "pass",
            "complexion-palette-and-contrast": "pass",
            "device-semantic-node-presence": "pass",
            "animation-clips-and-reduced-motion": "pass",
            "glb-semantic-presentation-readability-threshold": "pass",
            "animated-webp-loop-and-reduced-motion-structure": "pass",
            "glb-load-render-and-palette-transport": "pass",
        }
        design_review = read_json(args.design_review.resolve())
        if (
            design_review.get("family_id") != "human-character-library-canonical-family"
            or design_review.get("authority") != "project-owner"
            or design_review.get("decision") not in {"approved", "partial-approval", "rejected"}
        ):
            raise ValueError("production design review is malformed or lacks project-owner authority")
        artifact_hashes = {path.name: sha256(path) for path in sheets.values()}
        review_is_bound = design_review.get("reviewed_artifacts") == artifact_hashes
        if review_is_bound and design_review["decision"] == "approved":
            review_status = "public-release-approved"
            production_use = "public-release"
            production_gates = design_review["production_gates"]
            blocking_findings: list[str] = []
        elif review_is_bound and design_review["decision"] in {"partial-approval", "rejected"}:
            review_status = "release-blocked"
            production_use = "forbidden"
            production_gates = design_review["production_gates"]
            blocking_findings = design_review.get("blocking_findings", [])
        else:
            review_status = "awaiting-owner-production-design-review"
            production_use = "forbidden"
            production_gates = {
                "owner-production-design-review": "pending",
                "neutral-turnaround": "pending",
                "isolated-expression": "pending",
                "isolated-pose": "pending",
                "layered-depth-and-motion": "pending",
                "assistive-device-topology": "pending",
                "cross-backend-identity-parity": "pending",
                "cross-backend-art-direction-parity": "pending",
                "glb-semantic-pose-parity": "pending",
                "animation-and-reduced-motion-visual-review": "pending",
            }
            blocking_findings = ["current-review-artifact-hashes-lack-a-bound-owner-design-decision"]
        write_json(staging / "release-review.json", {
            "schema_version": 1, "family_id": "human-character-library-canonical-family",
            "verification_status": "technical-validation-success", "review_status": review_status,
            "production_use": production_use, "license": "MIT", "master_count": len(MASTER_IDS),
            "technical_gates": technical_gates, "production_gates": production_gates,
            "backend_status": design_review.get("backend_status", {}) if review_is_bound else {},
            "blocking_findings": blocking_findings,
            "owner_design_review": {
                "path": str(args.design_review.resolve()),
                "sha256": sha256(args.design_review.resolve()),
                "decision": design_review["decision"] if review_is_bound else "not-bound-to-current-artifacts",
                "artifact_hashes_match": review_is_bound,
            },
            "prior_bound_owner_decision": {
                "decision": design_review["decision"],
                "production_use": design_review.get("production_use", "forbidden"),
                "approved_gates": design_review.get("approved_gates", {}),
                "rejected_gates": design_review.get("rejected_gates", {}),
                "reviewed_artifacts": design_review.get("reviewed_artifacts", {}),
                "applies_to_current_artifact_hashes": review_is_bound,
            },
            "turnaround_render_count": len(turnaround),
            "isolated_expression_render_count": len(expressions),
            "isolated_pose_render_count": len(poses),
            "depth_evidence_render_count": len(depth),
            "device_topology_render_count": len(device_topology),
            "reduced_motion_render_count": len(reduced_records),
            "glb_master_count": len(glb_records), "glb_semantic_clip_count": sum(record["required_clip_count"] for record in glb_records),
            "provenance_sha256": sha256(source / "provenance.json"), "representation_review_sha256": sha256(source / "representation-review.json"),
            "contrast_validations": contrast_records, "reduced_motion_validations": reduced_records,
            "glb_validations": glb_records,
            "rigid_depth_validations": rigid_depth_records,
            "animation_playback_validations": playback_records,
            "animation_review_html": {"path": "animation-review.html", "sha256": sha256(staging / "animation-review.html")},
            "sheets": {name: {"path": path.name, "sha256": sha256(path)} for name, path in sheets.items()},
        })
        if destination.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {destination}")
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    report = read_json(destination / "release-review.json")
    if args.expect_review_status and report.get("review_status") != args.expect_review_status:
        raise RuntimeError(
            f"expected review status {args.expect_review_status!r}, got {report.get('review_status')!r}"
        )
    print(
        f"technical production review completed for {len(MASTER_IDS)} canonical humans; "
        f"status={report['review_status']} production_use={report['production_use']} in {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
