#!/usr/bin/env python3
"""Build visual and numeric review artifacts for the Wahalao font/motion pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
VOICE_PHRASES = (
    ("punch", "facts"),
    ("comic-slant", "chai"),
    ("rounded", "no-wahala"),
    ("handwritten", "hello"),
)
MASTER_IDS = ("h01", "h04", "h07", "h12", "h13")
BACKGROUND = (238, 243, 248, 255)
CARD = (255, 255, 255, 255)
INK = (22, 43, 69, 255)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def sticker_map(bundle: Path) -> dict[str, dict[str, Any]]:
    catalogue = read_json(bundle / "catalogue.json")
    return {str(item["sticker_id"]): item for item in catalogue["stickers"]}


def load_asset(bundle: Path, item: dict[str, Any], frame: int = 0) -> Image.Image:
    source = item.get("thumbnail")
    path = source["path"] if isinstance(source, dict) else item["path"]
    image = Image.open(bundle / str(path))
    image.seek(frame)
    return image.convert("RGBA")


def card_sheet(
    bundle: Path,
    items: list[tuple[str, dict[str, Any]]],
    columns: int,
    title: str,
    cell_size: int = 300,
) -> Image.Image:
    rows = (len(items) + columns - 1) // columns
    header = 72
    sheet = Image.new("RGBA", (columns * cell_size, header + rows * cell_size), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 18), title, fill=INK, font=font(28))
    for index, (label, item) in enumerate(items):
        row, column = divmod(index, columns)
        x = column * cell_size
        y = header + row * cell_size
        draw.rounded_rectangle(
            (x + 8, y + 8, x + cell_size - 8, y + cell_size - 8),
            radius=22,
            fill=CARD,
        )
        asset = load_asset(bundle, item)
        asset.thumbnail((cell_size - 38, cell_size - 62), Image.Resampling.LANCZOS)
        sheet.alpha_composite(asset, (x + (cell_size - asset.width) // 2, y + 34))
        draw.text((x + 18, y + 13), label, fill=INK, font=font(16))
    return sheet


def animation_sheet(bundle: Path, samples: list[tuple[str, dict[str, Any]]]) -> Image.Image:
    cell = 220
    label_width = 190
    columns = 4
    sheet = Image.new(
        "RGBA", (label_width + columns * cell, 70 + len(samples) * cell), BACKGROUND
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((22, 18), "Caption motion sampled frames", fill=INK, font=font(28))
    for row, (label, item) in enumerate(samples):
        source = Image.open(bundle / str(item["path"]))
        frame_count = getattr(source, "n_frames", 1)
        indices = (0, frame_count // 3, (2 * frame_count) // 3, frame_count - 1)
        y = 70 + row * cell
        draw.text((18, y + 82), label, fill=INK, font=font(17))
        for column, frame_index in enumerate(indices):
            source.seek(frame_index)
            frame = source.convert("RGBA")
            frame.thumbnail((cell - 18, cell - 18), Image.Resampling.LANCZOS)
            x = label_width + column * cell
            draw.rounded_rectangle((x + 5, y + 5, x + cell - 5, y + cell - 5), 18, fill=CARD)
            sheet.alpha_composite(frame, (x + (cell - frame.width) // 2, y + (cell - frame.height) // 2))
            draw.text((x + 12, y + 10), f"frame {frame_index}", fill=INK, font=font(13))
    return sheet


def frame_metrics(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    source = Image.open(path)
    frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(source)]
    hashes = [hashlib.sha256(frame.tobytes()).hexdigest() for frame in frames]
    changed = len(set(hashes)) > 1
    return {
        "frame_count": len(frames),
        "animated_webp_chunks": b"ANIM" in raw and b"ANMF" in raw,
        "visible_frame_change": changed,
        "loop_closure_exact": hashes[0] == hashes[-1],
        "alpha_bounds": list(frames[0].getchannel("A").getbbox() or (0, 0, 0, 0)),
    }


def build(bundle: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    stickers = sticker_map(bundle)

    typography_items: list[tuple[str, dict[str, Any]]] = []
    for master in MASTER_IDS:
        for voice, slug in VOICE_PHRASES:
            sticker_id = f"human-canonical-{master}-{slug}"
            typography_items.append((f"{master.upper()} · {voice}", stickers[sticker_id]))
    typography = card_sheet(
        bundle, typography_items, len(VOICE_PHRASES), "Four semantic font voices"
    )
    typography.save(output / "font-voice-sheet.png")

    occupancy_ids = (
        "generated-cat-001-no-stress",
        "human-canonical-h01-no-stress",
        "human-canonical-h04-no-stress",
        "human-canonical-h07-no-stress",
        "human-canonical-h12-no-stress",
        "human-canonical-h13-no-stress",
    )
    occupancy = card_sheet(
        bundle,
        [(sticker_id.replace("human-canonical-", "").replace("-no-stress", ""), stickers[sticker_id]) for sticker_id in occupancy_ids],
        3,
        "Perceived-size parity: classic mascot and full-body humans",
    )
    occupancy.save(output / "occupancy-parity-sheet.png")

    motion_samples = [
        (voice, stickers[f"human-canonical-h01-{slug}"])
        for voice, slug in VOICE_PHRASES
    ]
    animation_sheet(bundle, motion_samples).save(output / "caption-motion-sampled-frames.png")

    metrics = {
        label: frame_metrics(bundle / str(item["path"]))
        for label, item in motion_samples
    }
    catalogue = read_json(bundle / "catalogue.json")
    human = [item for item in catalogue["stickers"] if item.get("font_voice")]
    report = read_json(bundle / "build-report.json")
    summary = {
        "schema_version": 1,
        "review_status": "generated-for-owner-review",
        "bundle_version": catalogue["bundle_version"],
        "bundle_source_sha256": catalogue["source_sha256"],
        "human_sticker_count": len(human),
        "font_voice_counts": dict(sorted(Counter(str(item["font_voice"]) for item in human).items())),
        "caption_motion_counts": dict(sorted(Counter(str(item["caption_motion"]) for item in human).items())),
        "font_manifest_sha256": report["font_manifest_sha256"],
        "animation_samples": metrics,
        "gates": {
            "four_distinct_font_voices": len({item["font_voice"] for item in human}) == 4,
            "four_distinct_caption_motions": len({item["caption_motion"] for item in human}) == 4,
            "all_samples_are_real_animated_webp": all(value["animated_webp_chunks"] for value in metrics.values()),
            "all_samples_visibly_change": all(value["visible_frame_change"] for value in metrics.values()),
            "all_samples_close_exactly": all(value["loop_closure_exact"] for value in metrics.values()),
        },
        "artifacts": {
            name: sha256(output / name)
            for name in (
                "font-voice-sheet.png",
                "occupancy-parity-sheet.png",
                "caption-motion-sampled-frames.png",
            )
        },
    }
    write_json(output / "review.json", summary)
    (output / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>MascotRender typography review</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#162b45;margin:24px}"
        "img{display:block;max-width:100%;margin:16px 0 36px;border-radius:16px}</style>"
        "<h1>MascotRender typography and occupancy review</h1>"
        "<h2>Font voices</h2><img src='font-voice-sheet.png'>"
        "<h2>Human/mascot occupancy</h2><img src='occupancy-parity-sheet.png'>"
        "<h2>Caption motion samples</h2><img src='caption-motion-sampled-frames.png'>",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "generated" / "wahalao-human-dev-bundle")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "wahalao-typography-review")
    args = parser.parse_args()
    build(args.bundle.resolve(), args.output.resolve())
    print(f"built typography review at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
