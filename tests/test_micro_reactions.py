#!/usr/bin/env python3
"""Production-contract regression for the Micro Reactions review cohort."""

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--owner-approval", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = read_json(args.contract)
    matrix = read_json(args.matrix)
    assert contract["schema_version"] == 1
    assert contract["contract_id"] == "micro-reactions-pack-v1"
    assert contract["production_use"] == "forbidden-until-final-pack-owner-activation"
    approval = read_json(args.owner_approval)
    assert approval["authority"] == "project-owner"
    assert approval["decision"] == "approved"
    assert approval["approved_gates"]["ten-reaction-semantic-readability"] == "pass"
    assert approval["approved_gates"]["controlled-small-display-readability"] == "pass"
    assert contract["scope"] == {
        "identity_count": 6,
        "reactions_per_identity": 10,
        "sticker_count": 60,
        "animated_sticker_count": 60,
        "reduced_motion_sticker_count": 60,
    }
    assert contract["composition"]["canonical_canvas"] == {"width": 512, "height": 512}
    assert contract["composition"]["text_policy"] == "text-free-primary"
    assert contract["art_direction"]["identity_separation"]["recolor_only_variants_forbidden"] is True

    reactions = matrix["reactions"]
    performances = matrix["identity_performances"]
    assert len(reactions) == 10
    assert len({reaction["id"] for reaction in reactions}) == 10
    assert len(performances) == 6
    assert len({value["signature_motion"] for value in performances.values()}) == 6
    assert len({value["signature_effect"] for value in performances.values()}) == 6

    with tempfile.TemporaryDirectory(prefix="micro-reactions-test-") as directory:
        root = Path(directory)
        source = root / "source"
        review = root / "review"
        subprocess.run(
            [
                str(args.python),
                str(args.generator),
                "--source-output",
                str(source),
                "--review-output",
                str(review),
                "--mascotrender",
                str(args.cli),
            ],
            check=True,
        )
        manifest = read_json(source / "generation-manifest.json")
        result = read_json(review / "review.json")
        assert manifest["identity_count"] == 6
        assert manifest["sticker_count"] == 60
        assert len({pack["primary"] for pack in manifest["packs"]}) == 6
        assert len({pack["signature"] for pack in manifest["packs"]}) == 6
        assert result["review_status"] == "owner-approved"
        assert result["production_use"] == "forbidden-until-selected-glb-and-final-pack-review"
        assert result["sticker_count"] == 60
        assert result["animated_sticker_count"] == 60
        assert result["minimum_frame_margin_px"] >= 16
        assert result["distinct_primary_palette_count"] == 6
        assert result["distinct_signature_count"] == 6
        assert result["controlled_small_display_evidence"] == {
            "identity_count": 6,
            "reaction_count": 10,
            "sizes_px": [80, 100, 160],
            "rendered_comparison_count": 180,
            "same_reaction_positions_across_size_sheets": True,
        }
        assert set(result["artifacts"]) == {
            "identity-lineup.png",
            "reaction-matrix.png",
            "small-display-all-reactions-80px.png",
            "small-display-all-reactions-100px.png",
            "small-display-all-reactions-160px.png",
            "animation-review.html",
        }
        assert result["artifacts"] == approval["reviewed_artifacts"]["reaction_gate"]
        assert all(metric["animated_webp"] for metric in result["metrics"])
        assert all(metric["visible_mid_cycle_change"] for metric in result["metrics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
