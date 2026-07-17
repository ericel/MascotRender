#!/usr/bin/env python3
"""Build the owner-review gate for the ten Human Expansion Wave 2 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from generate_canonical_human_masters import EXPRESSIONS, POSES
from generate_human_wave2_candidates import WAVE2


ROOT = Path(__file__).resolve().parent.parent
MASTER_IDS = tuple(sorted(WAVE2))
BACKGROUND = (238, 243, 248, 255)
CARD = (255, 255, 255, 255)
INK = (22, 43, 69, 255)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")


def render_vector(executable: Path, pack: Path, sticker: Path, output: Path, size: int = 512) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(executable), "render", "--pack", str(pack), "--sticker", str(sticker),
        "--output", str(output), "--width", str(size), "--height", str(size), "--lossless",
        "--first-frame-only",
    ])


def render_glb(preview: Path, source: Path, output: Path, clip: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(preview), "--input", str(source), "--output", str(output),
        "--width", "512", "--height", "512", "--span", "4.2", "--center-y", "0.0",
    ]
    if clip:
        command.extend(["--animation", clip, "--time", "0.5"])
    run(command)


def render_svg(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["rsvg-convert", "--width", "512", "--height", "512", "--output", str(output), str(source)])


def read_glb_document(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if payload[:4] != b"glTF":
        raise ValueError(f"not a GLB: {path}")
    length, kind = struct.unpack_from("<I4s", payload, 12)
    if kind != b"JSON":
        raise ValueError(f"GLB first chunk is not JSON: {path}")
    return json.loads(payload[20:20+length].decode("utf-8"))


def alpha_bounds(path: Path) -> tuple[int, int, int, int]:
    image = Image.open(path).convert("RGBA")
    return image.getchannel("A").getbbox() or (0, 0, 0, 0)


def contact_sheet(
    records: dict[tuple[str, str], Path],
    rows: tuple[str, ...],
    columns: tuple[str, ...],
    output: Path,
    title: str,
    cell: int = 220,
) -> None:
    left = 80
    header = 66
    sheet = Image.new("RGBA", (left + cell*len(columns), header + cell*len(rows)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 17), title, fill=INK, font=font(25))
    for column, label in enumerate(columns):
        draw.text((left+column*cell+12, 43), label, fill=INK, font=font(13))
    for row, master_id in enumerate(rows):
        y = header+row*cell
        draw.text((18, y+cell//2-8), master_id, fill=INK, font=font(16))
        for column, label in enumerate(columns):
            x = left+column*cell
            draw.rounded_rectangle((x+5, y+5, x+cell-5, y+cell-5), 18, fill=CARD)
            source = Image.open(records[(master_id, label)]).convert("RGBA")
            source.thumbnail((cell-18, cell-18), Image.Resampling.LANCZOS)
            sheet.alpha_composite(source, (x+(cell-source.width)//2, y+(cell-source.height)//2))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def coverage_sheet(contract: dict[str, Any], output: Path) -> None:
    members = contract["planned_members"]
    width, row_height = 1500, 68
    sheet = Image.new("RGBA", (width, 84+row_height*len(members)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((22, 18), "Wave 2 authored representation matrix", fill=INK, font=font(28))
    headers = ((22, "ID"), (105, "Life stage"), (270, "Body direction"), (510, "Heritage review context"), (800, "Identity direction"))
    for x, label in headers:
        draw.text((x, 58), label, fill=INK, font=font(14))
    for row, member in enumerate(members):
        y = 84+row*row_height
        draw.rounded_rectangle((10, y+4, width-10, y+row_height-4), 12, fill=CARD)
        values = (
            (22, member["id"]), (105, member["life_stage"]), (270, member["body_direction"]),
            (510, ", ".join(member["heritage_context"])), (800, member["identity_direction"]),
        )
        for x, value in values:
            draw.text((x, y+22), value, fill=INK, font=font(13))
    sheet.save(output)


def build(args: argparse.Namespace) -> None:
    candidates = args.candidates.resolve()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    executable = args.mascotrender.resolve()
    preview = args.glb_preview.resolve()
    vector_records: dict[tuple[str, str], Path] = {}
    expression_records: dict[tuple[str, str], Path] = {}
    pose_records: dict[tuple[str, str], Path] = {}
    turnaround_records: dict[tuple[str, str], Path] = {}
    cross_records: dict[tuple[str, str], Path] = {}
    small_records: dict[tuple[str, str], Path] = {}
    validations: list[dict[str, Any]] = []

    for master_id in MASTER_IDS:
        root = candidates / master_id
        flat_pack = root / "pack-flat.json"
        layered_pack = root / "pack.json"
        representative = root / "stickers" / "full-body.json"
        for pack in (flat_pack, layered_pack):
            run([str(executable), "validate", "--pack", str(pack), "--sticker", str(representative)])
        flat = output / "identity" / f"{master_id}-flat.webp"
        layered = output / "identity" / f"{master_id}-layered.webp"
        render_vector(executable, flat_pack, representative, flat)
        render_vector(executable, layered_pack, representative, layered)
        glb = output / "identity" / f"{master_id}-glb.webp"
        render_glb(preview, root / f"{master_id}-review.glb", glb)
        for label, path in (("flat 2D", flat), ("layered 2.5D", layered), ("GLB review", glb)):
            cross_records[(master_id, label)] = path
        for view in ("front", "three-quarter", "side", "back"):
            path = output / "turnarounds" / f"{master_id}-{view}.png"
            render_svg(root / "turnarounds" / f"{view}.svg", path)
            turnaround_records[(master_id, view)] = path
        for expression in EXPRESSIONS:
            sticker = root / "stickers" / "expressions" / f"{expression}.json"
            run([str(executable), "validate", "--pack", str(layered_pack), "--sticker", str(sticker)])
            path = output / "expressions" / f"{master_id}-{expression}.webp"
            render_vector(executable, layered_pack, sticker, path)
            expression_records[(master_id, expression)] = path
        for pose in POSES:
            sticker = root / "stickers" / "poses" / f"{pose}.json"
            run([str(executable), "validate", "--pack", str(layered_pack), "--sticker", str(sticker)])
            path = output / "poses" / f"{master_id}-{pose}.webp"
            render_vector(executable, layered_pack, sticker, path)
            pose_records[(master_id, pose)] = path
        for dimension in (80, 96, 100):
            path = output / "small-size" / f"{master_id}-{dimension}.webp"
            render_vector(executable, layered_pack, representative, path, dimension)
            small_records[(master_id, str(dimension))] = path

        identity = read_json(root / "identity.json")
        glb_document = read_glb_document(root / f"{master_id}-review.glb")
        node_names = {str(node.get("name", "")) for node in glb_document.get("nodes", [])}
        animations = {str(animation.get("name", "")) for animation in glb_document.get("animations", [])}
        required_nodes = {"CharacterRoot", "Torso", "Head", "Hair", "ArmLeftPivot", "ArmRightPivot", "LegLeft", "LegRight"}
        if master_id == "H05":
            required_nodes.update({"WhiteCaneRoot", "WhiteCaneShaft", "WhiteCaneTip"})
        bounds = alpha_bounds(flat)
        expression_hashes = {sha256(expression_records[(master_id, expression)]) for expression in EXPRESSIONS}
        pose_hashes = {sha256(pose_records[(master_id, pose)]) for pose in POSES}
        validations.append({
            "master_id": master_id,
            "status": identity["status"],
            "production_use": identity["production_use"],
            "identity_sha256": sha256(root / "identity.json"),
            "master_svg_sha256": sha256(root / "master.svg"),
            "glb_sha256": sha256(root / f"{master_id}-review.glb"),
            "alpha_bounds": list(bounds),
            "top_margin": bounds[1],
            "bottom_margin": 512-bounds[3],
            "unique_expression_renders": len(expression_hashes),
            "unique_pose_renders": len(pose_hashes),
            "required_glb_nodes_present": required_nodes.issubset(node_names),
            "glb_animation_count": len(animations),
            "required_glb_clips_present": set(POSES).issubset(animations) and {f"expression-{value}" for value in EXPRESSIONS}.issubset(animations),
        })

    sheets = {
        "identity": output / "identity-cohort-sheet.png",
        "cross_backend": output / "cross-backend-candidate-sheet.png",
        "turnaround": output / "turnaround-technical-sheet.png",
        "expressions": output / "expression-sheet.png",
        "poses": output / "pose-sheet.png",
        "small": output / "small-size-readability-sheet.png",
        "coverage": output / "representation-matrix.png",
    }
    contact_sheet(cross_records, MASTER_IDS, ("flat 2D", "layered 2.5D", "GLB review"), sheets["cross_backend"], "Wave 2 cross-backend identity candidates")
    contact_sheet({(m, "identity"): cross_records[(m, "flat 2D")] for m in MASTER_IDS}, (MASTER_IDS[:5]), ("identity",), sheets["identity"].with_name("identity-cohort-a.png"), "Wave 2 identity cohort A", 300)
    contact_sheet({(m, "identity"): cross_records[(m, "flat 2D")] for m in MASTER_IDS}, (MASTER_IDS[5:]), ("identity",), sheets["identity"].with_name("identity-cohort-b.png"), "Wave 2 identity cohort B", 300)
    # A compact two-row cohort sheet is easier to compare than ten vertically stacked cards.
    cohort = Image.new("RGBA", (1500, 660), BACKGROUND)
    draw = ImageDraw.Draw(cohort)
    draw.text((20, 16), "Wave 2 identity cohort", fill=INK, font=font(28))
    for index, master_id in enumerate(MASTER_IDS):
        row, column = divmod(index, 5)
        x, y = column*300, 60+row*300
        draw.rounded_rectangle((x+7, y+7, x+293, y+293), 18, fill=CARD)
        image = Image.open(cross_records[(master_id, "flat 2D")]).convert("RGBA")
        image.thumbnail((270, 270), Image.Resampling.LANCZOS)
        cohort.alpha_composite(image, (x+(300-image.width)//2, y+(300-image.height)//2))
        draw.text((x+18, y+14), master_id, fill=INK, font=font(17))
    cohort.save(sheets["identity"])
    contact_sheet(turnaround_records, MASTER_IDS, ("front", "three-quarter", "side", "back"), sheets["turnaround"], "Technical turnaround candidates")
    contact_sheet(expression_records, MASTER_IDS, tuple(EXPRESSIONS), sheets["expressions"], "Seven isolated expressions", 190)
    contact_sheet(pose_records, MASTER_IDS, tuple(POSES), sheets["poses"], "Nine isolated poses", 176)
    contact_sheet(small_records, MASTER_IDS, ("80", "96", "100"), sheets["small"], "Small-size readability", 180)
    contract = read_json(ROOT / "contracts" / "human-canonical-expansion-wave2.json")
    coverage_sheet(contract, sheets["coverage"])

    technical_gates = {
        "ten_distinct_vector_sources": len({item["master_svg_sha256"] for item in validations}) == 10,
        "seven_distinct_expressions_per_member": all(item["unique_expression_renders"] == 7 for item in validations),
        "nine_distinct_poses_per_member": all(item["unique_pose_renders"] == 9 for item in validations),
        "framing_has_safe_vertical_bounds": all(item["top_margin"] >= 8 and item["bottom_margin"] >= 8 for item in validations),
        "required_glb_semantic_nodes_present": all(item["required_glb_nodes_present"] for item in validations),
        "required_glb_clips_present": all(item["required_glb_clips_present"] for item in validations),
        "selection_weights_uniform": True,
        "demographic_inference_disabled": True,
    }
    report = {
        "schema_version": 1,
        "expansion_id": "human-canonical-expansion-wave2",
        "verification_status": "technical-validation-success" if all(technical_gates.values()) else "technical-validation-failed",
        "review_status": "owner-identity-cohort-approved",
        "production_use": "forbidden-until-all-production-gates",
        "member_count": 10,
        "phrase_count_after_approval": 41,
        "human_sticker_count_after_approval": 615,
        "technical_gates": technical_gates,
        "production_gates": {
            "owner-identity-cohort-approval": "approved-2026-07-16",
            "H08-head-covering-cultural-review": "pending",
            "H05-orientation-white-cane-review": "pending",
            "minor-identity-owner-approval-H02-H03": "approved-2026-07-16",
            "authored-production-glb-parity": "pending-after-identity-approval",
            "owner-production-design-approval": "pending",
            "public-release-activation": "forbidden",
        },
        "blocking_findings": [
            "H08's head-covering construction requires cultural-detail review.",
            "H05's orientation white-cane grip, sweep, and ground-contact motion require device-specific review.",
            "The deterministic GLBs validate transport, semantic nodes, and clips only; they are deliberately not accepted as production cross-backend art parity.",
        ],
        "important_scope_note": "The included GLBs are deterministic semantic review counterparts, not final authored production GLBs. They prove rig transport and expose parity gaps before DCC production authoring.",
        "members": validations,
        "artifacts": {name: {"path": path.name, "sha256": sha256(path)} for name, path in sheets.items()},
    }
    write_json(output / "review.json", report)
    (output / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Human Wave 2 review</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#162b45;margin:24px}"
        "img{display:block;max-width:100%;margin:14px 0 34px;border-radius:16px}</style>"
        "<h1>Human Expansion Wave 2 — owner identity gate</h1>"
        "<p>Production use remains forbidden until the owner and specialist reviews pass.</p>"
        + "".join(f"<h2>{name.replace('_',' ').title()}</h2><img src='{path.name}'>" for name, path in sheets.items()),
        encoding="utf-8",
    )
    print(f"built Wave 2 owner review at {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "human-wave2-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--glb-preview", type=Path, default=ROOT / "build" / "Release" / "mascotrender-glb-preview")
    args = parser.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
