#!/usr/bin/env python3
"""Regression checks for the ten-character Human Expansion Wave 2 gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path


EXPECTED_IDS = {"H02", "H03", "H05", "H06", "H08", "H09", "H10", "H11", "H14", "H15"}
EXPECTED_POSES = {
    "rest", "greeting", "farewell", "agreement", "disagreement",
    "gratitude", "concern", "surprise", "celebration",
}
EXPECTED_EXPRESSIONS = {
    "expression-happy", "expression-laughing", "expression-surprised",
    "expression-thinking", "expression-confident", "expression-sorry",
    "expression-excited",
}
EXPECTED_TURNAROUNDS = {
    "turnaround-three-quarter", "turnaround-side", "turnaround-back",
}
EXPECTED_ART_DIRECTION_HASHES = {
    "rest-matched-parity.png": "70e8dbf63083dd04a83e10d87cfda33434c36f41a6b229cba02fc380207dcb9f",
    "greeting-matched-parity.png": "7427cae0e2b68134e145dd821404fee439139ed7b3e0660d9b3254bdca40cb19",
    "excited-matched-parity.png": "a5f921e3e6237662a5e73ffc98a305133eda666cadf7b4c06cca507086d4d0a2",
    "cross-backend-art-direction-correction.png": "a0178f1bddafe09fc50e745964660cccd34023a9ada130e6e0f61617a6631d75",
}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, text=True, capture_output=True)


def tree_hash(root: Path, suffixes: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in suffixes):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_glb_json(path: Path) -> dict:
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"glTF":
        raise AssertionError(f"invalid GLB header: {path}")
    _, version, total_length = struct.unpack_from("<4sII", payload)
    if version != 2 or total_length != len(payload):
        raise AssertionError(f"invalid GLB envelope: {path}")
    chunk_length, chunk_type = struct.unpack_from("<II", payload, 12)
    if chunk_type != 0x4E4F534A:
        raise AssertionError(f"GLB JSON chunk is missing: {path}")
    return json.loads(payload[20:20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\0"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--glb-generator", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--owner-approval", type=Path, required=True)
    parser.add_argument("--art-direction-approval", type=Path, required=True)
    parser.add_argument("--production-activation", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--phrase-eligibility", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    members = contract["planned_members"]
    if {member["id"] for member in members} != EXPECTED_IDS:
        raise AssertionError("Wave 2 contract must contain exactly the ten approved candidate IDs")
    if contract["production_use"] != "forbidden-until-all-production-gates":
        raise AssertionError("Wave 2 must remain blocked before owner and specialist gates")
    if len({member["identity_direction"] for member in members}) != 10:
        raise AssertionError("Wave 2 identities must be authored independently")

    approval = read_json(args.owner_approval)
    if approval["decision"] != "approved" or set(approval["approved_members"]) != EXPECTED_IDS:
        raise AssertionError("owner approval must bind all ten Wave 2 vector identities")
    if approval["minor_identity_owner_approval"] != {"H02": "approved", "H03": "approved"}:
        raise AssertionError("H02 and H03 require explicit owner approval")
    if approval["production_use"] != "forbidden-until-all-production-gates":
        raise AssertionError("vector approval must not activate production release")

    art_approval = read_json(args.art_direction_approval)
    if (
        art_approval["authority"] != "project-owner"
        or art_approval["decision"] != "approved"
        or art_approval["gate"] != "cross-backend-art-direction-parity"
        or art_approval["reviewed_artifacts"] != EXPECTED_ART_DIRECTION_HASHES
    ):
        raise AssertionError("cross-backend art-direction approval is not bound to the reviewed artifacts")

    activation = read_json(args.production_activation)
    if (
        activation["authority"] != "project-owner"
        or activation["decision"] != "approved-for-production-release"
        or activation["production_use"] != "public-release"
        or activation["public_release_activation"] != "approved"
        or set(activation["approved_members"]) != EXPECTED_IDS
    ):
        raise AssertionError("Wave 2 production activation is incomplete")
    specialist = activation["specialist_gate_disposition"]
    if specialist["specialist_approval_claimed"] or {
        specialist["H05-orientation-white-cane-specialist-review"],
        specialist["H08-head-covering-cultural-detail-review"],
    } != {"non-blocking-post-release-advisory"}:
        raise AssertionError("specialist follow-up must remain disclosed without claiming specialist approval")

    selector = read_json(args.selector)
    identities = selector["identities"]
    if len(identities) != 15 or {item["character_id"] for item in identities} != EXPECTED_IDS | {"H01", "H04", "H07", "H12", "H13"}:
        raise AssertionError("selector must enumerate the full 15-character library")
    if {item["selection_weight"] for item in identities} != {1}:
        raise AssertionError("production-eligible identities must rotate uniformly")
    if not all(item["production_eligible"] for item in identities):
        raise AssertionError("all 15 owner-approved identities must participate in production rotation")
    if not all(item["development_eligible"] for item in identities):
        raise AssertionError("all 15 identities must participate in the local development rotation")
    policy = selector["policy"]
    if policy["demographic_inference"] or policy["user-race-or-ethnicity-targeting"] or policy["appearance-metadata-visible-to-selector"]:
        raise AssertionError("balanced rotation must not infer or target demographic identity")

    eligibility = read_json(args.phrase_eligibility)
    phrase_rules = eligibility["phrases"]
    expected_life_stages = {"pre-teen", "teen", "young-adult", "adult", "middle-aged", "senior"}
    if len(phrase_rules) != 41 or len({item["phrase_id"] for item in phrase_rules}) != 41:
        raise AssertionError("the chat matrix must classify exactly 41 unique phrases")
    if any(item["audience_class"] != "general" for item in phrase_rules):
        raise AssertionError("the current owner-reviewed phrase set is expected to be general audience")
    if any(set(item["allowed_life_stages"]) != expected_life_stages for item in phrase_rules):
        raise AssertionError("every current general phrase must explicitly allow every authored life stage")
    if not eligibility["policy"]["authored_compatibility_not_engine_inference"]:
        raise AssertionError("phrase eligibility must remain authored data")

    with tempfile.TemporaryDirectory(prefix="mascotrender-human-wave2-") as temporary:
        output = Path(temporary) / "candidates"
        command = [args.python, str(args.generator), "--output", str(output), "--force"]
        run(command)
        first = tree_hash(output, (".json", ".svg"))
        run(command)
        second = tree_hash(output, (".json", ".svg"))
        if first != second:
            raise AssertionError("Wave 2 vector generation is not byte deterministic")

        for master_id in EXPECTED_IDS:
            root = output / master_id
            identity = read_json(root / "identity.json")
            if identity["status"] != "public-release-approved":
                raise AssertionError(f"candidate status drifted: {master_id}")
            if identity["production_use"] != "public-release":
                raise AssertionError(f"candidate was accidentally production-blocked: {master_id}")
            if not (root / "master.svg").is_file() or not (root / "pack.json").is_file():
                raise AssertionError(f"candidate is missing editable vector/pack assets: {master_id}")
            if len(list((root / "stickers" / "expressions").glob("*.json"))) != 7:
                raise AssertionError(f"candidate expression matrix is incomplete: {master_id}")
            if len(list((root / "stickers" / "poses").glob("*.json"))) != 9:
                raise AssertionError(f"candidate pose matrix is incomplete: {master_id}")

        h05_scene = (output / "H05" / "pack.json").read_text(encoding="utf-8")
        for semantic_part in ("device-white-cane-grip", "device-white-cane-shaft", "device-white-cane-tip"):
            if semantic_part not in h05_scene:
                raise AssertionError(f"H05 is missing semantic cane part: {semantic_part}")
        h05_motion = read_json(output / "H05" / "stickers" / "device-motion-check.json")
        cane_angles = [
            frame["value"]
            for track in h05_motion["animation"]["tracks"]
            if track["target"] == "device-white-cane-grip"
            for frame in track["keyframes"]
        ]
        if not cane_angles or max(cane_angles) >= 0 or min(cane_angles) > -25:
            raise AssertionError("H05 vector cane sweep must remain visible outside the leg silhouette")

        run([args.python, str(args.glb_generator), "--input", str(output)])
        first_glb = tree_hash(output, (".glb",))
        run([args.python, str(args.glb_generator), "--input", str(output), "--check"])
        second_glb = tree_hash(output, (".glb",))
        if first_glb != second_glb:
            raise AssertionError("Wave 2 semantic GLB review generation is not deterministic")

        for master_id in EXPECTED_IDS:
            document = read_glb_json(output / master_id / f"{master_id}-review.glb")
            clips = {item.get("name") for item in document.get("animations", [])}
            required_clips = (
                EXPECTED_POSES
                | EXPECTED_EXPRESSIONS
                | EXPECTED_TURNAROUNDS
                | {"semantic-excited"}
            )
            if master_id == "H05":
                required_clips.add("device-white-cane-sweep")
            if not required_clips.issubset(clips):
                raise AssertionError(f"Wave 2 GLB clips are incomplete: {master_id}")

            node_names = {item.get("name") for item in document.get("nodes", [])}
            if not {
                "HeadInkOutline", "TorsoInkOutline", "EyeOutlines",
                "ArmLeftInkOutline", "ArmRightInkOutline",
                "LegLeftInkOutline", "FootLeftInkOutline",
            }.issubset(node_names):
                raise AssertionError(f"Wave 2 GLB style hierarchy is incomplete: {master_id}")
            if master_id == "H05" and not {
                "WhiteCaneRoot", "WhiteCaneShaft", "WhiteCaneTip",
            }.issubset(node_names):
                raise AssertionError("H05 GLB cane hierarchy is incomplete")
            if master_id == "H08" and not {
                "HeadCoveringDrape", "HeadCoveringCrown",
                "HeadCoveringPanelLeft", "HeadCoveringPanelRight",
            }.issubset(node_names):
                raise AssertionError("H08 GLB head-covering topology is incomplete")

    print("Human Expansion Wave 2 contract and deterministic candidate pipeline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
