#!/usr/bin/env python3
"""Focused regression tests for animation-aware small-display composition."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_human_display_profiles import compose_profile, resample_to_timeline  # noqa: E402


def frame(rect: tuple[int, int, int, int] | None) -> Image.Image:
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    if rect is not None:
        ImageDraw.Draw(image).rectangle(rect, fill=(255, 255, 255, 255))
    return image


def main() -> int:
    contract_path = ROOT / "contracts" / "human-small-display-occupancy-v1.json"
    approval = json.loads(
        (ROOT / "contracts" / "human-small-display-occupancy-owner-approval-v1.json").read_text(encoding="utf-8")
    )
    assert approval["decision"] == "approved"
    assert approval["review_status"] == "small-display-occupancy-approved"
    assert approval["contract_sha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert approval["profile_disposition"]["tray-100"]["role"] == "recommended-default"
    assert approval["profile_disposition"]["stress-80"]["recommended_as_default"] is False

    source = [frame((10, 10, 20, 20)), frame((30, 10, 40, 20))]
    sampled = resample_to_timeline(source, [200, 200], [100, 100, 100, 100])
    assert [value.getchannel("A").getbbox() for value in sampled] == [
        (10, 10, 21, 21), (10, 10, 21, 21), (30, 10, 41, 21), (30, 10, 41, 21)
    ]

    characters = [frame((190, 100, 310, 410)) for _ in range(4)]
    # Wide, shallow caption with invisible loop endpoints exercises both the
    # actual-glyph-height fallback and animation-union occupancy rule.
    captions = [frame(None), frame((60, 50, 450, 85)), frame((60, 50, 450, 85)), frame(None)]
    profile = {
        "target_content_occupancy": 0.85,
        "target_character_height": [0.60, 0.70],
        "minimum_caption_visible_height_ratio": 0.10,
    }
    output, metrics = compose_profile(96, "left", profile, characters, captions, False)
    assert len(output) == 4
    assert metrics["resolved_layout"] == "top"
    assert metrics["animation_union_occupancy"] >= 0.72
    assert metrics["gate_pass"] is True
    assert all(value["caption_character_overlap_pixels"] == 0 for value in metrics["frame_metrics"])
    assert max(value["combined_occupancy"] for value in metrics["frame_metrics"]) <= 0.90
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
