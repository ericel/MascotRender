#!/usr/bin/env python3
"""End-to-end test for procedural pack generation and batch rendering."""

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
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--font-source", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="mascotrender-pipeline-") as temporary:
        root = Path(temporary)
        generated_a = root / "generated-a"
        generated_b = root / "generated-b"
        bundle_a = root / "bundle-a"
        bundle_b = root / "bundle-b"

        generate_base = [
            args.python,
            str(args.generator),
            "--count",
            "2",
            "--seed",
            "123456789",
            "--font-source",
            str(args.font_source),
        ]
        run(generate_base + ["--output", str(generated_a)])
        run(generate_base + ["--output", str(generated_b)])
        if tree_digest(generated_a) != tree_digest(generated_b):
            raise AssertionError("same seed did not generate byte-identical mascot packs")

        render_base = [
            args.python,
            str(args.renderer),
            "--mascotrender",
            str(args.cli),
            "--quality",
            "90",
        ]
        run(render_base + ["--input", str(generated_a), "--output", str(bundle_a)])
        run(render_base + ["--input", str(generated_b), "--output", str(bundle_b)])
        if tree_digest(bundle_a) != tree_digest(bundle_b):
            raise AssertionError("same generated input did not render a byte-identical bundle")

        manifest = json.loads((generated_a / "generation-manifest.json").read_text())
        catalogue = json.loads((bundle_a / "catalogue.json").read_text())
        dictionary = json.loads((bundle_a / "dictionary.json").read_text())
        report = json.loads((bundle_a / "build-report.json").read_text())
        if manifest["pack_count"] != 2 or manifest["sticker_count"] != 20:
            raise AssertionError("unexpected generation manifest counts")
        if catalogue["sticker_count"] != 20 or len(catalogue["stickers"]) != 20:
            raise AssertionError("unexpected catalogue counts")
        if dictionary["trigger_count"] != 10 or len(dictionary["entries"]) != 10:
            raise AssertionError("unexpected dictionary counts")
        if report["asset_count"] != 40 or report["status"] != "success":
            raise AssertionError("unexpected build report")

        webps = sorted(bundle_a.rglob("*.webp"))
        if len(webps) != 40:
            raise AssertionError(f"expected 40 rendered WebPs, got {len(webps)}")
        for webp in webps:
            data = webp.read_bytes()
            if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                raise AssertionError(f"invalid WebP output: {webp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
