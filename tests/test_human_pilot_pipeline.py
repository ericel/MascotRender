#!/usr/bin/env python3
"""Deterministic integration gate for human identity, rig, and recipe packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}\n{completed.stderr}")


def digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        value.update(relative)
        value.update(b"\0")
        value.update(path.read_bytes())
    return value.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--reviewer", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--font-source", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run([args.python, str(args.validator)])
    with tempfile.TemporaryDirectory(prefix="mascotrender-human-pilots-") as temporary:
        root = Path(temporary)
        first = root / "first"
        second = root / "second"
        base = [args.python, str(args.generator), "--count", "2", "--seed", "42", "--font-source", str(args.font_source)]
        run(base + ["--output", str(first)])
        run(base + ["--output", str(second)])
        if digest(first) != digest(second):
            raise AssertionError("human pilot generation is not byte deterministic")
        manifest = json.loads((first / "generation-manifest.json").read_text())
        if manifest["pack_count"] != 2 or manifest["sticker_count"] != 24 or manifest["phrase_count"] != 12:
            raise AssertionError("unexpected human pilot manifest counts")
        if manifest.get("asset_class") != "technical-fixture" or manifest.get("production_use") != "forbidden":
            raise AssertionError("procedural humans are not locked to technical-fixture use")
        for pack_path in sorted(first.glob("human-*/pack.json")):
            pack = json.loads(pack_path.read_text())
            if pack["rig"]["contract_id"] != "humanoid-full-body-v1":
                raise AssertionError("generated pack lost its humanoid rig contract")
            if not any(layer.get("parent") for layer in pack["layers"]):
                raise AssertionError("generated humanoid pack is not parented")
            sticker_paths = sorted((pack_path.parent / "stickers").glob("*.json"))
            if len(sticker_paths) != 12:
                raise AssertionError("generated humanoid pack is missing a core phrase")
            for sticker in sticker_paths:
                document = json.loads(sticker.read_text())
                selected = set(pack["base_layers"] + pack["expressions"][document["expression"]] + pack["poses"][document["pose"]])
                if document["camera"]["framing"] not in {"face-closeup", "bust", "three-quarter", "full-body", "dynamic-full-body"}:
                    raise AssertionError("sticker has no semantic camera framing")
                if any(track["target"] not in selected for track in document["animation"]["tracks"]):
                    raise AssertionError("semantic recipe did not compile to selected rig layers")
                run([str(args.cli), "validate", "--pack", str(pack_path), "--sticker", str(sticker)])

        pillow_available = subprocess.run(
            [args.python, "-c", "import PIL"], capture_output=True, check=False
        ).returncode == 0
        if pillow_available:
            review = root / "review"
            run([args.python, str(args.reviewer), "--input", str(first), "--output", str(review), "--mascotrender", str(args.cli), "--size", "128"])
            review_report = json.loads((review / "review.json").read_text())
            if review_report["verification_status"] != "success" or review_report["poster_count"] != 24 or len(review_report["contact_sheets"]) != 12:
                raise AssertionError("human pilot review did not cover every rendition")
            if review_report.get("asset_class") != "technical-fixture" or review_report.get("production_use") != "forbidden":
                raise AssertionError("fixture review incorrectly implies production eligibility")

        one_pack = root / "one-pack"
        run([args.python, str(args.generator), "--count", "1", "--seed", "42", "--font-source", str(args.font_source), "--output", str(one_pack)])
        bundle = root / "bundle"
        run([args.python, str(args.renderer), "--input", str(one_pack), "--output", str(bundle), "--mascotrender", str(args.cli), "--width", "128", "--height", "128", "--thumbnail-size", "64", "--lossless"])
        catalogue = json.loads((bundle / "catalogue.json").read_text())
        if catalogue["sticker_count"] != 12 or catalogue["animated_sticker_count"] != 12:
            raise AssertionError("human pilot bundle counts are incorrect")
        if any(not item.get("phrase_id") or not item.get("recipe_id") or not item.get("camera") for item in catalogue["stickers"]):
            raise AssertionError("bundle catalogue lost semantic sticker metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
