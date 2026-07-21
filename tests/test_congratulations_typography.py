#!/usr/bin/env python3
"""Development-contract regression for Congratulations Pop."""

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
    assert contract["contract_id"] == "congratulations-typography-pack-v1"
    assert contract["status"] == "owner-production-approved"
    assert contract["production_use"] == "approved-for-public-production"
    approval = read_json(args.owner_approval)
    assert approval["authority"] == "project-owner"
    assert approval["decision"] == "approved"
    assert approval["gate"] == (
        "congratulations-typography-production-art-and-playback-v1"
    )
    assert approval["production_use"] == "approved-for-public-production"
    assert contract["scope"] == {
        "core_count": 12,
        "achievement_count": 8,
        "milestone_count": 8,
        "cheer_count": 8,
        "sticker_count": 36,
        "animated_sticker_count": 36,
        "reduced_motion_sticker_count": 36,
    }
    assert contract["composition"]["canonical_canvas"] == {
        "width": 512,
        "height": 512,
    }
    typography = contract["art_direction"]["typography"]
    assert typography["single_read_requirement"] is True
    assert (
        typography["front_depth_and_highlight_share_one_fitted_glyph_layout"]
        is True
    )
    assert typography["independently_typeset_duplicate_word_forbidden"] is True
    assert typography["maximum_lines"] == 2

    entries = matrix["entries"]
    assert len(entries) == 36
    assert len({entry["id"] for entry in entries}) == 36
    assert len({entry["label"] for entry in entries}) == 36
    assert {
        category: sum(entry["category"] == category for entry in entries)
        for category in ("core", "achievement", "milestone", "cheer")
    } == {
        "core": 12,
        "achievement": 8,
        "milestone": 8,
        "cheer": 8,
    }
    assert len({entry["font_voice"] for entry in entries}) == 4
    assert {entry["motion"] for entry in entries} == {
        "pop",
        "pulse",
        "wobble",
        "float",
    }
    assert len({entry["layout"] for entry in entries}) == 6
    assert len({entry["effect"] for entry in entries}) >= 18
    assert all(entry["aliases"] for entry in entries)

    with tempfile.TemporaryDirectory(
        prefix="congratulations-pop-test-"
    ) as directory:
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
        decision = read_json(review / "owner-approval.json")
        triggers = read_json(
            source / "congratulations-pop-v1" / "triggers.json"
        )
        assert manifest["sticker_count"] == 36
        assert manifest["category_counts"] == {
            "core": 12,
            "achievement": 8,
            "milestone": 8,
            "cheer": 8,
        }
        assert manifest["font_voice_count"] == 4
        assert manifest["motion_family_count"] == 4
        assert manifest["composition_system_count"] == 6
        assert manifest["motif_family_count"] >= 18
        assert manifest["single_fitted_glyph_layout_per_sticker"] is True
        assert manifest["independently_typeset_duplicate_text_blocks"] == 0
        assert manifest["owner_approval"] == (
            "contracts/congratulations-typography-owner-approval-v1.json"
        )
        assert manifest["production_use"] == "approved-for-public-production"

        assert result["review_status"] == "owner-approved"
        assert result["production_use"] == "approved-for-public-production"
        assert result["owner_approval"] == (
            "contracts/congratulations-typography-owner-approval-v1.json"
        )
        assert result["owner_reviewed_artifacts"] == approval["reviewed_artifacts"]
        assert isinstance(result["owner_artifact_hash_match"], bool)
        assert result["artifact_hash_scope"] == "render-runtime-specific"
        assert result["sticker_count"] == 36
        assert result["animated_sticker_count"] == 36
        assert result["loop_closed_sticker_count"] == 36
        assert result["single_layout_shell_sticker_count"] == 36
        assert result["independently_typeset_duplicate_text_block_count"] == 0
        assert result["minimum_frame_margin_px"] >= 16
        assert set(result["artifacts"]) == {
            "contact-sheet.png",
            "small-display-80-100-160.png",
            "motion-sample-sheet.png",
            "animation-review.html",
        }
        assert result["artifacts"] == {
            name: sha256(review / name)
            for name in result["artifacts"]
        }
        assert all(metric["animated_webp"] for metric in result["metrics"])
        assert all(
            metric["visible_mid_cycle_change"] for metric in result["metrics"]
        )
        assert all(metric["loop_closure"] for metric in result["metrics"])

        assert decision["decision"] == "approved"
        assert decision["gate"] == (
            "congratulations-typography-production-art-and-playback-v1"
        )
        assert decision["production_use"] == "approved-for-public-production"
        assert decision["reviewed_artifacts"] == result["artifacts"]

        assert len(triggers["entries"]) == 36
        pack_root = source / "congratulations-pop-v1"
        for entry in entries:
            slug = entry["id"].rsplit(".", 1)[-1]
            sticker = read_json(pack_root / "stickers" / f"{slug}.json")
            assert "texts" not in sticker
            assert sticker["text"]["content"] == entry["label"]
            assert sticker["text"].get("scale", 1) == 1
            trigger_entry = next(
                item
                for item in triggers["entries"]
                if item["phrase_id"] == entry["id"]
            )
            assert {item["text"] for item in trigger_entry["triggers"]} == set(
                entry["aliases"]
            )

        assert tree_hashes(source) == tree_hashes(args.canonical_source)
        if args.determinism_runs == 2:
            assert tree_hashes(source) == tree_hashes(repeated_source)
            assert tree_hashes(review) == tree_hashes(repeated_review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
