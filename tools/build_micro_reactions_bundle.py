#!/usr/bin/env python3
"""Build the owner-approved Micro Reactions production bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = "mascotrender-bundle-v1"
MATCHING = "casefolded full phrase with Unicode word boundaries"
IDENTITY_IDS = (
    "micro-sprig-001",
    "micro-cinder-002",
    "micro-ripple-003",
    "micro-orbit-004",
    "micro-crumb-005",
    "micro-mallow-006",
)
ORBIT_ID = "micro-orbit-004"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> bytes:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def asset(
    path: Path,
    relative: Path,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {
        "width": width,
        "height": height,
        "path": relative.as_posix(),
        "sha256": sha256_file(path),
        "encoded_bytes": path.stat().st_size,
    }


def replace_directory(staging: Path, output: Path, force: bool) -> None:
    if output.exists() and not force:
        raise FileExistsError(f"output exists (use --force): {output}")
    backup = output.with_name(output.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        staging.rename(output)
    except Exception:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def parse_glb(path: Path) -> tuple[list[str], int]:
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"glTF":
        raise ValueError(f"invalid GLB header: {path}")
    version, declared_size = struct.unpack_from("<II", payload, 4)
    if version != 2 or declared_size != len(payload):
        raise ValueError(f"invalid GLB v2 envelope: {path}")
    json_size, chunk_type = struct.unpack_from("<II", payload, 12)
    if chunk_type != 0x4E4F534A:
        raise ValueError(f"first GLB chunk is not JSON: {path}")
    document = json.loads(payload[20 : 20 + json_size].rstrip(b" \0"))
    animations = document.get("animations", [])
    nodes = document.get("nodes", [])
    clips = [str(value.get("name", "")) for value in animations]
    if not clips or any(not clip for clip in clips):
        raise ValueError(f"GLB must contain named animation clips: {path}")
    semantic_nodes = [
        value
        for value in nodes
        if isinstance(value, dict)
        and isinstance(value.get("name"), str)
        and value["name"].strip()
    ]
    if len(semantic_nodes) < 1:
        raise ValueError(f"GLB must contain named semantic nodes: {path}")
    return clips, len(semantic_nodes)


def verify_approvals(
    orbit_approval_path: Path,
    family_approval_path: Path,
    glbs: dict[str, Path],
) -> None:
    orbit = read_json(orbit_approval_path)
    if (
        orbit.get("decision") != "approved"
        or orbit.get("identity_id") != ORBIT_ID
        or orbit.get("production_use") != "approved-as-selected-styled-glb-proof"
    ):
        raise ValueError("Orbit final GLB owner approval is incomplete")

    family = read_json(family_approval_path)
    if (
        family.get("decision") != "approved"
        or family.get("production_use")
        != "approved-for-styled-glb-family-expansion"
    ):
        raise ValueError("styled GLB family owner approval is incomplete")
    expected_ids = set(IDENTITY_IDS) - {ORBIT_ID}
    if set(family.get("approved_identities", [])) != expected_ids:
        raise ValueError("styled GLB family approval does not cover five identities")
    approved_hashes = family.get("approved_glbs")
    if not isinstance(approved_hashes, dict):
        raise ValueError("styled GLB family approval has no immutable GLB hashes")
    for identity_id in sorted(expected_ids):
        actual = sha256_file(glbs[identity_id])
        if approved_hashes.get(identity_id) != actual:
            raise ValueError(f"owner-approved GLB changed: {identity_id}")


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    review_root = args.review_root.resolve()
    source_root = args.source_root.resolve()
    matrix_path = args.matrix.resolve()
    output = args.output.resolve()
    matrix = read_json(matrix_path)
    reactions = matrix.get("reactions")
    if not isinstance(reactions, list) or len(reactions) != 10:
        raise ValueError("Micro Reactions matrix must contain ten reactions")
    reaction_by_id = {
        str(value["id"]): value for value in reactions if isinstance(value, dict)
    }
    if len(reaction_by_id) != 10:
        raise ValueError("Micro Reactions matrix contains duplicate reaction IDs")

    review = read_json(review_root / "review.json")
    if (
        review.get("review_status") != "owner-approved"
        or review.get("identity_count") != 6
        or review.get("sticker_count") != 60
        or review.get("animated_sticker_count") != 60
    ):
        raise ValueError("the owner-approved 60-sticker vector review is incomplete")

    glbs = {
        identity_id: (
            args.orbit_glb.resolve()
            if identity_id == ORBIT_ID
            else (args.family_glb_root.resolve() / f"{identity_id}.glb")
        )
        for identity_id in IDENTITY_IDS
    }
    if any(not value.is_file() for value in glbs.values()):
        missing = [str(value) for value in glbs.values() if not value.is_file()]
        raise FileNotFoundError(f"missing styled GLB: {', '.join(missing)}")
    verify_approvals(args.orbit_approval, args.family_approval, glbs)

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output.name + ".staging-", dir=output.parent))
    encoded_bytes = 0
    stickers: list[dict[str, Any]] = []
    source_inputs = [
        matrix_path,
        review_root / "review.json",
        args.orbit_approval.resolve(),
        args.family_approval.resolve(),
    ]
    try:
        for identity_id in IDENTITY_IDS:
            identity_path = source_root / identity_id / "identity.json"
            pack_path = source_root / identity_id / "pack.json"
            identity = read_json(identity_path)
            pack = read_json(pack_path)
            if (
                identity.get("identity_id") != identity_id
                or pack.get("pack_id") != identity_id
            ):
                raise ValueError(f"source identity mismatch: {identity_id}")
            display_name = str(identity.get("display_name", identity_id))
            source_inputs.extend((identity_path, pack_path))
            for reaction_id, reaction in reaction_by_id.items():
                sticker_id = f"{identity_id}-{reaction_id}"
                source_primary = (
                    review_root / "assets" / identity_id / f"{sticker_id}.webp"
                )
                source_reduced = (
                    review_root
                    / "reduced-motion"
                    / identity_id
                    / f"{sticker_id}.webp"
                )
                if not source_primary.is_file() or not source_reduced.is_file():
                    raise FileNotFoundError(f"missing reviewed sticker: {sticker_id}")
                primary_relative = Path("assets") / identity_id / source_primary.name
                reduced_relative = (
                    Path("reduced-motion") / identity_id / source_reduced.name
                )
                thumbnail_relative = (
                    Path("thumbnails") / identity_id / source_reduced.name
                )
                primary = staging / primary_relative
                reduced = staging / reduced_relative
                thumbnail = staging / thumbnail_relative
                primary.parent.mkdir(parents=True, exist_ok=True)
                reduced.parent.mkdir(parents=True, exist_ok=True)
                thumbnail.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_primary, primary)
                shutil.copyfile(source_reduced, reduced)
                with Image.open(source_reduced) as image:
                    frame = image.convert("RGBA").resize(
                        (256, 256), Image.Resampling.LANCZOS
                    )
                    frame.save(
                        thumbnail,
                        format="WEBP",
                        lossless=True,
                        exact=True,
                        method=6,
                    )
                if b"ANIM" not in primary.read_bytes() or b"ANMF" not in primary.read_bytes():
                    raise ValueError(f"primary sticker is not animated WebP: {sticker_id}")
                primary_asset = asset(primary, primary_relative, 512, 512)
                reduced_asset = asset(reduced, reduced_relative, 512, 512)
                thumbnail_asset = asset(
                    thumbnail, thumbnail_relative, 256, 256
                )
                encoded_bytes += (
                    primary_asset["encoded_bytes"]
                    + reduced_asset["encoded_bytes"]
                    + thumbnail_asset["encoded_bytes"]
                )
                stickers.append(
                    {
                        "pack_id": identity_id,
                        "sticker_id": sticker_id,
                        "phrase_id": str(reaction["intent"]),
                        "text": "",
                        "alt_text": f"{display_name}: {reaction_id} reaction",
                        "animated": True,
                        "media_type": "image/webp",
                        **primary_asset,
                        "thumbnail": thumbnail_asset,
                        "reduced_motion": {
                            **reduced_asset,
                            "presentation": "static-semantic-equivalent",
                        },
                    }
                )

        models: list[dict[str, Any]] = []
        for identity_id in IDENTITY_IDS:
            source = glbs[identity_id]
            destination_relative = Path("models") / source.name
            destination = staging / destination_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            clips, node_count = parse_glb(destination)
            digest = sha256_file(destination)
            size = destination.stat().st_size
            encoded_bytes += size
            source_inputs.append(source)
            models.append(
                {
                    "model_id": f"{identity_id}-styled",
                    "identity_id": identity_id,
                    "media_type": "model/gltf-binary",
                    "path": destination_relative.as_posix(),
                    "sha256": digest,
                    "encoded_bytes": size,
                    "clip_names": clips,
                    "semantic_node_count": node_count,
                }
            )

        source_digest = hashlib.sha256()
        for path in sorted(set(source_inputs), key=lambda value: value.as_posix()):
            source_digest.update(path.name.encode())
            source_digest.update(b"\0")
            source_digest.update(sha256_file(path).encode())
            source_digest.update(b"\0")
        catalogue = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "bundle_version": 1,
            "source_sha256": source_digest.hexdigest(),
            "sticker_count": len(stickers),
            "animated_sticker_count": len(stickers),
            "model_count": len(models),
            "models": models,
            "stickers": stickers,
        }
        dictionary_entries = [
            {
                "trigger": reaction_id,
                "match": "unicode-word-boundary",
                "phrase_ids": [str(reaction_by_id[reaction_id]["intent"])],
            }
            for reaction_id in reaction_by_id
        ]
        dictionary = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "matching": MATCHING,
            "trigger_count": len(dictionary_entries),
            "entries": dictionary_entries,
        }
        report = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "status": "success",
            "pack_count": len(IDENTITY_IDS),
            "sticker_count": len(stickers),
            "animated_sticker_count": len(stickers),
            "model_count": len(models),
            "asset_count": len(stickers) * 3 + len(models),
            "reduced_motion_sticker_count": len(stickers),
            "encoded_bytes": encoded_bytes,
        }
        write_json(staging / "catalogue.json", catalogue)
        write_json(staging / "dictionary.json", dictionary)
        write_json(staging / "build-report.json", report)
        replace_directory(staging, output, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-root",
        type=Path,
        default=ROOT / "generated" / "micro-reactions-v1-review",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT / "art" / "micro-reactions-v1" / "candidates",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=ROOT / "content" / "micro-reactions-emotion-matrix-v1.json",
    )
    parser.add_argument(
        "--orbit-glb",
        type=Path,
        default=ROOT
        / "art"
        / "micro-reactions-v1"
        / "orbit-glb-proof"
        / "micro-orbit-004.glb",
    )
    parser.add_argument(
        "--family-glb-root",
        type=Path,
        default=ROOT / "art" / "micro-reactions-v1" / "styled-glb-proofs",
    )
    parser.add_argument(
        "--orbit-approval",
        type=Path,
        default=ROOT
        / "contracts"
        / "micro-orbit-final-glb-face-parity-owner-approval-v1.json",
    )
    parser.add_argument(
        "--family-approval",
        type=Path,
        default=ROOT
        / "contracts"
        / "micro-reactions-styled-glb-family-owner-approval-v1.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "micro-reactions-production-bundle",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_bundle(args)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
