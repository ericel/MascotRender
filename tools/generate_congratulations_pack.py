#!/usr/bin/env python3
"""Author and render the Congratulations Pop 36-sticker pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from generate_calendar_typography_pack import (
    asset_metrics,
    first_frame,
    image_frames,
    read_json,
    render,
    replace_directory,
    review_font,
    rgb,
    run,
    sha256,
    sparkle,
    svg,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parent.parent
GENERATOR_VERSION = 1
PACK_ID = "congratulations-pop-v1"
CANVAS = 512
INK = "#20324B"


@dataclass(frozen=True)
class Entry:
    semantic_id: str
    label: str
    category: str
    aliases: tuple[str, ...]
    font_voice: str
    motion: str
    effect: str
    layout: str

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
    ("#FF5D73", "#A63A66", "#FFD166"),
    ("#5E8BFF", "#4D4DB7", "#7EE7C4"),
    ("#FF9F43", "#D94F40", "#FFE39A"),
    ("#26C485", "#147D73", "#B7F5CB"),
    ("#A66CFF", "#5E4BB3", "#FFD166"),
    ("#FF6B9A", "#AA3D79", "#8DEBFF"),
    ("#22B8CF", "#2363A5", "#FFE66D"),
    ("#F7B32B", "#D95739", "#FFF0A8"),
    ("#66D17A", "#168C68", "#F5D76E"),
    ("#FF7A59", "#B33F62", "#B7F2E8"),
    ("#7B68EE", "#4B4B9B", "#FFCD70"),
    ("#44B7E8", "#3A5EAE", "#FF8FB1"),
)

ROTATIONS = (-3.0, 2.0, -1.5, 2.5, -2.0, 1.0, 0.0)

LAYOUT_AREAS = {
    "top-icon": {"x": 44, "y": 210, "width": 424, "height": 224},
    "side-icon": {"x": 164, "y": 126, "width": 304, "height": 270},
    "bottom-ribbon": {"x": 48, "y": 84, "width": 416, "height": 246},
    "badge": {"x": 64, "y": 142, "width": 384, "height": 238},
    "full-burst": {"x": 70, "y": 142, "width": 372, "height": 232},
    "corner-icon": {"x": 48, "y": 112, "width": 400, "height": 258},
}


def entries() -> tuple[Entry, ...]:
    matrix = read_json(
        ROOT / "content" / "congratulations-typography-matrix-v1.json"
    )
    return tuple(
        Entry(
            semantic_id=item["id"],
            label=item["label"],
            category=item["category"],
            aliases=tuple(item["aliases"]),
            font_voice=item["font_voice"],
            motion=item["motion"],
            effect=item["effect"],
            layout=item["layout"],
        )
        for item in matrix["entries"]
    )


def star_points(cx: float, cy: float, outer: float, inner: float) -> str:
    points = []
    for index in range(10):
        angle = math.radians(-90 + index * 36)
        radius = outer if index % 2 == 0 else inner
        points.append(
            f"{cx + math.cos(angle) * radius:.1f},"
            f"{cy + math.sin(angle) * radius:.1f}"
        )
    return " ".join(points)


def confetti(primary: str, secondary: str, highlight: str, index: int) -> str:
    colors = (primary, secondary, highlight)
    parts = []
    positions = (
        (76, 103, 18, 8, -20),
        (119, 78, 9, 20, 28),
        (397, 89, 18, 8, 18),
        (430, 136, 9, 20, -28),
        (82, 404, 18, 8, 16),
        (427, 398, 18, 8, -18),
    )
    for offset, (x, y, width, height, rotation) in enumerate(positions):
        color = colors[(index + offset) % len(colors)]
        parts.append(
            f'<rect x="{x - width / 2:.1f}" y="{y - height / 2:.1f}" '
            f'width="{width}" height="{height}" rx="3" fill="{color}" '
            f'transform="rotate({rotation} {x} {y})"/>'
        )
    parts.extend(
        (
            sparkle(72, 154, 12, highlight, secondary),
            sparkle(435, 352, 12, primary, secondary),
            f'<circle cx="94" cy="371" r="7" fill="{primary}"/>',
            f'<circle cx="414" cy="151" r="7" fill="{highlight}"/>',
        )
    )
    return "".join(parts)


def ambient_accents(
    primary: str,
    secondary: str,
    highlight: str,
    index: int,
) -> str:
    mode = index % 4
    if mode == 0:
        return confetti(primary, secondary, highlight, index)
    if mode == 1:
        return (
            f'<path d="M68 118 q34 -29 58 4 M77 151 q30 -18 49 8 '
            f'M444 342 q-34 29 -58 -4 M435 309 q-30 18 -49 -8" '
            f'fill="none" stroke="{primary}" stroke-width="9" '
            'stroke-linecap="round"/>'
            f'{sparkle(90, 352, 13, highlight, secondary)}'
            f'{sparkle(419, 147, 12, secondary, primary)}'
            f'<circle cx="121" cy="78" r="7" fill="{highlight}"/>'
            f'<circle cx="397" cy="416" r="7" fill="{primary}"/>'
        )
    if mode == 2:
        return (
            f'<circle cx="79" cy="118" r="10" fill="{primary}"/>'
            f'<circle cx="105" cy="91" r="6" fill="{highlight}"/>'
            f'<circle cx="432" cy="375" r="10" fill="{secondary}"/>'
            f'<circle cx="405" cy="404" r="6" fill="{highlight}"/>'
            f'<path d="M69 366 l22 -34 l20 34 Z M401 107 l21 34 l21 -34 Z" '
            f'fill="{highlight}" stroke="{secondary}" stroke-width="5" '
            'stroke-linejoin="round"/>'
            f'{sparkle(422, 185, 11, primary, secondary)}'
        )
    return (
        f'<path d="M72 188 H112 M82 156 L111 177 M82 220 L111 199 '
        f'M400 312 H440 M401 323 L430 344 M401 301 L430 280" '
        f'fill="none" stroke="{primary}" stroke-width="9" '
        'stroke-linecap="round"/>'
        f'<path d="M104 91 l14 24 l-27 0 Z M408 396 l14 24 l-27 0 Z" '
        f'fill="{highlight}" stroke="{secondary}" stroke-width="5" '
        'stroke-linejoin="round"/>'
        f'<circle cx="421" cy="103" r="8" fill="{secondary}"/>'
        f'<circle cx="91" cy="409" r="8" fill="{primary}"/>'
    )


def grounding_accent(
    primary: str,
    secondary: str,
    highlight: str,
    index: int,
) -> str:
    mode = index % 4
    if mode == 0:
        return (
            '<path d="M89 438 Q256 461 423 438" fill="none" '
            f'stroke="{secondary}" stroke-width="13" stroke-linecap="round" '
            'opacity=".22"/>'
        )
    if mode == 1:
        return (
            f'<path d="M132 436 Q202 450 250 439 M273 439 Q330 449 381 432" '
            f'fill="none" stroke="{primary}" stroke-width="10" '
            'stroke-linecap="round" opacity=".26"/>'
        )
    if mode == 2:
        return (
            f'<circle cx="224" cy="439" r="7" fill="{secondary}" opacity=".32"/>'
            f'<circle cx="256" cy="443" r="10" fill="{primary}" opacity=".28"/>'
            f'<circle cx="291" cy="438" r="6" fill="{highlight}" opacity=".48"/>'
        )
    return (
        f'<path d="M177 439 H335" fill="none" stroke="{secondary}" '
        'stroke-width="9" stroke-linecap="round" opacity=".22"/>'
    )


def icon_group(
    body: str,
    layout: str,
    *,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
) -> str:
    positions = {
        "top-icon": (256, 106, 0.72),
        "side-icon": (122, 250, 0.60),
        "bottom-ribbon": (256, 391, 0.70),
        "badge": (376, 106, 0.55),
        "full-burst": (256, 92, 0.52),
        "corner-icon": (408, 395, 0.48),
    }
    x, y, base_scale = positions[layout]
    return (
        f'<g transform="translate({x + offset_x} {y + offset_y}) '
        f'scale({base_scale * scale:.3f})">{body}</g>'
    )


def motif_body(
    effect: str,
    primary: str,
    secondary: str,
    highlight: str,
) -> str:
    stroke = f'stroke="{INK}" stroke-width="8" stroke-linejoin="round"'
    rounded = f'{stroke} stroke-linecap="round"'
    if effect == "trophy":
        return (
            f'<path d="M-56 -56 H56 V-16 Q50 48 0 54 Q-50 48 -56 -16 Z" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M-56 -34 Q-104 -42 -92 8 Q-80 38 -48 24 '
            f'M56 -34 Q104 -42 92 8 Q80 38 48 24" fill="none" {rounded}/>'
            f'<path d="M0 54 V84 M-42 98 H42" fill="none" stroke="{secondary}" '
            'stroke-width="18" stroke-linecap="round"/>'
            f'<polygon points="{star_points(0, -8, 27, 12)}" fill="{primary}"/>'
        )
    if effect == "diploma":
        return (
            f'<g transform="rotate(-8)"><rect x="-82" y="-42" width="164" '
            f'height="84" rx="24" fill="#FFF9E8" {stroke}/>'
            f'<path d="M-55 -12 H48 M-55 10 H34" fill="none" '
            f'stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
            f'<circle cx="70" cy="0" r="24" fill="{primary}" {stroke}/>'
            f'<path d="M59 18 L50 67 L72 53 L91 69 L82 18" '
            f'fill="{highlight}" {stroke}/></g>'
        )
    if effect == "check-badge":
        return (
            f'<circle cx="0" cy="0" r="74" fill="{highlight}" {stroke}/>'
            f'<circle cx="0" cy="0" r="53" fill="{primary}" opacity=".20"/>'
            f'<path d="M-38 1 L-10 31 L44 -31" fill="none" stroke="{secondary}" '
            'stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if effect == "finish-flag":
        return (
            f'<path d="M-72 -66 V80" fill="none" {rounded}/>'
            f'<path d="M-64 -58 Q8 -88 70 -54 V18 Q6 -14 -64 16 Z" '
            f'fill="{primary}" {stroke}/>'
            f'<path d="M-58 -54 L-10 -68 V-15 L-58 0 Z M-10 -68 L38 -64 '
            f'V-8 L-10 -15 Z M38 -64 L65 -55 V5 L38 -8 Z" '
            f'fill="{highlight}" opacity=".9"/>'
        )
    if effect in {"star-medal", "star-ribbon"}:
        return (
            f'<path d="M-48 35 L-74 94 L-24 78 L0 112 L23 78 L75 94 '
            f'L48 35" fill="{secondary}" {stroke}/>'
            f'<circle cx="0" cy="0" r="70" fill="{highlight}" {stroke}/>'
            f'<polygon points="{star_points(0, 0, 46, 21)}" '
            f'fill="{primary}" {stroke}/>'
        )
    if effect == "applause":
        return (
            f'<g transform="rotate(-18 -30 0)"><rect x="-75" y="-62" '
            f'width="62" height="132" rx="28" fill="{highlight}" {stroke}/>'
            f'<path d="M-62 -58 V-102 M-45 -59 V-116 M-28 -58 V-105" '
            f'fill="none" stroke="{highlight}" stroke-width="19" '
            'stroke-linecap="round"/></g>'
            f'<g transform="rotate(18 30 0)"><rect x="13" y="-62" '
            f'width="62" height="132" rx="28" fill="{primary}" {stroke}/>'
            f'<path d="M28 -58 V-105 M45 -59 V-116 M62 -58 V-102" '
            f'fill="none" stroke="{primary}" stroke-width="19" '
            'stroke-linecap="round"/></g>'
        )
    if effect == "target":
        return (
            f'<circle cx="0" cy="0" r="76" fill="#FFF9E8" {stroke}/>'
            f'<circle cx="0" cy="0" r="52" fill="{primary}"/>'
            f'<circle cx="0" cy="0" r="26" fill="{highlight}"/>'
            f'<path d="M-88 82 L32 -22 M22 -44 L45 -31 L39 -7" '
            f'fill="none" stroke="{secondary}" stroke-width="13" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if effect == "crown":
        return (
            f'<path d="M-88 -44 L-52 18 L-18 -48 L15 18 L54 -48 '
            f'L88 -42 L70 70 H-70 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-64 42 H65" fill="none" stroke="{primary}" '
            'stroke-width="13" stroke-linecap="round"/>'
            f'<circle cx="-18" cy="15" r="10" fill="{secondary}"/>'
            f'<circle cx="18" cy="15" r="10" fill="{primary}"/>'
        )
    if effect == "megaphone":
        return (
            f'<path d="M-86 -33 H-38 L61 -76 V72 L-38 32 H-86 Z" '
            f'fill="{primary}" {stroke}/>'
            f'<path d="M-44 35 L-21 91 H18 L5 52" fill="{highlight}" {stroke}/>'
            f'<path d="M84 -49 L108 -71 M89 0 H124 M84 49 L108 71" '
            f'fill="none" stroke="{secondary}" stroke-width="12" '
            'stroke-linecap="round"/>'
        )
    if effect == "heart-laurel":
        return (
            f'<path d="M0 67 C-92 10 -72 -65 -18 -48 C-3 -43 0 -25 '
            f'0 -25 C0 -25 5 -46 27 -49 C82 -56 94 17 0 67 Z" '
            f'fill="{primary}" {stroke}/>'
            f'<path d="M-42 74 Q-96 26 -80 -42 M42 74 Q96 26 80 -42" '
            f'fill="none" stroke="{secondary}" stroke-width="11" '
            'stroke-linecap="round"/>'
            f'<path d="M-73 22 l-27 -8 M-67 -6 l-26 -16 M73 22 l27 -8 '
            f'M67 -6 l26 -16" fill="none" stroke="{highlight}" '
            'stroke-width="13" stroke-linecap="round"/>'
        )
    if effect == "laurel-medal":
        return (
            f'<circle cx="0" cy="0" r="64" fill="{highlight}" {stroke}/>'
            f'<polygon points="{star_points(0, 0, 38, 17)}" fill="{primary}"/>'
            f'<path d="M-56 68 Q-105 18 -83 -56 M56 68 Q105 18 83 -56" '
            f'fill="none" stroke="{secondary}" stroke-width="12" '
            'stroke-linecap="round"/>'
        )
    if effect == "pencil-spark":
        return (
            f'<g transform="rotate(-35)"><rect x="-72" y="-24" width="144" '
            f'height="48" rx="12" fill="{primary}" {stroke}/>'
            f'<path d="M72 -24 L112 0 L72 24 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-72 -24 H-105 V24 H-72" fill="{secondary}" {stroke}/>'
            f'</g>{sparkle(69, -64, 24, highlight, INK)}'
        )
    if effect == "rocket":
        return (
            f'<path d="M-20 62 Q-72 30 -67 -11 Q-59 -72 0 -106 '
            f'Q59 -72 67 -11 Q72 30 20 62 Z" fill="{highlight}" {stroke}/>'
            f'<circle cx="0" cy="-35" r="24" fill="{primary}" {stroke}/>'
            f'<path d="M-35 35 L-74 72 L-28 65 M35 35 L74 72 L28 65" '
            f'fill="{secondary}" {stroke}/>'
            f'<path d="M-21 64 Q0 122 22 64 Q0 86 -21 64 Z" '
            f'fill="{primary}" {stroke}/>'
        )
    if effect == "diamond-burst":
        return (
            f'<path d="M-88 -20 L-48 -72 H52 L91 -20 L0 88 Z" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M-48 -72 L0 88 L52 -72 M-88 -20 H91 '
            f'M-48 -72 L-7 -20 L52 -72" fill="none" '
            f'stroke="{primary}" stroke-width="9" stroke-linejoin="round"/>'
            f'<path d="M-112 -75 L-133 -98 M111 -74 L132 -97 M0 -103 V-134" '
            f'fill="none" stroke="{secondary}" stroke-width="12" '
            'stroke-linecap="round"/>'
        )
    if effect == "podium":
        return (
            f'<rect x="-34" y="-80" width="68" height="158" rx="12" '
            f'fill="{highlight}" {stroke}/>'
            f'<rect x="-105" y="-20" width="70" height="98" rx="12" '
            f'fill="{primary}" {stroke}/>'
            f'<rect x="35" y="13" width="70" height="65" rx="12" '
            f'fill="{secondary}" {stroke}/>'
            f'<polygon points="{star_points(0, -34, 26, 12)}" '
            f'fill="{primary}"/>'
        )
    if effect == "graduation-cap":
        return (
            f'<path d="M-104 -28 L0 -79 L104 -28 L0 24 Z" '
            f'fill="{primary}" {stroke}/>'
            f'<path d="M-66 1 V56 Q0 93 66 56 V1" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M82 -17 V57" fill="none" {rounded}/>'
            f'<circle cx="82" cy="70" r="13" fill="{secondary}" {stroke}/>'
        )
    if effect == "wedding-rings":
        return (
            f'<circle cx="-35" cy="9" r="61" fill="none" '
            f'stroke="{highlight}" stroke-width="20"/>'
            f'<circle cx="37" cy="9" r="61" fill="none" '
            f'stroke="{primary}" stroke-width="20"/>'
            f'<path d="M0 -75 C-34 -112 -81 -62 0 -7 '
            f'C81 -62 34 -112 0 -75 Z" fill="{secondary}" {stroke}/>'
        )
    if effect == "briefcase-up":
        return (
            f'<rect x="-91" y="-43" width="182" height="116" rx="22" '
            f'fill="{primary}" {stroke}/>'
            f'<path d="M-38 -43 V-72 H38 V-43 M-91 6 H91" '
            f'fill="none" {rounded}/>'
            f'<path d="M0 51 V-20 M-28 7 L0 -21 L28 7" fill="none" '
            f'stroke="{highlight}" stroke-width="15" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
        )
    if effect == "up-arrow-medal":
        return (
            f'<circle cx="0" cy="15" r="67" fill="{highlight}" {stroke}/>'
            f'<path d="M0 51 V-33 M-34 -2 L0 -36 L34 -2" fill="none" '
            f'stroke="{primary}" stroke-width="17" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
            f'<path d="M-42 76 L-66 112 L-15 98 M42 76 L66 112 L15 98" '
            f'fill="{secondary}" {stroke}/>'
        )
    if effect == "happy-house":
        return (
            f'<path d="M-99 -17 L0 -93 L99 -17 V88 H-99 Z" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M-118 -7 L0 -105 L118 -7" fill="none" '
            f'stroke="{primary}" stroke-width="19" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
            f'<rect x="-21" y="24" width="42" height="64" rx="10" '
            f'fill="{secondary}" {stroke}/>'
            f'<path d="M-47 2 Q-24 -18 0 2 Q24 -18 47 2" '
            f'fill="none" stroke="{primary}" stroke-width="10" '
            'stroke-linecap="round"/>'
        )
    if effect == "baby-blocks":
        return (
            f'<rect x="-102" y="-8" width="76" height="76" rx="15" '
            f'fill="{primary}" {stroke}/>'
            f'<rect x="-37" y="-73" width="76" height="76" rx="15" '
            f'fill="{highlight}" {stroke}/>'
            f'<rect x="28" y="-8" width="76" height="76" rx="15" '
            f'fill="{secondary}" {stroke}/>'
            f'<circle cx="-64" cy="30" r="14" fill="#FFF9E8"/>'
            f'<polygon points="{star_points(1, -35, 18, 8)}" fill="{primary}"/>'
            f'<path d="M50 31 Q66 16 83 31" fill="none" stroke="#FFF9E8" '
            'stroke-width="10" stroke-linecap="round"/>'
        )
    if effect == "shooting-star":
        return (
            f'<polygon points="{star_points(45, -22, 58, 25)}" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M-106 55 Q-39 -13 10 -25 M-91 87 Q-29 27 17 8" '
            f'fill="none" stroke="{primary}" stroke-width="16" '
            'stroke-linecap="round"/>'
        )
    if effect == "party-popper":
        return (
            f'<path d="M-72 79 L-26 -40 L57 43 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-56 36 L-7 58 M-42 -3 L25 30" fill="none" '
            f'stroke="{highlight}" stroke-width="13"/>'
            f'<path d="M-14 -73 Q-41 -103 -13 -124 M22 -67 Q65 -95 70 -56 '
            f'M57 -30 Q99 -27 105 7" fill="none" stroke="{secondary}" '
            'stroke-width="11" stroke-linecap="round"/>'
            f'<circle cx="-14" cy="-74" r="10" fill="{highlight}"/>'
            f'<circle cx="57" cy="-42" r="11" fill="{primary}"/>'
        )
    if effect == "toast":
        return (
            f'<path d="M-82 -67 H-14 L-24 22 Q-28 53 -49 53 '
            f'Q-70 53 -74 22 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M14 -67 H82 L74 22 Q70 53 49 53 '
            f'Q28 53 24 22 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-49 53 V89 M49 53 V89 M-78 92 H-20 M20 92 H78" '
            f'fill="none" {rounded}/>'
            f'<path d="M-14 -20 L14 -4" fill="none" stroke="{secondary}" '
            'stroke-width="10" stroke-linecap="round"/>'
        )
    if effect == "pennant":
        return (
            f'<path d="M-88 -75 V93" fill="none" {rounded}/>'
            f'<path d="M-80 -66 H96 L51 0 L96 66 H-80 Z" '
            f'fill="{primary}" {stroke}/>'
            f'<polygon points="{star_points(7, 0, 36, 16)}" '
            f'fill="{highlight}"/>'
        )
    if effect == "cloud-stars":
        return (
            f'<path d="M-92 42 Q-119 -4 -74 -25 Q-65 -81 -10 -68 '
            f'Q31 -102 65 -60 Q111 -53 107 -7 Q126 31 86 53 H-72 '
            f'Q-86 53 -92 42 Z" fill="{highlight}" {stroke}/>'
            f'{sparkle(-70, -77, 18, primary, INK)}'
            f'{sparkle(85, -70, 14, secondary, INK)}'
        )
    if effect == "mountain-flag":
        return (
            f'<path d="M-118 84 L-42 -51 L-2 2 L42 -83 L118 84 Z" '
            f'fill="{highlight}" {stroke}/>'
            f'<path d="M-42 -51 L-14 -7 L8 -35 M42 -83 L68 -37 L82 -54" '
            f'fill="none" stroke="#FFF9E8" stroke-width="13" '
            'stroke-linecap="round"/>'
            f'<path d="M42 -83 V-112 M48 -107 H116 L91 -84 L116 -61 H48" '
            f'fill="{primary}" {stroke}/>'
        )
    if effect == "sun-rays":
        rays = "".join(
            f'<path d="M{math.cos(math.radians(angle)) * 88:.1f} '
            f'{math.sin(math.radians(angle)) * 88:.1f} L'
            f'{math.cos(math.radians(angle)) * 124:.1f} '
            f'{math.sin(math.radians(angle)) * 124:.1f}" '
            f'stroke="{secondary}" stroke-width="12" stroke-linecap="round"/>'
            for angle in range(0, 360, 45)
        )
        return (
            rays
            + f'<circle cx="0" cy="0" r="69" fill="{highlight}" {stroke}/>'
            + f'<polygon points="{star_points(0, 0, 42, 20)}" '
            f'fill="{primary}"/>'
        )
    return (
        f'<circle cx="0" cy="0" r="72" fill="{highlight}" {stroke}/>'
        f'<polygon points="{star_points(0, 0, 45, 20)}" '
        f'fill="{primary}"/>'
    )


def motif_svg(entry: Entry, index: int) -> str:
    primary, secondary, highlight = PALETTES[index % len(PALETTES)]
    body = motif_body(entry.effect, primary, secondary, highlight)
    parts = [
        grounding_accent(primary, secondary, highlight, index),
        ambient_accents(primary, secondary, highlight, index),
        icon_group(body, entry.layout),
    ]
    if entry.layout == "full-burst":
        parts.append(
            f'<path d="M124 248 H61 M388 248 H451 M148 165 L105 122 '
            f'M364 165 L407 122 M148 334 L105 377 M364 334 L407 377" '
            f'fill="none" stroke="{primary}" stroke-width="9" '
            'stroke-linecap="round" opacity=".55"/>'
        )
    elif entry.layout == "bottom-ribbon":
        parts.append(
            f'<path d="M118 386 Q256 430 394 386 L375 438 '
            f'Q256 405 137 438 Z" fill="{highlight}" '
            f'stroke="{secondary}" stroke-width="7" stroke-linejoin="round"/>'
        )
    return svg("\n".join(parts))


def text_area(entry: Entry) -> dict[str, int]:
    area = dict(LAYOUT_AREAS[entry.layout])
    if entry.motion == "pop":
        # The engine's loop-safe pop overlay reaches 1.15x. Fit the resting
        # glyph layout inside an inset area so the overshoot remains in-bounds.
        area["x"] += 32
        area["width"] -= 64
        area["y"] += 20
        area["height"] -= 40
    return area


def animation_document(entry: Entry, index: int) -> dict[str, Any]:
    duration = (900, 1000, 1100, 1200)[index % 4]
    middle = duration // 2
    overlay = {
        "pop": "text_pop",
        "pulse": "text_pulse",
        "wobble": "text_wobble",
        "float": "text_float",
    }[entry.motion]
    property_name = {
        "pop": "scale_x",
        "pulse": "scale_y",
        "wobble": "rotation_degrees",
        "float": "translate_y",
    }[entry.motion]
    rest = 1.0 if property_name.startswith("scale_") else 0.0
    middle_value = {
        "pop": 1.065,
        "pulse": 1.035,
        "wobble": 3.0 if index % 2 else -3.0,
        "float": -6.0,
    }[entry.motion]
    return {
        "duration_ms": duration,
        "fps": 12,
        "loop": "loop",
        "overlays": [overlay],
        "tracks": [
            {
                "target": f"motif-{entry.slug}",
                "property": property_name,
                "keyframes": [
                    {"at_ms": 0, "value": rest, "easing": "ease_in_out"},
                    {
                        "at_ms": middle,
                        "value": middle_value,
                        "easing": "ease_in_out",
                    },
                    {
                        "at_ms": duration,
                        "value": rest,
                        "easing": "ease_in_out",
                    },
                ],
            }
        ],
    }


def pack_document(items: tuple[Entry, ...]) -> dict[str, Any]:
    layers = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(items):
        layer_id = f"motif-{entry.slug}"
        layers.append(
            {
                "id": layer_id,
                "source": f"layers/{index:02d}-{layer_id}.svg",
                "z": 10 + index,
                "pivot": "composition",
                "depth": 0.0,
            }
        )
        expressions[entry.slug] = [layer_id]
        primary, secondary, highlight = PALETTES[index % len(PALETTES)]
        font_id = FONT_VOICES[entry.font_voice][0]
        outline_width = (6, 7, 8, 7)[index % 4]
        styles[f"{entry.slug}-main"] = {
            "font": font_id,
            "safe_area": text_area(entry),
            "min_font_size": 27,
            "max_font_size": 190,
            "max_lines": 2,
            "fill": rgb(primary),
            "outline": {"width": outline_width, "color": rgb(INK)},
            "depth_shell": {
                "offset_x": 8 + index % 3,
                "offset_y": 9 + index % 3,
                "color": rgb(secondary),
            },
            "highlight_shell": {
                "offset_x": -3,
                "offset_y": -3,
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
        "poses": {"celebration": []},
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT; bundled fonts separately SIL OFL 1.1",
            "source": (
                f"generate_congratulations_pack.py v{GENERATOR_VERSION}; "
                "original procedural compositions"
            ),
        },
        "anchors": {"composition_center": {"x": 256, "y": 256}},
        "pivots": {"composition": {"x": 256, "y": 256}},
        "avoid_regions": [],
        "text_clearance": 0,
        "caption_validation": {
            "minimum_canvas_margin_px": 16,
            "maximum_lines": 2,
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
    return {
        "schema_version": 1,
        "sticker_id": f"congratulations-pop-{entry.slug}",
        "pack_id": PACK_ID,
        "phrase_id": entry.semantic_id,
        "recipe_id": f"congratulations-typography.{entry.motion}",
        "intent": entry.semantic_id,
        "alt_text": f"Decorative animated sticker saying {entry.label}",
        "accessible_description": (
            f"The phrase {entry.label} with an original {entry.effect.replace('-', ' ')} "
            "celebration motif"
        ),
        "expression": entry.slug,
        "pose": "celebration",
        "seed": 1,
        "text": {
            "content": entry.label,
            "style": f"{entry.slug}-main",
            "rotation_degrees": ROTATIONS[index % len(ROTATIONS)],
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
            pack_root / "layers" / f"{index:02d}-motif-{entry.slug}.svg",
            motif_svg(entry, index),
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
                    "sticker_id": f"congratulations-pop-{entry.slug}",
                    "triggers": [
                        {
                            "text": alias,
                            "locale": "en",
                            "match": "exact-phrase",
                            "weight": 1.0 if alias == entry.label.lower().rstrip("!")
                            else 0.85,
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
            "generator": "generate_congratulations_pack.py",
            "generator_version": GENERATOR_VERSION,
            "pack_id": PACK_ID,
            "pack_contract": "contracts/congratulations-typography-pack-v1.json",
            "content_matrix": (
                "content/congratulations-typography-matrix-v1.json"
            ),
            "sticker_count": len(items),
            "category_counts": {
                category: sum(entry.category == category for entry in items)
                for category in ("core", "achievement", "milestone", "cheer")
            },
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "composition_system_count": len({entry.layout for entry in items}),
            "motif_family_count": len({entry.effect for entry in items}),
            "single_fitted_glyph_layout_per_sticker": True,
            "independently_typeset_duplicate_text_blocks": 0,
            "owner_approval": (
                "contracts/congratulations-typography-owner-approval-v1.json"
            ),
            "production_use": "approved-for-public-production",
        },
    )


def build_contact_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns = 6
    cell_width = 232
    cell_height = 252
    rows = math.ceil(len(items) / columns)
    canvas = Image.new(
        "RGBA",
        (columns * cell_width + 40, rows * cell_height + 82),
        "#EEF3F8",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 18),
        "CONGRATULATIONS POP · 36-STICKER ART-DIRECTION REVIEW",
        fill=INK,
        font=review_font(30),
    )
    for index, entry in enumerate(items):
        column = index % columns
        row = index // columns
        x = 20 + column * cell_width
        y = 70 + row * cell_height
        draw.rounded_rectangle(
            (x, y, x + 214, y + 232),
            radius=22,
            fill="#FFFFFF",
            outline="#D9E2EC",
            width=2,
        )
        image = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        image.thumbnail((198, 198), Image.Resampling.LANCZOS)
        canvas.alpha_composite(
            image,
            (x + (214 - image.width) // 2, y + 4),
        )
        draw.text(
            (x + 10, y + 203),
            entry.label,
            fill=INK,
            font=review_font(14),
        )
        draw.text(
            (x + 10, y + 219),
            f"{entry.category} · {entry.motion}",
            fill="#65758B",
            font=review_font(10),
        )
    path = review_root / "contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_small_display_sheet(
    review_root: Path,
    items: tuple[Entry, ...],
) -> Path:
    sizes = (80, 100, 160)
    columns = 6
    rows = 6
    cell_width = 200
    cell_height = 218
    panel_width = columns * cell_width + 24
    canvas = Image.new(
        "RGBA",
        (len(sizes) * panel_width + 24, rows * cell_height + 100),
        "#26384F",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 18),
        "ALL 36 PHRASES · CONTROLLED READABILITY AT 80 / 100 / 160 PX",
        fill="#FFFFFF",
        font=review_font(30),
    )
    for panel, size in enumerate(sizes):
        panel_x = 12 + panel * panel_width
        draw.text(
            (panel_x + 12, 58),
            f"{size}px" + (" · RECOMMENDED DEFAULT" if size == 100 else ""),
            fill="#FFFFFF",
            font=review_font(18),
        )
        for index, entry in enumerate(items):
            column = index % columns
            row = index // columns
            x = panel_x + column * cell_width
            y = 88 + row * cell_height
            draw.rounded_rectangle(
                (x + 4, y, x + cell_width - 6, y + 200),
                radius=18,
                fill="#F8FAFC",
            )
            source = first_frame(
                review_root / "reduced-motion" / f"{entry.slug}.webp"
            )
            image = source.resize((size, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(
                image,
                (
                    x + (cell_width - size) // 2,
                    y + 8 + (164 - size) // 2,
                ),
            )
            label = entry.label if len(entry.label) <= 18 else entry.label[:17] + "…"
            draw.text(
                (x + 12, y + 174),
                label,
                fill=INK,
                font=review_font(12),
            )
    path = review_root / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_motion_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns = 4
    cell_width = 300
    cell_height = 194
    rows = math.ceil(len(items) / columns)
    canvas = Image.new(
        "RGBA",
        (columns * cell_width + 40, rows * cell_height + 88),
        "#EEF3F8",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 18),
        "ALL 36 LOOPS · START / MID / CLOSURE",
        fill=INK,
        font=review_font(30),
    )
    draw.text(
        (24, 52),
        "Each cell must visibly change at mid-cycle and return exactly.",
        fill="#65758B",
        font=review_font(15),
    )
    for index, entry in enumerate(items):
        column = index % columns
        row = index // columns
        x = 20 + column * cell_width
        y = 78 + row * cell_height
        draw.rounded_rectangle(
            (x, y, x + 282, y + 178),
            radius=20,
            fill="#FFFFFF",
            outline="#D9E2EC",
            width=2,
        )
        frames = image_frames(review_root / "assets" / f"{entry.slug}.webp")
        selected = (frames[0], frames[len(frames) // 2], frames[-1])
        for frame_index, frame in enumerate(selected):
            image = frame.resize((82, 82), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + 9 + frame_index * 90, y + 8))
        draw.text(
            (x + 12, y + 99),
            entry.label,
            fill=INK,
            font=review_font(14),
        )
        draw.text(
            (x + 12, y + 121),
            f"{entry.motion} · {entry.effect}",
            fill="#65758B",
            font=review_font(11),
        )
        draw.text(
            (x + 12, y + 145),
            "START",
            fill="#7A8798",
            font=review_font(9),
        )
        draw.text(
            (x + 102, y + 145),
            "MID",
            fill="#7A8798",
            font=review_font(9),
        )
        draw.text(
            (x + 192, y + 145),
            "CLOSURE",
            fill="#7A8798",
            font=review_font(9),
        )
    path = review_root / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_animation_html(review_root: Path, items: tuple[Entry, ...]) -> Path:
    figures = "".join(
        f'<figure><img src="assets/{entry.slug}.webp" '
        f'alt="{entry.label} animated celebration sticker">'
        f"<figcaption>{entry.label}<small>{entry.font_voice} · "
        f"{entry.layout} · {entry.motion}</small></figcaption></figure>"
        for entry in items
    )
    path = review_root / "animation-review.html"
    write_text(
        path,
        "<!doctype html><meta charset=\"utf-8\">"
        "<title>Congratulations Pop animation review</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#20324b;"
        "margin:24px}main{display:grid;grid-template-columns:"
        "repeat(auto-fill,minmax(220px,1fr));gap:16px}"
        "figure{margin:0;background:white;border-radius:20px;padding:12px;"
        "text-align:center}img{width:100%;height:auto}"
        "figcaption{font-weight:800}small{display:block;color:#65758b;"
        "font-weight:500;margin-top:4px}</style>"
        "<h1>Congratulations Pop · animation playback</h1>"
        "<p>Review exact spelling, motif clarity, motion variety, loop seams, "
        "and minimum canvas clearance.</p><main>"
        + figures
        + "</main>",
    )
    return path


def render_review(
    source_root: Path,
    review_root: Path,
    executable: Path,
) -> None:
    items = entries()
    pack_root = source_root / PACK_ID
    pack = pack_root / "pack.json"
    metrics = []
    for entry in items:
        sticker = pack_root / "stickers" / f"{entry.slug}.json"
        run(
            [
                str(executable),
                "validate",
                "--pack",
                str(pack),
                "--sticker",
                str(sticker),
            ]
        )
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
                f"{animated} violates 16px margin: "
                f"{values['minimum_frame_margin_px']}"
            )
        reduced_bounds = first_frame(reduced).getchannel("A").getbbox()
        if reduced_bounds is None:
            raise ValueError(f"reduced-motion asset is blank: {reduced}")
        values.update(
            {
                "semantic_id": entry.semantic_id,
                "label": entry.label,
                "category": entry.category,
                "font_voice": entry.font_voice,
                "layout": entry.layout,
                "effect": entry.effect,
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
        ROOT
        / "contracts"
        / "congratulations-typography-owner-approval-v1.json"
    )
    owner_approval = read_json(owner_approval_path)
    if owner_approval["decision"] != "approved":
        raise ValueError("Congratulations Pop owner decision is not approved")
    owner_reviewed_artifacts = owner_approval["reviewed_artifacts"]
    owner_artifact_hash_match = owner_reviewed_artifacts == artifact_hashes
    write_json(
        review_root / "owner-approval.json",
        owner_approval,
    )
    contract = ROOT / "contracts" / "congratulations-typography-pack-v1.json"
    matrix = (
        ROOT / "content" / "congratulations-typography-matrix-v1.json"
    )
    write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "congratulations-pop-development-review-v1",
            "review_status": "owner-approved",
            "production_use": "approved-for-public-production",
            "owner_approval": (
                "contracts/congratulations-typography-owner-approval-v1.json"
            ),
            "owner_reviewed_artifacts": owner_reviewed_artifacts,
            "owner_artifact_hash_match": owner_artifact_hash_match,
            "artifact_hash_scope": "render-runtime-specific",
            "contract_sha256": sha256(contract),
            "matrix_sha256": sha256(matrix),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "sticker_count": len(metrics),
            "category_counts": {
                category: sum(entry.category == category for entry in items)
                for category in ("core", "achievement", "milestone", "cheer")
            },
            "animated_sticker_count": sum(
                bool(item["animated_webp"]) for item in metrics
            ),
            "loop_closed_sticker_count": sum(
                bool(item["loop_closure"]) for item in metrics
            ),
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "composition_system_count": len({entry.layout for entry in items}),
            "motif_family_count": len({entry.effect for entry in items}),
            "single_layout_shell_sticker_count": len(metrics),
            "independently_typeset_duplicate_text_block_count": 0,
            "minimum_frame_margin_px": min(
                item["minimum_frame_margin_px"] for item in metrics
            ),
            "artifacts": artifact_hashes,
            "metrics": metrics,
            "owner_review_questions": [],
        },
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-output",
        type=Path,
        default=ROOT / "art" / "congratulations-pop-v1",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=ROOT / "generated" / "congratulations-pop-v1-review",
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
    with tempfile.TemporaryDirectory(prefix="congratulations-pop-") as directory:
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
