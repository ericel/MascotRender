#!/usr/bin/env python3
"""Regression checks for the authorized Micro Reactions Orbit proofs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def read_glb_document(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    version, total = struct.unpack_from("<II", data, 4)
    assert version == 2
    assert total == len(data)
    json_length, json_kind = struct.unpack_from("<I4s", data, 12)
    assert json_kind == b"JSON"
    return json.loads(data[20 : 20 + json_length].decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--layered-generator", type=Path, required=True)
    parser.add_argument("--glb-generator", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--owner-decision", type=Path, required=True)
    parser.add_argument("--final-owner-decision", type=Path, required=True)
    args = parser.parse_args()

    decision = read_json(args.owner_decision)
    assert decision["authority"] == "project-owner"
    assert decision["decision"] == "approved"
    assert decision["production_use"] == (
        "still-requires-selected-glb-and-final-pack-review"
    )
    assert decision["approved_gates"]["orbit-layered-2_5d-depth"] == "pass"
    assert decision["approved_gates"]["orbit-parallax"] == "pass"
    assert decision["approved_gates"]["orbit-animation-and-loop"] == "pass"
    assert decision["approved_gates"]["orbit-reduced-motion"] == "pass"

    final_decision = read_json(args.final_owner_decision)
    assert final_decision["authority"] == "project-owner"
    assert final_decision["decision"] == "approved"
    assert final_decision["gate"] == "micro-orbit-final-glb-face-parity-v1"
    assert final_decision["identity_id"] == "micro-orbit-004"
    assert final_decision["semantic"] == "proud"
    assert final_decision["production_use"] == (
        "approved-as-selected-styled-glb-proof"
    )
    assert {
        "cross-backend-identity-parity",
        "final-glb-facial-parity",
        "proud-semantic-readability",
        "styled-outline-and-palette",
        "antenna-attachment-continuity",
        "idle-animation",
        "orbital-tilt-animation",
        "proud-animation",
        "loop-closure",
        "reduced-motion-equivalent",
        "small-display-readability",
        "deterministic-generation",
    } == set(final_decision["approved_scope"])

    run(
        [
            str(args.python),
            str(args.glb_generator),
            "--output",
            str(args.glb),
            "--check",
        ]
    )
    document = read_glb_document(args.glb)
    assert document["asset"]["extras"]["mascot"] == "micro-orbit-004"
    assert document["asset"]["extras"]["productionUse"] == (
        "approved-as-selected-styled-glb-proof"
    )
    assert document["asset"]["extras"]["approvalGate"] == (
        "micro-orbit-final-glb-face-parity-v1"
    )
    assert document["asset"]["extras"]["faceParityContract"] == {
        "eyeConstruction": "narrow-horizontal-almond",
        "proudEyelids": "composed",
        "eyebrows": "smooth-arched",
        "smile": "compact-curved",
        "blush": "restrained",
        "antennaAttachment": "continuous-curved",
    }
    assert document["extensionsUsed"] == ["KHR_materials_unlit"]
    assert {animation["name"] for animation in document["animations"]} == {
        "idle",
        "orbital-tilt",
        "proud",
    }
    node_names = {node["name"] for node in document["nodes"]}
    assert {
        "OrbitRoot",
        "Body",
        "OrbitRing",
        "AntennaTip",
        "UpwardBrows",
        "AsymmetricConfidentSmile",
        "AchievementMedal",
        "GroundShadow",
    }.issubset(node_names)

    with tempfile.TemporaryDirectory(prefix="micro-orbit-proof-test-") as directory:
        root = Path(directory)
        source = root / "source"
        review = root / "review"
        run(
            [
                str(args.python),
                str(args.layered_generator),
                "--source-output",
                str(source),
                "--review-output",
                str(review),
                "--mascotrender",
                str(args.cli),
            ]
        )
        result = read_json(review / "review.json")
        assert result["review_status"] == "owner-approved"
        assert result["production_use"] == (
            "forbidden-until-selected-glb-and-final-pack-review"
        )
        assert result["identity_id"] == "micro-orbit-004"
        assert result["layer_count"] == 9
        assert result["parented_layer_count"] >= 6
        assert result["distinct_depth_count"] >= 8
        assert result["parallax_left_right_meaningful_delta"] > 0
        assert result["flat_dimensional_meaningful_delta"] > 0
        assert result["animation"] == {
            "frame_count": 15,
            "animated_webp": True,
            "visible_mid_cycle_change": True,
            "loop_closure": True,
        }
        assert result["artifacts"] == decision["reviewed_artifacts"][
            "orbit_layered_2_5d_gate"
        ]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
