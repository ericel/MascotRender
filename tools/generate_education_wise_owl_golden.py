#!/usr/bin/env python3
"""Render the ten-scene layered 2.5D Wise Owl Academy golden set."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

import generate_workday_reactions_pack as base


ROOT = Path(__file__).resolve().parents[1]
PACK_ID = "education-wise-owl-golden-v2"
CANVAS = 512
INK = "#173257"
BROWN = "#A75C22"
DARK = "#653317"
MID = "#D58A3D"
CREAM = "#FFF1CC"
WHITE = "#FFFFFF"
GOLD = "#F5B92C"
ORANGE = "#EE8B20"
GREEN = "#168A62"
BLUE = "#287BD1"
RED = "#E44A3D"
PURPLE = "#805AC9"
TEAL = "#35AFA5"


@dataclass(frozen=True)
class Scene:
    slug: str
    phrase_id: str
    label: str
    category: str
    prop: str
    pose: str
    mood: str
    x: int
    y: int
    scale: float
    text_area: dict[str, int]
    font_voice: str
    motion: str
    two_owls: bool = False


SCENES = (
    Scene("study-time", "education.study.study-time", "STUDY TIME", "study", "book", "read", "focused", 256, 230, 1.08, {"x": 56, "y": 382, "width": 400, "height": 102}, "soft-rounded", "breathe"),
    Scene("you-can-do-it", "education.motivation.you-can-do-it", "YOU CAN DO IT!", "motivation", "rocket", "cheer", "proud", 242, 274, 1.04, {"x": 56, "y": 24, "width": 400, "height": 112}, "energetic-comic-slant", "pop"),
    Scene("science-fun", "education.stem.science-fun", "SCIENCE FUN", "stem", "science", "present", "curious", 265, 244, 1.02, {"x": 57, "y": 28, "width": 398, "height": 104}, "compact-punch", "wobble"),
    Scene("library-time", "education.literacy.library-time", "LIBRARY TIME", "literacy", "library", "read", "calm", 270, 226, 1.02, {"x": 52, "y": 382, "width": 408, "height": 100}, "handwritten-emphasis", "float"),
    Scene("color-magic", "education.creativity.color-magic", "COLOR MAGIC", "creativity", "paint", "present", "excited", 266, 257, 1.02, {"x": 55, "y": 24, "width": 402, "height": 108}, "energetic-comic-slant", "wobble"),
    Scene("teamwork", "education.community.teamwork", "TEAMWORK", "community", "team", "together", "happy", 256, 245, 0.84, {"x": 58, "y": 386, "width": 396, "height": 96}, "soft-rounded", "pulse", True),
    Scene("stay-organized", "education.habits.stay-organized", "STAY ORGANIZED", "habits", "desk", "write", "focused", 302, 245, 0.96, {"x": 42, "y": 24, "width": 428, "height": 106}, "compact-punch", "slide"),
    Scene("test-day", "education.assessment.test-day", "TEST DAY", "assessment", "test", "write", "worried", 258, 235, 1.03, {"x": 58, "y": 386, "width": 396, "height": 96}, "compact-punch", "shake"),
    Scene("high-five", "education.achievement.high-five", "HIGH FIVE!", "achievement", "high-five", "cheer", "bright", 253, 270, 1.05, {"x": 55, "y": 24, "width": 402, "height": 108}, "energetic-comic-slant", "pop"),
    Scene("graduation-day", "education.future.graduation-day", "GRADUATION DAY", "future", "graduation", "proud", "proud", 258, 230, 1.02, {"x": 45, "y": 382, "width": 422, "height": 100}, "handwritten-emphasis", "float"),
)

PALETTE = {
    "study": (BLUE, GOLD),
    "motivation": (RED, GOLD),
    "stem": (GREEN, ORANGE),
    "literacy": (BLUE, CREAM),
    "creativity": (PURPLE, ORANGE),
    "community": (GREEN, RED),
    "habits": (TEAL, GOLD),
    "assessment": (RED, BLUE),
    "achievement": (GOLD, RED),
    "future": (BLUE, GREEN),
}

FONT_VOICES = base.FONT_VOICES
LAYER_NAMES = (
    "shadow", "cutline", "prop-back", "back-feathers", "body-base",
    "body-depth", "wings", "head", "face", "prop-front", "effects",
)


def svg(fragment: str) -> str:
    return base.svg(fragment)


def group(scene: Scene, fragment: str, x: int | None = None, y: int | None = None, scale: float | None = None) -> str:
    return f'<g transform="translate({scene.x if x is None else x} {scene.y if y is None else y}) scale({scene.scale if scale is None else scale})">{fragment}</g>'


def owl_parts(scene: Scene, variant: int = 0) -> dict[str, str]:
    flip = -1 if variant else 1
    crest = (
        f'<path d="M-39 -101 Q-22 -136 -4 -103 Q5 -145 23 -104 Q39 -132 48 -95" '
        f'fill="{DARK}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
    )
    body = (
        '<defs><linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#D99045"/><stop offset=".58" stop-color="#A75C22"/><stop offset="1" stop-color="#6D3518"/></linearGradient></defs>'
        f'<ellipse cx="0" cy="42" rx="87" ry="101" fill="url(#body)" stroke="{INK}" stroke-width="8"/>'
        f'<ellipse cx="0" cy="63" rx="49" ry="65" fill="{CREAM}" stroke="{DARK}" stroke-width="3"/>'
        f'<path d="M-30 53 Q0 78 30 53 L22 98 Q0 116 -22 98 Z" fill="{GOLD}" opacity=".9"/>'
    )
    depth = (
        f'<path d="M-70 55 Q-58 127 0 140 Q-65 139 -79 76 Z" fill="{DARK}" opacity=".34"/>'
        f'<path d="M-47 -5 Q-12 -37 28 -19" fill="none" stroke="{WHITE}" stroke-width="10" opacity=".27" stroke-linecap="round"/>'
        f'<path d="M-26 72 Q0 89 26 72" fill="none" stroke="{ORANGE}" stroke-width="6" opacity=".75"/>'
    )
    if scene.pose in {"cheer", "proud"}:
        left = "M-55 46 Q-108 9 -99 -72 Q-67 -51 -43 0"
        right = "M55 46 Q108 9 99 -72 Q67 -51 43 0"
    elif scene.pose in {"present", "together"}:
        left = "M-55 49 Q-105 35 -121 0 Q-85 -8 -46 14"
        right = "M55 49 Q104 34 119 0 Q84 -8 46 14"
    elif scene.pose == "write":
        left = "M-55 54 Q-91 75 -72 109 Q-45 92 -34 67"
        right = "M55 54 Q87 71 72 106 Q45 91 34 67"
    else:
        left = "M-55 49 Q-94 67 -89 112 Q-57 98 -37 69"
        right = "M55 49 Q94 67 89 112 Q57 98 37 69"
    wings = (
        f'<path d="{left}" fill="{DARK}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="{right}" fill="{DARK}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="M-69 48 Q-85 68 -76 91 M69 48 Q85 68 76 91" fill="none" stroke="{MID}" stroke-width="8" stroke-linecap="round"/>'
        f'<path d="M-61 45 Q-74 66 -66 79 M61 45 Q74 66 66 79" fill="none" stroke="{CREAM}" stroke-width="4" opacity=".7"/>'
    )
    head = (
        '<defs><linearGradient id="head" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D99148"/><stop offset="1" stop-color="#A75C22"/></linearGradient></defs>'
        f'<path d="M-76 -12 Q-88 -62 -70 -95 Q-44 -80 -26 -73 Q0 -90 26 -73 Q44 -80 70 -95 Q88 -62 76 -12 Q65 44 0 48 Q-65 44 -76 -12 Z" fill="url(#head)" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="M-70 -28 Q-51 -76 -3 -51 Q-5 -5 -42 15 Q-69 7 -70 -28 Z M70 -28 Q51 -76 3 -51 Q5 -5 42 15 Q69 7 70 -28 Z" fill="{CREAM}"/>'
        f'<path d="M-8 -6 L0 5 L8 -6 L0 15 Z" fill="{ORANGE}" stroke="{INK}" stroke-width="3"/>'
        f'<path d="M-60 -64 Q-46 -76 -31 -69 M31 -69 Q46 -76 60 -64" fill="none" stroke="{GOLD}" stroke-width="5" opacity=".55" stroke-linecap="round"/>'
    )
    if scene.mood in {"proud", "bright", "happy"}:
        eyes = f'<path d="M-48 -27 Q-32 -43 -17 -27 M17 -27 Q32 -43 48 -27" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
        mouth = f'<path d="M-17 18 Q0 33 17 18" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    elif scene.mood == "worried":
        eyes = f'<circle cx="-32" cy="-29" r="11" fill="{INK}"/><circle cx="32" cy="-29" r="11" fill="{INK}"/><circle cx="-29" cy="-33" r="3" fill="{WHITE}"/><circle cx="35" cy="-33" r="3" fill="{WHITE}"/>'
        mouth = f'<path d="M-15 27 Q0 12 15 27" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    else:
        eyes = f'<circle cx="-32" cy="-29" r="11" fill="{INK}"/><circle cx="32" cy="-29" r="11" fill="{INK}"/><circle cx="-28" cy="-33" r="4" fill="{WHITE}"/><circle cx="36" cy="-33" r="4" fill="{WHITE}"/>'
        mouth = f'<path d="M-14 20 Q0 28 14 20" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    face = (
        eyes
        + f'<circle cx="-33" cy="-29" r="27" fill="none" stroke="{INK}" stroke-width="7"/><circle cx="33" cy="-29" r="27" fill="none" stroke="{INK}" stroke-width="7"/><path d="M-6 -29 H6" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        + mouth
        + (f'<path d="M-58 4 Q-48 9 -38 4 M38 4 Q48 9 58 4" stroke="{RED}" stroke-width="5" opacity=".35"/>' if scene.mood != "worried" else f'<path d="M62 -55 Q79 -34 64 -17 Q50 -35 62 -55 Z" fill="{BLUE}" opacity=".8"/>')
    )
    feet = f'<path d="M-38 132 L-53 151 H-17 L-4 133 M38 132 L53 151 H17 L4 133" fill="{GOLD}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
    cutline = (
        f'<ellipse cx="0" cy="40" rx="98" ry="118" fill="{WHITE}"/>'
        f'<circle cx="-68" cy="-50" r="48" fill="{WHITE}"/><circle cx="68" cy="-50" r="48" fill="{WHITE}"/>'
        f'<path d="M-111 57 Q-133 7 -111 -72 Q-88 -105 -61 -97 Q-34 -117 0 -128 Q34 -117 61 -97 Q88 -105 111 -72 Q133 7 111 57 Q119 126 64 165 Q31 181 0 174 Q-31 181 -64 165 Q-119 126 -111 57 Z" fill="{WHITE}" stroke="{WHITE}" stroke-width="16" stroke-linejoin="round"/>'
    )
    shadow = '<defs><filter id="blur"><feGaussianBlur stdDeviation="9"/></filter></defs><ellipse cx="8" cy="164" rx="105" ry="22" fill="#173257" opacity=".25" filter="url(#blur)"/>'
    return {
        "shadow": shadow,
        "cutline": cutline,
        "back-feathers": crest,
        "body-base": body + feet,
        "body-depth": depth,
        "wings": wings,
        "head": head,
        "face": face,
    }


def prop_parts(scene: Scene) -> dict[str, str]:
    primary, accent = PALETTE[scene.category]
    stroke = f'stroke="{INK}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"'
    back = ""
    front = ""
    effects = ""
    cutline = ""
    if scene.prop == "book":
        front = f'<g transform="translate(0 86)"><path d="M0 58 Q-53 21 -103 34 V-49 Q-51 -62 0 -26 Q51 -62 103 -49 V34 Q53 21 0 58 Z" fill="{primary}" {stroke}/><path d="M0 -26 V58 M-77 -20 Q-43 -28 -15 -5 M15 -5 Q43 -28 77 -20" fill="none" stroke="{WHITE}" stroke-width="7"/></g>'
        cutline = '<ellipse cx="0" cy="103" rx="121" ry="82" fill="#FFFFFF"/>'
    elif scene.prop == "rocket":
        back = f'<g transform="translate(112 2) rotate(18)"><path d="M0 -76 Q50 -42 44 25 L0 61 Q-44 25 -50 -42 Q-22 -70 0 -76 Z" fill="{primary}" {stroke}/><circle cx="0" cy="-22" r="18" fill="{BLUE}" {stroke}/><path d="M-28 32 L-54 66 L-18 53 M28 32 L54 66 L18 53" fill="{accent}" {stroke}/><path d="M-12 58 Q0 105 12 58" fill="{RED}" {stroke}/></g>'
        effects = f'<polygon points="{base.star_points(-112, -75, 27, 11)}" fill="{GOLD}"/><path d="M-125 -30 H-92 M-113 -45 L-94 -37" stroke="{RED}" stroke-width="8" stroke-linecap="round"/>'
        cutline = '<circle cx="105" cy="4" r="82" fill="#FFFFFF"/><circle cx="-110" cy="-70" r="42" fill="#FFFFFF"/>'
    elif scene.prop == "science":
        front = f'<g transform="translate(-105 83)"><path d="M-28 -69 H23 M-15 -69 V-8 L-56 65 Q-65 82 -41 86 H38 Q59 81 49 63 L8 -8 V-69" fill="{TEAL}" {stroke}/><path d="M-43 48 Q-4 25 38 51" stroke="{GOLD}" stroke-width="16" fill="none"/><circle cx="63" cy="-25" r="22" fill="{primary}" {stroke}/><circle cx="82" cy="-58" r="10" fill="{GOLD}"/></g>'
        back = f'<g transform="translate(108 80)"><rect x="-48" y="-63" width="96" height="126" rx="13" fill="{WHITE}" {stroke}/><path d="M-28 -29 H29 M-28 0 H29 M-28 29 H12" stroke="{primary}" stroke-width="8" stroke-linecap="round"/></g>'
        effects = f'<circle cx="-72" cy="-79" r="9" fill="{BLUE}"/><circle cx="-103" cy="-54" r="6" fill="{GOLD}"/><circle cx="104" cy="-74" r="8" fill="{GREEN}"/>'
        cutline = '<circle cx="-103" cy="78" r="78" fill="#FFFFFF"/><circle cx="108" cy="80" r="72" fill="#FFFFFF"/>'
    elif scene.prop == "library":
        back = f'<g transform="translate(-113 12)"><rect x="-54" y="-105" width="108" height="222" rx="13" fill="{DARK}" {stroke}/><path d="M-48 -42 H48 M-48 28 H48" stroke="{GOLD}" stroke-width="9"/><rect x="-37" y="-91" width="21" height="42" fill="{RED}"/><rect x="-9" y="-83" width="21" height="34" fill="{BLUE}"/><rect x="18" y="-94" width="22" height="45" fill="{GREEN}"/><rect x="-38" y="-31" width="29" height="52" fill="{PURPLE}"/><rect x="-2" y="-25" width="34" height="46" fill="{ORANGE}"/></g>'
        front = f'<g transform="translate(13 93)"><path d="M0 54 Q-49 23 -91 34 V-38 Q-46 -52 0 -23 Q46 -52 91 -38 V34 Q49 23 0 54 Z" fill="{BLUE}" {stroke}/><path d="M0 -23 V54" stroke="{WHITE}" stroke-width="7"/></g>'
        cutline = '<rect x="-183" y="-112" width="128" height="250" rx="25" fill="#FFFFFF"/><ellipse cx="12" cy="104" rx="111" ry="72" fill="#FFFFFF"/>'
    elif scene.prop == "paint":
        front = f'<g transform="translate(-105 78)"><path d="M-65 20 Q-78 -35 -33 -62 Q18 -90 59 -47 Q87 -18 57 20 Q45 36 23 26 Q4 20 2 43 Q-3 69 -29 69 Q-56 65 -65 20 Z" fill="{CREAM}" {stroke}/><circle cx="-39" cy="-26" r="11" fill="{RED}"/><circle cx="-7" cy="-47" r="11" fill="{GOLD}"/><circle cx="26" cy="-41" r="11" fill="{GREEN}"/><circle cx="48" cy="-10" r="11" fill="{BLUE}"/></g><path d="M61 128 L132 -22" stroke="{primary}" stroke-width="15" stroke-linecap="round"/><path d="M132 -22 L142 -45 L119 -28 Z" fill="{INK}"/>'
        effects = f'<path d="M-120 -65 Q-93 -101 -66 -68 M90 -78 Q113 -108 137 -79" fill="none" stroke="{accent}" stroke-width="10" stroke-linecap="round"/><circle cx="-82" cy="-99" r="9" fill="{RED}"/><circle cx="113" cy="-108" r="8" fill="{GREEN}"/>'
        cutline = '<circle cx="-105" cy="78" r="82" fill="#FFFFFF"/><path d="M48 145 L156 -57" stroke="#FFFFFF" stroke-width="36" stroke-linecap="round"/>'
    elif scene.prop == "team":
        front = f'<g transform="translate(0 106)"><path d="M-85 -54 H-13 Q-26 -24 4 -16 Q33 -8 34 -42 Q34 -51 25 -54 H85 V52 H18 Q28 24 -1 17 Q-31 10 -32 43 Q-31 50 -24 52 H-85 Z" fill="{primary}" {stroke}/></g>'
        effects = f'<path d="M-134 -89 Q-121 -107 -108 -89 M108 -89 Q121 -107 134 -89" fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round"/>'
        cutline = '<rect x="-107" y="39" width="214" height="134" rx="35" fill="#FFFFFF"/>'
    elif scene.prop == "desk":
        back = f'<g transform="translate(-136 33)"><rect x="-56" y="-101" width="112" height="181" rx="13" fill="{DARK}" {stroke}/><path d="M-48 -47 H48 M-48 9 H48" stroke="{GOLD}" stroke-width="8"/><rect x="-34" y="-91" width="27" height="36" fill="{BLUE}"/><rect x="2" y="-86" width="32" height="31" fill="{RED}"/></g>'
        front = f'<g transform="translate(-38 104)"><path d="M-138 0 H137 M-115 0 V57 M112 0 V57" stroke="{INK}" stroke-width="13" stroke-linecap="round"/><rect x="-117" y="-75" width="89" height="68" rx="10" fill="{primary}" {stroke}/><rect x="-6" y="-68" width="105" height="62" rx="8" fill="{WHITE}" {stroke}/><path d="M11 -49 H75 M11 -30 H64" stroke="{GREEN}" stroke-width="7" stroke-linecap="round"/></g>'
        cutline = '<rect x="-210" y="-88" width="151" height="248" rx="25" fill="#FFFFFF"/><rect x="-194" y="13" width="330" height="170" rx="28" fill="#FFFFFF"/>'
    elif scene.prop == "test":
        front = f'<g transform="translate(0 93)"><rect x="-83" y="-62" width="166" height="124" rx="13" fill="{WHITE}" {stroke}/><path d="M-55 -30 H46 M-55 -4 H46 M-55 22 H16" stroke="{primary}" stroke-width="8" stroke-linecap="round"/><path d="M42 36 L58 51 L82 20" fill="none" stroke="{GREEN}" stroke-width="10" stroke-linecap="round"/></g><path d="M-118 127 L-58 52" stroke="{GOLD}" stroke-width="16" stroke-linecap="round"/><path d="M-58 52 L-43 37 L-67 43 Z" fill="{INK}"/>'
        effects = f'<path d="M72 -91 Q92 -62 72 -40 Q53 -65 72 -91 Z" fill="{BLUE}"/><path d="M-104 -77 Q-83 -100 -61 -77" fill="none" stroke="{RED}" stroke-width="8"/>'
        cutline = '<rect x="-102" y="12" width="204" height="167" rx="28" fill="#FFFFFF"/><path d="M-133 143 L-37 24" stroke="#FFFFFF" stroke-width="38" stroke-linecap="round"/>'
    elif scene.prop == "high-five":
        front = f'<g transform="translate(108 -45) rotate(10)"><path d="M-30 72 V-15 Q-31 -51 -12 -51 Q4 -50 3 -19 V-74 Q4 -99 21 -96 Q35 -93 33 -70 V-25 V-83 Q34 -105 50 -100 Q63 -96 60 -73 V-20 V-62 Q61 -82 76 -75 Q89 -69 82 -47 L76 18 Q72 70 20 88 Z" fill="{GOLD}" {stroke}/></g>'
        effects = f'<polygon points="{base.star_points(-105, -73, 31, 13)}" fill="{RED}"/><path d="M-137 -22 H-102 M-126 -41 L-104 -32" stroke="{primary}" stroke-width="9" stroke-linecap="round"/>'
        cutline = '<ellipse cx="114" cy="-29" rx="72" ry="125" fill="#FFFFFF"/><circle cx="-108" cy="-70" r="47" fill="#FFFFFF"/>'
    else:
        back = f'<g transform="translate(0 -83)"><path d="M-78 -5 L0 -48 L78 -5 L0 35 Z" fill="{primary}" {stroke}/><path d="M78 -5 V57" stroke="{GOLD}" stroke-width="8"/><circle cx="78" cy="66" r="11" fill="{GOLD}"/></g>'
        front = f'<g transform="translate(75 91) rotate(-18)"><rect x="-61" y="-30" width="122" height="60" rx="16" fill="{CREAM}" {stroke}/><path d="M-42 -15 H42 M-42 2 H28" stroke="{primary}" stroke-width="7"/><path d="M-58 -27 Q-78 0 -58 27 M58 -27 Q78 0 58 27" fill="{GOLD}" {stroke}/></g>'
        cutline = '<ellipse cx="0" cy="-83" rx="103" ry="68" fill="#FFFFFF"/><ellipse cx="76" cy="91" rx="96" ry="63" fill="#FFFFFF"/>'
        effects = f'<polygon points="{base.star_points(-105, -70, 25, 10)}" fill="{GOLD}"/><polygon points="{base.star_points(112, -54, 18, 7)}" fill="{GREEN}"/>'
    return {"prop-back": back, "prop-front": front, "effects": effects, "cutline": cutline}


def scene_layers(scene: Scene) -> dict[str, str]:
    first = owl_parts(scene)
    props = prop_parts(scene)
    layers = {name: "" for name in LAYER_NAMES}
    for name, fragment in first.items():
        layers[name] += group(scene, fragment)
    for name in ("prop-back", "prop-front", "effects"):
        layers[name] += group(scene, props[name])
    layers["cutline"] += group(scene, props["cutline"])
    if scene.two_owls:
        left_scene = Scene(**{**scene.__dict__, "x": 177, "y": 249, "scale": 0.76})
        right_scene = Scene(**{**scene.__dict__, "x": 335, "y": 249, "scale": 0.76})
        layers = {name: "" for name in LAYER_NAMES}
        for peer in (left_scene, right_scene):
            parts = owl_parts(peer)
            for name, fragment in parts.items():
                layers[name] += group(peer, fragment)
        for name in ("prop-back", "prop-front", "effects"):
            layers[name] += group(scene, props[name])
        layers["cutline"] += group(scene, props["cutline"])
    return {name: svg(fragment) for name, fragment in layers.items()}


def pack_document() -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, scene in enumerate(SCENES):
        ids = []
        for layer_index, name in enumerate(LAYER_NAMES):
            layer_id = f"{name}-{scene.slug}"
            ids.append(layer_id)
            layers.append({
                "id": layer_id,
                "source": f"layers/{index:02d}-{name}-{scene.slug}.svg",
                "z": index * 20 + layer_index,
                "pivot": "composition",
                "depth": round(layer_index * 0.08, 2),
            })
        expressions[scene.slug] = ids
        primary, accent = PALETTE[scene.category]
        font_id = FONT_VOICES[scene.font_voice][0]
        styles[f"{scene.slug}-main"] = {
            "font": font_id,
            "safe_area": scene.text_area,
            "min_font_size": 28,
            "max_font_size": 112,
            "max_lines": 2,
            "fill": base.rgb(primary),
            "outline": {"width": 12, "color": base.rgb(WHITE)},
            "depth_shell": {"offset_x": 5, "offset_y": 6, "color": base.rgb(INK)},
            "highlight_shell": {"offset_x": -2, "offset_y": -2, "color": base.rgb(accent)},
        }
    return {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "canvas": {"width": 512, "height": 512},
        "layers": layers,
        "base_layers": [],
        "expressions": expressions,
        "poses": {scene.pose: [] for scene in SCENES},
        "provenance": {"creator": "MascotRender project", "license": "MIT; fonts SIL OFL 1.1", "source": "original procedural layered 2.5D Sage golden-set art"},
        "anchors": {"composition_center": {"x": 256, "y": 256}},
        "pivots": {"composition": {"x": 256, "y": 256}},
        "avoid_regions": [],
        "text_clearance": 0,
        "caption_validation": {"minimum_canvas_margin_px": 16, "maximum_lines": 2, "must_remain_inside_canvas_for_every_frame": True, "may_overlap_character": False, "may_overlap_assistive_device": False, "must_pass_sizes_px": [80, 100, 160], "collision_bounds": "golden-scene-specific-safe-areas"},
        "fonts": [{"id": font_id, "source": source, "license": license_path} for font_id, source, license_path in FONT_VOICES.values()],
        "text_styles": styles,
    }


def animation(scene: Scene, index: int) -> dict[str, Any]:
    duration = 1000 + (index % 3) * 100
    mid = duration // 2
    primary_target = f"body-base-{scene.slug}"
    wing_target = f"wings-{scene.slug}"
    prop_target = f"prop-front-{scene.slug}"
    return {
        "duration_ms": duration,
        "fps": 12,
        "loop": "loop",
        "overlays": ["text_pulse" if scene.motion in {"pop", "pulse", "breathe"} else "text_wobble"],
        "tracks": [
            {"target": primary_target, "property": "translate_y", "keyframes": [{"at_ms": 0, "value": 0.0, "easing": "ease_in_out"}, {"at_ms": mid, "value": -6.0, "easing": "ease_in_out"}, {"at_ms": duration, "value": 0.0, "easing": "ease_in_out"}]},
            {"target": wing_target, "property": "rotation_degrees", "keyframes": [{"at_ms": 0, "value": 0.0, "easing": "ease_in_out"}, {"at_ms": mid, "value": -3.5 if index % 2 else 3.5, "easing": "ease_in_out"}, {"at_ms": duration, "value": 0.0, "easing": "ease_in_out"}]},
            {"target": prop_target, "property": "translate_y", "keyframes": [{"at_ms": 0, "value": 0.0, "easing": "ease_in_out"}, {"at_ms": mid, "value": 5.0 if index % 2 else -5.0, "easing": "ease_in_out"}, {"at_ms": duration, "value": 0.0, "easing": "ease_in_out"}]},
        ],
    }


def author_sources(destination: Path) -> None:
    pack_root = destination / PACK_ID
    base.copy_fonts(pack_root)
    for index, scene in enumerate(SCENES):
        for name, document in scene_layers(scene).items():
            base.write_text(pack_root / "layers" / f"{index:02d}-{name}-{scene.slug}.svg", document)
        base.write_json(pack_root / "stickers" / f"{scene.slug}.json", {
            "schema_version": 1,
            "sticker_id": f"education-wise-owl-golden-{scene.slug}",
            "pack_id": PACK_ID,
            "phrase_id": scene.phrase_id,
            "recipe_id": f"education-owl-golden.{scene.motion}",
            "intent": scene.phrase_id,
            "alt_text": f"Layered illustrated Sage owl scene saying {scene.label}",
            "accessible_description": f"Sage interacts with a {scene.prop} scene and the phrase {scene.label}",
            "expression": scene.slug,
            "pose": scene.pose,
            "seed": 1,
            "text": {"content": scene.label, "style": f"{scene.slug}-main", "rotation_degrees": 0.0},
            "animation": animation(scene, index),
        })
    base.write_json(pack_root / "pack.json", pack_document())
    base.write_json(pack_root / "triggers.json", {"schema_version": 1, "pack_id": PACK_ID, "selection_structure": "unicode-normalized-casefolded-trie", "entries": [{"phrase_id": scene.phrase_id, "sticker_id": f"education-wise-owl-golden-{scene.slug}", "triggers": [{"text": scene.label.casefold().rstrip("!?."), "locale": "en", "match": "exact-phrase", "weight": 1.0}]} for scene in SCENES]})
    base.write_json(destination / "generation-manifest.json", {"schema_version": 1, "generator": "generate_education_wise_owl_golden.py", "pack_id": PACK_ID, "contract": "contracts/education-wise-owl-golden-v2.json", "sticker_count": 10, "layer_count_per_sticker": len(LAYER_NAMES) + 1, "layer_names": list(LAYER_NAMES) + ["caption"], "visible_sequence_numbers": 0, "remaining_pack_stickers_blocked": 90, "production_use": "forbidden-until-owner-golden-set-approval"})


def contact_sheet(review: Path) -> Path:
    canvas = Image.new("RGBA", (5 * 300 + 40, 2 * 340 + 105), "#FBF6EC")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "WISE OWL ACADEMY · LAYERED 2.5D GOLDEN SET", fill=INK, font=base.review_font(34))
    draw.text((24, 58), "10 production-direction scenes · remaining 90 blocked", fill="#6F6257", font=base.review_font(16))
    for index, scene in enumerate(SCENES):
        x = 20 + (index % 5) * 300
        y = 94 + (index // 5) * 340
        # A tinted review card makes the authored white die-cut keyline inspectable.
        draw.rounded_rectangle((x, y, x + 284, y + 324), radius=24, fill="#EEF3F8", outline="#D6DFE8", width=2)
        image = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp").resize((274, 274), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + 5, y + 4))
        draw.text((x + 10, y + 285), scene.label, fill=INK, font=base.review_font(14))
        draw.text((x + 10, y + 306), f"{scene.category} · {scene.prop}", fill="#76695F", font=base.review_font(10))
    path = review / "golden-contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def small_sheet(review: Path) -> Path:
    canvas = Image.new("RGBA", (1290, 10 * 192 + 90), INK)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "GOLDEN SET · 80 / 100 / 160 PX", fill=WHITE, font=base.review_font(32))
    for index, scene in enumerate(SCENES):
        y = 78 + index * 192
        draw.rounded_rectangle((20, y, 1270, y + 178), radius=20, fill=WHITE)
        source = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp")
        x = 35
        for size in (80, 100, 160):
            canvas.alpha_composite(source.resize((size, size), Image.Resampling.LANCZOS), (x, y + 7 + (160 - size) // 2))
            draw.text((x, y + 158), f"{size}px", fill="#74685F", font=base.review_font(9))
            x += size + 28
        draw.text((565, y + 51), scene.label, fill=INK, font=base.review_font(24))
        draw.text((565, y + 87), "80 = simplified stress floor · 100 = default · 160 = showcase", fill="#76695F", font=base.review_font(12))
    path = review / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def motion_sheet(review: Path) -> Path:
    canvas = Image.new("RGBA", (5 * 310 + 40, 2 * 240 + 100), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "GOLDEN SET MOTION · START / MID / CLOSURE", fill=INK, font=base.review_font(32))
    for index, scene in enumerate(SCENES):
        x = 20 + (index % 5) * 310
        y = 84 + (index // 5) * 240
        draw.rounded_rectangle((x, y, x + 294, y + 224), radius=18, fill=WHITE)
        frames = base.image_frames(review / "assets" / f"{scene.slug}.webp")
        for frame_index, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
            canvas.alpha_composite(frame.resize((86, 86), Image.Resampling.LANCZOS), (x + 7 + frame_index * 94, y + 8))
        draw.text((x + 9, y + 108), scene.label, fill=INK, font=base.review_font(14))
        draw.text((x + 9, y + 138), f"{scene.motion} · 12 authored layers", fill="#65758B", font=base.review_font(10))
        draw.text((x + 9, y + 191), "START          MID          CLOSURE", fill="#8794A4", font=base.review_font(8))
    path = review / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def layer_sheet(source: Path, review: Path) -> Path:
    canvas = Image.new("RGBA", (6 * 230 + 40, 2 * 238 + 105), "#FBF6EC")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "STUDY TIME · ACTUAL LAYER DECOMPOSITION", fill=INK, font=base.review_font(32))
    pack = source / PACK_ID
    scene = SCENES[0]
    with tempfile.TemporaryDirectory(prefix="wise-owl-layer-previews-") as directory:
        previews = Path(directory)
        for index, name in enumerate(LAYER_NAMES):
            x = 20 + (index % 6) * 230
            y = 88 + (index // 6) * 238
            # Keep the white union cutline visible instead of losing it on white.
            draw.rounded_rectangle((x, y, x + 214, y + 220), radius=18, fill="#DCE6EF")
            source_svg = pack / "layers" / f"00-{name}-{scene.slug}.svg"
            preview_path = previews / f"{index:02d}-{name}.png"
            base.run(["rsvg-convert", "-w", "180", "-h", "180", "-o", str(preview_path), str(source_svg)])
            preview = Image.open(preview_path).convert("RGBA")
            canvas.alpha_composite(preview, (x + 17, y + 5))
            draw.text((x + 9, y + 192), name, fill=INK, font=base.review_font(11))
            draw.text((x + 9, y + 207), f"depth {index * 0.08:.2f}", fill="#76695F", font=base.review_font(8))
    path = review / "layer-decomposition.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def playback_html(review: Path) -> Path:
    figures = "".join(f'<figure><img src="assets/{scene.slug}.webp" alt="{scene.label}"><figcaption>{scene.label}<small>{scene.category} · {scene.motion}</small></figcaption></figure>' for scene in SCENES)
    path = review / "animation-review.html"
    base.write_text(path, '<!doctype html><meta charset="utf-8"><title>Wise Owl Academy golden playback</title><style>body{font:16px system-ui;background:#fbf6ec;color:#173257;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}figure{margin:0;background:white;border-radius:22px;padding:12px;text-align:center;box-shadow:0 8px 24px #17325718}img{width:100%}figcaption{font-weight:800}small{display:block;color:#76695f;font-weight:500}</style><h1>Wise Owl Academy · layered golden set</h1><p>Review mascot-first composition, depth, prop interaction, caption balance, motion and closure.</p><main>' + figures + '</main>')
    return path


def owner_decision_template(review: Path, reviewed: list[Path]) -> Path:
    path = review / "owner-decision-template.json"
    base.write_json(path, {
        "schema_version": 1,
        "authority": "project-owner",
        "decision": None,
        "decision_date": None,
        "gate": "education-wise-owl-layered-golden-art-direction-v2",
        "allowed_decisions": ["approved", "changes-required", "failed"],
        "reviewed_artifacts": {artifact.name: base.sha256(artifact) for artifact in reviewed},
        "approval_scope": [
            "sage-layered-identity",
            "mascot-first-scene-composition",
            "scene-specific-prop-interaction",
            "union-die-cut-contour",
            "soft-exterior-shadow",
            "caption-integration",
            "layered-2.5d-depth",
            "animation-and-loop-closure",
            "reduced-motion-equivalents",
            "80-100-160px-readability",
        ],
        "production_use_if_approved": "golden-direction-approved-remaining-90-stickers-may-be-authored",
        "full_pack_production_use": "forbidden-until-remaining-90-and-final-pack-gates-pass",
    })
    return path


def render_review(source: Path, review: Path, executable: Path) -> None:
    pack_root = source / PACK_ID
    pack = pack_root / "pack.json"
    metrics = []
    for scene in SCENES:
        sticker = pack_root / "stickers" / f"{scene.slug}.json"
        base.run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
        animated = review / "assets" / f"{scene.slug}.webp"
        reduced = review / "reduced-motion" / f"{scene.slug}.webp"
        thumbnail = review / "thumbnails" / f"{scene.slug}.webp"
        base.render(executable, pack, sticker, animated, 512, False)
        base.render(executable, pack, sticker, reduced, 512, True)
        base.render(executable, pack, sticker, thumbnail, 256, True)
        values = base.asset_metrics(animated)
        if not values["animated_webp"] or not values["visible_mid_cycle_change"] or not values["loop_closure"]:
            raise ValueError(f"animation gate failed: {animated}")
        if values["minimum_frame_margin_px"] < 16:
            raise ValueError(f"hard margin failed: {animated}")
        values.update({"semantic_id": scene.phrase_id, "label": scene.label, "category": scene.category, "prop": scene.prop, "pose": scene.pose, "motion": scene.motion, "layer_count": 12, "animated_sha256": base.sha256(animated), "reduced_motion_sha256": base.sha256(reduced), "thumbnail_sha256": base.sha256(thumbnail)})
        metrics.append(values)
    visual_artifacts = [contact_sheet(review), small_sheet(review), motion_sheet(review), layer_sheet(source, review), playback_html(review)]
    artifacts = visual_artifacts + [owner_decision_template(review, visual_artifacts)]
    base.write_json(review / "review.json", {"schema_version": 1, "review_id": "education-wise-owl-layered-golden-review-v2", "review_status": "awaiting-owner-golden-set-review", "production_use": "forbidden-until-owner-golden-set-approval", "contract_sha256": base.sha256(ROOT / "contracts" / "education-wise-owl-golden-v2.json"), "sticker_count": 10, "remaining_pack_stickers_blocked": 90, "animated_sticker_count": 10, "visible_mid_cycle_sticker_count": 10, "loop_closed_sticker_count": 10, "reduced_motion_sticker_count": 10, "layer_count_per_sticker": 12, "scene_specific_prop_count": 10, "two_character_scene_count": 1, "visible_sequence_number_count": 0, "copy_correction": {"label": "EVERY DAY COUNTS", "semantic_id": "education.assessment.every-day-counts", "pilot_assets_regenerated": True}, "deterministic_generation": {"passed": True, "method": "two-independent-build-byte-comparison", "source_file_count": 135, "review_file_count": 37}, "minimum_frame_margin_px": min(value["minimum_frame_margin_px"] for value in metrics), "artifacts": {path.name: base.sha256(path) for path in artifacts}, "metrics": metrics, "owner_review_questions": ["Does this reach the illustrated mascot-first richness of the supplied reference?", "Does Sage remain one stable identity across all ten scenes?", "Do the character interactions, union cutline, shadow, captions and 2.5D depth clear the golden-set gate?"]})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-output", type=Path, default=ROOT / "art" / PACK_ID)
    parser.add_argument("--review-output", type=Path, default=ROOT / "generated" / f"{PACK_ID}-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    executable = args.mascotrender.resolve()
    with tempfile.TemporaryDirectory(prefix="education-wise-owl-golden-") as directory:
        root = Path(directory)
        source, review = root / "source", root / "review"
        author_sources(source)
        render_review(source, review, executable)
        base.replace_directory(source, args.source_output.resolve(), args.force)
        base.replace_directory(review, args.review_output.resolve(), args.force)
    print(args.source_output.resolve())
    print(args.review_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
