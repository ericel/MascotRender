#!/usr/bin/env python3
"""Author and render the Calendar Pop typography-first sticker pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
GENERATOR_VERSION = 1
PACK_ID = "calendar-pop-v1"
CANVAS = 512
OUTLINE = "#20324B"


@dataclass(frozen=True)
class Entry:
    semantic_id: str
    label: str
    category: str
    aliases: tuple[str, ...]
    font_voice: str
    motion: str
    effect: str

    @property
    def slug(self) -> str:
        return self.semantic_id.rsplit(".", 1)[-1]


FONT_VOICES = {
    "compact-punch": (
        "punch",
        "fonts/changa-one/ChangaOne-Regular.ttf",
        "fonts/changa-one/OFL.txt",
    ),
    "energetic-comic-slant": (
        "comic-slant",
        "fonts/bangers/Bangers-Regular.ttf",
        "fonts/bangers/OFL.txt",
    ),
    "soft-rounded": (
        "rounded",
        "fonts/lilita-one/LilitaOne-Regular.ttf",
        "fonts/lilita-one/OFL.txt",
    ),
    "handwritten-emphasis": (
        "handwritten",
        "fonts/kalam/Kalam-Bold.ttf",
        "fonts/kalam/OFL.txt",
    ),
}

PALETTES = (
    ("#37C978", "#0D8C75", "#9BF0B5"),
    ("#FF9D42", "#DB4F32", "#FFD36B"),
    ("#5F8DFF", "#6551C9", "#A7D8FF"),
    ("#F15BB5", "#9B45C7", "#FFB7DE"),
    ("#19B9C5", "#176DA8", "#8DEBE8"),
    ("#FFCA3A", "#EF6F33", "#FFF0A6"),
    ("#70D36B", "#148F69", "#CCF6A7"),
    ("#5AB4FF", "#3F67C6", "#B8E4FF"),
    ("#EF6A83", "#A44179", "#FFC0C8"),
    ("#31C48D", "#0E7C66", "#A6F0D5"),
    ("#AF7AF3", "#6154C7", "#E0C7FF"),
    ("#FFB52E", "#EA6334", "#FFE09B"),
    ("#20B7D5", "#2259B4", "#A5F1F4"),
    ("#FF8066", "#D93878", "#FFD0A6"),
    ("#F4A340", "#B04A35", "#FFE093"),
    ("#52B8B2", "#3D5AA8", "#BDEBE3"),
    ("#FF795D", "#963B72", "#FFC5A8"),
    ("#8669E8", "#3E4FA3", "#D9CAFF"),
    ("#5B9DEA", "#3E55A4", "#C9E9FF"),
    ("#56C96F", "#188A65", "#D7F3A2"),
    ("#FFB128", "#E45232", "#FFF098"),
    ("#E57A42", "#A63838", "#F6C36D"),
    ("#64A9F1", "#425DB9", "#D6EEFF"),
)

ROTATIONS = (-4.0, 2.5, -1.5, 3.5, -3.0, 1.5, -2.0)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entries() -> tuple[Entry, ...]:
    matrix = read_json(ROOT / "content" / "calendar-typography-matrix-v1.json")
    return tuple(
        Entry(
            semantic_id=item["id"],
            label=item["label"],
            category=item["category"],
            aliases=tuple(item["aliases"]),
            font_voice=item["font_voice"],
            motion=item["motion"],
            effect=item["effect"],
        )
        for item in matrix["entries"]
    )


def svg(content: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">\n'
        f"{content.rstrip()}\n"
        "</svg>\n"
    )


def sparkle(cx: int, cy: int, radius: int, fill: str, stroke: str = OUTLINE) -> str:
    inner = max(3, radius // 4)
    points = (
        (cx, cy - radius),
        (cx + inner, cy - inner),
        (cx + radius, cy),
        (cx + inner, cy + inner),
        (cx, cy + radius),
        (cx - inner, cy + inner),
        (cx - radius, cy),
        (cx - inner, cy - inner),
    )
    return (
        f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="5" '
        'stroke-linejoin="round"/>'
    )


def accent_svg(entry: Entry, index: int) -> str:
    primary, secondary, highlight = PALETTES[index]
    mode = index % 6
    parts = [
        f'<path d="M105 356 Q256 {376 + (index % 3) * 7} 407 356" '
        f'fill="none" stroke="{secondary}" stroke-width="13" '
        'stroke-linecap="round" opacity="0.32"/>'
    ]
    if mode == 0:
        parts.extend(
            (
                sparkle(84, 185, 23, highlight),
                sparkle(425, 330, 16, primary),
                f'<circle cx="110" cy="333" r="9" fill="{secondary}"/>',
                f'<circle cx="404" cy="174" r="8" fill="{primary}"/>',
            )
        )
    elif mode == 1:
        parts.extend(
            (
                f'<path d="M76 205 l30 -18 M82 229 l36 -5 M436 294 l-30 20 '
                f'M430 268 l-36 7" stroke="{primary}" stroke-width="9" '
                'stroke-linecap="round"/>',
                sparkle(414, 179, 19, highlight),
                f'<circle cx="96" cy="322" r="10" fill="{secondary}"/>',
            )
        )
    elif mode == 2:
        parts.extend(
            (
                f'<circle cx="91" cy="198" r="16" fill="{highlight}" '
                f'stroke="{secondary}" stroke-width="5"/>',
                f'<circle cx="421" cy="187" r="9" fill="{primary}"/>',
                f'<circle cx="429" cy="324" r="18" fill="{highlight}" '
                f'stroke="{secondary}" stroke-width="5"/>',
                sparkle(92, 327, 15, primary),
            )
        )
    elif mode == 3:
        parts.extend(
            (
                f'<path d="M84 180 q32 18 0 36 q-25 16 2 35" fill="none" '
                f'stroke="{primary}" stroke-width="9" stroke-linecap="round"/>',
                f'<path d="M428 277 q-32 18 0 36 q25 16 -2 35" fill="none" '
                f'stroke="{secondary}" stroke-width="9" stroke-linecap="round"/>',
                sparkle(412, 173, 18, highlight),
            )
        )
    elif mode == 4:
        parts.extend(
            (
                f'<path d="M91 188 l18 30 l-34 0 Z" fill="{primary}" '
                f'stroke="{secondary}" stroke-width="5"/>',
                f'<path d="M421 315 l18 30 l-34 0 Z" fill="{highlight}" '
                f'stroke="{secondary}" stroke-width="5"/>',
                f'<circle cx="414" cy="184" r="11" fill="{primary}"/>',
                f'<circle cx="98" cy="327" r="8" fill="{highlight}"/>',
            )
        )
    else:
        parts.extend(
            (
                f'<path d="M70 224 Q95 191 121 224 Q95 257 70 224 Z" '
                f'fill="{highlight}" stroke="{secondary}" stroke-width="5"/>',
                f'<path d="M391 298 Q417 265 442 298 Q417 331 391 298 Z" '
                f'fill="{primary}" stroke="{secondary}" stroke-width="5"/>',
                sparkle(418, 177, 14, highlight),
                sparkle(96, 335, 17, primary),
            )
        )
    return svg("\n".join(parts))


def rgb(value: str) -> dict[str, int]:
    value = value.lstrip("#")
    return {
        "r": int(value[0:2], 16),
        "g": int(value[2:4], 16),
        "b": int(value[4:6], 16),
    }


def text_area(entry: Entry, index: int) -> dict[str, int]:
    top = 136 + (index % 3) * 6
    return {"x": 52, "y": top, "width": 408, "height": 220}


def animation_document(entry: Entry, index: int) -> dict[str, Any]:
    duration = (900, 1000, 1100, 1200)[index % 4]
    middle = duration // 2
    overlay = {
        "pulse": "text_pulse",
        "wobble": "text_wobble",
        "float": "text_float",
    }[entry.motion]
    property_name = {
        "pulse": "scale_x",
        "wobble": "rotation_degrees",
        "float": "translate_y",
    }[entry.motion]
    middle_value = {
        "pulse": 1.035,
        "wobble": 3.0 if index % 2 else -3.0,
        "float": -5.0,
    }[entry.motion]
    return {
        "duration_ms": duration,
        "fps": 12,
        "loop": "loop",
        "overlays": [overlay],
        "tracks": [
            {
                "target": f"accent-{entry.slug}",
                "property": property_name,
                "keyframes": [
                    {"at_ms": 0, "value": 1.0 if property_name == "scale_x" else 0.0, "easing": "ease_in_out"},
                    {"at_ms": middle, "value": middle_value, "easing": "ease_in_out"},
                    {"at_ms": duration, "value": 1.0 if property_name == "scale_x" else 0.0, "easing": "ease_in_out"},
                ],
            }
        ],
    }


def pack_document(items: tuple[Entry, ...]) -> dict[str, Any]:
    layers = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(items):
        layer_id = f"accent-{entry.slug}"
        layers.append(
            {
                "id": layer_id,
                "source": f"layers/{index:02d}-{layer_id}.svg",
                "z": 10 + index,
                "pivot": "word",
                "depth": 0.0,
            }
        )
        expressions[entry.slug] = [layer_id]
        primary, secondary, highlight = PALETTES[index]
        font_id = FONT_VOICES[entry.font_voice][0]
        area = text_area(entry, index)
        styles[f"{entry.slug}-main"] = {
            "font": font_id,
            "safe_area": area,
            "min_font_size": 34,
            "max_font_size": 190,
            "max_lines": 1,
            "fill": rgb(primary),
            "outline": {"width": 8, "color": rgb(OUTLINE)},
            "depth_shell": {
                "offset_x": 10,
                "offset_y": 11,
                "color": rgb(secondary),
            },
            "highlight_shell": {
                "offset_x": -4,
                "offset_y": -4,
                "color": rgb(highlight),
            },
        }
    return {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "canvas": {"width": CANVAS, "height": CANVAS},
        "layers": layers,
        "base_layers": [],
        "expressions": expressions,
        "poses": {"word-art": []},
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT; bundled fonts separately SIL OFL 1.1",
            "source": f"generate_calendar_typography_pack.py v{GENERATOR_VERSION}; original procedural composition",
        },
        "anchors": {"word_center": {"x": 256, "y": 256}},
        "pivots": {"word": {"x": 256, "y": 256}},
        "avoid_regions": [],
        "text_clearance": 0,
        "caption_validation": {
            "minimum_canvas_margin_px": 16,
            "maximum_lines": 1,
            "must_remain_inside_canvas_for_every_frame": True,
            "may_overlap_character": False,
            "may_overlap_assistive_device": False,
            "must_pass_sizes_px": [80, 100, 160],
            "collision_bounds": "per-frame-alpha-bounds",
        },
        "fonts": [
            {"id": font_id, "source": source, "license": license_path}
            for font_id, source, license_path in FONT_VOICES.values()
        ],
        "text_styles": styles,
    }


def sticker_document(entry: Entry, index: int) -> dict[str, Any]:
    rotation = ROTATIONS[index % len(ROTATIONS)]
    return {
        "schema_version": 1,
        "sticker_id": f"calendar-pop-{entry.slug}",
        "pack_id": PACK_ID,
        "phrase_id": entry.semantic_id,
        "recipe_id": f"calendar-typography.{entry.motion}",
        "intent": entry.semantic_id,
        "alt_text": f"Decorative animated {entry.label.title()} word sticker",
        "accessible_description": (
            f"The word {entry.label.title()} in colorful layered display lettering"
        ),
        "expression": entry.slug,
        "pose": "word-art",
        "seed": 1,
        "text": {
            "content": entry.label,
            "style": f"{entry.slug}-main",
            "rotation_degrees": rotation,
        },
        "animation": animation_document(entry, index),
    }


def copy_fonts(pack_root: Path) -> None:
    source_root = ROOT / "content" / "fonts" / "sticker-display-v1"
    for directory in ("changa-one", "bangers", "lilita-one", "kalam"):
        shutil.copytree(source_root / directory, pack_root / "fonts" / directory)


def author_sources(destination: Path) -> None:
    items = entries()
    pack_root = destination / PACK_ID
    copy_fonts(pack_root)
    for index, entry in enumerate(items):
        write_text(
            pack_root / "layers" / f"{index:02d}-accent-{entry.slug}.svg",
            accent_svg(entry, index),
        )
        write_json(
            pack_root / "stickers" / f"{entry.slug}.json",
            sticker_document(entry, index),
        )
    write_json(pack_root / "pack.json", pack_document(items))
    write_json(
        pack_root / "triggers.json",
        {
            "schema_version": 1,
            "pack_id": PACK_ID,
            "selection_structure": "unicode-normalized-casefolded-trie",
            "entries": [
                {
                    "phrase_id": entry.semantic_id,
                    "sticker_id": f"calendar-pop-{entry.slug}",
                    "triggers": [
                        {
                            "text": alias,
                            "locale": "en",
                            "match": "exact-token",
                            "weight": 1.0 if alias == entry.slug else 0.85,
                        }
                        for alias in entry.aliases
                    ],
                }
                for entry in items
            ],
        },
    )
    write_json(
        destination / "generation-manifest.json",
        {
            "schema_version": 1,
            "generator": "generate_calendar_typography_pack.py",
            "generator_version": GENERATOR_VERSION,
            "pack_id": PACK_ID,
            "pack_contract": "contracts/calendar-typography-pack-v1.json",
            "content_matrix": "content/calendar-typography-matrix-v1.json",
            "sticker_count": len(items),
            "category_counts": {
                category: sum(entry.category == category for entry in items)
                for category in ("weekday", "month", "season")
            },
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "single_fitted_glyph_layout_per_sticker": True,
            "independently_scaled_duplicate_text_blocks": 0,
            "owner_approval": "contracts/calendar-typography-owner-approval-v1.json",
            "production_use": "approved-for-public-production",
        },
    )


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}"
        )


def render(
    executable: Path,
    pack: Path,
    sticker: Path,
    output: Path,
    width: int,
    first_frame_only: bool,
) -> None:
    command = [
        str(executable),
        "render",
        "--pack",
        str(pack),
        "--sticker",
        str(sticker),
        "--output",
        str(output),
        "--width",
        str(width),
        "--height",
        str(width),
        "--quality",
        "100",
        "--lossless",
    ]
    if first_frame_only:
        command.append("--first-frame-only")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(command)


def image_frames(path: Path) -> list[Image.Image]:
    frames: list[Image.Image] = []
    with Image.open(path) as image:
        for frame_index in range(getattr(image, "n_frames", 1)):
            image.seek(frame_index)
            frames.append(image.convert("RGBA"))
    return frames


def asset_metrics(path: Path) -> dict[str, Any]:
    frames = image_frames(path)
    hashes = [hashlib.sha256(frame.tobytes()).hexdigest() for frame in frames]
    bounds = [frame.getchannel("A").getbbox() for frame in frames]
    if any(bound is None for bound in bounds):
        raise ValueError(f"transparent frame found: {path}")
    margins = [
        min(
            bound[0],
            bound[1],
            frame.width - bound[2],
            frame.height - bound[3],
        )
        for frame, bound in zip(frames, bounds, strict=True)
        if bound is not None
    ]
    return {
        "frame_count": len(frames),
        "animated_webp": b"ANIM" in path.read_bytes() and b"ANMF" in path.read_bytes(),
        "visible_mid_cycle_change": len(set(hashes)) > 1,
        "loop_closure": hashes[0] == hashes[-1],
        "minimum_frame_margin_px": min(margins),
        "frame_hashes": hashes,
    }


def review_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        str(
            ROOT
            / "content"
            / "fonts"
            / "sticker-display-v1"
            / "lilita-one"
            / "LilitaOne-Regular.ttf"
        ),
        size,
    )


def first_frame(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def build_contact_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns = 5
    cell = 245
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * cell + 40, rows * 270 + 78), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "CALENDAR POP · 23-STICKER ART-DIRECTION REVIEW", fill=OUTLINE, font=review_font(30))
    for index, entry in enumerate(items):
        column = index % columns
        row = index // columns
        x = 20 + column * cell
        y = 68 + row * 270
        draw.rounded_rectangle((x, y, x + 225, y + 248), radius=22, fill="#FFFFFF", outline="#D9E2EC", width=2)
        image = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        image.thumbnail((205, 205), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + (225 - image.width) // 2, y + 8))
        draw.text((x + 12, y + 217), entry.semantic_id, fill="#50657D", font=review_font(12))
    path = review_root / "contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_small_display_sheet(
    review_root: Path, items: tuple[Entry, ...]
) -> Path:
    sizes = (80, 100, 160)
    columns = len(sizes)
    cell_width = 250
    row_height = 176
    canvas = Image.new(
        "RGBA",
        (columns * cell_width + 190, len(items) * row_height + 76),
        "#26384F",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "CONTROLLED WORD READABILITY · 80 / 100 / 160 PX", fill="#FFFFFF", font=review_font(28))
    for column, size in enumerate(sizes):
        draw.text((205 + column * cell_width, 48), f"{size}px", fill="#FFFFFF", font=review_font(18))
    for row, entry in enumerate(items):
        y = 74 + row * row_height
        draw.text((18, y + 72), entry.label, fill="#FFFFFF", font=review_font(16))
        source = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        for column, size in enumerate(sizes):
            left = 175 + column * cell_width
            draw.rounded_rectangle((left, y, left + 226, y + 160), radius=20, fill="#F8FAFC")
            image = source.resize((size, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (left + (226 - size) // 2, y + (160 - size) // 2))
    path = review_root / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_motion_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns = 3
    cell = 190
    canvas = Image.new("RGBA", (columns * cell + 190, len(items) * 188 + 76), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "ANIMATION SAMPLING · START / MID / CLOSURE", fill=OUTLINE, font=review_font(28))
    for column, label in enumerate(("start", "mid", "closure")):
        draw.text((205 + column * cell, 48), label.upper(), fill=OUTLINE, font=review_font(16))
    for row, entry in enumerate(items):
        y = 74 + row * 188
        draw.text((18, y + 78), entry.label, fill=OUTLINE, font=review_font(16))
        frames = image_frames(review_root / "assets" / f"{entry.slug}.webp")
        selected = (frames[0], frames[len(frames) // 2], frames[-1])
        for column, frame in enumerate(selected):
            left = 175 + column * cell
            draw.rounded_rectangle((left, y, left + 174, y + 172), radius=20, fill="#FFFFFF", outline="#D9E2EC", width=2)
            image = frame.resize((160, 160), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (left + 7, y + 6))
    path = review_root / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_animation_html(review_root: Path, items: tuple[Entry, ...]) -> Path:
    figures = "".join(
        f'<figure><img src="assets/{entry.slug}.webp" alt="{entry.label} animated word art">'
        f"<figcaption>{entry.label} · {entry.font_voice} · {entry.motion}</figcaption></figure>"
        for entry in items
    )
    path = review_root / "animation-review.html"
    write_text(
        path,
        "<!doctype html><meta charset=\"utf-8\"><title>Calendar Pop animation review</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#20324b;margin:24px}"
        "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}"
        "figure{margin:0;background:white;border-radius:20px;padding:12px;text-align:center}"
        "img{width:100%;height:auto}figcaption{font-weight:700}</style>"
        "<h1>Calendar Pop · animation playback</h1><p>Review complete words, motion variety, "
        "loop seams, and 16px canvas clearance.</p><main>"
        + figures
        + "</main>",
    )
    return path


def render_review(source_root: Path, review_root: Path, executable: Path) -> None:
    items = entries()
    pack_root = source_root / PACK_ID
    pack = pack_root / "pack.json"
    metrics = []
    for entry in items:
        sticker = pack_root / "stickers" / f"{entry.slug}.json"
        run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
        animated = review_root / "assets" / f"{entry.slug}.webp"
        reduced = review_root / "reduced-motion" / f"{entry.slug}.webp"
        thumbnail = review_root / "thumbnails" / f"{entry.slug}.webp"
        render(executable, pack, sticker, animated, 512, False)
        render(executable, pack, sticker, reduced, 512, True)
        render(executable, pack, sticker, thumbnail, 256, True)
        values = asset_metrics(animated)
        if not values["animated_webp"] or not values["visible_mid_cycle_change"]:
            raise ValueError(f"missing visible animation: {animated}")
        if not values["loop_closure"]:
            raise ValueError(f"animation does not close: {animated}")
        if values["minimum_frame_margin_px"] < 16:
            raise ValueError(
                f"{animated} violates 16px margin: {values['minimum_frame_margin_px']}"
            )
        reduced_bounds = first_frame(reduced).getchannel("A").getbbox()
        if reduced_bounds is None:
            raise ValueError(f"reduced-motion asset is blank: {reduced}")
        values.update(
            {
                "semantic_id": entry.semantic_id,
                "label": entry.label,
                "font_voice": entry.font_voice,
                "motion": entry.motion,
                "animated_sha256": sha256(animated),
                "reduced_motion_sha256": sha256(reduced),
                "thumbnail_sha256": sha256(thumbnail),
            }
        )
        metrics.append(values)
    artifacts = [
        build_contact_sheet(review_root, items),
        build_small_display_sheet(review_root, items),
        build_motion_sheet(review_root, items),
        build_animation_html(review_root, items),
    ]
    artifact_hashes = {path.name: sha256(path) for path in artifacts}
    owner_approval_path = (
        ROOT / "contracts" / "calendar-typography-owner-approval-v1.json"
    )
    owner_approval = read_json(owner_approval_path)
    if owner_approval["decision"] != "approved":
        raise ValueError("Calendar Pop owner decision is not approved")
    if owner_approval["reviewed_artifacts"] != artifact_hashes:
        raise ValueError(
            "Calendar Pop artifacts no longer match the bound owner approval"
        )
    contract = ROOT / "contracts" / "calendar-typography-pack-v1.json"
    matrix = ROOT / "content" / "calendar-typography-matrix-v1.json"
    write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "calendar-pop-development-review-v1",
            "review_status": "owner-approved",
            "production_use": "approved-for-public-production",
            "owner_approval": "contracts/calendar-typography-owner-approval-v1.json",
            "contract_sha256": sha256(contract),
            "matrix_sha256": sha256(matrix),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "sticker_count": len(metrics),
            "category_counts": {
                category: sum(entry.category == category for entry in items)
                for category in ("weekday", "month", "season")
            },
            "animated_sticker_count": sum(bool(item["animated_webp"]) for item in metrics),
            "loop_closed_sticker_count": sum(bool(item["loop_closure"]) for item in metrics),
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "single_layout_shell_sticker_count": len(metrics),
            "independently_scaled_duplicate_text_block_count": 0,
            "minimum_frame_margin_px": min(item["minimum_frame_margin_px"] for item in metrics),
            "artifacts": artifact_hashes,
            "metrics": metrics,
            "owner_review_questions": [],
        },
    )


def replace_directory(staging: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        raise FileExistsError(f"output exists (use --force): {destination}")
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        staging.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-output",
        type=Path,
        default=ROOT / "art" / "calendar-pop-v1",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=ROOT / "generated" / "calendar-pop-v1-review",
    )
    parser.add_argument(
        "--mascotrender",
        type=Path,
        default=ROOT / "build" / "Release" / "mascotrender",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_output = args.source_output.resolve()
    review_output = args.review_output.resolve()
    executable = args.mascotrender.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"MascotRender CLI is missing: {executable}")
    with tempfile.TemporaryDirectory(prefix="calendar-pop-") as directory:
        temporary = Path(directory)
        source_stage = temporary / "source"
        review_stage = temporary / "review"
        author_sources(source_stage)
        render_review(source_stage, review_stage, executable)
        replace_directory(source_stage, source_output, args.force)
        replace_directory(review_stage, review_output, args.force)
    print(source_output)
    print(review_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
