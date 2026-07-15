#!/usr/bin/env python3
"""Validate production standards and deterministic draft .mascot packaging."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path


def run(command: list[str], expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if (completed.returncode == 0) != expect_success:
        raise AssertionError(
            f"unexpected command result ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--packager", type=Path, required=True)
    parser.add_argument("--standard", type=Path, required=True)
    parser.add_argument("--canonical-family", type=Path, required=True)
    parser.add_argument("--production-design-review", type=Path, required=True)
    parser.add_argument("--canonical-asset", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run([
        args.python, str(args.validator),
        "--production-standard", str(args.standard),
        "--canonical-family", str(args.canonical_family),
        "--canonical-asset", str(args.canonical_asset),
    ])
    standard = json.loads(args.standard.read_text(encoding="utf-8"))
    if standard["asset_class"] != "production-art":
        raise AssertionError("human visual standard is not a production-art contract")
    family = json.loads(args.canonical_family.read_text(encoding="utf-8"))
    if family["status"] != "approved-canonical-foundation" or family["scope"] != "foundation-not-complete-library":
        raise AssertionError("canonical family approval or scope is incorrect")
    design_review = json.loads(args.production_design_review.read_text(encoding="utf-8"))
    if (
        design_review.get("authority") != "project-owner"
        or design_review.get("decision") != "approved"
        or design_review.get("release_disposition") != "activate-public-release"
    ):
        raise AssertionError("current production approval and public-release activation are not enforced")
    if design_review.get("blocking_findings"):
        raise AssertionError("approved production design retains blocking findings")
    if not all(design_review.get("owner_attestations", {}).values()):
        raise AssertionError("production approval lacks complete owner playback attestations")

    with tempfile.TemporaryDirectory(prefix="mascotrender-package-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        payloads = {
            "identity.json": b'{"character_id":"human-test-001"}\n',
            "rig.json": b'{"rig_id":"humanoid-full-body-v1"}\n',
            "licenses/ART.txt": b"Original test fixture art.\n",
            "provenance/source.json": b'{"kind":"test-fixture"}\n',
        }
        for relative, payload in payloads.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        manifest = {
            "format_version": 1,
            "package_id": "org.mascotrender.human-test",
            "package_version": "0.1.0",
            "character_id": "human-test-001",
            "status": "technical-fixture",
            "engine": {"api_major": 0, "minimum_version": "0.1.0"},
            "entry_points": {"identity": "identity.json", "rig": "rig.json"},
            "files": [
                {"path": relative, "sha256": hashlib.sha256(payload).hexdigest(), "role": "test-fixture"}
                for relative, payload in sorted(payloads.items())
            ],
            "capabilities": {
                "backends": ["vector"],
                "outputs": ["webp-static"],
                "framings": ["full-body"],
                "semantics": ["gesture.primary"]
            },
            "default_locale": "en",
            "licenses": ["licenses/ART.txt"],
            "provenance": ["provenance/source.json"]
        }
        manifest_path = source / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        first = root / "first.mascot"
        second = root / "second.mascot"
        build = [args.python, str(args.packager), "build", "--source", str(source), "--manifest", str(manifest_path)]
        run(build + ["--output", str(first)])
        run(build + ["--output", str(second)])
        if first.read_bytes() != second.read_bytes():
            raise AssertionError(".mascot package build is not byte deterministic")
        run([args.python, str(args.packager), "verify", "--input", str(first)])
        with zipfile.ZipFile(first, "r") as archive:
            if archive.namelist() != sorted(archive.namelist()):
                raise AssertionError(".mascot entries are not sorted")
            if archive.getinfo("identity.json").compress_type != zipfile.ZIP_STORED:
                raise AssertionError("draft package unexpectedly uses variable compression")

        manifest["files"][0]["path"] = "../escape.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        run(build + ["--output", str(root / "unsafe.mascot")], expect_success=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
