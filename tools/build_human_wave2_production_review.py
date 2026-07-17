#!/usr/bin/env python3
"""Build the complete Wave 2 technical, specialist, and owner review package."""

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

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageSequence, ImageStat

from build_human_wave2_review import (
    BACKGROUND,
    CARD,
    INK,
    MASTER_IDS,
    contact_sheet,
    font,
    read_glb_document,
    read_json,
    render_svg,
    render_vector,
    sha256,
    write_json,
)
from generate_canonical_human_masters import EXPRESSIONS, POSES


ROOT = Path(__file__).resolve().parent.parent
APPROVED_REVIEW = ROOT / "generated" / "human-wave2-review"
APPROVAL = ROOT / "contracts" / "human-canonical-expansion-wave2-owner-approval.json"
VIEWS = ("front", "three-quarter", "side", "back")
TURNAROUND_CLIPS = {
    "three-quarter": "turnaround-three-quarter",
    "side": "turnaround-side",
    "back": "turnaround-back",
}
PLAYBACK_LABELS = ("t0", "t25", "t50", "t75", "t100", "reduced")


def verify_owner_approval(review_root: Path) -> dict[str, Any]:
    decision = read_json(APPROVAL)
    if decision.get("decision") != "approved":
        raise ValueError("Wave 2 owner identity approval is absent")
    for name, expected in decision["approved_artifacts"].items():
        path = review_root / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"owner-approved artifact hash mismatch: {name}")
    return decision


def run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())


def render_glb_at(
    preview: Path,
    source: Path,
    output: Path,
    clip: str | None = None,
    time: float = 0.5,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(preview), "--input", str(source), "--output", str(output),
        "--width", "512", "--height", "512", "--span", "4.2", "--center-y", "0.0",
    ]
    if clip:
        command.extend(["--animation", clip, "--time", f"{time:.6f}"])
    run(command)
    # GPU readback can leave undefined RGB values under fully transparent
    # pixels. They are visually irrelevant but would make hash-bound review
    # artifacts differ between otherwise identical runs.
    image = Image.open(output).convert("RGBA")
    transparent = image.getchannel("A").point(lambda alpha: 255 if alpha == 0 else 0)
    image.paste((0, 0, 0, 0), mask=transparent)
    image.save(output, lossless=True)


