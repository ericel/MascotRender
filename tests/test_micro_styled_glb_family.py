#!/usr/bin/env python3
"""Regression checks for the Micro Reactions styled GLB family expansion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--glb-root", type=Path, required=True)
    parser.add_argument("--orbit-owner-approval", type=Path, required=True)
    parser.add_argument("--family-owner-approval", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    assert contract["schema_version"] == 1
    assert contract["reference_identity"] == "micro-orbit-004"
    specs = contract["identities"]
    assert len(specs) == 5
    assert {spec["identity_id"] for spec in specs} == {
        "micro-sprig-001",
        "micro-cinder-002",
        "micro-ripple-003",
        "micro-crumb-005",
        "micro-mallow-006",
    }
    assert len({spec["signature_node"] for spec in specs}) == 5
    assert len({spec["signature_clip"] for spec in specs}) == 5

    orbit_approval = read_json(args.orbit_owner_approval)
    assert orbit_approval["decision"] == "approved"
    assert orbit_approval["gate"] == "micro-orbit-final-glb-face-parity-v1"
    assert orbit_approval["production_use"] == (
        "approved-as-selected-styled-glb-proof"
    )
    family_approval = read_json(args.family_owner_approval)
    assert family_approval["authority"] == "project-owner"
    assert family_approval["decision"] == "approved"
    assert family_approval["gate"] == (
        "micro-reactions-styled-glb-family-expansion-v1"
    )
    assert family_approval["production_use"] == (
        "approved-for-styled-glb-family-expansion"
    )
    assert family_approval["remaining_gate"] == (
        "final-micro-reactions-pack-activation"
    )

    subprocess.run(
        [
            str(args.python),
            str(args.generator),
            "--contract",
            str(args.contract),
            "--output-root",
            str(args.glb_root),
            "--check",
        ],
        check=True,
    )

    for spec in specs:
        identity_id = spec["identity_id"]
        glb = args.glb_root / f"{identity_id}.glb"
        document = read_glb_document(glb)
        assert sha256(glb) == family_approval["approved_glbs"][identity_id]
        extras = document["asset"]["extras"]
        assert extras["mascot"] == identity_id
        assert extras["referenceIdentity"] == "micro-orbit-004"
        assert extras["referenceApprovalGate"] == (
            "micro-orbit-final-glb-face-parity-v1"
        )
        assert extras["productionUse"] == (
            "forbidden-until-family-styled-glb-review"
        )
        assert extras["palette"] == spec["palette"]
        assert document["extensionsUsed"] == ["KHR_materials_unlit"]
        assert {animation["name"] for animation in document["animations"]} == {
            "idle",
            spec["signature_clip"],
            "proud",
        }
        node_names = {node["name"] for node in document["nodes"]}
        assert {
            "MascotRoot",
            "Body",
            "Face",
            "ProudEyeShapes",
            "CompactProudSmile",
            spec["signature_node"],
            "AchievementMedal",
            "GroundShadow",
        }.issubset(node_names)
        signature_node = next(
            node for node in document["nodes"] if node["name"] == spec["signature_node"]
        )
        assert signature_node["extras"]["identitySpecific"] is True
        assert signature_node["extras"]["secondaryMotionClip"] == (
            spec["signature_clip"]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
