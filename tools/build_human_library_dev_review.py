#!/usr/bin/env python3
"""Build a visual and structural review for the 15 × 41 local human bundle."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
MASTER_IDS = tuple(f"H{index:02d}" for index in range(1, 16))
SAMPLE_PHRASES = (
    "chat.hello", "chat.haha", "chat.omg", "chat.thanks",
    "chat.sorry", "chat.no.wahala", "chat.well.done", "chat.love",
)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int):
    for candidate in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "generated" / "wahalao-human-dev-bundle-v7")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "human-library-production-candidate-review")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    catalogue = read_json(bundle / "catalogue.json")
    dictionary = read_json(bundle / "dictionary.json")
    humans = [value for value in catalogue["stickers"] if str(value.get("approved_identity_source", "")) in MASTER_IDS]
    counts = Counter(str(value["approved_identity_source"]) for value in humans)
    if counts != Counter({master_id: 41 for master_id in MASTER_IDS}):
        raise ValueError(f"human matrix is incomplete: {counts}")
    if not all(value.get("animated") is True for value in humans):
        raise ValueError("every local human phrase must carry real animation")
    if not all(value.get("width") == 512 and value.get("height") == 512 for value in humans):
        raise ValueError("human assets must use a uniform 512x512 canvas")
    animated_chunks = 0
    unsafe_frame_bounds: list[dict[str, object]] = []
    for value in humans:
        asset_path = bundle / value["path"]
        payload = asset_path.read_bytes()
        if b"ANIM" in payload and b"ANMF" in payload:
            animated_chunks += 1
        for frame_index, frame in enumerate(ImageSequence.Iterator(Image.open(asset_path))):
            bounds = frame.convert("RGBA").getchannel("A").getbbox()
            if bounds is None or min(bounds[0], bounds[1], 512-bounds[2], 512-bounds[3]) < 16:
                unsafe_frame_bounds.append({
                    "character_id": value["approved_identity_source"],
                    "phrase_id": value["phrase_id"],
                    "frame": frame_index,
                    "bounds": list(bounds) if bounds else None,
                })
    if animated_chunks != 615:
        raise ValueError(f"only {animated_chunks}/615 human assets contain WebP animation chunks")

    by_key = {(str(value["approved_identity_source"]), str(value["phrase_id"])): value for value in humans}
    cell, left, top = 180, 80, 70
    sheet = Image.new("RGBA", (left+cell*len(SAMPLE_PHRASES), top+cell*len(MASTER_IDS)), (238, 243, 248, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 15), "15-character human library — animated phrase sample", fill=(22, 43, 69, 255), font=font(26))
    for column, phrase_id in enumerate(SAMPLE_PHRASES):
        draw.text((left+column*cell+8, 48), phrase_id.removeprefix("chat."), fill=(22, 43, 69, 255), font=font(12))
    cards = []
    for row, master_id in enumerate(MASTER_IDS):
        y = top+row*cell
        draw.text((18, y+cell//2), master_id, fill=(22, 43, 69, 255), font=font(16))
        for column, phrase_id in enumerate(SAMPLE_PHRASES):
            value = by_key[(master_id, phrase_id)]
            x = left+column*cell
            draw.rounded_rectangle((x+5, y+5, x+cell-5, y+cell-5), 16, fill=(255, 255, 255, 255))
            image = Image.open(bundle / value["thumbnail"]["path"]).convert("RGBA")
            image.thumbnail((cell-14, cell-14), Image.Resampling.LANCZOS)
            sheet.alpha_composite(image, (x+(cell-image.width)//2, y+(cell-image.height)//2))
            cards.append(
                f"<article><strong>{html.escape(master_id)} · {html.escape(phrase_id)}</strong>"
                f"<img src='{html.escape((bundle / value['path']).as_uri())}' alt='{html.escape(value['alt_text'])}'></article>"
            )
    contact = output / "15x8-animated-phrase-contact-sheet.png"
    sheet.save(contact)
    small_size_sheets: dict[int, Path] = {}
    for dimension in (80, 96, 100):
        preview_cell = 118
        small = Image.new("RGBA", (left+preview_cell*len(SAMPLE_PHRASES), top+preview_cell*len(MASTER_IDS)), (238, 243, 248, 255))
        small_draw = ImageDraw.Draw(small)
        small_draw.text((16, 15), f"Complete sticker readability at {dimension}px", fill=(22, 43, 69, 255), font=font(24))
        for column, phrase_id in enumerate(SAMPLE_PHRASES):
            small_draw.text((left+column*preview_cell+5, 49), phrase_id.removeprefix("chat."), fill=(22, 43, 69, 255), font=font(10))
        for row, master_id in enumerate(MASTER_IDS):
            y = top+row*preview_cell
            small_draw.text((18, y+preview_cell//2), master_id, fill=(22, 43, 69, 255), font=font(13))
            for column, phrase_id in enumerate(SAMPLE_PHRASES):
                value = by_key[(master_id, phrase_id)]
                x = left+column*preview_cell
                small_draw.rounded_rectangle((x+4, y+4, x+preview_cell-4, y+preview_cell-4), 12, fill=(255, 255, 255, 255))
                image = Image.open(bundle / value["path"]).convert("RGBA").resize((dimension, dimension), Image.Resampling.LANCZOS)
                small.alpha_composite(image, (x+(preview_cell-dimension)//2, y+(preview_cell-dimension)//2))
        path = output / f"caption-readability-{dimension}px.png"
        small.save(path)
        small_size_sheets[dimension] = path
    (output / "animation-review.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Human library animation review</title>"
        "<style>body{font:14px system-ui;background:#eef3f8;color:#162b45;margin:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}article{background:white;padding:10px;border-radius:14px}img{width:100%;aspect-ratio:1;object-fit:contain}</style>"
        "<h1>15-character × 8-phrase animated development review</h1><p>All images below are the real 512px animated WebP assets.</p><div class='grid'>" + "".join(cards) + "</div>",
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "review_status": "local-development-matrix-success",
        "production_use": "forbidden-for-wave2-until-production-gates",
        "identity_count": 15,
        "phrase_count": 41,
        "human_sticker_count": len(humans),
        "animated_human_sticker_count": animated_chunks,
        "all_animation_frames_respect_16px_canvas_margin": not unsafe_frame_bounds,
        "unsafe_frame_bounds": unsafe_frame_bounds,
        "uniform_canvas": "512x512",
        "identity_counts": dict(sorted(counts.items())),
        "selection_policy": dictionary.get("human_selection_policy"),
        "selection_eligibility_field": dictionary.get("human_selection_eligibility_field"),
        "demographic_inference": dictionary.get("demographic_inference"),
        "sample_contact_sheet": {"path": contact.name, "sha256": sha256(contact)},
        "small_size_caption_sheets": {
            str(size): {"path": path.name, "sha256": sha256(path)}
            for size, path in small_size_sheets.items()
        },
        "semantic_metadata_gates": {
            "sorry_is_apology": all(value.get("intent") == "apology" and value.get("pose_implementation") == "gratitude" and "apologetically" in str(value.get("accessible_description", "")) for value in humans if value["phrase_id"] == "chat.sorry"),
            "love_is_general_affection": all(value.get("intent") == "affection" and value.get("audience_class") == "general" and value.get("pose_implementation") == "gratitude" and "affectionately" in str(value.get("accessible_description", "")) for value in humans if value["phrase_id"] == "chat.love"),
        },
        "bundle_catalogue_sha256": sha256(bundle / "catalogue.json"),
        "bundle_dictionary_sha256": sha256(bundle / "dictionary.json"),
    }
    (output / "review.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(f"built 615-human-sticker development review at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