def frame_sheet(frames: list[Image.Image], labels: list[str], output: Path, title: str) -> None:
    cell = 250
    sheet = Image.new("RGBA", (cell * len(frames), 310), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 14), title, fill=INK, font=font(24))
    for index, (frame, label) in enumerate(zip(frames, labels, strict=True)):
        x = index * cell
        draw.rounded_rectangle((x + 6, 54, x + cell - 6, 304), 18, fill=CARD)
        copy = frame.convert("RGBA")
        copy.thumbnail((230, 220), Image.Resampling.LANCZOS)
        sheet.alpha_composite(copy, (x + (cell - copy.width) // 2, 60))
        draw.text((x + 15, 281), label, fill=INK, font=font(13))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def alpha_bounds(path: Path) -> tuple[int, int, int, int]:
    bounds = Image.open(path).convert("RGBA").getchannel("A").getbbox()
    if bounds is None:
        raise RuntimeError(f"empty render: {path}")
    return bounds


def channels(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


def matching_pixels(path: Path, color: str, tolerance: int = 8) -> int:
    target = channels(color)
    return sum(
        alpha > 180
        and all(abs(actual - expected) <= tolerance for actual, expected in zip((red, green, blue), target))
        for red, green, blue, alpha in Image.open(path).convert("RGBA").getdata()
    )


def composited_delta(left: Path, right: Path) -> float:
    background = Image.new("RGBA", (512, 512), BACKGROUND)
    first = Image.alpha_composite(background, Image.open(left).convert("RGBA")).convert("RGB")
    second = Image.alpha_composite(background, Image.open(right).convert("RGBA")).convert("RGB")
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3.0


def red_tip_bounds(frame: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = frame.convert("RGBA")
    mask = Image.new("L", rgba.size)
    pixels = []
    width, height = rgba.size
    for index, (red, green, blue, alpha) in enumerate(rgba.getdata()):
        y = index // width
        pixels.append(
            255 if y > height * .52 and alpha > 0 and red > 170 and green < 150 and blue < 150 else 0
        )
    mask.putdata(pixels)
    return mask.getbbox()


def encode_animation(
    frames: list[Image.Image],
    output: Path,
    duration_ms: int = 125,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        "WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        lossless=True,
        quality=100,
        method=0,
    )


def render_playback(
    preview: Path,
    glb: Path,
    output_root: Path,
    master_id: str,
    clip: str,
) -> tuple[dict[str, Path], dict[str, Any], list[Image.Image]]:
    frame_paths: list[Path] = []
    frames: list[Image.Image] = []
    for index in range(9):
        path = output_root / master_id / clip / "frames" / f"{index:02d}.webp"
        render_glb_at(preview, glb, path, clip, index / 8)
        frame_paths.append(path)
        frames.append(Image.open(path).convert("RGBA"))
    animated = output_root / master_id / f"{master_id}-{clip}-animated.webp"
    reduced = output_root / master_id / f"{master_id}-{clip}-reduced-motion.webp"
    encode_animation(frames, animated)
    frames[4].save(reduced, "WEBP", lossless=True, quality=100, method=0)
    selected = {
        "t0": frame_paths[0],
        "t25": frame_paths[2],
        "t50": frame_paths[4],
        "t75": frame_paths[6],
        "t100": frame_paths[8],
        "reduced": reduced,
    }
    first_last_delta = composited_delta(frame_paths[0], frame_paths[8])
    midpoint_delta = composited_delta(frame_paths[0], frame_paths[4])
    adjacent = [
        composited_delta(left, right)
        for left, right in zip(frame_paths, frame_paths[1:])
    ]
    with Image.open(animated) as animation, Image.open(reduced) as static:
        animated_frame_count = getattr(animation, "n_frames", 1)
        reduced_frame_count = getattr(static, "n_frames", 1)
    if (
        animated_frame_count < 4
        or reduced_frame_count != 1
        or first_last_delta != 0
        or midpoint_delta < .5
        or b"ANIM" not in animated.read_bytes()
        or b"ANMF" not in animated.read_bytes()
    ):
        raise RuntimeError(
            f"{master_id}/{clip} playback evidence failed: "
            f"encoded_frames={animated_frame_count}, reduced={reduced_frame_count}, "
            f"loop_delta={first_last_delta:.3f}, midpoint_delta={midpoint_delta:.3f}, "
            f"has_anim={b'ANIM' in animated.read_bytes()}, has_anmf={b'ANMF' in animated.read_bytes()}"
        )
    return selected, {
        "master_id": master_id,
        "clip": clip,
        "animated_webp": animated.relative_to(output_root.parent).as_posix(),
        "animated_sha256": sha256(animated),
        "animated_frame_count": animated_frame_count,
        "frame_duration_ms": 125,
        "loop_duration_ms": 1000,
        "first_last_mean_channel_delta": first_last_delta,
        "midpoint_mean_channel_delta": midpoint_delta,
        "maximum_adjacent_frame_delta": max(adjacent),
        "reduced_motion_webp": reduced.relative_to(output_root.parent).as_posix(),
        "reduced_motion_sha256": sha256(reduced),
        "reduced_motion_frame_count": reduced_frame_count,
        "reduced_motion_presentation": "static-semantic-midpoint",
        "technical_status": "pass",
        "visual_playback_status": "awaiting-owner-review",
    }, frames


def html_page(title: str, intro: str, sections: list[tuple[str, str]]) -> str:
    body = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        "<style>body{font:15px system-ui;background:#eef3f8;color:#162b45;margin:24px;max-width:1500px}"
        "section{background:white;padding:18px;border-radius:16px;margin:18px 0}"
        "img{display:block;max-width:100%;margin:12px 0;border-radius:12px}"
        ".anim{width:256px;height:256px;object-fit:contain;background:#f7f9fb}"
        "code{background:#e8eef4;padding:2px 5px;border-radius:5px}</style>",
        f"<h1>{html.escape(title)}</h1><p>{html.escape(intro)}</p>",
    ]
    for heading, content in sections:
        body.append(f"<section><h2>{html.escape(heading)}</h2>{content}</section>")
    return "\n".join(body) + "\n"


def build(args: argparse.Namespace) -> None:
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        approved = verify_owner_approval(args.approved_review.resolve())
        candidates = args.candidates.resolve()
        executable = args.mascotrender.resolve()
        preview = args.glb_preview.resolve()
        if not executable.is_file() or not preview.is_file():
            raise FileNotFoundError("MascotRender and GLB preview executables are required")

        cross_records: dict[tuple[str, str], Path] = {}
        turnaround_records: dict[tuple[str, str], Path] = {}
        pose_records: dict[tuple[str, str], Path] = {}
        expression_records: dict[tuple[str, str], Path] = {}
        playback_records: dict[tuple[str, str], Path] = {}
        validations: list[dict[str, Any]] = []
        playback_validations: list[dict[str, Any]] = []
        h05_vector_frames: list[Image.Image] = []
        h05_vector_tip_bounds: list[tuple[int, int, int, int] | None] = []
        h05_glb_frames: list[Image.Image] = []
        h05_glb_tip_bounds: list[tuple[int, int, int, int] | None] = []

        for master_id in MASTER_IDS:
            root = candidates / master_id
            identity = read_json(root / "identity.json")
            palette = identity["palette"]
            glb = root / f"{master_id}-review.glb"
            document = read_glb_document(glb)
            names = {str(node.get("name", "")) for node in document.get("nodes", [])}
            clips = {str(animation.get("name", "")) for animation in document.get("animations", [])}
            asset_identity = document.get("asset", {}).get("extras", {}).get("characterIdentity", {})
            required_nodes = {
                "CharacterRoot", "Head", "Face", "Hair", "Torso",
                "ArmLeftPivot", "ArmRightPivot", "LegLeft", "LegRight",
            }
            if master_id == "H05":
                required_nodes.update({"WhiteCaneRoot", "WhiteCaneShaft", "WhiteCaneTip"})
            if master_id == "H08":
                required_nodes.update({
                    "HeadCoveringDrape", "HeadCoveringCrown",
                    "HeadCoveringPanelLeft", "HeadCoveringPanelRight",
                })
            expected_clips = {
                *POSES,
                *{f"expression-{value}" for value in EXPRESSIONS},
                "semantic-excited",
                *TURNAROUND_CLIPS.values(),
            }
            if master_id == "H05":
                expected_clips.add("device-white-cane-sweep")
            if (
                asset_identity.get("characterId") != master_id
                or not required_nodes.issubset(names)
                or not expected_clips.issubset(clips)
            ):
                raise RuntimeError(f"{master_id} GLB identity, nodes, or clips are incomplete")

            sticker = root / "stickers" / "full-body.json"
            flat = staging / "cross-backend" / f"{master_id}-flat.webp"
            layered = staging / "cross-backend" / f"{master_id}-layered.webp"
            rest = staging / "cross-backend" / f"{master_id}-glb-rest.webp"
            greeting = staging / "cross-backend" / f"{master_id}-glb-greeting.webp"
            excited = staging / "cross-backend" / f"{master_id}-glb-excited.webp"
            render_vector(executable, root / "pack-flat.json", sticker, flat)
            render_vector(executable, root / "pack.json", sticker, layered)
            render_glb_at(preview, glb, rest)
            render_glb_at(preview, glb, greeting, "greeting")
            render_glb_at(preview, glb, excited, "semantic-excited")
            for label, path in (
                ("flat 2D", flat),
                ("layered 2.5D", layered),
                ("GLB rest", rest),
                ("GLB greeting", greeting),
                ("GLB excited", excited),
            ):
                cross_records[(master_id, label)] = path

            vector_bounds = alpha_bounds(flat)
            glb_bounds = alpha_bounds(rest)
            vector_aspect = (vector_bounds[2] - vector_bounds[0]) / (vector_bounds[3] - vector_bounds[1])
            glb_aspect = (glb_bounds[2] - glb_bounds[0]) / (glb_bounds[3] - glb_bounds[1])
            flat_layered_delta = composited_delta(flat, layered)
            greeting_delta = composited_delta(rest, greeting)
            excited_delta = composited_delta(rest, excited)
            palette_counts = {
                key: matching_pixels(rest, palette[key])
                for key in ("skin", "hair", "primary", "outline")
            }
            if (
                flat_layered_delta > 2.0
                or abs(vector_aspect - glb_aspect) > .65
                or greeting_delta < .30
                or excited_delta < .65
                or min(palette_counts.values()) < 12
            ):
                raise RuntimeError(
                    f"{master_id} cross-backend numeric parity failed: "
                    f"flat_layered={flat_layered_delta:.3f}, "
                    f"aspect_delta={abs(vector_aspect - glb_aspect):.3f}, "
                    f"greeting={greeting_delta:.3f}, excited={excited_delta:.3f}, "
                    f"palette={palette_counts}"
                )

            for view in VIEWS:
                vector_path = staging / "turnarounds" / "vector" / f"{master_id}-{view}.png"
                glb_path = staging / "turnarounds" / "glb" / f"{master_id}-{view}.webp"
                render_svg(root / "turnarounds" / f"{view}.svg", vector_path)
                if view == "front":
                    glb_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(rest, glb_path)
                else:
                    render_glb_at(preview, glb, glb_path, TURNAROUND_CLIPS[view])
                turnaround_records[(master_id, f"2D {view}")] = vector_path
                turnaround_records[(master_id, f"GLB {view}")] = glb_path
                bounds = alpha_bounds(glb_path)
                if bounds[2] - bounds[0] < 34 or bounds[3] - bounds[1] < 135:
                    raise RuntimeError(f"{master_id}/{view} GLB turnaround is implausibly small")

            pose_hashes: set[str] = set()
            for pose in POSES:
                path = staging / "glb-poses" / f"{master_id}-{pose}.webp"
                render_glb_at(preview, glb, path, pose)
                pose_records[(master_id, pose)] = path
                pose_hashes.add(sha256(path))
            expression_hashes: set[str] = set()
            for expression in EXPRESSIONS:
                path = staging / "glb-expressions" / f"{master_id}-{expression}.webp"
                render_glb_at(preview, glb, path, f"expression-{expression}")
                expression_records[(master_id, expression)] = path
                expression_hashes.add(sha256(path))
            if len(pose_hashes) != len(POSES) or len(expression_hashes) != len(EXPRESSIONS):
                raise RuntimeError(f"{master_id} GLB pose/expression clips are not visually distinct")

            selected, playback, _ = render_playback(
                preview, glb, staging / "animation-playback", master_id, "semantic-excited"
            )
            for label, path in selected.items():
                playback_records[(master_id, label)] = path
            playback_validations.append(playback)

            if master_id == "H05":
                vector_animation = staging / "specialist" / "H05" / "H05-vector-cane-motion.webp"
                vector_animation.parent.mkdir(parents=True, exist_ok=True)
                run([
                    str(executable), "render",
                    "--pack", str(root / "pack.json"),
                    "--sticker", str(root / "stickers" / "device-motion-check.json"),
                    "--output", str(vector_animation),
                    "--width", "512", "--height", "512", "--lossless",
                ])
                h05_vector_frames = [
                    frame.convert("RGBA") for frame in ImageSequence.Iterator(Image.open(vector_animation))
                ]
                h05_vector_tip_bounds = [red_tip_bounds(frame) for frame in h05_vector_frames]
                _, h05_playback, h05_glb_frames = render_playback(
                    preview, glb, staging / "specialist", master_id, "device-white-cane-sweep"
                )
                h05_glb_tip_bounds = [red_tip_bounds(frame) for frame in h05_glb_frames]
                h05_playback["red_tip_detected_every_frame"] = all(h05_glb_tip_bounds)
                playback_validations.append(h05_playback)

            validations.append({
                "master_id": master_id,
                "glb_sha256": sha256(glb),
                "animation_count": len(clips),
                "required_node_count": len(required_nodes),
                "required_nodes_present": True,
                "required_clips_present": True,
                "flat_layered_mean_channel_delta": flat_layered_delta,
                "silhouette_aspect_delta": abs(vector_aspect - glb_aspect),
                "semantic_greeting_mean_channel_delta": greeting_delta,
                "semantic_excited_mean_channel_delta": excited_delta,
                "palette_pixel_counts": palette_counts,
                "pose_clip_count": len(pose_hashes),
                "expression_clip_count": len(expression_hashes),
                "turnaround_clip_count": len(TURNAROUND_CLIPS),
                "status": "technical-pass",
            })

        sheets = {
            "cross_backend": staging / "cross-backend-production-candidate.png",
            "turnaround_parity": staging / "turnaround-parity-sheet.png",
            "glb_poses": staging / "glb-nine-pose-sheet.png",
            "glb_expressions": staging / "glb-seven-expression-sheet.png",
            "animation_playback": staging / "animation-playback-sheet.png",
        }
        contact_sheet(
            cross_records,
            MASTER_IDS,
            ("flat 2D", "layered 2.5D", "GLB rest", "GLB greeting", "GLB excited"),
            sheets["cross_backend"],
            "Wave 2 full cross-backend production candidate",
            205,
        )
        turnaround_columns = tuple(
            value for view in VIEWS for value in (f"2D {view}", f"GLB {view}")
        )
        contact_sheet(
            turnaround_records,
            MASTER_IDS,
            turnaround_columns,
            sheets["turnaround_parity"],
            "Wave 2 vector/GLB neutral-turnaround parity",
            170,
        )
        contact_sheet(
            pose_records, MASTER_IDS, POSES, sheets["glb_poses"],
            "Wave 2 GLB nine-pose semantic parity", 160,
        )
        contact_sheet(
            expression_records, MASTER_IDS, EXPRESSIONS, sheets["glb_expressions"],
            "Wave 2 GLB seven-expression semantic parity", 175,
        )
        contact_sheet(
            playback_records, MASTER_IDS, PLAYBACK_LABELS, sheets["animation_playback"],
            "Wave 2 semantic-excited playback and reduced-motion evidence", 185,
        )

        h05_indices = sorted({0, len(h05_vector_frames) // 4, len(h05_vector_frames) // 2, (len(h05_vector_frames) * 3) // 4, len(h05_vector_frames) - 1})
        h05_vector_sheet = staging / "specialist" / "H05" / "H05-vector-cane-motion-sheet.png"
        h05_glb_sheet = staging / "specialist" / "H05" / "H05-glb-cane-motion-sheet.png"
        frame_sheet(
            [h05_vector_frames[index] for index in h05_indices],
            [f"vector frame {index}" for index in h05_indices],
            h05_vector_sheet,
            "H05 orientation white-cane vector motion",
        )
        frame_sheet(
            [h05_glb_frames[index] for index in (0, 2, 4, 6, 8)],
            [f"GLB t{value}" for value in ("0", "25", "50", "75", "100")],
            h05_glb_sheet,
            "H05 orientation white-cane GLB sweep",
        )
        if not all(h05_vector_tip_bounds) or not all(h05_glb_tip_bounds):
            raise RuntimeError("H05 red cane tip is not visible in every vector/GLB review frame")

        h08_frames: list[Image.Image] = []
        h08_labels: list[str] = []
        for view in VIEWS:
            h08_frames.append(Image.open(turnaround_records[("H08", f"2D {view}")]).convert("RGBA"))
            h08_labels.append(f"2D {view}")
            h08_frames.append(Image.open(turnaround_records[("H08", f"GLB {view}")]).convert("RGBA"))
            h08_labels.append(f"GLB {view}")
        h08_sheet = staging / "specialist" / "H08" / "H08-head-covering-parity-sheet.png"
        frame_sheet(h08_frames, h08_labels, h08_sheet, "H08 everyday draped hijab 2D/GLB construction")

        h05_review = {
            "schema_version": 1,
            "gate": "H05-orientation-white-cane-specialist-review",
            "status": "awaiting-qualified-reviewer",
            "reviewer_fields": {
                "name": None,
                "qualification_or_lived_experience": None,
                "review_date": None,
                "decision": None,
                "notes": None,
            },
            "questions": [
                "Is the cane held consistently on the authored side?",
                "Does the grip and wrist relationship remain plausible?",
                "Is the sweep arc useful and free from the body?",
                "Does the tip maintain a believable ground relationship?",
                "Is the timing respectful and functionally legible?",
                "Do vector and GLB versions preserve the same device behavior?",
            ],
            "technical_evidence": {
                "vector_frame_count": len(h05_vector_frames),
                "vector_red_tip_detected_every_frame": all(h05_vector_tip_bounds),
                "glb_frame_count": len(h05_glb_frames),
                "glb_red_tip_detected_every_frame": all(h05_glb_tip_bounds),
                "vector_loop_closure": h05_vector_frames[0].tobytes() == h05_vector_frames[-1].tobytes(),
                "glb_loop_closure": h05_glb_frames[0].tobytes() == h05_glb_frames[-1].tobytes(),
            },
            "artifacts": {
                h05_vector_sheet.name: sha256(h05_vector_sheet),
                h05_glb_sheet.name: sha256(h05_glb_sheet),
                "H05-vector-cane-motion.webp": sha256(staging / "specialist" / "H05" / "H05-vector-cane-motion.webp"),
                "H05-device-white-cane-sweep-animated.webp": sha256(staging / "specialist" / "H05" / "H05-device-white-cane-sweep-animated.webp"),
            },
        }
        write_json(staging / "specialist" / "H05" / "review-form.json", h05_review)

        h08_identity = read_json(candidates / "H08" / "identity.json")
        h08_review = {
            "schema_version": 1,
            "gate": "H08-head-covering-cultural-detail-review",
            "status": "awaiting-culturally-informed-reviewer",
            "authored_construction": h08_identity["head_covering"],
            "reviewer_fields": {
                "name": None,
                "qualification_or_lived_experience": None,
                "review_date": None,
                "decision": None,
                "notes": None,
            },
            "questions": [
                "Does the face opening read naturally without exposing authored covered areas?",
                "Do the crown, side panels, shoulder drape, and rear fold form one plausible garment?",
                "Is coverage consistent across front, three-quarter, side, and back views?",
                "Does the GLB preserve the vector construction without helmet-like drift?",
                "Is the representation respectful and free from caricature?",
            ],
            "artifacts": {h08_sheet.name: sha256(h08_sheet)},
        }
        write_json(staging / "specialist" / "H08" / "review-form.json", h08_review)

        h05_html = html_page(
            "H05 orientation white-cane specialist review",
            "Technical validation has passed. A qualified reviewer must decide functional and representational correctness.",
            [
                ("Vector motion", f"<img src='{h05_vector_sheet.name}'><img class='anim' src='H05-vector-cane-motion.webp'>"),
                ("GLB motion", f"<img src='{h05_glb_sheet.name}'><img class='anim' src='H05-device-white-cane-sweep-animated.webp'>"),
                ("Decision", "<p>Complete <code>review-form.json</code>; automation must not issue this decision.</p>"),
            ],
        )
        (staging / "specialist" / "H05" / "index.html").write_text(h05_html, encoding="utf-8")
        h08_html = html_page(
            "H08 head-covering cultural-detail review",
            "Technical topology and cross-backend evidence have passed. A culturally informed reviewer must decide construction and representation.",
            [
                ("2D and GLB views", f"<img src='{h08_sheet.name}'>"),
                ("Decision", "<p>Complete <code>review-form.json</code>; automation must not issue this decision.</p>"),
            ],
        )
        (staging / "specialist" / "H08" / "index.html").write_text(h08_html, encoding="utf-8")

        animation_sections = []
        for record in playback_validations:
            if record["clip"] != "semantic-excited":
                continue
            animation_sections.append((
                record["master_id"],
                f"<img class='anim' src='{record['animated_webp']}' alt='{record['master_id']} animated'>"
                f"<img class='anim' src='{record['reduced_motion_webp']}' alt='{record['master_id']} reduced motion'>",
            ))
        (staging / "animation-review.html").write_text(
            html_page(
                "Wave 2 native animation and reduced-motion review",
                "Each left image is a real nine-frame looping WebP. Each right image is its one-frame reduced-motion semantic midpoint.",
                animation_sections,
            ),
            encoding="utf-8",
        )

        artifact_paths = {
            **sheets,
            "H05_vector_cane_sheet": h05_vector_sheet,
            "H05_glb_cane_sheet": h05_glb_sheet,
            "H08_head_covering_sheet": h08_sheet,
            "animation_review": staging / "animation-review.html",
            "H05_specialist_review": staging / "specialist" / "H05" / "index.html",
            "H08_specialist_review": staging / "specialist" / "H08" / "index.html",
        }
        technical_gates = {
            "owner-vector-identity-approval-bound": "pass",
            "deterministic-glb-generation": "pass",
            "required-glb-hierarchy-and-semantic-nodes": "pass",
            "vector-glb-neutral-turnarounds": "pass",
            "nine-glb-semantic-poses-distinct": "pass",
            "seven-glb-expressions-distinct": "pass",
            "cross-backend-palette-and-silhouette-thresholds": "pass",
            "semantic-animation-loop-and-visible-motion": "pass",
            "reduced-motion-static-equivalent": "pass",
            "H05-vector-and-glb-cane-tip-presence": "pass",
            "H08-vector-and-glb-head-covering-topology": "pass",
            "small-display-occupancy-owner-approval": "pass",
        }
        report = {
            "schema_version": 2,
            "expansion_id": "human-canonical-expansion-wave2",
            "verification_status": "technical-validation-success",
            "review_status": "awaiting-specialist-and-owner-production-review",
            "production_use": "forbidden-until-all-production-gates",
            "owner_vector_identity_approval": {
                "decision": approved["decision"],
                "decision_date": approved["decision_date"],
                "contract_sha256": sha256(APPROVAL),
            },
            "small_display_approval": {
                "decision": "approved",
                "path": "contracts/human-small-display-occupancy-owner-approval-v1.json",
                "sha256": sha256(ROOT / "contracts" / "human-small-display-occupancy-owner-approval-v1.json"),
            },
            "technical_gates": technical_gates,
            "glb_validations": validations,
            "animation_playback_validations": playback_validations,
            "specialist_review_status": {
                "H05-orientation-white-cane": "awaiting-qualified-reviewer",
                "H08-head-covering-cultural-detail": "awaiting-culturally-informed-reviewer",
            },
            "owner_review_status": {
                "wave2-turnaround-approval": "pending",
                "production-GLB-identity-and-art-direction-parity": "pending",
                "final-animation-playback-review": "pending",
                "owner-production-approval": "pending",
            },
            "public_release_activation": "forbidden",
            "artifacts": {
                name: {"path": path.relative_to(staging).as_posix(), "sha256": sha256(path)}
                for name, path in artifact_paths.items()
            },
        }
        write_json(staging / "review.json", report)

        owner_template = {
            "schema_version": 1,
            "authority": "project-owner",
            "decision": None,
            "decision_date": None,
            "production_use": "forbidden-until-decision-and-specialist-gates",
            "required_specialist_decisions": {
                "H05-orientation-white-cane": "pending",
                "H08-head-covering-cultural-detail": "pending",
            },
            "reviewed_artifacts": {
                path.relative_to(staging).as_posix(): sha256(path)
                for path in sheets.values()
            },
            "production_gates": {
                "wave2-neutral-turnarounds": "pending-owner-decision",
                "cross-backend-identity-parity": "pending-owner-decision",
                "cross-backend-art-direction-parity": "pending-owner-decision",
                "glb-semantic-pose-and-expression-parity": "pending-owner-decision",
                "animation-and-reduced-motion-visual-quality": "pending-owner-decision",
            },
        }
        write_json(staging / "owner-decision-template.json", owner_template)

        review_sections = [
            ("Cross-backend parity", f"<img src='{sheets['cross_backend'].name}'>"),
            ("Neutral turnaround parity", f"<img src='{sheets['turnaround_parity'].name}'>"),
            ("Nine GLB poses", f"<img src='{sheets['glb_poses'].name}'>"),
            ("Seven GLB expressions", f"<img src='{sheets['glb_expressions'].name}'>"),
            ("Animation playback", f"<img src='{sheets['animation_playback'].name}'><p><a href='animation-review.html'>Open live animation review</a></p>"),
            ("Specialist gates", "<p><a href='specialist/H05/index.html'>H05 white-cane review</a></p><p><a href='specialist/H08/index.html'>H08 head-covering review</a></p>"),
        ]
        (staging / "index.html").write_text(
            html_page(
                "Human Expansion Wave 2 — final production candidate",
                "All automated technical gates pass. Specialist and project-owner visual decisions remain intentionally pending.",
                review_sections,
            ),
            encoding="utf-8",
        )

        if destination.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {destination}")
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"built Wave 2 final production review at {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--approved-review", type=Path, default=APPROVED_REVIEW)
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "human-wave2-final-production-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--glb-preview", type=Path, default=ROOT / "build" / "Release" / "mascotrender-glb-preview")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
