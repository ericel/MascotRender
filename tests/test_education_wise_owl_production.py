#!/usr/bin/env python3
"""Validate the approved Wise Owl Academy production source and install gate."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--owner-approval", type=Path, required=True)
    parser.add_argument("--canonical-source", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = read_json(args.contract)
    approval = read_json(args.owner_approval)
    source = args.canonical_source
    manifest = read_json(source / "generation-manifest.json")
    pack_root = source / "education-wise-owl-illustrated-v2"
    pack_path = pack_root / "pack.json"
    pack = read_json(pack_path)
    triggers = read_json(pack_root / "triggers.json")
    sticker_paths = sorted((pack_root / "stickers").glob("*.json"))

    assert contract["status"] == "owner-production-approved"
    assert contract["production_use"] == (
        "approved-for-production-packaging-and-public-release"
    )
    assert contract["sticker_finish"]["hard-frame-margin-px"] == 16
    assert contract["sticker_finish"][
        "hard-frame-margin-is-immutable-lower-bound"
    ]
    assert not contract["sticker_finish"][
        "automatic-cropping-may-tighten-below-bound"
    ]
    assert not contract["sticker_finish"][
        "store-platform-effects-may-exceed-union-bounds"
    ]

    assert approval["authority"] == "project-owner"
    assert approval["decision"] == "approved"
    assert approval["decision_date"] == "2026-07-22"
    assert len(approval["reviewed_artifacts"]) == 15

    assert manifest["pack_id"] == "education-wise-owl-illustrated-v2"
    assert manifest["sticker_count"] == 100
    assert manifest["golden_sticker_count"] == 10
    assert manifest["expanded_sticker_count"] == 90
    assert manifest["composited_layer_count_per_sticker"] == 12
    assert manifest["visible_sequence_numbers"] == 0
    assert manifest["production_use"] == (
        "approved-for-production-packaging-and-public-release"
    )

    assert pack["pack_id"] == manifest["pack_id"]
    assert pack["canvas"] == {"width": 512, "height": 512}
    assert len(sticker_paths) == 100
    assert triggers["selection_structure"] == (
        "unicode-normalized-casefolded-trie"
    )
    assert len(triggers["entries"]) == 100
    assert len({entry["phrase_id"] for entry in triggers["entries"]}) == 100
    assert len({entry["sticker_id"] for entry in triggers["entries"]}) == 100
    assert any(
        entry["phrase_id"] == "education.assessment.every-day-counts"
        for entry in triggers["entries"]
    )

    cli = args.cli.resolve()
    for sticker_path in sticker_paths:
        subprocess.run(
            [
                str(cli),
                "validate",
                "--pack",
                str(pack_path),
                "--sticker",
                str(sticker_path),
            ],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
