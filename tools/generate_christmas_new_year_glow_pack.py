#!/usr/bin/env python3
"""Author and render the Christmas & New Year Glow 30-sticker pack."""

from __future__ import annotations

import argparse
import hashlib
import html
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
GENERATOR_VERSION = 3
PACK_ID = "christmas-new-year-glow-v1"
CANVAS = 512
INK = "#172B46"
SNOW = "#F7FCFF"


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

# Christmas palettes lead with evergreen, berry, warm gold, and snow. New Year
# palettes shift toward midnight blue, violet, champagne, and electric cyan.
PALETTES = (
    ("#E63958", "#087F5B", "#FFD166"),
    ("#0BAA83", "#D93256", "#FFE2A8"),
    ("#EF476F", "#0A7C66", "#F5C451"),
    ("#E24444", "#1A6D54", "#FFF1C9"),
    ("#D92F4F", "#0B8F72", "#FFCB5C"),
    ("#69C9F5", "#2E5FA7", "#F9FDFF"),
    ("#E84D62", "#0E765D", "#FFC857"),
    ("#D93C55", "#236B54", "#FFF0D5"),
    ("#E55050", "#0B7A62", "#F7C94B"),
    ("#BE354D", "#176B57", "#FFE1A3"),
    ("#E84A5F", "#16836B", "#FFD56A"),
    ("#DC3652", "#087C65", "#FFF3C8"),
    ("#2F80ED", "#7057D9", "#FFD166"),
    ("#5965D8", "#9B51E0", "#72E1F2"),
    ("#6C5CE7", "#244C9A", "#FFD76A"),
    ("#3D7AE6", "#814DD6", "#F8E16C"),
    ("#8D5CF6", "#254E9B", "#6FE7E7"),
    ("#2F76DC", "#7149C6", "#FFE08A"),
)

ROTATIONS = (-2.5, 1.5, -1.0, 2.0, -1.8, 1.0, 0.0)

LAYOUT_AREAS = {
    "top-icon": {"x": 44, "y": 238, "width": 424, "height": 194},
    "side-icon": {"x": 202, "y": 104, "width": 270, "height": 306},
    "bottom-ribbon": {"x": 45, "y": 66, "width": 422, "height": 246},
    "badge": {"x": 46, "y": 154, "width": 330, "height": 260},
    "full-burst": {"x": 72, "y": 224, "width": 368, "height": 198},
    "corner-icon": {"x": 44, "y": 76, "width": 338, "height": 288},
}


def entries() -> tuple[Entry, ...]:
    matrix = read_json(ROOT / "content" / "christmas-new-year-glow-matrix-v1.json")
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


def winter_ambient(
    primary: str,
    secondary: str,
    highlight: str,
    index: int,
    category: str,
) -> str:
    if category == "new-year":
        return (
            f'<path d="M72 144 l21 -33 M91 149 l34 -10 M420 342 l-28 25 '
            f'M426 364 l-10 35" fill="none" stroke="{highlight}" '
            'stroke-width="9" stroke-linecap="round"/>'
            f'{sparkle(92, 379, 14, primary, INK)}'
            f'{sparkle(419, 127, 12, highlight, INK)}'
            f'<circle cx="119" cy="91" r="7" fill="{secondary}"/>'
            f'<circle cx="397" cy="414" r="6" fill="{primary}"/>'
        )
    return (
        f'<path d="M78 111 v31 M62 126 h32 M68 116 l20 20 M88 116 '
        f'l-20 20 M422 355 v31 M406 370 h32 M412 360 l20 20 '
        f'M432 360 l-20 20" fill="none" stroke="{highlight}" '
        'stroke-width="6" stroke-linecap="round" opacity=".92"/>'
        f'<circle cx="112" cy="383" r="7" fill="{primary}"/>'
        f'<circle cx="403" cy="105" r="6" fill="{secondary}"/>'
        f'{sparkle(91, 351, 11, highlight, INK)}'
    )


def grounding(category: str, index: int, primary: str, secondary: str) -> str:
    if category == "new-year":
        return (
            f'<path d="M112 440 Q256 {456 + index % 3} 400 440" '
            f'fill="none" stroke="{secondary}" stroke-width="12" '
            'stroke-linecap="round" opacity=".20"/>'
        )
    return (
        f'<path d="M106 440 Q256 {452 + index % 4} 406 440" '
        f'fill="none" stroke="{primary}" stroke-width="13" '
        'stroke-linecap="round" opacity=".18"/>'
    )


