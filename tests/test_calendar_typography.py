#!/usr/bin/env python3
"""Development-contract regression for the Calendar Pop typography pack."""

from __future__ import annotations

import argparse
import hashlib
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--owner-approval", type=Path, required=True)
    parser.add_argument("--canonical-source", type=Path, required=True)
    parser.add_argument("--determinism-runs", type=int, choices=(1, 2), default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = read_json(args.contract)
    matrix = read_json(args.matrix)

    assert contract["schema_version"] == 1
    assert contract["contract_id"] == "calendar-typography-pack-v1"
    assert contract["status"] == "owner-production-approved"
    assert contract["production_use"] == "approved-for-public-production"
    approval = read_json(args.owner_approval)
    assert approval["authority"] == "project-owner"
    assert approval["decision"] == "approved"
    assert approval["gate"] == "calendar-typography-production-art-and-playback-v1"
    assert approval["production_use"] == "approved-for-public-production"
    assert contract["scope"] == {
        "weekday_count": 7,
        "month_count": 12,
        "season_count": 4,
        "sticker_count": 23,
        "animated_sticker_count": 23,
        "reduced_motion_sticker_count": 23,
    }
    assert contract["composition"]["canonical_canvas"] == {
        "width": 512,
        "height": 512,
    }
    assert contract["composition"]["hemisphere_assumption_forbidden"] is True
    assert contract["art_direction"]["typography"]["single_read_requirement"] is True
    assert (
        contract["art_direction"]["typography"][
            "front_depth_and_highlight_share_one_fitted_glyph_layout"
        ]
        is True
    )
    assert (
        contract["art_direction"]["typography"][
            "independently_scaled_duplicate_word_forbidden"
        ]
        is True
    )
    assert contract["search_and_localization"]["autumn_aliases"] == [
        "autumn",
        "fall",
    ]

    entries = matrix["entries"]
    assert len(entries) == 23
    assert len({entry["id"] for entry in entries}) == 23
    assert len({entry["label"] for entry in entries}) == 23
    assert sum(entry["category"] == "weekday" for entry in entries) == 7
    assert sum(entry["category"] == "month" for entry in entries) == 12
    assert sum(entry["category"] == "season" for entry in entries) == 4
    assert len({entry["font_voice"] for entry in entries}) == 4
    assert {entry["motion"] for entry in entries} == {"pulse", "wobble", "float"}
    autumn = next(
        entry for entry in entries if entry["id"] == "calendar.season.autumn"
    )
    assert autumn["label"] == "AUTUMN"
    assert autumn["aliases"] == ["autumn", "fall"]

    with tempfile.TemporaryDirectory(prefix="calendar-pop-test-") as directory:
        root = Path(directory)
        source = root / "source"
        review = root / "review"
        repeated_source = root / "repeated-source"
        repeated_review = root / "repeated-review"
        outputs = [(source, review)]
        if args.determinism_runs == 2:
            outputs.append((repeated_source, repeated_review))
        for source_output, review_output in outputs:
            subprocess.run(
                [
                    str(args.python),
                    str(args.generator),
                    "--source-output",
                    str(source_output),
                    "--review-output",
                    str(review_output),
                    "--mascotrender",
                    str(args.cli),
                ],
                check=True,
            )

        manifest = read_json(source / "generation-manifest.json")
        result = read_json(review / "review.json")
        triggers = read_json(source / "calendar-pop-v1" / "triggers.json")
        assert manifest["sticker_count"] == 23
        assert manifest["category_counts"] == {
            "weekday": 7,
            "month": 12,
            "season": 4,
        }
        assert manifest["font_voice_count"] == 4
        assert manifest["motion_family_count"] == 3
        assert manifest["single_fitted_glyph_layout_per_sticker"] is True
        assert manifest["independently_scaled_duplicate_text_blocks"] == 0
        assert result["review_status"] == "owner-approved"
        assert result["production_use"] == "approved-for-public-production"
        assert result["owner_approval"] == (
            "contracts/calendar-typography-owner-approval-v1.json"
        )
        assert result["sticker_count"] == 23
        assert result["animated_sticker_count"] == 23
        assert result["loop_closed_sticker_count"] == 23
        assert result["single_layout_shell_sticker_count"] == 23
        assert result["independently_scaled_duplicate_text_block_count"] == 0
        assert result["minimum_frame_margin_px"] >= 16
        assert set(result["artifacts"]) == {
            "contact-sheet.png",
            "small-display-80-100-160.png",
            "motion-sample-sheet.png",
            "animation-review.html",
        }
        assert result["owner_reviewed_artifacts"] == approval["reviewed_artifacts"]
        assert isinstance(result["owner_artifact_hash_match"], bool)
        assert result["artifact_hash_scope"] == "render-runtime-specific"
        assert result["artifacts"] == {
            name: sha256(review / name)
            for name in result["artifacts"]
        }
        assert all(metric["animated_webp"] for metric in result["metrics"])
        assert all(metric["visible_mid_cycle_change"] for metric in result["metrics"])
        assert all(metric["loop_closure"] for metric in result["metrics"])
        assert len(triggers["entries"]) == 23
        pack_root = source / "calendar-pop-v1"
        for entry in entries:
            sticker = read_json(
                pack_root / "stickers" / f"{entry['id'].rsplit('.', 1)[-1]}.json"
            )
            assert "texts" not in sticker
            assert sticker["text"]["content"] == entry["label"]
            assert sticker["text"].get("scale", 1) == 1
        autumn_triggers = next(
            item
            for item in triggers["entries"]
            if item["phrase_id"] == "calendar.season.autumn"
        )
        assert {trigger["text"] for trigger in autumn_triggers["triggers"]} == {
            "autumn",
            "fall",
        }
        assert tree_hashes(source) == tree_hashes(args.canonical_source)
        if args.determinism_runs == 2:
            assert tree_hashes(source) == tree_hashes(repeated_source)
            assert tree_hashes(review) == tree_hashes(repeated_review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
