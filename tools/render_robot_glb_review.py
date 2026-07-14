#!/usr/bin/env python3
"""Render the rest pose and four MR-112 clips for visual review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


SAMPLES = [
    ("rest", "", 0.0),
    ("idle", "idle", 0.5),
    ("hello", "hello", 0.3),
    ("hop", "hop", 0.3),
    ("celebrate", "celebrate", 0.5),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = {"asset": str(args.input), "samples": []}
    for label, animation, time in SAMPLES:
        destination = args.output / f"robot-004-{label}.webp"
        command = [
            str(args.renderer),
            "--input",
            str(args.input),
            "--output",
            str(destination),
            "--width",
            "512",
            "--height",
            "512",
            "--span",
            "3.6",
        ]
        if animation:
            command.extend(["--animation", animation, "--time", str(time)])
        subprocess.run(command, check=True)
        payload = destination.read_bytes()
        manifest["samples"].append(
            {
                "label": label,
                "animation": animation or None,
                "time_seconds": time,
                "file": destination.name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    (args.output / "review.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(SAMPLES)} robot review frames to {args.output}")


if __name__ == "__main__":
    main()