def seasonal_scene(
    category: str,
    index: int,
    primary: str,
    secondary: str,
    highlight: str,
) -> str:
    """Build an original repeat-motif frame with a clear central window."""
    stroke = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round"'
    if category == "new-year":
        family = index % 4
        common = (
            f'<path d="M60 392 Q118 340 174 367 M338 132 Q397 78 452 119" '
            f'fill="none" stroke="{secondary}" stroke-width="14" '
            'stroke-linecap="round" opacity=".26"/>'
            f'<path d="M62 245 l25 -20 M88 266 l34 -6 M424 238 l-21 -26 '
            f'M449 264 l-35 4" stroke="{highlight}" stroke-width="9" '
            'stroke-linecap="round"/>'
        )
        fireworks = (
            f'<g transform="translate(87 105)"><circle r="9" fill="{highlight}"/>'
            f'<path d="M0 -22 V-57 M0 22 V57 M-22 0 H-57 M22 0 H57 '
            f'M-16 -16 L-40 -40 M16 16 L40 40 M16 -16 L40 -40 '
            f'M-16 16 L-40 40" stroke="{primary}" stroke-width="8" '
            'stroke-linecap="round"/></g>'
            f'<g transform="translate(423 374) scale(.58)"><circle r="58" '
            f'fill="{secondary}" {stroke}/><path d="M-39 -9 H39 M-31 -34 H31 '
            f'M-28 18 H28 M0 -52 V52" stroke="{highlight}" stroke-width="8"/>'
            '</g>'
        )
        confetti = (
            f'<path d="M50 73 L102 44 L120 121 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="102" cy="44" r="12" fill="{highlight}"/>'
            f'<path d="M392 392 q25 -45 56 -5 M398 359 q20 -25 42 2" '
            f'fill="none" stroke="{primary}" stroke-width="9" '
            'stroke-linecap="round"/>'
            f'<rect x="418" y="72" width="12" height="43" rx="6" '
            f'fill="{highlight}" transform="rotate(28 424 94)"/>'
            f'<rect x="67" y="354" width="12" height="40" rx="6" '
            f'fill="{secondary}" transform="rotate(-31 73 374)"/>'
        )
        midnight = (
            f'<g transform="translate(84 106) scale(.54)"><circle r="73" '
            f'fill="{SNOW}" {stroke}/><path d="M0 0 V-56 M0 0 L32 -32" '
            f'stroke="{primary}" stroke-width="12" stroke-linecap="round"/></g>'
            f'<g transform="translate(424 367) rotate(10)"><path d="M-29 -58 '
            f'H29 L22 13 Q17 42 0 44 Q-17 42 -22 13 Z" '
            f'fill="{highlight}" {stroke}/><path d="M0 44 V74 M-31 78 H31" '
            f'stroke="{INK}" stroke-width="7" stroke-linecap="round"/></g>'
            f'<circle cx="391" cy="302" r="8" fill="{primary}"/>'
            f'<circle cx="451" cy="292" r="7" fill="{highlight}"/>'
        )
        fresh_start = (
            f'<g transform="translate(84 105)"><rect x="-48" y="-43" '
            f'width="96" height="89" rx="12" fill="{SNOW}" {stroke}/>'
            f'<path d="M-48 -14 H48" stroke="{primary}" stroke-width="13"/>'
            f'<path d="M-24 -57 V-27 M24 -57 V-27" stroke="{INK}" '
            'stroke-width="8" stroke-linecap="round"/></g>'
            f'<path d="M382 364 Q414 320 449 349 Q468 382 430 409 '
            f'Q394 420 382 388 Z" fill="{secondary}" {stroke}/>'
            f'<polygon points="{star_points(426, 366, 25, 11)}" fill="{highlight}"/>'
        )
        return common + (fireworks, confetti, midnight, fresh_start)[family]

    family = index % 5
    common = (
        f'<path d="M56 400 Q122 345 184 375 M327 128 Q390 70 453 119" '
        f'fill="none" stroke="{secondary}" stroke-width="14" '
        'stroke-linecap="round" opacity=".23"/>'
    )
    woodland = (
        f'<g transform="translate(78 105) scale(.58)"><path d="M0 -72 '
        f'L-43 -16 H-21 L-60 34 H-29 L-72 90 H72 L29 34 H60 '
        f'L21 -16 H43 Z" fill="{secondary}" {stroke}/></g>'
        f'<g transform="translate(418 372) scale(.50)"><ellipse rx="50" ry="28" '
        f'fill="{primary}"/><path d="M27 -13 Q54 -52 78 -52 L80 -9 '
        f'Q64 4 44 8 M-29 17 V72 M-2 20 V72" fill="none" '
        f'stroke="{primary}" stroke-width="14" stroke-linecap="round"/>'
        f'<circle cx="75" cy="-62" r="20" fill="{primary}"/>'
        f'<path d="M70 -81 l-15 -29 M83 -82 l17 -29 M60 -92 l-20 -9 '
        f'M93 -94 l20 -11" stroke="{INK}" stroke-width="6" '
        'stroke-linecap="round"/></g>'
        f'<path d="M62 365 C82 336 108 365 86 389 C74 401 63 409 62 413 '
        f'C61 409 49 401 38 389 C16 365 42 336 62 365 Z" fill="{primary}"/>'
    )
    botanical = (
        f'<g transform="translate(80 106) rotate(-12)"><path d="M0 0 '
        f'C-9 -37 15 -60 42 -64 C33 -34 22 -12 0 0 Z M0 0 '
        f'C28 -27 60 -15 68 14 C35 15 14 12 0 0 Z M0 0 '
        f'C9 37 -18 58 -45 56 C-33 27 -19 8 0 0 Z" '
        f'fill="{secondary}" {stroke}/><circle cx="8" cy="0" r="12" '
        f'fill="{primary}"/><circle cx="29" cy="-8" r="10" '
        f'fill="{primary}"/></g>'
        f'<g transform="translate(420 371)"><path d="M0 -56 L18 -17 '
        f'L60 -20 L30 10 L46 50 L7 27 L-27 52 L-18 12 L-55 -12 '
        f'L-13 -16 Z" fill="{primary}" {stroke}/><circle r="10" '
        f'fill="{highlight}"/></g>'
        f'<circle cx="64" cy="373" r="10" fill="{primary}"/>'
        f'<circle cx="87" cy="391" r="8" fill="{primary}"/>'
    )
    confection = (
        f'<g transform="translate(79 104) rotate(28)"><path d="M0 56 V-26 '
        f'Q0 -68 39 -68 Q70 -68 70 -39" fill="none" stroke="{SNOW}" '
        f'stroke-width="27" stroke-linecap="round"/><path d="M-13 29 H13 '
        f'M-13 -8 H13 M4 -47 L27 -36 M38 -66 L54 -48" '
        f'stroke="{primary}" stroke-width="11"/></g>'
        f'<g transform="translate(423 371)"><circle r="50" fill="{SNOW}" '
        f'{stroke}/><path d="M-41 0 Q0 -44 41 0 Q0 44 -41 0 Z" '
        f'fill="{primary}"/><circle r="11" fill="{highlight}"/></g>'
        f'<polygon points="{star_points(74, 378, 24, 10)}" fill="{highlight}" '
        f'{stroke}/>'
    )
    ornaments = (
        f'<path d="M77 43 V80 M423 42 V80" stroke="{INK}" stroke-width="7"/>'
        f'<circle cx="77" cy="116" r="38" fill="{primary}" {stroke}/>'
        f'<circle cx="423" cy="117" r="39" fill="{secondary}" {stroke}/>'
        f'<path d="M47 116 Q77 87 107 116 M393 117 Q423 146 453 117" '
        f'fill="none" stroke="{highlight}" stroke-width="8"/>'
        f'<g transform="translate(420 376)"><rect x="-47" y="-40" '
        f'width="94" height="80" rx="10" fill="{primary}" {stroke}/>'
        f'<path d="M0 -40 V40 M-47 0 H47" stroke="{SNOW}" stroke-width="9"/>'
        '</g>'
    )
    cozy = (
        f'<g transform="translate(80 122)"><path d="M-44 -37 H27 V33 '
        f'Q26 57 -8 58 Q-42 57 -44 33 Z" fill="{primary}" {stroke}/>'
        f'<path d="M27 -23 Q67 -25 60 13 Q54 37 29 30" fill="none" '
        f'stroke="{INK}" stroke-width="8"/><path d="M-24 -54 q-13 -19 1 -35 '
        f'M8 -53 q-10 -20 3 -34" fill="none" stroke="{highlight}" '
        'stroke-width="7" stroke-linecap="round"/></g>'
        f'<g transform="translate(420 372)"><path d="M-37 -58 V15 '
        f'Q-35 52 0 51 Q37 51 39 18 L14 3 V-58 Z" fill="{secondary}" '
        f'{stroke}/><path d="M-37 -26 H15" stroke="{highlight}" '
        'stroke-width="10"/></g>'
    )
    return common + (woodland, botanical, confection, ornaments, cozy)[family]


