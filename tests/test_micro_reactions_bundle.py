#!/usr/bin/env python3
"""End-to-end regression for the Micro Reactions production bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--bundle-tool", type=Path, required=True)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
