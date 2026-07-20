#!/usr/bin/env python3
"""End-to-end regression for the Micro Reactions production bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--bundle-tool", type=Path, required=True)
    parser.add_argument("--archive-tool", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--orbit-glb", type=Path, required=True)
    parser.add_argument("--family-glb-root", type=Path, required=True)
    parser.add_argument("--orbit-approval", type=Path, required=True)
    parser.add_argument("--family-approval", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="micro-reactions-bundle-") as directory:
        root = Path(directory)
        source = root / "source"
        review = root / "review"
        bundle = root / "bundle"
        distribution = root / "distribution"
        incremental = root / "incremental"
        run(
            [
                args.python,
                str(args.generator),
                "--source-output",
                str(source),
                "--review-output",
                str(review),
                "--mascotrender",
                str(args.cli),
            ]
        )
        build_command = [
            args.python,
            str(args.builder),
            "--review-root",
            str(review),
            "--source-root",
            str(source),
            "--matrix",
            str(args.matrix),
            "--orbit-glb",
            str(args.orbit_glb),
            "--family-glb-root",
            str(args.family_glb_root),
            "--orbit-approval",
            str(args.orbit_approval),
            "--family-approval",
            str(args.family_approval),
            "--output",
            str(bundle),
        ]
        run(build_command)
        run(
            [
                args.python,
                str(args.bundle_tool),
                "validate",
                "--bundle",
                str(bundle),
            ]
        )
        report = read_json(bundle / "build-report.json")
        assert report["pack_count"] == 6
        assert report["sticker_count"] == 60
        assert report["animated_sticker_count"] == 60
        assert report["model_count"] == 6
        assert report["asset_count"] == 186

        run(
            [
                args.python,
                str(args.bundle_tool),
                "stage",
                "--bundle",
                str(bundle),
                "--output",
                str(distribution),
                "--channel",
                "micro-reactions-stable",
            ]
        )
        plan = read_json(distribution / "publish-plan.json")
        assert plan["object_count"] == 190
        assert plan["upload_count"] == 190
        model_objects = [
            value
            for value in plan["objects"]
            if value["content_type"] == "model/gltf-binary"
        ]
        assert len(model_objects) == 6
        assert all(
            value["cache_control"] == "public,max-age=31536000,immutable"
            for value in model_objects
        )

        run(
            [
                args.python,
                str(args.bundle_tool),
                "stage",
                "--bundle",
                str(bundle),
                "--output",
                str(incremental),
                "--channel",
                "micro-reactions-stable",
                "--previous-plan",
                str(distribution / "publish-plan.json"),
            ]
        )
        incremental_plan = read_json(incremental / "publish-plan.json")
        assert incremental_plan["bundle_id"] == plan["bundle_id"]
        assert incremental_plan["upload_count"] == 0
        assert incremental_plan["skip_count"] == 190

        approval = root / "owner-approval.json"
        approval.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "authority": "project-owner",
                    "decision": "approved",
                    "production_use": "approved-for-public-production",
                    "candidate": {
                        "bundle_id": plan["bundle_id"],
                        "object_count": plan["object_count"],
                    },
                    "candidate_artifacts": {
                        "catalogue.json": sha256_file(bundle / "catalogue.json"),
                        "dictionary.json": sha256_file(bundle / "dictionary.json"),
                        "build-report.json": sha256_file(bundle / "build-report.json"),
                        "channels/micro-reactions-stable.json": sha256_file(
                            distribution / "channels/micro-reactions-stable.json"
                        ),
                        "release.json": sha256_file(
                            distribution
                            / "bundles"
                            / plan["bundle_id"]
                            / "release.json"
                        ),
                        "publish-plan.json": sha256_file(
                            distribution / "publish-plan.json"
                        ),
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        archive_a = root / "release-a.zip"
        archive_b = root / "release-b.zip"
        for output in (archive_a, archive_b):
            run(
                [
                    args.python,
                    str(args.archive_tool),
                    "--distribution",
                    str(distribution),
                    "--source-bundle",
                    str(bundle),
                    "--approval",
                    str(approval),
                    "--output",
                    str(output),
                ]
            )
        assert sha256_file(archive_a) == sha256_file(archive_b)
        with zipfile.ZipFile(archive_a) as archive:
            names = archive.namelist()
            assert len(names) == 192
            assert names[-1].endswith("/owner-approval.json")
            assert any(name.endswith("/channels/micro-reactions-stable.json") for name in names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
