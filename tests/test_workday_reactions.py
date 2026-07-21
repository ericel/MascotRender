#!/usr/bin/env python3
"""Development-contract regression for Workday Reactions."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
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
    parser.add_argument("--canonical-source", type=Path, required=True)
    parser.add_argument("--determinism-runs", type=int, choices=(1, 2), default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = read_json(args.contract)
    matrix = read_json(args.matrix)
    assert contract["contract_id"] == "workday-reactions-pack-v1"
    assert contract["status"] == "owner-production-approved"
    assert contract["production_use"] == "approved-for-public-production"
    assert contract["scope"] == {
        "category_count": 8,
        "stickers_per_category": 12,
        "sticker_count": 96,
        "animated_sticker_count": 96,
        "reduced_motion_sticker_count": 96,
    }
    assert contract["character_identity"]["character_id"] == (
        "pace-red-panda-001"
    )
    entries = matrix["entries"]
    assert len(entries) == 96
    assert len({entry["id"] for entry in entries}) == 96
    assert len({entry["label"] for entry in entries}) == 96
    expected_categories = {
        "workflow", "meetings", "decisions", "team", "results", "time",
        "energy", "humor",
    }
    assert Counter(entry["category"] for entry in entries) == {
        category: 12 for category in expected_categories
    }
    variety = contract["art_direction"]["family_variety"]
    assert len({entry["font_voice"] for entry in entries}) >= variety["minimum_font_voices"]
    assert len({entry["motion"] for entry in entries}) >= variety["minimum_motion_families"]
    assert len({entry["layout"] for entry in entries}) >= variety["minimum_composition_systems"]
    assert len({entry["effect"] for entry in entries}) >= variety["minimum_semantic_prop_effect_concepts"]
    assert len({entry["pose"] for entry in entries}) >= variety["minimum_pose_families"]
    assert len({entry["mood"] for entry in entries}) >= variety["minimum_mood_families"]
    assert all(entry["aliases"] for entry in entries)

    with tempfile.TemporaryDirectory(prefix="workday-reactions-test-") as directory:
        root = Path(directory)
        outputs = [(root / "source", root / "review")]
        if args.determinism_runs == 2:
            outputs.append((root / "source-repeat", root / "review-repeat"))
        for source, review in outputs:
            subprocess.run(
                [
                    str(args.python), str(args.generator),
                    "--source-output", str(source),
                    "--review-output", str(review),
                    "--mascotrender", str(args.cli),
                ],
                check=True,
            )
        source, review = outputs[0]
        manifest = read_json(source / "generation-manifest.json")
        result = read_json(review / "review.json")
        triggers = read_json(source / "workday-reactions-v1" / "triggers.json")
        decision = read_json(review / "owner-approval.json")
        assert manifest["sticker_count"] == 96
        assert manifest["category_counts"] == {
            category: 12 for category in sorted(expected_categories)
        }
        assert manifest["font_voice_count"] >= 4
        assert manifest["motion_family_count"] >= 12
        assert manifest["composition_system_count"] >= 8
        assert manifest["effect_family_count"] >= 48
        assert manifest["visual_prop_archetype_count"] >= 20
        assert manifest["pose_family_count"] >= 12
        assert manifest["mood_family_count"] >= 18
        assert manifest["independently_typeset_duplicate_text_blocks"] == 0
        assert result["review_status"] == "owner-approved"
        assert result["production_use"] == "approved-for-public-production"
        assert isinstance(result["owner_artifact_hash_match"], bool)
        assert result["artifact_hash_scope"] == "render-runtime-specific"
        assert result["sticker_count"] == 96
        assert result["animated_sticker_count"] == 96
        assert result["loop_closed_sticker_count"] == 96
        assert result["minimum_frame_margin_px"] >= 16
        assert result["visual_prop_archetype_count"] >= 20
        assert all(item["animated_webp"] for item in result["metrics"])
        assert all(item["visible_mid_cycle_change"] for item in result["metrics"])
        assert all(item["loop_closure"] for item in result["metrics"])
        assert decision["decision"] == "approved"
        assert decision["production_use"] == "approved-for-public-production"
        assert decision["reviewed_artifacts"] == result["owner_reviewed_artifacts"]
        assert len(triggers["entries"]) == 96
        pack_root = source / "workday-reactions-v1"
        for entry in entries:
            slug = entry["id"].rsplit(".", 1)[-1]
            sticker = read_json(pack_root / "stickers" / f"{slug}.json")
            assert "texts" not in sticker
            assert sticker["text"]["content"] == entry["label"]
            trigger = next(
                item for item in triggers["entries"]
                if item["phrase_id"] == entry["id"]
            )
            assert {item["text"] for item in trigger["triggers"]} == set(entry["aliases"])
        assert tree_hashes(source) == tree_hashes(args.canonical_source)
        if args.determinism_runs == 2:
            assert tree_hashes(outputs[0][0]) == tree_hashes(outputs[1][0])
            assert tree_hashes(outputs[0][1]) == tree_hashes(outputs[1][1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
