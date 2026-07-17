#!/usr/bin/env python3
"""Regression test the canonical family semantic-vector production handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


MASTER_IDS = ("H01", "H04", "H07", "H12", "H13")
FRAMINGS = ("face-closeup", "bust", "three-quarter", "full-body", "dynamic-full-body")


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--glb-generator", type=Path, required=True)
    parser.add_argument("--reviewer", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--rig-contract", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rig = read_json(args.rig_contract)
    profiles = rig["device_profiles"]
    with tempfile.TemporaryDirectory(prefix="mascotrender-canonical-humans-") as temporary:
        root = Path(temporary)
        first, second = root / "first", root / "second"
        for output in (first, second):
            run([args.python, str(args.generator), "--output", str(output)])
            run([args.python, str(args.glb_generator), "--input", str(output)])
        if tree_hashes(first) != tree_hashes(second):
            raise AssertionError("canonical human master generation is not byte deterministic")
        generation = read_json(first / "generation-manifest.json")
        if generation.get("master_count") != 5 or generation.get("production_use") != "forbidden":
            raise AssertionError("canonical generation manifest has invalid scope")
        poster_count = 0
        for master_id in MASTER_IDS:
            master = first / master_id
            identity = read_json(master / "identity.json")
            pack = read_json(master / "pack.json")
            manifest = read_json(master / "source-manifest.json")
            if manifest.get("layer_count", 0) < 11:
                raise AssertionError(f"{master_id} lacks semantic source layers")
            if manifest.get("turnaround_view_count") != 4 or manifest.get("production_expression_count") != 7 or manifest.get("production_pose_count") != 9:
                raise AssertionError(f"{master_id} production source matrix is incomplete")
            if manifest.get("reduced_motion_presentation_count") != 7 or manifest.get("claimed_backends") != ["flat-2d", "layered-2.5d", "filament-glb"]:
                raise AssertionError(f"{master_id} release capability declaration is incomplete")
            groups = {
                element.attrib["id"]
                for element in ET.parse(master / "master.svg").getroot().iter()
                if element.tag.endswith("g") and "id" in element.attrib
            }
            if not {"torso", "head", "face-friendly", "arm-right-greeting"}.issubset(groups):
                raise AssertionError(f"{master_id} master SVG lacks required semantic groups")
            profile_id = identity["device_profile"]
            bindings = pack["rig"]["device_bindings"]
            if set(bindings) != set(profiles[profile_id]["required_parts"]):
                raise AssertionError(f"{master_id} device bindings drifted from production rig")
            layer_ids = {layer["id"] for layer in pack["layers"]}
            layers_by_id = {layer["id"]: layer for layer in pack["layers"]}
            if not set(bindings.values()).issubset(layer_ids):
                raise AssertionError(f"{master_id} device binding references an absent layer")
            pivots = pack["pivots"]
            if not (
                pivots["shoulder_right"]["x"] < pivots["shoulder_left"]["x"]
                and pivots["hip_right"]["x"] < pivots["hip_left"]["x"]
                and pivots["ear_right"]["x"] < pivots["head"]["x"]
            ):
                raise AssertionError(f"{master_id} violates anatomical front-view left/right convention")
            if master_id == "H07":
                for side in ("left", "right"):
                    for prefix in ("device-wheel", "device-pushrim"):
                        layer = layers_by_id[f"{prefix}-{side}"]
                        if layer.get("parent") != "device-wheelchair-frame" or layer.get("pivot") != f"device_wheel_{side}":
                            raise AssertionError("H07 wheel motion is not centered on its authored wheel pivot")
            if master_id == "H13":
                for position in ("front-left", "front-right", "rear-left", "rear-right"):
                    layer = layers_by_id[f"device-rollator-wheel-{position}"]
                    pivot = f"device_wheel_{position.replace('-', '_')}"
                    if layer.get("parent") != "device-rollator-frame" or layer.get("pivot") != pivot:
                        raise AssertionError("H13 wheel motion is not centered on its authored wheel pivot")
            for framing in FRAMINGS:
                sticker = master / "stickers" / f"{framing}.json"
                run([str(args.cli), "validate", "--pack", str(master / "pack.json"), "--sticker", str(sticker)])
                poster_count += 1
            for expression in ("happy", "laughing", "surprised", "thinking", "confident", "sorry", "excited"):
                for presentation in ("production", "reduced-motion"):
                    run([
                        str(args.cli), "validate", "--pack", str(master / "pack.json"),
                        "--sticker", str(master / "stickers" / presentation / f"{expression}.json"),
                    ])
            run([
                str(args.cli), "validate", "--pack", str(master / "pack-flat.json"),
                "--sticker", str(master / "stickers" / "production" / "happy.json"),
            ])
            run([
                str(args.cli), "validate", "--pack", str(master / "pack.json"),
                "--sticker", str(master / "stickers" / "canonical-scale.json"),
            ])
            motion = master / "stickers" / "device-motion-check.json"
            if master_id == "H01" and motion.exists():
                raise AssertionError("H01 unexpectedly has an assistive-device motion check")
            if master_id != "H01":
                run([str(args.cli), "validate", "--pack", str(master / "pack.json"), "--sticker", str(motion)])
        if poster_count != 25:
            raise AssertionError("canonical family does not provide five framings per master")
        pillow_available = subprocess.run(
            [args.python, "-c", "import PIL"], capture_output=True, check=False
        ).returncode == 0
        if pillow_available:
            review = root / "review"
            run([
                args.python, str(args.reviewer), "--input", str(first), "--output", str(review),
                "--mascotrender", str(args.cli), "--rig-contract", str(args.rig_contract),
            ])
            report = read_json(review / "review.json")
            if report.get("poster_count") != 25 or report.get("review_status") != "owner-vector-parity-approved":
                raise AssertionError("canonical review report has incorrect count or approval state")
            if report.get("production_use") != "forbidden":
                raise AssertionError("canonical review incorrectly enables production use")
            if report.get("semantic_device_part_count") != 19 or report.get("device_motion_count") != 4:
                raise AssertionError("canonical review lacks semantic part or motion proof")
            if report.get("small_size_render_count") != 15 or report.get("authored_lod_master_count") != 4:
                raise AssertionError("canonical review lacks true-size or authored-LOD proof")
            h13_three_quarter = next(
                item for item in report["validations"]
                if item["master_id"] == "H13" and item["framing"] == "three-quarter"
            )
            if h13_three_quarter["alpha_bounds"][1] < 16:
                raise AssertionError("H13 three-quarter framing lacks its preferred top safe margin")
        glb_manifest = read_json(first / "glb-manifest.json")
        if glb_manifest.get("master_count") != 5 or any(record.get("clip_count") != 20 for record in glb_manifest.get("records", [])):
            raise AssertionError("canonical GLB generation is incomplete")
        if read_json(first / "provenance.json").get("license") != "MIT":
            raise AssertionError("canonical family lacks MIT provenance")
        if read_json(first / "representation-review.json").get("decision") != "approved":
            raise AssertionError("canonical family lacks representation disposition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