def companion_motifs(
    effect: str,
    category: str,
    primary: str,
    secondary: str,
    highlight: str,
) -> str:
    """Add small, semantic scene props so every composition feels illustrated."""
    stroke = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round"'
    if category == "new-year":
        if effect in {"fireworks-skyline", "midnight-clock", "countdown-clock", "number-burst"}:
            return (
                f'<g transform="translate(426 116)"><circle r="8" fill="{highlight}"/>'
                f'<path d="M0 -18 V-45 M0 18 V45 M-18 0 H-45 M18 0 H45 '
                f'M-14 -14 L-34 -34 M14 14 L34 34 M14 -14 L34 -34 M-14 14 L-34 34" '
                f'stroke="{primary}" stroke-width="7" stroke-linecap="round"/></g>'
                f'<polygon points="{star_points(86, 385, 25, 11)}" fill="{highlight}" {stroke}/>'
            )
        if effect == "bubbly-pop":
            return (
                f'<circle cx="91" cy="120" r="20" fill="none" stroke="{highlight}" stroke-width="7"/>'
                f'<circle cx="124" cy="91" r="11" fill="none" stroke="{primary}" stroke-width="6"/>'
                f'<circle cx="420" cy="355" r="16" fill="none" stroke="{secondary}" stroke-width="6"/>'
                f'<circle cx="447" cy="328" r="8" fill="{highlight}"/>'
            )
        if effect in {"first-page", "open-door-confetti", "calendar-flip"}:
            return (
                f'<path d="M66 355 l34 -18 20 38 -34 18 Z" fill="{primary}" {stroke}/>'
                f'<path d="M402 116 l36 12 -12 38 -36 -12 Z" fill="{highlight}" {stroke}/>'
                f'<path d="M82 95 l19 22 M431 386 l-23 17" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
            )
        return (
            f'<polygon points="{star_points(92, 118, 28, 12)}" fill="{highlight}" {stroke}/>'
            f'<path d="M69 393 Q117 350 153 365" fill="none" stroke="{primary}" stroke-width="12" stroke-linecap="round"/>'
            f'{sparkle(425, 371, 18, secondary, INK)}'
        )

    if effect in {"tree-gifts", "gift-burst", "nice-list"}:
        return (
            f'<rect x="58" y="344" width="68" height="58" rx="9" fill="{primary}" {stroke}/>'
            f'<path d="M92 344 V402 M58 371 H126" stroke="{highlight}" stroke-width="9"/>'
            f'<path d="M403 97 q19 -31 38 0 q-19 26 -38 0 Z" fill="{secondary}" {stroke}/>'
        )
    if effect in {"wreath-bow", "garland-lights", "mittens-heart"}:
        return (
            f'<path d="M67 360 q32 -47 72 -16 q-29 9 -35 46 q-20 -20 -37 -30 Z" fill="{secondary}" {stroke}/>'
            f'<circle cx="120" cy="376" r="11" fill="{primary}" {stroke}/>'
            f'<circle cx="139" cy="365" r="10" fill="{primary}" {stroke}/>'
            f'{sparkle(420, 114, 19, highlight, INK)}'
        )
    if effect in {"santa-hat", "chimney-santa", "sleigh-gifts"}:
        return (
            f'<path d="M59 339 H121 V405 Q90 431 59 405 Z" fill="{primary}" {stroke}/>'
            f'<rect x="50" y="331" width="80" height="24" rx="12" fill="{SNOW}" {stroke}/>'
            f'<path d="M388 103 q24 -23 48 0" fill="none" stroke="{highlight}" stroke-width="11" stroke-linecap="round"/>'
            f'{sparkle(432, 136, 14, highlight, INK)}'
        )
    if effect in {"cocoa-mug", "candy-canes", "festive-toast"}:
        return (
            f'<circle cx="91" cy="378" r="35" fill="{highlight}" {stroke}/>'
            f'<circle cx="80" cy="365" r="5" fill="{primary}"/><circle cx="105" cy="384" r="5" fill="{secondary}"/>'
            f'<path d="M399 92 q28 29 0 58 q-28 -29 0 -58 Z" fill="{primary}" {stroke}/>'
            f'<path d="M390 104 l19 10 M390 127 l18 9" stroke="{SNOW}" stroke-width="6"/>'
        )
    return (
        f'<polygon points="{star_points(91, 116, 28, 12)}" fill="{highlight}" {stroke}/>'
        f'<path d="M390 365 l52 0 M416 339 v52 M398 347 l36 36 M434 347 l-36 36" '
        f'stroke="{secondary}" stroke-width="7" stroke-linecap="round"/>'
    )


def icon_group(body: str, layout: str) -> str:
    positions = {
        "top-icon": (256, 145, 0.80),
        "side-icon": (112, 267, 0.82),
        "bottom-ribbon": (256, 385, 0.88),
        "badge": (394, 136, 0.70),
        "full-burst": (256, 142, 0.62),
        "corner-icon": (400, 386, 0.70),
    }
    x, y, scale = positions[layout]
    return f'<g transform="translate({x} {y}) scale({scale})">{body}</g>'


