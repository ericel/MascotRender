#!/usr/bin/env python3
"""Author and render the Workday Reactions 96-sticker development pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter
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
    svg,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parent.parent
GENERATOR_VERSION = 2
PACK_ID = "workday-reactions-v1"
CANVAS = 512
INK = "#20324B"
FUR = "#C86543"
FUR_DARK = "#8E3F38"
CREAM = "#FFF0D5"
TEAL = "#24B39B"
GOLD = "#FFCA55"
CORAL = "#FF6577"
SKY = "#69C9F2"
PURPLE = "#8567D9"


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
    pose: str
    mood: str

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


CATEGORY_PALETTES = {
    "workflow": (TEAL, "#147D73", GOLD),
    "meetings": (SKY, "#2868A9", CORAL),
    "decisions": (PURPLE, "#563E9C", GOLD),
    "team": ("#5BCB78", "#23855C", CORAL),
    "results": (GOLD, "#D57A24", TEAL),
    "time": ("#6B8CFF", "#414F9D", "#FFB85C"),
    "energy": ("#FF8F5A", "#A94D55", SKY),
    "humor": (CORAL, "#9D4163", "#A78BFA"),
}


LAYOUTS: dict[str, dict[str, Any]] = {
    "caption-top": {
        "scene": (256, 316, 0.82),
        "text": {"x": 48, "y": 34, "width": 416, "height": 142},
    },
    "caption-bottom": {
        "scene": (256, 198, 0.82),
        "text": {"x": 48, "y": 350, "width": 416, "height": 132},
    },
    "caption-left": {
        "scene": (366, 258, 0.76),
        "text": {"x": 32, "y": 130, "width": 226, "height": 224},
    },
    "caption-right": {
        "scene": (146, 258, 0.76),
        "text": {"x": 254, "y": 130, "width": 226, "height": 224},
    },
    "speech-right": {
        "scene": (164, 290, 0.76),
        "text": {"x": 268, "y": 58, "width": 208, "height": 190},
    },
    "banner-bottom": {
        "scene": (256, 190, 0.72),
        "text": {"x": 54, "y": 344, "width": 404, "height": 138},
    },
    "badge-top": {
        "scene": (256, 310, 0.74),
        "text": {"x": 72, "y": 38, "width": 368, "height": 148},
    },
    "badge-side": {
        "scene": (156, 260, 0.76),
        "text": {"x": 264, "y": 126, "width": 214, "height": 236},
    },
}


ROTATIONS = (-2.5, 0.0, 1.8, -1.2, 2.2, 0.0, -1.8, 1.0)


def entries() -> tuple[Entry, ...]:
    matrix = read_json(ROOT / "content" / "workday-reactions-matrix-v1.json")
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
            pose=item["pose"],
            mood=item["mood"],
        )
        for item in matrix["entries"]
    )


def star_points(cx: float, cy: float, outer: float, inner: float) -> str:
    values = []
    for index in range(10):
        angle = math.radians(-90 + index * 36)
        radius = outer if index % 2 == 0 else inner
        values.append(
            f"{cx + math.cos(angle) * radius:.1f},"
            f"{cy + math.sin(angle) * radius:.1f}"
        )
    return " ".join(values)


def mood_face(mood: str) -> str:
    positive = {
        "happy", "excited", "proud", "impressed", "amused", "grateful",
        "kind", "open", "encouraging", "bright", "relieved", "playful",
        "hopeful",
    }
    narrow = {"focused", "serious", "annoyed", "firm", "determined"}
    wide = {"worried", "stressed", "shocked", "confused", "alert", "curious"}
    tired = mood in {"tired", "relaxed", "calm"}
    if mood in positive:
        eyes = (
            f'<path d="M-47 -63 Q-31 -78 -15 -62 M15 -62 Q31 -78 47 -63" '
            f'fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'
        )
    else:
        eye_height = 20 if mood in wide else 12 if mood in narrow or tired else 17
        pupil_y = -61 if mood in wide else -58
        eyes = (
            f'<ellipse cx="-31" cy="-61" rx="18" ry="{eye_height}" fill="#FFFFFF"/>'
            f'<ellipse cx="31" cy="-61" rx="18" ry="{eye_height}" fill="#FFFFFF"/>'
            f'<circle cx="-29" cy="{pupil_y}" r="7" fill="{INK}"/>'
            f'<circle cx="29" cy="{pupil_y}" r="7" fill="{INK}"/>'
        )
        if mood in narrow:
            eyes += (
                f'<path d="M-52 -79 L-14 -73 M14 -73 L52 -79" '
                f'stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
            )
        elif mood in wide:
            eyes += (
                f'<path d="M-51 -86 Q-32 -95 -13 -84 M13 -84 Q32 -95 51 -86" '
                f'fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
            )
    if mood in positive or mood in {"confident", "bright"}:
        mouth = (
            f'<path d="M-31 -20 Q0 12 32 -20" fill="none" stroke="{INK}" '
            'stroke-width="9" stroke-linecap="round"/>'
        )
    elif mood in {"shocked", "stressed", "worried", "confused", "alert"}:
        mouth = f'<ellipse cx="0" cy="-14" rx="13" ry="18" fill="{INK}"/>'
    elif mood in {"sorry", "embarrassed", "tired", "annoyed"}:
        mouth = (
            f'<path d="M-25 -5 Q0 -27 25 -5" fill="none" stroke="{INK}" '
            'stroke-width="9" stroke-linecap="round"/>'
        )
    else:
        mouth = (
            f'<path d="M-22 -15 Q0 -3 22 -15" fill="none" stroke="{INK}" '
            'stroke-width="8" stroke-linecap="round"/>'
        )
    blush = ""
    if mood in positive | {"embarrassed", "sorry"}:
        blush = (
            f'<ellipse cx="-62" cy="-27" rx="15" ry="7" fill="{CORAL}" opacity=".38"/>'
            f'<ellipse cx="62" cy="-27" rx="15" ry="7" fill="{CORAL}" opacity=".38"/>'
        )
    return eyes + mouth + blush


def arms_for_pose(pose: str) -> str:
    stroke = f'stroke="{INK}" stroke-width="18" stroke-linecap="round"'
    fur = f'stroke="{FUR}" stroke-width="14" stroke-linecap="round"'
    if pose == "cheer":
        return f'<path d="M-63 58 Q-100 8 -102 -40 M63 58 Q100 8 102 -40" fill="none" {stroke}/><path d="M-63 58 Q-100 8 -102 -40 M63 58 Q100 8 102 -40" fill="none" {fur}/>'
    if pose in {"wave", "heart"}:
        return f'<path d="M-61 60 Q-94 35 -101 -18 M61 60 Q76 89 94 92" fill="none" {stroke}/><path d="M-61 60 Q-94 35 -101 -18 M61 60 Q76 89 94 92" fill="none" {fur}/><circle cx="-102" cy="-30" r="13" fill="{CREAM}" stroke="{INK}" stroke-width="7"/>'
    if pose in {"shrug", "stop"}:
        return f'<path d="M-62 62 Q-102 56 -119 26 M62 62 Q102 56 119 26" fill="none" {stroke}/><path d="M-62 62 Q-102 56 -119 26 M62 62 Q102 56 119 26" fill="none" {fur}/><circle cx="-121" cy="22" r="13" fill="{CREAM}" stroke="{INK}" stroke-width="7"/><circle cx="121" cy="22" r="13" fill="{CREAM}" stroke="{INK}" stroke-width="7"/>'
    if pose in {"think", "facepalm", "listen", "phone"}:
        return f'<path d="M-62 61 Q-88 26 -70 -20 M62 61 Q82 82 93 88" fill="none" {stroke}/><path d="M-62 61 Q-88 26 -70 -20 M62 61 Q82 82 93 88" fill="none" {fur}/><circle cx="-66" cy="-29" r="13" fill="{CREAM}" stroke="{INK}" stroke-width="7"/>'
    if pose in {"point", "present", "thumb"}:
        return f'<path d="M-62 62 Q-82 88 -97 92 M62 62 Q99 36 117 6" fill="none" {stroke}/><path d="M-62 62 Q-82 88 -97 92 M62 62 Q99 36 117 6" fill="none" {fur}/><circle cx="119" cy="2" r="13" fill="{CREAM}" stroke="{INK}" stroke-width="7"/>'
    if pose == "run":
        return f'<path d="M-62 60 Q-96 29 -115 46 M62 60 Q91 87 111 71" fill="none" {stroke}/><path d="M-62 60 Q-96 29 -115 46 M62 60 Q91 87 111 71" fill="none" {fur}/>'
    if pose == "bow":
        return f'<path d="M-60 60 Q-30 93 0 82 M60 60 Q30 93 0 82" fill="none" {stroke}/><path d="M-60 60 Q-30 93 0 82 M60 60 Q30 93 0 82" fill="none" {fur}/>'
    return f'<path d="M-62 60 Q-72 91 -47 102 M62 60 Q72 91 47 102" fill="none" {stroke}/><path d="M-62 60 Q-72 91 -47 102 M62 60 Q72 91 47 102" fill="none" {fur}/>'


def pace_character(entry: Entry) -> str:
    lean = -4 if entry.pose in {"run", "point"} else 3 if entry.pose in {"rest", "bow"} else 0
    legs = (
        f'<path d="M-33 111 L-39 145 M33 111 L39 145" stroke="{INK}" stroke-width="25" stroke-linecap="round"/>'
        f'<path d="M-33 111 L-39 145 M33 111 L39 145" stroke="{FUR_DARK}" stroke-width="17" stroke-linecap="round"/>'
        f'<path d="M-57 150 H-22 M22 150 H57" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'
        f'<path d="M-55 150 H-24 M24 150 H55" stroke="{CREAM}" stroke-width="10" stroke-linecap="round"/>'
    )
    tail = (
        f'<path d="M62 65 Q139 45 117 115 Q102 156 63 129" fill="none" stroke="{INK}" stroke-width="48" stroke-linecap="round"/>'
        f'<path d="M62 65 Q139 45 117 115 Q102 156 63 129" fill="none" stroke="{FUR}" stroke-width="37" stroke-linecap="round"/>'
        f'<path d="M101 61 Q125 77 128 95 M111 122 Q91 131 75 126" fill="none" stroke="{CREAM}" stroke-width="13" stroke-linecap="round" opacity=".9"/>'
    )
    body = (
        f'<rect x="-68" y="36" width="136" height="95" rx="48" fill="{FUR}" stroke="{INK}" stroke-width="9"/>'
        f'<path d="M-43 43 Q0 68 43 43 L35 121 H-35 Z" fill="{CREAM}" opacity=".96"/>'
        f'<path d="M0 47 L-15 72 L0 91 L15 72 Z" fill="{TEAL}" stroke="{INK}" stroke-width="6"/>'
        f'<path d="M0 90 V119" stroke="{TEAL}" stroke-width="14" stroke-linecap="round"/>'
    )
    head = (
        f'<circle cx="-62" cy="-102" r="35" fill="{FUR_DARK}" stroke="{INK}" stroke-width="9"/>'
        f'<circle cx="62" cy="-102" r="35" fill="{FUR_DARK}" stroke="{INK}" stroke-width="9"/>'
        f'<circle cx="-62" cy="-102" r="18" fill="{CREAM}"/>'
        f'<circle cx="62" cy="-102" r="18" fill="{CREAM}"/>'
        f'<rect x="-91" y="-126" width="182" height="146" rx="70" fill="{FUR}" stroke="{INK}" stroke-width="10"/>'
        f'<path d="M-82 -85 Q-43 -119 -4 -79 Q-40 -41 -79 -55 Z M82 -85 Q43 -119 4 -79 Q40 -41 79 -55 Z" fill="{FUR_DARK}"/>'
        f'<path d="M-80 -117 Q-46 -144 -13 -119 Q-31 -89 -61 -89 Z M80 -117 Q46 -144 13 -119 Q31 -89 61 -89 Z" fill="{CREAM}" opacity=".94"/>'
        f'<ellipse cx="0" cy="-22" rx="61" ry="44" fill="{CREAM}"/>'
        f'<path d="M-13 -44 Q0 -57 13 -44 Q10 -29 0 -27 Q-10 -29 -13 -44 Z" fill="{INK}"/>'
        + mood_face(entry.mood)
    )
    return (
        f'<g transform="rotate({lean})">'
        '<ellipse cx="0" cy="160" rx="94" ry="16" fill="#20324B" opacity=".18"/>'
        + tail + legs + body + arms_for_pose(entry.pose) + head + '</g>'
    )


def prop_kind(effect: str) -> str:
    if any(token in effect for token in ("bullseye", "target", "focus-ring")):
        return "target"
    if any(token in effect for token in ("trophy", "medal")):
        return "trophy"
    if any(token in effect for token in ("coins", "paid", "invoice", "deal", "lead-magnet")):
        return "money"
    if any(token in effect for token in ("calendar", "today", "tomorrow")):
        return "calendar"
    if any(token in effect for token in ("battery",)):
        return "battery"
    if any(token in effect for token in ("rain", "storm")):
        return "weather"
    if any(token in effect for token in ("lunch",)):
        return "food"
    if any(token in effect for token in ("briefcase", "weekend-bag")):
        return "briefcase"
    if any(token in effect for token in ("puzzle",)):
        return "puzzle"
    if any(token in effect for token in ("gavel",)):
        return "gavel"
    if any(token in effect for token in ("paper-stack", "paper-wave", "notebook", "sticky-note")):
        return "paper"
    if any(token in effect for token in ("headset", "muted-mic")):
        return "audio"
    if any(token in effect for token in ("check", "stamp", "finish-flag")):
        return "check"
    if any(token in effect for token in ("laptop", "video", "camera", "analytics")):
        return "screen"
    if any(token in effect for token in ("clock", "hourglass", "stopwatch", "sunset")):
        return "time"
    if any(token in effect for token in ("rocket", "launch", "plane", "speed", "return")):
        return "rocket"
    if any(token in effect for token in ("coffee", "mug", "lunch")):
        return "cup"
    if any(token in effect for token in ("phone", "headset", "mic", "speech", "feedback", "megaphone")):
        return "communication"
    if any(token in effect for token in ("chart", "progress", "arrow", "growth", "numbers")):
        return "chart"
    if any(token in effect for token in ("star",)):
        return "award"
    if any(token in effect for token in ("warning", "alert", "siren", "block", "no-sign", "repeat")):
        return "warning"
    if any(token in effect for token in ("wrench", "gear", "puzzle", "bulb", "solution", "edit")):
        return "tool"
    if any(token in effect for token in ("heart", "hand", "team", "shield", "help", "lifebuoy", "baton")):
        return "team"
    if any(token in effect for token in ("battery", "pillow", "hammock", "moon", "vacation", "rain", "storm")):
        return "rest"
    return "document"


def prop_art(entry: Entry, index: int) -> str:
    primary, secondary, highlight = CATEGORY_PALETTES[entry.category]
    if entry.layout == "caption-left":
        side = -1
    elif entry.layout in {"caption-right", "speech-right", "badge-side"}:
        side = 1
    else:
        side = -1 if index % 2 else 1
    x = 112 * side
    kind = prop_kind(entry.effect)
    stroke = f'stroke="{INK}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"'
    if kind == "target":
        art = (
            f'<circle cx="0" cy="0" r="65" fill="#FFFDF7" {stroke}/>'
            f'<circle cx="0" cy="0" r="45" fill="{primary}"/>'
            f'<circle cx="0" cy="0" r="25" fill="#FFFDF7"/>'
            f'<circle cx="0" cy="0" r="10" fill="{CORAL}"/>'
            f'<path d="M-78 73 L18 -14 M10 -33 L31 -25 L29 -4" fill="none" stroke="{secondary}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    elif kind == "trophy":
        art = (
            f'<path d="M-50 -61 H50 V-8 Q43 48 0 54 Q-43 48 -50 -8 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-50 -39 Q-88 -43 -81 -6 Q-74 29 -42 22 M50 -39 Q88 -43 81 -6 Q74 29 42 22" fill="none" {stroke}/>'
            f'<path d="M0 54 V76 M-37 86 H37" fill="none" stroke="{secondary}" stroke-width="13" stroke-linecap="round"/>'
            f'<polygon points="{star_points(0, -10, 24, 10)}" fill="{primary}"/>'
        )
    elif kind == "money":
        art = (
            f'<rect x="-72" y="-42" width="144" height="84" rx="13" fill="{primary}" {stroke}/>'
            f'<circle cx="0" cy="0" r="25" fill="{highlight}" stroke="{secondary}" stroke-width="6"/>'
            f'<path d="M0 -17 V17 M12 -10 Q0 -19 -11 -9 Q-18 0 2 4 Q18 8 11 17 Q2 25 -13 15" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="-54" cy="-23" r="8" fill="{highlight}"/><circle cx="54" cy="23" r="8" fill="{highlight}"/>'
        )
    elif kind == "calendar":
        art = (
            f'<rect x="-65" y="-61" width="130" height="126" rx="15" fill="#FFFDF7" {stroke}/>'
            f'<path d="M-65 -25 H65" stroke="{primary}" stroke-width="15"/>'
            f'<path d="M-35 -77 V-45 M35 -77 V-45" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M-33 7 H-15 M8 7 H26 M-33 35 H-15 M8 35 H26" stroke="{secondary}" stroke-width="9" stroke-linecap="round"/>'
        )
    elif kind == "battery":
        art = (
            f'<rect x="-71" y="-39" width="132" height="78" rx="14" fill="#FFFDF7" {stroke}/>'
            f'<rect x="61" y="-17" width="18" height="34" rx="5" fill="{INK}"/>'
            f'<rect x="-55" y="-23" width="32" height="46" rx="7" fill="{CORAL}"/>'
            f'<path d="M-9 -21 L-28 7 H-7 L-19 31 L21 -8 H0 L12 -21 Z" fill="{highlight}"/>'
        )
    elif kind == "weather":
        art = (
            f'<path d="M-66 11 Q-72 -28 -36 -37 Q-17 -72 18 -47 Q57 -55 68 -18 Q90 -8 78 20 H-65 Q-83 17 -66 11 Z" fill="#B9C8D8" {stroke}/>'
            f'<path d="M-46 39 L-58 70 M-5 39 L-17 77 M36 39 L24 70" stroke="{SKY}" stroke-width="11" stroke-linecap="round"/>'
        )
    elif kind == "food":
        art = (
            f'<rect x="-73" y="-29" width="146" height="86" rx="18" fill="{primary}" {stroke}/>'
            f'<path d="M-42 -29 Q-26 -70 0 -38 Q28 -72 43 -29" fill="{highlight}" {stroke}/>'
            f'<circle cx="-28" cy="15" r="12" fill="{CORAL}"/><circle cx="8" cy="11" r="12" fill="{TEAL}"/><circle cx="38" cy="21" r="12" fill="{GOLD}"/>'
        )
    elif kind == "briefcase":
        art = (
            f'<rect x="-78" y="-35" width="156" height="105" rx="18" fill="{primary}" {stroke}/>'
            f'<path d="M-31 -35 V-62 H31 V-35 M-78 7 H78" fill="none" {stroke}/>'
            f'<rect x="-13" y="-3" width="26" height="26" rx="5" fill="{highlight}" stroke="{INK}" stroke-width="6"/>'
        )
    elif kind == "puzzle":
        art = (
            f'<path d="M-66 -54 H-15 Q-25 -29 -4 -20 Q18 -11 24 -36 Q28 -49 18 -54 H66 V-8 Q42 -18 34 4 Q27 27 53 33 Q61 35 66 29 V69 H16 Q25 45 4 38 Q-20 30 -25 54 Q-28 64 -20 69 H-66 V24 Q-43 35 -34 13 Q-26 -10 -51 -17 Q-60 -19 -66 -13 Z" fill="{primary}" {stroke}/>'
        )
    elif kind == "gavel":
        art = (
            f'<g transform="rotate(-28)"><rect x="-18" y="-73" width="36" height="142" rx="13" fill="{highlight}" {stroke}/><rect x="-63" y="-79" width="126" height="47" rx="14" fill="{primary}" {stroke}/></g>'
            f'<path d="M-57 73 H59" stroke="{secondary}" stroke-width="18" stroke-linecap="round"/>'
        )
    elif kind == "paper":
        art = (
            f'<rect x="-54" y="-65" width="108" height="125" rx="11" fill="#FFFDF7" {stroke}/>'
            f'<rect x="-68" y="-50" width="108" height="125" rx="11" fill="{highlight}" {stroke}/>'
            f'<rect x="-81" y="-35" width="108" height="125" rx="11" fill="#FFFDF7" {stroke}/>'
            f'<path d="M-59 -2 H5 M-59 23 H5 M-59 48 H-8" stroke="{primary}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "audio":
        art = (
            f'<path d="M-60 5 V-17 Q-60 -65 0 -65 Q60 -65 60 -17 V5" fill="none" stroke="{primary}" stroke-width="19" stroke-linecap="round"/>'
            f'<rect x="-75" y="-8" width="32" height="64" rx="13" fill="{highlight}" {stroke}/><rect x="43" y="-8" width="32" height="64" rx="13" fill="{highlight}" {stroke}/>'
            f'<path d="M58 47 Q51 73 24 72" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "check":
        art = (
            f'<rect x="-64" y="-62" width="128" height="124" rx="18" fill="#FFFDF7" {stroke}/>'
            f'<path d="M-38 3 L-10 30 L43 -28" fill="none" stroke="{primary}" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    elif kind == "screen":
        art = (
            f'<rect x="-66" y="-46" width="132" height="88" rx="13" fill="{INK}"/>'
            f'<rect x="-54" y="-34" width="108" height="64" rx="7" fill="{SKY}"/>'
            f'<path d="M-29 13 L-5 -9 L14 2 L41 -25" fill="none" stroke="{TEAL}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M0 42 V62 M-35 66 H35" {stroke}/>'
        )
    elif kind == "time":
        art = (
            f'<circle cx="0" cy="0" r="61" fill="{highlight}" {stroke}/>'
            f'<circle cx="0" cy="0" r="45" fill="#FFFDF7" stroke="{secondary}" stroke-width="6"/>'
            f'<path d="M0 0 V-27 M0 0 L25 14" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "rocket":
        art = (
            f'<path d="M-12 43 Q-52 18 -42 -24 Q-27 -70 10 -82 Q43 -48 44 -5 Q43 35 12 48 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="6" cy="-24" r="18" fill="{SKY}" {stroke}/>'
            f'<path d="M-24 31 L-57 62 L-15 54 M29 31 L55 65 L17 53" fill="{highlight}" {stroke}/>'
            f'<path d="M-9 48 Q2 95 15 48" fill="{CORAL}" {stroke}/>'
        )
    elif kind == "cup":
        art = (
            f'<path d="M-55 -25 H40 V52 Q34 74 -8 74 Q-50 74 -55 52 Z" fill="{primary}" {stroke}/>'
            f'<path d="M40 -7 Q78 -6 69 31 Q61 55 38 46" fill="none" {stroke}/>'
            f'<path d="M-29 -45 Q-46 -68 -22 -84 M1 -45 Q-15 -70 9 -89 M30 -45 Q13 -65 36 -82" fill="none" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "communication":
        art = (
            f'<path d="M-66 -50 H66 V35 H14 L-17 66 L-13 35 H-66 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="-30" cy="-7" r="8" fill="#FFFFFF"/><circle cx="0" cy="-7" r="8" fill="#FFFFFF"/><circle cx="30" cy="-7" r="8" fill="#FFFFFF"/>'
        )
    elif kind == "chart":
        art = (
            f'<rect x="-68" y="-55" width="136" height="112" rx="12" fill="#FFFDF7" {stroke}/>'
            f'<rect x="-48" y="16" width="24" height="25" rx="5" fill="{CORAL}"/>'
            f'<rect x="-12" y="-7" width="24" height="48" rx="5" fill="{highlight}"/>'
            f'<rect x="24" y="-33" width="24" height="74" rx="5" fill="{primary}"/>'
            f'<path d="M-45 -19 L-8 -37 L25 -49 L47 -72" fill="none" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "award":
        art = (
            f'<circle cx="0" cy="-7" r="55" fill="{highlight}" {stroke}/>'
            f'<polygon points="{star_points(0, -7, 34, 15)}" fill="{primary}"/>'
            f'<path d="M-34 38 L-54 85 L-12 68 L0 91 L14 68 L55 84 L34 38" fill="{secondary}" {stroke}/>'
        )
    elif kind == "warning":
        art = (
            f'<path d="M0 -73 L78 62 H-78 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M0 -32 V20" stroke="{INK}" stroke-width="15" stroke-linecap="round"/>'
            f'<circle cx="0" cy="43" r="9" fill="{INK}"/>'
        )
    elif kind == "tool":
        art = (
            f'<path d="M-6 -78 A42 42 0 0 0 32 -18 L-55 69 L-27 97 L60 10 A42 42 0 0 0 78 -39 L45 -6 L13 -38 L45 -70 A42 42 0 0 0 -6 -78 Z" fill="{primary}" {stroke}/>'
            f'<circle cx="-31" cy="67" r="10" fill="{highlight}"/>'
        )
    elif kind == "team":
        art = (
            f'<path d="M0 67 C-94 10 -73 -69 -18 -49 C-3 -44 0 -23 0 -23 C0 -23 6 -47 29 -50 C84 -56 95 18 0 67 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-47 -3 L-12 27 L48 -34" fill="none" stroke="{highlight}" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    elif kind == "rest":
        art = (
            f'<rect x="-76" y="-42" width="152" height="86" rx="23" fill="{primary}" {stroke}/>'
            f'<rect x="-55" y="-23" width="46" height="43" rx="14" fill="{CREAM}"/>'
            f'<path d="M-72 44 Q0 83 72 44" fill="none" stroke="{secondary}" stroke-width="13" stroke-linecap="round"/>'
            f'<path d="M20 -73 Q2 -59 17 -42 Q30 -30 48 -43 Q20 -38 20 -73 Z" fill="{highlight}"/>'
        )
    else:
        art = (
            f'<rect x="-61" y="-72" width="122" height="144" rx="15" fill="#FFFDF7" {stroke}/>'
            f'<path d="M-39 -36 H38 M-39 -8 H38 M-39 20 H24" fill="none" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M20 45 L35 58 L58 30" fill="none" stroke="{primary}" stroke-width="10" stroke-linecap="round"/>'
        )
    return f'<g transform="translate({x} 28) scale(.68)">{art}</g>'


def scene_svg(entry: Entry, index: int) -> str:
    x, y, scale = LAYOUTS[entry.layout]["scene"]
    return svg(
        f'<g transform="translate({x} {y}) scale({scale})">'
        + pace_character(entry)
        + prop_art(entry, index)
        + '</g>'
    )


def accent_svg(entry: Entry, index: int) -> str:
    primary, secondary, highlight = CATEGORY_PALETTES[entry.category]
    x, y, scale = LAYOUTS[entry.layout]["scene"]
    mode = index % 4
    if mode == 0:
        local = (
            f'<polygon points="{star_points(-125, -115, 20, 8)}" fill="{highlight}"/>'
            f'<polygon points="{star_points(128, -92, 15, 6)}" fill="{primary}"/>'
            f'<circle cx="-135" cy="42" r="8" fill="{secondary}"/>'
        )
    elif mode == 1:
        local = (
            f'<path d="M-135 -55 H-105 M-125 -72 L-107 -63 M-125 -38 L-107 -47 M108 -78 H138 M117 -95 L135 -86" fill="none" stroke="{primary}" stroke-width="8" stroke-linecap="round"/>'
            f'<circle cx="132" cy="42" r="8" fill="{highlight}"/>'
        )
    elif mode == 2:
        local = (
            f'<path d="M-134 -74 q24 -27 47 -2 M95 -88 q24 -27 47 -2" fill="none" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/>'
            f'<polygon points="{star_points(126, 52, 15, 6)}" fill="{highlight}"/>'
        )
    else:
        local = (
            f'<circle cx="-128" cy="-80" r="9" fill="{primary}"/><circle cx="-103" cy="-105" r="6" fill="{highlight}"/>'
            f'<circle cx="126" cy="-76" r="9" fill="{secondary}"/><circle cx="108" cy="-108" r="6" fill="{highlight}"/>'
        )
    return svg(f'<g transform="translate({x} {y}) scale({scale})">{local}</g>')


def text_area(entry: Entry) -> dict[str, int]:
    return dict(LAYOUTS[entry.layout]["text"])


def animation_family(motion: str, index: int) -> tuple[str, str, float, float]:
    if motion in {"pop", "pulse", "stamp", "breathe", "glow"}:
        return ("text_pulse", "scale_x", 1.0, 1.045 if motion != "pop" else 1.075)
    if motion in {"wobble", "shake", "nod", "point", "rewind", "ring", "write", "scan", "type", "tick", "sync", "blink"}:
        value = 3.5 if index % 2 else -3.5
        return ("text_wobble", "rotation_degrees", 0.0, value)
    if motion in {"slide", "launch", "catch"}:
        return ("text_float", "translate_x", 0.0, 7.0 if index % 2 else -7.0)
    return ("text_float", "translate_y", 0.0, -7.0 if motion not in {"drop"} else 6.0)


def animation_document(entry: Entry, index: int) -> dict[str, Any]:
    duration = (900, 1000, 1100, 1200)[index % 4]
    middle = duration // 2
    overlay, prop, rest, peak = animation_family(entry.motion, index)
    accent_prop = "rotation_degrees" if prop != "rotation_degrees" else "translate_y"
    accent_peak = (4.0 if index % 2 else -4.0) if accent_prop == "rotation_degrees" else -5.0
    return {
        "duration_ms": duration,
        "fps": 12,
        "loop": "loop",
        "overlays": [overlay],
        "tracks": [
            {
                "target": f"scene-{entry.slug}",
                "property": prop,
                "keyframes": [
                    {"at_ms": 0, "value": rest, "easing": "ease_in_out"},
                    {"at_ms": middle, "value": peak, "easing": "ease_in_out"},
                    {"at_ms": duration, "value": rest, "easing": "ease_in_out"}
                ]
            },
            {
                "target": f"accent-{entry.slug}",
                "property": accent_prop,
                "keyframes": [
                    {"at_ms": 0, "value": 0.0, "easing": "ease_in_out"},
                    {"at_ms": middle, "value": accent_peak, "easing": "ease_in_out"},
                    {"at_ms": duration, "value": 0.0, "easing": "ease_in_out"}
                ]
            }
        ]
    }


def pack_document(items: tuple[Entry, ...]) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(items):
        scene_id = f"scene-{entry.slug}"
        accent_id = f"accent-{entry.slug}"
        layers.extend(
            [
                {"id": scene_id, "source": f"layers/{index:02d}-{scene_id}.svg", "z": 10 + index * 2, "pivot": "composition", "depth": 0.0},
                {"id": accent_id, "source": f"layers/{index:02d}-{accent_id}.svg", "z": 11 + index * 2, "pivot": "composition", "depth": 0.1},
            ]
        )
        expressions[entry.slug] = [scene_id, accent_id]
        primary, secondary, highlight = CATEGORY_PALETTES[entry.category]
        font_id = FONT_VOICES[entry.font_voice][0]
        styles[f"{entry.slug}-main"] = {
            "font": font_id,
            "safe_area": text_area(entry),
            "min_font_size": 24,
            "max_font_size": 128,
            "max_lines": 2,
            "fill": rgb(primary),
            "outline": {"width": 7, "color": rgb(INK)},
            "depth_shell": {"offset_x": 6 + index % 2, "offset_y": 7 + index % 2, "color": rgb(secondary)},
            "highlight_shell": {"offset_x": -2, "offset_y": -2, "color": rgb(highlight)},
        }
    return {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "canvas": {"width": CANVAS, "height": CANVAS},
        "layers": layers,
        "base_layers": [],
        "expressions": expressions,
        "poses": {pose: [] for pose in sorted({item.pose for item in items})},
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT; bundled fonts separately SIL OFL 1.1",
            "source": f"generate_workday_reactions_pack.py v{GENERATOR_VERSION}; original procedural character scenes",
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
            "collision_bounds": "layout-specific-authored-safe-areas",
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
        "sticker_id": f"workday-reactions-{entry.slug}",
        "pack_id": PACK_ID,
        "phrase_id": entry.semantic_id,
        "recipe_id": f"workday-character-scene.{entry.motion}",
        "intent": entry.semantic_id,
        "alt_text": f"Pace the red panda in a workplace scene saying {entry.label}",
        "accessible_description": f"Pace performs a {entry.pose} pose with a {entry.effect.replace('-', ' ')} cue and the phrase {entry.label}",
        "expression": entry.slug,
        "pose": entry.pose,
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
        write_text(pack_root / "layers" / f"{index:02d}-scene-{entry.slug}.svg", scene_svg(entry, index))
        write_text(pack_root / "layers" / f"{index:02d}-accent-{entry.slug}.svg", accent_svg(entry, index))
        write_json(pack_root / "stickers" / f"{entry.slug}.json", sticker_document(entry, index))
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
                    "sticker_id": f"workday-reactions-{entry.slug}",
                    "triggers": [
                        {"text": alias, "locale": "en", "match": "exact-phrase", "weight": 1.0 if alias == entry.label.lower().rstrip("!?.") else 0.84}
                        for alias in entry.aliases
                    ],
                }
                for entry in items
            ],
        },
    )
    category_counts = dict(sorted(Counter(item.category for item in items).items()))
    write_json(
        destination / "generation-manifest.json",
        {
            "schema_version": 1,
            "generator": "generate_workday_reactions_pack.py",
            "generator_version": GENERATOR_VERSION,
            "pack_id": PACK_ID,
            "pack_contract": "contracts/workday-reactions-pack-v1.json",
            "content_matrix": "content/workday-reactions-matrix-v1.json",
            "sticker_count": len(items),
            "category_counts": category_counts,
            "font_voice_count": len({item.font_voice for item in items}),
            "motion_family_count": len({item.motion for item in items}),
            "composition_system_count": len({item.layout for item in items}),
            "effect_family_count": len({item.effect for item in items}),
            "visual_prop_archetype_count": len({prop_kind(item.effect) for item in items}),
            "pose_family_count": len({item.pose for item in items}),
            "mood_family_count": len({item.mood for item in items}),
            "single_fitted_text_layout_per_sticker": True,
            "independently_typeset_duplicate_text_blocks": 0,
            "owner_approval": "contracts/workday-reactions-owner-approval-v1.json",
            "production_use": "approved-for-public-production",
        },
    )


def build_contact_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns, cell_w, cell_h = 8, 216, 230
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_w + 40, rows * cell_h + 92), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "WORKDAY REACTIONS · 96-STICKER FAMILY REVIEW", fill=INK, font=review_font(32))
    draw.text((24, 55), "Pace identity · workplace semantics · text-placement variety", fill="#65758B", font=review_font(16))
    for index, entry in enumerate(items):
        x = 20 + (index % columns) * cell_w
        y = 82 + (index // columns) * cell_h
        draw.rounded_rectangle((x, y, x + 200, y + 214), radius=20, fill="#FFFFFF", outline="#D9E2EC", width=2)
        image = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        image.thumbnail((186, 186), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + (200 - image.width) // 2, y + 2))
        draw.text((x + 9, y + 186), entry.label, fill=INK, font=review_font(12))
        draw.text((x + 9, y + 201), f"{entry.category} · {entry.layout}", fill="#65758B", font=review_font(9))
    path = review_root / "contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_category_sheets(review_root: Path, items: tuple[Entry, ...]) -> list[Path]:
    paths = []
    for category in CATEGORY_PALETTES:
        selected = [item for item in items if item.category == category]
        canvas = Image.new("RGBA", (4 * 300 + 40, 3 * 300 + 90), "#EEF3F8")
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 20), f"{category.upper()} · 12 SCENES", fill=INK, font=review_font(31))
        for index, entry in enumerate(selected):
            x = 20 + (index % 4) * 300
            y = 74 + (index // 4) * 300
            draw.rounded_rectangle((x, y, x + 282, y + 282), radius=24, fill="#FFFFFF", outline="#D9E2EC", width=2)
            image = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
            image.thumbnail((248, 248), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + (282 - image.width) // 2, y + 1))
            draw.text((x + 12, y + 250), f"{entry.label} · {entry.pose}", fill=INK, font=review_font(12))
        path = review_root / f"category-{category}.png"
        canvas.convert("RGB").save(path, optimize=True)
        paths.append(path)
    return paths


def build_small_display_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    sizes = (80, 100, 160)
    columns, rows = 12, 8
    cell_w, cell_h = 178, 190
    panel_w = columns * cell_w + 28
    canvas = Image.new("RGBA", (panel_w * 3 + 24, rows * cell_h + 104), "#26384F")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "ALL 96 · 80 / 100 / 160 PX READABILITY", fill="#FFFFFF", font=review_font(31))
    for panel, size in enumerate(sizes):
        panel_x = 12 + panel * panel_w
        draw.text((panel_x + 8, 58), f"{size}px" + (" · RECOMMENDED" if size == 100 else ""), fill="#FFFFFF", font=review_font(17))
        for index, entry in enumerate(items):
            x = panel_x + (index % columns) * cell_w
            y = 88 + (index // columns) * cell_h
            draw.rounded_rectangle((x + 3, y, x + cell_w - 5, y + 176), radius=16, fill="#F8FAFC")
            source = first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
            image = source.resize((size, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + (cell_w - size) // 2, y + 4 + (142 - size) // 2))
            label = entry.label if len(entry.label) <= 19 else entry.label[:18] + "…"
            draw.text((x + 8, y + 151), label, fill=INK, font=review_font(10))
    path = review_root / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_motion_sheet(review_root: Path, items: tuple[Entry, ...]) -> Path:
    columns, cell_w, cell_h = 6, 270, 176
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_w + 40, rows * cell_h + 90), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "ALL 96 LOOPS · START / MID / CLOSURE", fill=INK, font=review_font(30))
    for index, entry in enumerate(items):
        x = 20 + (index % columns) * cell_w
        y = 72 + (index // columns) * cell_h
        draw.rounded_rectangle((x, y, x + 254, y + 160), radius=18, fill="#FFFFFF", outline="#D9E2EC", width=2)
        frames = image_frames(review_root / "assets" / f"{entry.slug}.webp")
        for frame_index, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
            image = frame.resize((72, 72), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + 7 + frame_index * 81, y + 6))
        draw.text((x + 9, y + 83), entry.label, fill=INK, font=review_font(12))
        draw.text((x + 9, y + 101), f"{entry.motion} · {entry.effect}", fill="#65758B", font=review_font(9))
        draw.text((x + 9, y + 135), "START", fill="#7A8798", font=review_font(8))
        draw.text((x + 91, y + 135), "MID", fill="#7A8798", font=review_font(8))
        draw.text((x + 170, y + 135), "CLOSURE", fill="#7A8798", font=review_font(8))
    path = review_root / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_animation_html(review_root: Path, items: tuple[Entry, ...]) -> Path:
    figures = "".join(
        f'<figure data-category="{entry.category}"><img src="assets/{entry.slug}.webp" alt="{entry.label} animated workplace sticker"><figcaption>{entry.label}<small>{entry.category} · {entry.pose} · {entry.motion}</small></figcaption></figure>'
        for entry in items
    )
    path = review_root / "animation-review.html"
    write_text(path, '<!doctype html><meta charset="utf-8"><title>Workday Reactions playback</title><style>body{font:16px system-ui;background:#eef3f8;color:#20324b;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}figure{margin:0;background:white;border-radius:20px;padding:10px;text-align:center}img{width:100%;height:auto}figcaption{font-weight:800}small{display:block;color:#65758b;font-weight:500;margin-top:4px}</style><h1>Workday Reactions · all 96 animations</h1><p>Review Pace identity, exact text, scene semantics, layout variety, motion, and loop closure.</p><main>' + figures + '</main>')
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
            raise ValueError(f"{animated} violates 16px margin: {values['minimum_frame_margin_px']}")
        if first_frame(reduced).getchannel("A").getbbox() is None:
            raise ValueError(f"reduced-motion asset is blank: {reduced}")
        values.update({
            "semantic_id": entry.semantic_id,
            "label": entry.label,
            "category": entry.category,
            "font_voice": entry.font_voice,
            "layout": entry.layout,
            "effect": entry.effect,
            "pose": entry.pose,
            "mood": entry.mood,
            "motion": entry.motion,
            "animated_sha256": sha256(animated),
            "reduced_motion_sha256": sha256(reduced),
            "thumbnail_sha256": sha256(thumbnail),
        })
        metrics.append(values)
    artifacts = [build_contact_sheet(review_root, items)]
    artifacts.extend(build_category_sheets(review_root, items))
    artifacts.extend([build_small_display_sheet(review_root, items), build_motion_sheet(review_root, items), build_animation_html(review_root, items)])
    artifact_hashes = {path.name: sha256(path) for path in artifacts}
    owner_approval_path = ROOT / "contracts" / "workday-reactions-owner-approval-v1.json"
    owner_approval = read_json(owner_approval_path)
    if owner_approval["decision"] != "approved":
        raise ValueError("Workday Reactions owner decision is not approved")
    if owner_approval["reviewed_artifacts"] != artifact_hashes:
        raise ValueError("Workday Reactions owner decision does not match rendered artifacts")
    write_json(review_root / "owner-approval.json", owner_approval)
    contract = ROOT / "contracts" / "workday-reactions-pack-v1.json"
    matrix = ROOT / "content" / "workday-reactions-matrix-v1.json"
    write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "workday-reactions-development-review-v1",
            "review_status": "owner-approved",
            "production_use": "approved-for-public-production",
            "owner_approval": "contracts/workday-reactions-owner-approval-v1.json",
            "owner_reviewed_artifacts": owner_approval["reviewed_artifacts"],
            "owner_artifact_hash_match": True,
            "contract_sha256": sha256(contract),
            "matrix_sha256": sha256(matrix),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "sticker_count": len(metrics),
            "category_counts": dict(sorted(Counter(item.category for item in items).items())),
            "animated_sticker_count": sum(bool(item["animated_webp"]) for item in metrics),
            "loop_closed_sticker_count": sum(bool(item["loop_closure"]) for item in metrics),
            "font_voice_count": len({item.font_voice for item in items}),
            "motion_family_count": len({item.motion for item in items}),
            "composition_system_count": len({item.layout for item in items}),
            "effect_family_count": len({item.effect for item in items}),
            "visual_prop_archetype_count": len({prop_kind(item.effect) for item in items}),
            "pose_family_count": len({item.pose for item in items}),
            "mood_family_count": len({item.mood for item in items}),
            "independently_typeset_duplicate_text_block_count": 0,
            "minimum_frame_margin_px": min(item["minimum_frame_margin_px"] for item in metrics),
            "artifacts": artifact_hashes,
            "metrics": metrics,
            "owner_review_questions": [],
        },
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-output", type=Path, default=ROOT / "art" / PACK_ID)
    parser.add_argument("--review-output", type=Path, default=ROOT / "generated" / f"{PACK_ID}-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    executable = args.mascotrender.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"MascotRender CLI is missing: {executable}")
    with tempfile.TemporaryDirectory(prefix="workday-reactions-") as directory:
        stage = Path(directory)
        source = stage / "source"
        review = stage / "review"
        author_sources(source)
        render_review(source, review, executable)
        replace_directory(source, args.source_output.resolve(), args.force)
        replace_directory(review, args.review_output.resolve(), args.force)
    print(args.source_output.resolve())
    print(args.review_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