def motif_body(effect: str, primary: str, secondary: str, highlight: str) -> str:
    stroke = f'stroke="{INK}" stroke-width="8" stroke-linejoin="round"'
    round_stroke = f'{stroke} stroke-linecap="round"'
    if effect == "tree-gifts":
        return (
            f'<path d="M0 -116 L-58 -48 H-28 L-91 22 H-48 L-112 91 '
            f'H112 L48 22 H91 L28 -48 H58 Z" fill="{secondary}" {stroke}/>'
            f'<rect x="-14" y="88" width="28" height="38" rx="5" '
            f'fill="{highlight}" {stroke}/>'
            f'<polygon points="{star_points(0, -121, 25, 11)}" fill="{highlight}" {stroke}/>'
            f'<circle cx="-43" cy="18" r="11" fill="{primary}"/>'
            f'<circle cx="39" cy="48" r="10" fill="{highlight}"/>'
            f'<rect x="-103" y="74" width="57" height="47" rx="8" fill="{primary}" {stroke}/>'
            f'<path d="M-75 74 V121 M-103 92 H-46" fill="none" stroke="{SNOW}" stroke-width="8"/>'
        )
    if effect == "wreath-bow":
        return (
            f'<circle cx="0" cy="0" r="77" fill="none" stroke="{secondary}" stroke-width="35"/>'
            f'<circle cx="-48" cy="-45" r="9" fill="{primary}"/><circle cx="52" cy="-36" r="9" fill="{highlight}"/>'
            f'<circle cx="-58" cy="38" r="8" fill="{highlight}"/><circle cx="45" cy="49" r="8" fill="{primary}"/>'
            f'<path d="M0 58 C-29 23 -73 58 -38 91 Q-18 103 0 76 '
            f'C29 23 73 58 38 91 Q18 103 0 76 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-10 79 L-38 126 L0 109 L37 128 L11 79" fill="{primary}" {stroke}/>'
        )
    if effect == "ornament-cluster":
        return (
            f'<path d="M-70 -116 V-74 M0 -126 V-84 M70 -112 V-66" fill="none" {round_stroke}/>'
            f'<circle cx="-70" cy="-23" r="54" fill="{primary}" {stroke}/>'
            f'<circle cx="0" cy="-28" r="62" fill="{highlight}" {stroke}/>'
            f'<circle cx="70" cy="-14" r="49" fill="{secondary}" {stroke}/>'
            f'<path d="M-97 -25 Q-70 -50 -42 -25 M-28 -18 Q0 12 29 -18 '
            f'M48 -17 Q70 -38 92 -17" fill="none" stroke="{SNOW}" stroke-width="10" stroke-linecap="round"/>'
        )
    if effect == "santa-hat":
        return (
            f'<path d="M-98 39 Q-39 -88 47 -103 Q38 -27 95 31 Z" fill="{primary}" {stroke}/>'
            f'<rect x="-108" y="25" width="211" height="53" rx="27" fill="{SNOW}" {stroke}/>'
            f'<circle cx="54" cy="-91" r="33" fill="{SNOW}" {stroke}/>'
        )
    if effect == "jingle-bells":
        return (
            f'<g transform="rotate(-20)"><path d="M-96 36 Q-88 -64 -30 -69 Q29 -63 35 36 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-103 38 H42" fill="none" {round_stroke}/><circle cx="-30" cy="45" r="14" fill="{primary}"/></g>'
            f'<g transform="translate(66 2) rotate(18)"><path d="M-58 31 Q-51 -52 0 -58 Q51 -52 58 31 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-64 33 H64" fill="none" {round_stroke}/><circle cx="0" cy="40" r="13" fill="{highlight}"/></g>'
        )
    if effect == "snow-globe":
        return (
            f'<circle cx="0" cy="-18" r="82" fill="#CDEFFF" {stroke}/>'
            f'<path d="M-72 30 Q0 -6 72 30" fill="{SNOW}" stroke="none"/>'
            f'<path d="M0 -62 L-33 -15 H-13 L-48 29 H48 L13 -15 H33 Z" fill="{secondary}" {stroke}/>'
            f'<circle cx="-46" cy="-46" r="6" fill="{SNOW}"/><circle cx="47" cy="-24" r="7" fill="{SNOW}"/>'
            f'<path d="M-77 68 H77 L98 111 H-98 Z" fill="{primary}" {stroke}/>'
        )
    if effect == "sleigh-gifts":
        return (
            f'<path d="M-104 36 H58 Q100 33 103 -6 Q119 70 49 82 H-77 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-92 81 Q-38 119 80 83" fill="none" {round_stroke}/>'
            f'<rect x="-73" y="-37" width="65" height="72" rx="9" fill="{highlight}" {stroke}/>'
            f'<rect x="-7" y="-57" width="63" height="92" rx="9" fill="{secondary}" {stroke}/>'
            f'<path d="M-41 -37 V35 M-73 -8 H-8 M24 -57 V35 M-7 -24 H56" fill="none" stroke="{SNOW}" stroke-width="8"/>'
        )
    if effect == "chimney-santa":
        return (
            f'<rect x="-85" y="-5" width="170" height="111" rx="8" fill="{primary}" {stroke}/>'
            f'<path d="M-85 30 H85 M-28 -5 V106 M35 30 V106" fill="none" stroke="{highlight}" stroke-width="8"/>'
            f'<circle cx="0" cy="-49" r="45" fill="#8B4A35" {stroke}/>'
            f'<path d="M-42 -57 Q-4 -116 52 -88 L35 -41 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="48" cy="-88" r="18" fill="{SNOW}" {stroke}/>'
            f'<path d="M-31 -31 Q0 7 31 -31" fill="{SNOW}" {stroke}/>'
        )
    if effect == "nice-list":
        return (
            f'<path d="M-77 -100 Q-102 -88 -86 -61 V89 Q-99 112 -66 118 H66 Q99 112 86 89 V-61 Q102 -88 77 -100 Z" fill="{SNOW}" {stroke}/>'
            f'<path d="M-52 -49 H53 M-52 -8 H53 M-52 33 H34" fill="none" stroke="{secondary}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M-48 69 L-27 91 L17 54" fill="none" stroke="{primary}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if effect == "cocoa-mug":
        return (
            f'<path d="M-86 -40 H61 V72 Q58 104 0 107 Q-61 104 -65 72 Z" fill="{primary}" {stroke}/>'
            f'<path d="M61 -17 Q118 -21 108 38 Q98 77 62 64" fill="none" {round_stroke}/>'
            f'<ellipse cx="-12" cy="-39" rx="73" ry="24" fill="#6E3B2E" {stroke}/>'
            f'<circle cx="-45" cy="-51" r="17" fill="{SNOW}"/><circle cx="-7" cy="-49" r="18" fill="{SNOW}"/><circle cx="32" cy="-48" r="16" fill="{SNOW}"/>'
            f'<path d="M-50 -83 Q-66 -111 -47 -129 M2 -82 Q-12 -109 5 -130 M48 -78 Q35 -102 51 -121" fill="none" stroke="{highlight}" stroke-width="8" stroke-linecap="round"/>'
        )
    if effect == "mittens-heart":
        return (
            f'<g transform="rotate(-16 -38 0)"><path d="M-90 -28 Q-95 -74 -58 -80 Q-22 -83 -11 -48 L9 -2 Q17 51 -28 70 Q-73 84 -83 36 Z" fill="{primary}" {stroke}/>'
            f'<rect x="-82" y="46" width="67" height="39" rx="14" fill="{highlight}" {stroke}/></g>'
            f'<g transform="rotate(16 38 0)"><path d="M90 -28 Q95 -74 58 -80 Q22 -83 11 -48 L-9 -2 Q-17 51 28 70 Q73 84 83 36 Z" fill="{secondary}" {stroke}/>'
            f'<rect x="15" y="46" width="67" height="39" rx="14" fill="{highlight}" {stroke}/></g>'
            f'<path d="M0 112 C-54 78 -41 38 -8 47 Q0 50 0 64 Q0 50 9 47 C42 38 54 78 0 112 Z" fill="{primary}"/>'
        )
    if effect == "candy-canes":
        return (
            f'<path d="M-83 90 L-28 -71 Q-12 -118 -52 -126 Q-89 -132 -103 -96" fill="none" stroke="{SNOW}" stroke-width="34" stroke-linecap="round"/>'
            f'<path d="M83 90 L28 -71 Q12 -118 52 -126 Q89 -132 103 -96" fill="none" stroke="{SNOW}" stroke-width="34" stroke-linecap="round"/>'
            f'<path d="M-74 63 l-26 -9 M-57 14 l-26 -9 M-40 -35 l-25 -9 M74 63 l26 -9 M57 14 l26 -9 M40 -35 l25 -9" stroke="{primary}" stroke-width="15"/>'
            f'<path d="M-61 24 Q0 91 61 24" fill="none" stroke="{secondary}" stroke-width="16" stroke-linecap="round"/>'
        )
    if effect == "globe-star":
        return (
            f'<circle cx="0" cy="12" r="82" fill="#61C6E8" {stroke}/>'
            f'<path d="M-70 -22 Q-34 -45 -7 -18 Q6 3 35 -10 Q72 -20 78 17 Q49 25 41 52 Q11 46 -5 69 Q-40 66 -51 38 Q-77 22 -70 -22 Z" fill="{secondary}"/>'
            f'<polygon points="{star_points(0, -100, 35, 15)}" fill="{highlight}" {stroke}/>'
        )
    if effect == "dove-olive":
        return (
            f'<path d="M-100 21 Q-49 -79 13 -39 Q43 -95 92 -87 Q55 -43 77 2 Q44 68 -25 55 Q-58 89 -100 74 Q-69 49 -100 21 Z" fill="{SNOW}" {stroke}/>'
            f'<circle cx="49" cy="-46" r="6" fill="{INK}"/>'
            f'<path d="M72 -31 L111 -18 L75 -3 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-29 62 Q20 99 82 69 M14 84 l-9 27 M42 82 l8 26 M65 72 l17 22" fill="none" stroke="{secondary}" stroke-width="10" stroke-linecap="round"/>'
        )
    if effect == "gift-burst":
        return (
            f'<rect x="-94" y="-43" width="188" height="143" rx="14" fill="{primary}" {stroke}/>'
            f'<rect x="-108" y="-73" width="216" height="47" rx="13" fill="{highlight}" {stroke}/>'
            f'<path d="M0 -73 V100 M-94 18 H94" fill="none" stroke="{secondary}" stroke-width="19"/>'
            f'<path d="M0 -72 Q-75 -84 -71 -122 Q-65 -153 -22 -124 Q-4 -111 0 -72 Q75 -84 71 -122 Q65 -153 22 -124 Q4 -111 0 -72 Z" fill="{secondary}" {stroke}/>'
        )
    if effect == "garland-lights":
        bulbs = "".join(
            f'<circle cx="{x}" cy="{y}" r="13" fill="{color}" {stroke}/>'
            for x, y, color in (
                (-91, 10, primary), (-49, 36, highlight), (0, 44, primary),
                (49, 36, highlight), (91, 10, primary)
            )
        )
        return (
            f'<path d="M-112 -24 Q0 104 112 -24" fill="none" stroke="{secondary}" stroke-width="15" stroke-linecap="round"/>'
            + bulbs
            + f'<path d="M-77 -17 l-22 -45 M-29 21 l-8 -52 M29 21 l8 -52 M77 -17 l22 -45" stroke="{INK}" stroke-width="7"/>'
        )
    if effect == "magic-star":
        return (
            f'<polygon points="{star_points(0, 0, 93, 40)}" fill="{highlight}" {stroke}/>'
            f'<path d="M-106 77 Q-34 44 -16 2 M26 -21 Q76 -57 111 -39" fill="none" stroke="{primary}" stroke-width="13" stroke-linecap="round"/>'
            f'{sparkle(-82, -73, 18, SNOW, INK)}{sparkle(83, 72, 15, secondary, INK)}'
        )
    if effect == "festive-toast":
        return (
            f'<g transform="rotate(-12 -42 0)"><path d="M-88 -79 H-14 L-25 17 Q-29 55 -52 55 Q-75 55 -79 17 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-52 55 V94 M-86 98 H-19" fill="none" {round_stroke}/></g>'
            f'<g transform="rotate(12 42 0)"><path d="M14 -79 H88 L79 17 Q75 55 52 55 Q29 55 25 17 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M52 55 V94 M19 98 H86" fill="none" {round_stroke}/></g>'
            f'<circle cx="0" cy="-103" r="8" fill="{secondary}"/><circle cx="27" cy="-123" r="6" fill="{primary}"/>'
        )
    if effect == "fireworks-skyline":
        rays = "".join(
            f'<path d="M0 -{58 + i % 2 * 10} L0 -{105 + i % 3 * 8}" '
            f'transform="rotate({i * 30})" stroke="{(primary, highlight, secondary)[i % 3]}" stroke-width="10" stroke-linecap="round"/>'
            for i in range(12)
        )
        return (
            rays
            + f'<circle cx="0" cy="0" r="18" fill="{highlight}"/>'
            + f'<path d="M-120 109 V49 H-79 V72 H-43 V20 H-5 V81 H34 V42 H70 V66 H112 V109 Z" fill="{INK}"/>'
        )
    if effect == "sunrise-door":
        rays = "".join(
            f'<path d="M0 -31 L0 -{82 + (i % 2) * 13}" transform="rotate({-75 + i * 25})" stroke="{highlight}" stroke-width="10" stroke-linecap="round"/>'
            for i in range(7)
        )
        return (
            rays
            + f'<path d="M-103 98 Q-88 -30 0 -31 Q88 -30 103 98 Z" fill="{highlight}" {stroke}/>'
            + f'<rect x="-67" y="-9" width="134" height="118" rx="10" fill="{secondary}" {stroke}/>'
            + f'<path d="M0 -9 V109 L67 87 V10 Z" fill="{primary}" {stroke}/><circle cx="43" cy="50" r="8" fill="{highlight}"/>'
        )
    if effect in {"midnight-clock", "countdown-clock"}:
        minute = -84 if effect == "midnight-clock" else -55
        return (
            f'<circle cx="0" cy="0" r="94" fill="{SNOW}" {stroke}/>'
            f'<circle cx="0" cy="0" r="77" fill="none" stroke="{primary}" stroke-width="8"/>'
            f'<path d="M0 0 V{minute} M0 0 L{18 if effect == "midnight-clock" else 49} -42" fill="none" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>'
            f'<circle cx="0" cy="0" r="11" fill="{highlight}"/>'
            f'<path d="M0 -68 V-79 M68 0 H79 M0 68 V79 M-68 0 H-79" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
        )
    if effect == "number-burst":
        return (
            f'<polygon points="{star_points(0, 0, 115, 61)}" fill="{highlight}" {stroke}/>'
            f'<circle cx="0" cy="0" r="65" fill="{primary}" {stroke}/>'
            f'<path d="M-39 -23 H-8 L-31 6 Q-7 4 -7 29 Q-9 58 -46 53 M8 -18 Q18 -41 43 -25 Q63 -8 12 48 H61" fill="none" stroke="{SNOW}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    if effect == "bubbly-pop":
        return (
            f'<path d="M-58 -111 H57 L45 -4 Q40 50 0 53 Q-40 50 -45 -4 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-50 -31 Q0 -4 50 -31" fill="none" stroke="{primary}" stroke-width="17"/>'
            f'<path d="M0 53 V92 M-54 98 H54" fill="none" {round_stroke}/>'
            f'<circle cx="-56" cy="-112" r="10" fill="{primary}"/><circle cx="3" cy="-139" r="12" fill="{highlight}"/><circle cx="58" cy="-120" r="8" fill="{secondary}"/>'
        )
    if effect == "wish-star":
        return (
            f'<polygon points="{star_points(32, -18, 70, 30)}" fill="{highlight}" {stroke}/>'
            f'<path d="M-115 78 Q-61 20 -21 5 M-102 106 Q-42 50 1 34" fill="none" stroke="{primary}" stroke-width="17" stroke-linecap="round"/>'
            f'{sparkle(-63, -64, 16, secondary, INK)}{sparkle(99, 65, 12, SNOW, INK)}'
        )
    if effect == "first-page":
        return (
            f'<rect x="-94" y="-105" width="188" height="210" rx="17" fill="{SNOW}" {stroke}/>'
            f'<path d="M-94 -59 H94" stroke="{primary}" stroke-width="16"/>'
            f'<circle cx="-57" cy="-83" r="7" fill="{secondary}"/><circle cx="-31" cy="-83" r="7" fill="{highlight}"/>'
            f'<path d="M-58 -13 H56 M-58 25 H38 M-58 63 H19" fill="none" stroke="{secondary}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M50 43 V91 M25 67 H75" stroke="{primary}" stroke-width="12" stroke-linecap="round"/>'
        )
    if effect == "open-door-confetti":
        return (
            f'<rect x="-77" y="-103" width="154" height="215" rx="10" fill="{secondary}" {stroke}/>'
            f'<path d="M-2 -103 V112 L77 88 V-82 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="53" cy="21" r="8" fill="{highlight}"/>'
            f'<path d="M-109 -72 l25 20 M-108 -22 h32 M104 -76 l-24 22 M111 -24 H79" stroke="{highlight}" stroke-width="10" stroke-linecap="round"/>'
            f'<circle cx="-99" cy="28" r="8" fill="{primary}"/><circle cx="103" cy="36" r="7" fill="{secondary}"/>'
        )
    if effect == "disco-ball":
        grid = "".join(
            f'<path d="M{-62 + i * 31} -67 V67 M-67 {-62 + i * 31} H67" stroke="{secondary}" stroke-width="6" opacity=".72"/>'
            for i in range(5)
        )
        return (
            f'<path d="M0 -134 V-83" fill="none" {round_stroke}/>'
            f'<circle cx="0" cy="0" r="82" fill="{highlight}" {stroke}/><g clip-path="url(#ball)">{grid}</g>'
            f'<defs><clipPath id="ball"><circle cx="0" cy="0" r="76"/></clipPath></defs>'
            f'<path d="M-103 77 L-128 105 M103 77 L128 105" stroke="{primary}" stroke-width="12" stroke-linecap="round"/>'
        )
    if effect == "sparkle-trail":
        return (
            f'<path d="M-119 69 Q-53 -17 16 -17 Q67 -17 109 -77" fill="none" stroke="{primary}" stroke-width="18" stroke-linecap="round"/>'
            f'<polygon points="{star_points(45, -22, 58, 25)}" fill="{highlight}" {stroke}/>'
            f'{sparkle(-70, -39, 22, secondary, INK)}{sparkle(105, 35, 17, SNOW, INK)}'
            f'<circle cx="-106" cy="78" r="11" fill="{highlight}"/>'
        )
    if effect == "calendar-flip":
        return (
            f'<rect x="-101" y="-81" width="202" height="171" rx="18" fill="{SNOW}" {stroke}/>'
            f'<path d="M-101 -33 H101" stroke="{primary}" stroke-width="18"/>'
            f'<path d="M-52 -107 V-59 M52 -107 V-59" fill="none" {round_stroke}/>'
            f'<path d="M-56 13 H57 M-56 48 H25" fill="none" stroke="{secondary}" stroke-width="12" stroke-linecap="round"/>'
            f'<path d="M62 39 L102 79 L72 103" fill="{highlight}" {stroke}/>'
        )
    return (
        f'<circle cx="0" cy="0" r="82" fill="{highlight}" {stroke}/>'
        f'<polygon points="{star_points(0, 0, 47, 21)}" fill="{primary}"/>'
    )


def motif_svg(entry: Entry, index: int) -> str:
    primary, secondary, highlight = PALETTES[index % len(PALETTES)]
    body = motif_body(entry.effect, primary, secondary, highlight)
    pieces = [
        grounding(entry.category, index, primary, secondary),
        seasonal_scene(entry.category, index, primary, secondary, highlight),
        winter_ambient(primary, secondary, highlight, index, entry.category),
        companion_motifs(entry.effect, entry.category, primary, secondary, highlight),
        icon_group(body, entry.layout),
    ]
    if entry.layout == "full-burst":
        pieces.append(
            f'<path d="M126 250 H60 M386 250 H452 M148 168 L103 123 '
            f'M364 168 L409 123 M148 334 L105 377 M364 334 L407 377" '
            f'fill="none" stroke="{highlight}" stroke-width="9" '
            'stroke-linecap="round" opacity=".65"/>'
        )
    return svg("\n".join(pieces))


def text_area(entry: Entry) -> dict[str, int]:
    area = dict(LAYOUT_AREAS[entry.layout])
    if entry.motion == "pop":
        area["x"] += 16
        area["width"] -= 32
        area["y"] += 10
        area["height"] -= 20
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
        "pop": 1.04,
        "pulse": 1.035,
        "wobble": 3.0 if index % 2 else -3.0,
        "float": -6.0,
    }[entry.motion]
    return {
        "duration_ms": duration,
        "fps": 12,
        "loop": "loop",
        "overlays": [overlay],
        "tracks": [{
            "target": f"motif-{entry.slug}",
            "property": property_name,
            "keyframes": [
                {"at_ms": 0, "value": rest, "easing": "ease_in_out"},
                {"at_ms": middle, "value": middle_value, "easing": "ease_in_out"},
                {"at_ms": duration, "value": rest, "easing": "ease_in_out"},
            ],
        }],
    }


def pack_document(items: tuple[Entry, ...]) -> dict[str, Any]:
    layers = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(items):
        layer_id = f"motif-{entry.slug}"
        layers.append({
            "id": layer_id,
            "source": f"layers/{index:02d}-{layer_id}.svg",
            "z": 10 + index,
            "pivot": "composition",
            "depth": 0.0,
        })
        expressions[entry.slug] = [layer_id]
        primary, secondary, highlight = PALETTES[index % len(PALETTES)]
        font_id = FONT_VOICES[entry.font_voice][0]
        styles[f"{entry.slug}-main"] = {
            "font": font_id,
            "safe_area": text_area(entry),
            "min_font_size": 24,
            "max_font_size": 184,
            "max_lines": 3,
            "fill": rgb(primary),
            "outline": {"width": (6, 7, 8, 7)[index % 4], "color": rgb(INK)},
            "depth_shell": {
                "offset_x": 7 + index % 3,
                "offset_y": 8 + index % 3,
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
        "poses": {"festive": []},
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT; bundled fonts separately SIL OFL 1.1",
            "source": (
                f"generate_christmas_new_year_glow_pack.py v{GENERATOR_VERSION}; "
                "original procedural compositions"
            ),
        },
        "anchors": {"composition_center": {"x": 256, "y": 256}},
        "pivots": {"composition": {"x": 256, "y": 256}},
        "avoid_regions": [],
        "text_clearance": 0,
        "caption_validation": {
            "minimum_canvas_margin_px": 16,
            "maximum_lines": 3,
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
        "sticker_id": f"christmas-new-year-glow-{entry.slug}",
        "pack_id": PACK_ID,
        "phrase_id": entry.semantic_id,
        "recipe_id": f"seasonal-glow.{entry.motion}",
        "intent": entry.semantic_id,
        "alt_text": f"Festive animated sticker saying {entry.label}",
        "accessible_description": (
            f"The phrase {entry.label} with an original "
            f"{entry.effect.replace('-', ' ')} festive motif"
        ),
        "expression": entry.slug,
        "pose": "festive",
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
            "entries": [{
                "phrase_id": entry.semantic_id,
                "sticker_id": f"christmas-new-year-glow-{entry.slug}",
                "triggers": [{
                    "text": alias,
                    "locale": "en",
                    "match": "exact-phrase",
                    "weight": 1.0 if alias == entry.label.lower().rstrip("!") else 0.85,
                } for alias in entry.aliases],
            } for entry in items],
        },
    )
    write_json(
        destination / "generation-manifest.json",
        {
            "schema_version": 1,
            "generator": Path(__file__).name,
            "generator_version": GENERATOR_VERSION,
            "pack_id": PACK_ID,
            "pack_contract": "contracts/christmas-new-year-glow-pack-v1.json",
            "content_matrix": "content/christmas-new-year-glow-matrix-v1.json",
            "sticker_count": len(items),
            "category_counts": {
                category: sum(entry.category == category for entry in items)
                for category in ("christmas", "new-year")
            },
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "composition_system_count": len({entry.layout for entry in items}),
            "motif_family_count": len({entry.effect for entry in items}),
            "seasonal_pattern_family_count": 9,
            "single_fitted_glyph_layout_per_sticker": True,
            "independently_typeset_duplicate_text_blocks": 0,
            "owner_approval": (
                "contracts/christmas-new-year-glow-owner-approval-v1.json"
            ),
            "production_use": "approved-for-public-production",
        },
    )


def build_contact_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns, cell_width, cell_height = 6, 232, 252
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_width + 40, rows * cell_height + 82), "#EAF1F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "CHRISTMAS & NEW YEAR GLOW · 30-STICKER ART REVIEW", fill=INK, font=review_font(29))
    for index, entry in enumerate(items):
        column, row = index % columns, index // columns
        x, y = 20 + column * cell_width, 70 + row * cell_height
        panel = "#F7FCFF" if entry.category == "christmas" else "#F3F0FF"
        draw.rounded_rectangle((x, y, x + 214, y + 232), radius=22, fill=panel, outline="#CFDBE8", width=2)
        image = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        image.thumbnail((198, 198), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + (214 - image.width) // 2, y + 4))
        draw.text((x + 10, y + 203), entry.label, fill=INK, font=review_font(13))
        draw.text((x + 10, y + 219), f"{entry.category} · {entry.motion}", fill="#65758B", font=review_font(10))
    path = review_root / "contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_small_display_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    sizes = (80, 100, 160)
    columns, rows, cell_width, cell_height = 5, 6, 218, 214
    panel_width = columns * cell_width + 24
    canvas = Image.new("RGBA", (len(sizes) * panel_width + 24, rows * cell_height + 100), "#172B46")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "ALL 30 PHRASES · READABILITY AT 80 / 100 / 160 PX", fill="#FFFFFF", font=review_font(30))
    for panel, size in enumerate(sizes):
        panel_x = 12 + panel * panel_width
        draw.text((panel_x + 12, 58), f"{size}px" + (" · RECOMMENDED" if size == 100 else ""), fill="#FFFFFF", font=review_font(18))
        for index, entry in enumerate(items):
            column, row = index % columns, index // columns
            x, y = panel_x + column * cell_width, 88 + row * cell_height
            draw.rounded_rectangle((x + 4, y, x + cell_width - 6, y + 196), radius=18, fill="#F8FAFC")
            source = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
            image = source.resize((size, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + (cell_width - size) // 2, y + 6 + (160 - size) // 2))
            label = entry.label if len(entry.label) <= 23 else entry.label[:22] + "…"
            draw.text((x + 11, y + 170), label, fill=INK, font=review_font(11))
    path = review_root / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_motion_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns, cell_width, cell_height = 3, 392, 218
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_width + 40, rows * cell_height + 88), "#EAF1F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "ALL 30 LOOPS · START / MID / CLOSURE", fill=INK, font=review_font(30))
    draw.text((24, 52), "Mid-cycle must change visibly; closure must match the opening frame.", fill="#65758B", font=review_font(15))
    for index, entry in enumerate(items):
        column, row = index % columns, index // columns
        x, y = 20 + column * cell_width, 78 + row * cell_height
        draw.rounded_rectangle((x, y, x + 374, y + 202), radius=20, fill="#FFFFFF", outline="#D2DDEA", width=2)
        frames = image_frames(review_root / "assets" / f"{entry.slug}.webp")
        for frame_index, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
            image = frame.resize((88, 88), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + 9 + frame_index * 96, y + 7))
        for frame_index, label in enumerate(("START", "MID", "CLOSE")):
            draw.text((x + 18 + frame_index * 96, y + 98), label, fill="#7A8798", font=review_font(9))
        draw.text((x + 12, y + 126), entry.label, fill=INK, font=review_font(13))
        draw.text(
            (x + 12, y + 168),
            f"{entry.motion} · {entry.effect}",
            fill="#65758B",
            font=review_font(11),
        )
    path = review_root / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_animation_html(review_root: Path, items: tuple[Entry, ...]) -> Path:
    figures = "".join(
        f'<figure><img src="assets/{entry.slug}.webp" alt="{html.escape(entry.label)} animated festive sticker">'
        f'<figcaption>{html.escape(entry.label)}<small>{entry.category} · {entry.font_voice} · {entry.motion}</small></figcaption></figure>'
        for entry in items
    )
    path = review_root / "animation-review.html"
    write_text(
        path,
        '<!doctype html><meta charset="utf-8"><title>Christmas & New Year Glow animation review</title>'
        '<style>body{font:16px system-ui;background:#eaf1f8;color:#172b46;margin:24px}'
        'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}'
        'figure{margin:0;background:white;border-radius:20px;padding:12px;text-align:center}'
        'img{width:100%;height:auto}figcaption{font-weight:800}small{display:block;color:#65758b;font-weight:500;margin-top:4px}</style>'
        '<h1>Christmas & New Year Glow · animation playback</h1>'
        '<p>Review exact spelling, seasonal motif clarity, motion, loop closure, and frame clearance.</p><main>'
        + figures + '</main>',
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
            bounds = [frame.getchannel("A").getbbox() for frame in image_frames(animated)]
            raise ValueError(
                f"{animated} violates 16px margin: "
                f"{values['minimum_frame_margin_px']}; bounds={bounds}"
            )
        if first_frame(reduced).getchannel("A").getbbox() is None:
            raise ValueError(f"reduced-motion asset is blank: {reduced}")
        values.update({
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
        })
        metrics.append(values)
    artifacts = [
        build_contact_sheet(review_root, items),
        build_small_display_sheet(review_root, items),
        build_motion_sheet(review_root, items),
        build_animation_html(review_root, items),
    ]
    artifact_hashes = {path.name: sha256(path) for path in artifacts}
    owner_approval_path = (
        ROOT / "contracts" / "christmas-new-year-glow-owner-approval-v1.json"
    )
    owner_approval = read_json(owner_approval_path)
    if owner_approval["decision"] != "approved":
        raise ValueError("Christmas & New Year Glow owner decision is not approved")
    owner_reviewed_artifacts = owner_approval["reviewed_artifacts"]
    owner_artifact_hash_match = owner_reviewed_artifacts == artifact_hashes
    write_json(review_root / "owner-approval.json", owner_approval)
    contract = ROOT / "contracts" / "christmas-new-year-glow-pack-v1.json"
    matrix = ROOT / "content" / "christmas-new-year-glow-matrix-v1.json"
    write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "christmas-new-year-glow-production-review-v1",
            "review_status": "owner-approved",
            "production_use": "approved-for-public-production",
            "owner_approval": (
                "contracts/christmas-new-year-glow-owner-approval-v1.json"
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
                for category in ("christmas", "new-year")
            },
            "animated_sticker_count": sum(bool(item["animated_webp"]) for item in metrics),
            "loop_closed_sticker_count": sum(bool(item["loop_closure"]) for item in metrics),
            "visible_mid_cycle_sticker_count": sum(bool(item["visible_mid_cycle_change"]) for item in metrics),
            "reduced_motion_sticker_count": len(metrics),
            "font_voice_count": len({entry.font_voice for entry in items}),
            "motion_family_count": len({entry.motion for entry in items}),
            "composition_system_count": len({entry.layout for entry in items}),
            "motif_family_count": len({entry.effect for entry in items}),
            "seasonal_pattern_family_count": 9,
            "single_layout_shell_sticker_count": len(metrics),
            "independently_typeset_duplicate_text_block_count": 0,
            "minimum_frame_margin_px": min(item["minimum_frame_margin_px"] for item in metrics),
            "artifacts": artifact_hashes,
            "metrics": metrics,
            "owner_review_questions": [
                "Do all 30 phrases read as a coherent Christmas and New Year family?",
                "Are the Christmas and midnight New Year palette shifts complementary?",
                "Are exact spelling, punctuation, motif clarity, and 80px readability approved?",
                "Does animation playback remain expressive without distracting from the phrase?"
            ],
        },
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-output", type=Path, default=ROOT / "art" / PACK_ID)
    parser.add_argument("--review-output", type=Path, default=ROOT / "generated" / f"{PACK_ID}-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_output = args.source_output.resolve()
    review_output = args.review_output.resolve()
    executable = args.mascotrender.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"MascotRender CLI is missing: {executable}")
    with tempfile.TemporaryDirectory(prefix="christmas-new-year-glow-") as directory:
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
