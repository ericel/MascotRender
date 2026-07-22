#!/usr/bin/env python3
"""Author and render the Wise Owl Academy 100-sticker review candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

import generate_workday_reactions_pack as base


WORKDAY_ACCENT_SVG = base.accent_svg


ROOT = Path(__file__).resolve().parents[1]
PACK_ID = "education-wise-owl-v1"
GENERATOR_VERSION = 1
CANVAS = 512
INK = "#173257"
BROWN = "#A75C22"
BROWN_DARK = "#6D3518"
BROWN_LIGHT = "#D78A3E"
CREAM = "#FFF3D3"
DIECUT = "#FFFDF6"
ORANGE = "#F39A23"
GREEN = "#168A62"
RED = "#E34A3B"
BLUE = "#287BD1"
GOLD = "#F7BF32"
TEAL = "#38AFA5"


CATEGORY_PALETTES = {
    "study": (BLUE, INK, GOLD),
    "motivation": (RED, "#922F31", GOLD),
    "stem": (GREEN, "#155F54", ORANGE),
    "literacy": (BLUE, "#244C94", CREAM),
    "creativity": ("#8A5BD7", "#56369C", ORANGE),
    "community": (GREEN, "#176848", RED),
    "habits": (TEAL, "#25716F", GOLD),
    "assessment": (RED, "#8F343A", BLUE),
    "achievement": (GOLD, "#B26B13", RED),
    "future": (BLUE, "#244C94", GREEN),
}

FONT_VOICES = base.FONT_VOICES
LAYOUTS = base.LAYOUTS
ROTATIONS = (0.0, -1.5, 1.2, 0.0, -2.0, 1.5, 0.0, -1.0, 1.0, 0.0)
MOTIONS = ("pop", "pulse", "wobble", "float", "glow", "write", "nod", "slide", "stamp", "breathe")
LAYOUT_NAMES = tuple(LAYOUTS)
FONT_NAMES = tuple(FONT_VOICES)
POSES = ("read", "present", "think", "cheer", "write", "point", "wave", "listen", "study", "proud")
MOODS = ("focused", "proud", "curious", "worried", "happy", "excited", "thoughtful", "calm", "confident", "bright")


def slugify(label: str) -> str:
    value = label.casefold().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def entries() -> tuple[base.Entry, ...]:
    matrix = base.read_json(ROOT / "content" / "education-wise-owl-matrix-v1.json")
    result: list[base.Entry] = []
    index = 0
    for group in matrix["groups"]:
        category = group["category"]
        for label, effect in group["phrases"]:
            slug = slugify(label)
            normalized = label.casefold().rstrip("!?.")
            aliases = tuple(dict.fromkeys((normalized, slug.replace("-", " "))))
            result.append(
                base.Entry(
                    semantic_id=f"education.{category}.{slug}",
                    label=label,
                    category=category,
                    aliases=aliases,
                    font_voice=FONT_NAMES[index % len(FONT_NAMES)],
                    motion=MOTIONS[index % len(MOTIONS)],
                    effect=effect,
                    layout=LAYOUT_NAMES[index % len(LAYOUT_NAMES)],
                    pose=POSES[index % len(POSES)],
                    mood=MOODS[index % len(MOODS)],
                )
            )
            index += 1
    if len(result) != 100 or len({item.slug for item in result}) != 100:
        raise ValueError("education matrix must expand to 100 unique stickers")
    return tuple(result)


def owl_face(mood: str) -> str:
    if mood in {"happy", "excited", "proud", "bright", "confident"}:
        eyes = (
            f'<path d="M-47 -45 Q-32 -61 -16 -45 M16 -45 Q32 -61 47 -45" '
            f'fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
        )
        mouth = f'<path d="M-21 -2 Q0 20 21 -2" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    elif mood in {"focused", "thoughtful", "calm"}:
        eyes = (
            f'<ellipse cx="-31" cy="-44" rx="13" ry="10" fill="{INK}"/>'
            f'<ellipse cx="31" cy="-44" rx="13" ry="10" fill="{INK}"/>'
            f'<circle cx="-27" cy="-48" r="3" fill="#FFFFFF"/><circle cx="35" cy="-48" r="3" fill="#FFFFFF"/>'
        )
        mouth = f'<path d="M-15 2 Q0 10 15 2" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    else:
        eyes = (
            f'<circle cx="-31" cy="-44" r="13" fill="{INK}"/><circle cx="31" cy="-44" r="13" fill="{INK}"/>'
            f'<circle cx="-27" cy="-49" r="4" fill="#FFFFFF"/><circle cx="35" cy="-49" r="4" fill="#FFFFFF"/>'
        )
        mouth = f'<ellipse cx="0" cy="3" rx="9" ry="11" fill="{INK}"/>'
    glasses = (
        f'<circle cx="-32" cy="-44" r="27" fill="none" stroke="{INK}" stroke-width="7"/>'
        f'<circle cx="32" cy="-44" r="27" fill="none" stroke="{INK}" stroke-width="7"/>'
        f'<path d="M-5 -45 H5" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    )
    return eyes + glasses + mouth


def owl_wings(pose: str) -> str:
    if pose in {"cheer", "wave", "proud"}:
        left = "M-55 52 Q-112 18 -104 -51 Q-77 -38 -49 2"
        right = "M55 52 Q112 18 104 -51 Q77 -38 49 2"
    elif pose in {"present", "point", "listen"}:
        left = "M-55 54 Q-102 42 -119 11 Q-84 4 -47 18"
        right = "M55 54 Q91 60 111 86 Q77 90 46 73"
    else:
        left = "M-55 45 Q-91 62 -91 104 Q-60 96 -39 70"
        right = "M55 45 Q91 62 91 104 Q60 96 39 70"
    return (
        f'<path d="{left}" fill="{BROWN_DARK}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="{right}" fill="{BROWN_DARK}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="M-73 49 Q-86 66 -78 84 M73 49 Q86 66 78 84" fill="none" stroke="{BROWN_LIGHT}" stroke-width="7" stroke-linecap="round"/>'
    )


def owl_character(entry: base.Entry) -> str:
    # A cream under-silhouette creates the thick die-cut edge seen in the reference.
    silhouette = (
        '<g fill="none" stroke="#FFFDF6" stroke-width="28" stroke-linejoin="round" stroke-linecap="round">'
        '<ellipse cx="0" cy="43" rx="83" ry="102"/>'
        '<path d="M-72 -28 L-91 -111 L-31 -82 Q0 -105 31 -82 L91 -111 L72 -28"/>'
        '<path d="M-55 52 Q-103 46 -104 95 M55 52 Q103 46 104 95"/>'
        '</g>'
    )
    body = (
        f'<ellipse cx="0" cy="43" rx="81" ry="100" fill="{BROWN}" stroke="{INK}" stroke-width="9"/>'
        f'<ellipse cx="0" cy="61" rx="48" ry="65" fill="{CREAM}"/>'
        f'<path d="M-76 -18 L-88 -103 L-29 -76 Q0 -99 29 -76 L88 -103 L76 -18" fill="{BROWN}" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/>'
        f'<path d="M-73 -35 Q-50 -88 0 -57 Q50 -88 73 -35 Q55 16 0 17 Q-55 16 -73 -35 Z" fill="{CREAM}"/>'
        f'<path d="M-12 -17 L0 -7 L12 -17 L0 -2 Z" fill="{ORANGE}" stroke="{INK}" stroke-width="4"/>'
        + owl_face(entry.mood)
        + owl_wings(entry.pose)
        + f'<path d="M-37 132 L-52 151 H-19 L-5 133 M37 132 L52 151 H19 L5 133" fill="{GOLD}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
    )
    shadow = f'<ellipse cx="0" cy="158" rx="86" ry="13" fill="{INK}" opacity=".17"/>'
    return shadow + silhouette + body


def prop_kind(effect: str) -> str:
    if any(token in effect for token in ("globe", "discover")):
        return "globe"
    if "puzzle" in effect:
        return "puzzle"
    if any(token in effect for token in ("megaphone", "question-bubble", "idea-share")):
        return "megaphone"
    if any(token in effect for token in ("brain", "memory", "recall")):
        return "brain"
    if any(token in effect for token in ("graduation", "leader-cap", "future")):
        return "graduation"
    if any(token in effect for token in ("organized-desk", "homework")):
        return "desk"
    if any(token in effect for token in ("finish-flag", "success-path", "step-up")):
        return "flag"
    if any(token in effect for token in ("music", "guitar", "microphone", "dance")):
        return "music"
    if any(token in effect for token in ("paint", "color")):
        return "art"
    if any(token in effect for token in ("bulb", "bright", "shine")):
        return "light"
    if any(token in effect for token in ("book", "read", "library", "story", "word", "letter", "homework", "study")):
        return "book"
    if any(token in effect for token in ("flask", "lab", "science", "microscope", "experiment")):
        return "science"
    if any(token in effect for token in ("star", "medal", "trophy", "champion", "grade", "ace", "high-five")):
        return "award"
    if any(token in effect for token in ("clock", "calendar", "planner", "checklist", "organized", "daily")):
        return "time"
    if any(token in effect for token in ("target", "goal", "progress", "path", "step", "finish", "mountain")):
        return "target"
    if any(token in effect for token in ("heart", "friend", "team", "help", "respect", "listen", "hand", "partner", "share")):
        return "community"
    if any(token in effect for token in ("school", "graduation", "class", "leader", "student")):
        return "school"
    if any(token in effect for token in ("paper", "pencil", "pen", "quiz", "test", "review", "cards")):
        return "paper"
    return "spark"


def prop_art(entry: base.Entry, index: int) -> str:
    primary, secondary, highlight = CATEGORY_PALETTES[entry.category]
    side = -1 if entry.layout in {"caption-left", "caption-top", "badge-top"} else 1
    if entry.layout in {"caption-right", "speech-right", "badge-side"}:
        side = 1
    x = 112 * side
    stroke = f'stroke="{INK}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"'
    kind = prop_kind(entry.effect)
    if kind == "book":
        art = (
            f'<path d="M0 58 Q-37 30 -72 38 V-54 Q-34 -65 0 -35 Q34 -65 72 -54 V38 Q37 30 0 58 Z" fill="{primary}" {stroke}/>'
            f'<path d="M0 -35 V58 M-53 -26 Q-29 -31 -11 -12 M11 -12 Q29 -31 53 -26" fill="none" stroke="{DIECUT}" stroke-width="7"/>'
        )
    elif kind == "science":
        art = (
            f'<path d="M-44 -70 H-4 M-31 -70 V-13 L-67 55 Q-74 73 -50 78 H28 Q50 73 41 54 L5 -13 V-70" fill="{TEAL}" {stroke}/>'
            f'<path d="M-51 43 Q-8 20 31 46" fill="none" stroke="{highlight}" stroke-width="17"/>'
            f'<circle cx="49" cy="-34" r="20" fill="{primary}" {stroke}/><circle cx="65" cy="-65" r="9" fill="{GOLD}"/>'
        )
    elif kind == "globe":
        art = (
            f'<circle cx="0" cy="-5" r="62" fill="{BLUE}" {stroke}/>'
            f'<path d="M-52 -25 Q-12 -49 23 -28 Q48 -12 51 17 Q18 4 -9 23 Q-39 43 -55 14 M0 -67 Q-21 -5 0 57 M0 -67 Q21 -5 0 57 M-59 -5 H59" fill="none" stroke="{CREAM}" stroke-width="8"/>'
            f'<path d="M-75 70 H75 M0 57 V70" stroke="{secondary}" stroke-width="12" stroke-linecap="round"/>'
        )
    elif kind == "puzzle":
        art = (
            f'<path d="M-67 -59 H-14 Q-23 -37 -5 -28 Q18 -18 25 -41 Q28 -52 19 -59 H67 V-11 Q44 -20 35 2 Q27 26 53 32 Q62 34 67 28 V67 H17 Q25 45 5 38 Q-19 30 -25 53 Q-28 63 -20 67 H-67 V22 Q-45 33 -35 12 Q-27 -11 -52 -18 Q-60 -20 -67 -14 Z" fill="{primary}" {stroke}/>'
        )
    elif kind == "megaphone":
        art = (
            f'<path d="M-61 -20 L34 -60 V44 L-61 10 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-61 -20 V10 M-45 15 L-25 66 H8 L-4 2" fill="{highlight}" {stroke}/>'
            f'<path d="M52 -46 Q78 -21 56 6 M65 -67 Q106 -25 73 30" fill="none" stroke="{secondary}" stroke-width="9" stroke-linecap="round"/>'
        )
    elif kind == "brain":
        art = (
            f'<path d="M-4 57 Q-38 71 -48 39 Q-78 27 -65 -8 Q-78 -40 -45 -50 Q-31 -78 -3 -59 Q25 -77 42 -51 Q75 -43 64 -10 Q78 20 48 36 Q40 67 8 56 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-4 -55 V56 M-36 -40 Q-10 -26 -31 -5 Q-47 13 -25 34 M31 -42 Q9 -26 31 -5 Q47 14 24 35" fill="none" stroke="{highlight}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif kind == "graduation":
        art = (
            f'<path d="M-79 -20 L0 -65 L79 -20 L0 25 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-50 -5 V45 Q0 76 50 45 V-5" fill="{highlight}" {stroke}/>'
            f'<path d="M79 -20 V45" stroke="{secondary}" stroke-width="8" stroke-linecap="round"/><circle cx="79" cy="55" r="11" fill="{secondary}"/>'
        )
    elif kind == "desk":
        art = (
            f'<path d="M-82 43 H82 M-65 43 V80 M65 43 V80" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>'
            f'<rect x="-71" y="-30" width="70" height="68" rx="9" fill="{primary}" {stroke}/>'
            f'<path d="M15 24 H69 V-18 H15 Z" fill="{CREAM}" {stroke}/><path d="M27 -3 H57 M27 11 H50" stroke="{secondary}" stroke-width="7" stroke-linecap="round"/>'
            f'<rect x="-54" y="-53" width="36" height="23" rx="5" fill="{highlight}" {stroke}/>'
        )
    elif kind == "flag":
        art = (
            f'<path d="M-49 76 V-69" stroke="{INK}" stroke-width="11" stroke-linecap="round"/>'
            f'<path d="M-45 -64 Q7 -83 58 -57 L36 -22 L62 8 Q11 -9 -45 8 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-78 78 H5" stroke="{secondary}" stroke-width="15" stroke-linecap="round"/>'
        )
    elif kind == "music":
        art = (
            f'<path d="M-16 -65 V43 Q-27 72 -55 61 Q-73 52 -63 34 Q-51 16 -21 27 M-16 -43 L55 -61 V24 Q44 53 17 44 Q-2 36 8 17 Q20 0 50 9" fill="none" stroke="{primary}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<path d="M-15 -42 L54 -59" stroke="{highlight}" stroke-width="9"/>'
        )
    elif kind == "art":
        art = (
            f'<path d="M-65 25 Q-79 -32 -35 -61 Q15 -91 59 -48 Q88 -20 59 20 Q47 36 25 26 Q5 20 2 43 Q-3 68 -30 69 Q-58 66 -65 25 Z" fill="{CREAM}" {stroke}/>'
            f'<circle cx="-39" cy="-24" r="11" fill="{RED}"/><circle cx="-8" cy="-47" r="11" fill="{GOLD}"/><circle cx="25" cy="-42" r="11" fill="{GREEN}"/><circle cx="48" cy="-12" r="11" fill="{BLUE}"/>'
            f'<path d="M19 66 L70 -58" stroke="{primary}" stroke-width="15" stroke-linecap="round"/><path d="M70 -58 L77 -78 L58 -63 Z" fill="{INK}"/>'
        )
    elif kind == "light":
        art = (
            f'<path d="M-50 -18 Q-50 -70 0 -76 Q50 -70 50 -18 Q47 12 22 30 V48 H-22 V30 Q-47 12 -50 -18 Z" fill="{highlight}" {stroke}/>'
            f'<path d="M-23 51 H23 M-18 70 H18" stroke="{secondary}" stroke-width="12" stroke-linecap="round"/>'
            f'<path d="M0 -99 V-119 M-72 -72 L-88 -88 M72 -72 L88 -88 M-82 -5 H-104 M82 -5 H104" stroke="{primary}" stroke-width="9" stroke-linecap="round"/>'
        )
    elif kind == "award":
        art = (
            f'<circle cx="0" cy="-5" r="54" fill="{highlight}" {stroke}/>'
            f'<polygon points="{base.star_points(0, -5, 33, 14)}" fill="{primary}"/>'
            f'<path d="M-31 39 L-48 84 L-8 67 L0 91 L11 67 L50 83 L31 39" fill="{secondary}" {stroke}/>'
        )
    elif kind == "time":
        art = (
            f'<circle cx="0" cy="0" r="64" fill="{DIECUT}" {stroke}/>'
            f'<circle cx="0" cy="0" r="49" fill="{highlight}" stroke="{primary}" stroke-width="7"/>'
            f'<path d="M0 0 V-29 M0 0 L27 16" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M-33 -75 H33" stroke="{primary}" stroke-width="13" stroke-linecap="round"/>'
        )
    elif kind == "target":
        art = (
            f'<circle cx="0" cy="0" r="65" fill="{DIECUT}" {stroke}/><circle cx="0" cy="0" r="45" fill="{primary}"/><circle cx="0" cy="0" r="25" fill="{DIECUT}"/><circle cx="0" cy="0" r="10" fill="{RED}"/>'
            f'<path d="M-78 73 L18 -14 M10 -33 L31 -25 L29 -4" fill="none" stroke="{secondary}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    elif kind == "community":
        art = (
            f'<path d="M0 67 C-94 10 -73 -69 -18 -49 C-3 -44 0 -23 0 -23 C0 -23 6 -47 29 -50 C84 -56 95 18 0 67 Z" fill="{primary}" {stroke}/>'
            f'<path d="M-43 -2 L-12 25 L45 -31" fill="none" stroke="{highlight}" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    elif kind == "school":
        art = (
            f'<path d="M-73 -7 L0 -67 L73 -7 V69 H-73 Z" fill="{CREAM}" {stroke}/>'
            f'<path d="M-87 -3 L0 -80 L87 -3" fill="none" stroke="{primary}" stroke-width="18" stroke-linejoin="round"/>'
            f'<rect x="-20" y="18" width="40" height="51" rx="5" fill="{secondary}"/><rect x="-55" y="8" width="22" height="22" fill="{BLUE}"/><rect x="33" y="8" width="22" height="22" fill="{BLUE}"/>'
        )
    elif kind == "paper":
        art = (
            f'<rect x="-58" y="-70" width="116" height="142" rx="13" fill="{DIECUT}" {stroke}/>'
            f'<path d="M-35 -32 H35 M-35 -5 H35 M-35 22 H20" stroke="{primary}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M-69 63 L50 -69" stroke="{highlight}" stroke-width="15" stroke-linecap="round"/><path d="M50 -69 L68 -84 L60 -60 Z" fill="{INK}"/>'
        )
    else:
        art = (
            f'<polygon points="{base.star_points(0, 0, 65, 27)}" fill="{highlight}" {stroke}/>'
            f'<circle cx="0" cy="0" r="19" fill="{primary}"/>'
        )
    return f'<g transform="translate({x} 24) scale(.62)">{art}</g>'


def scene_svg(entry: base.Entry, index: int) -> str:
    x, y, scale = LAYOUTS[entry.layout]["scene"]
    return base.svg(
        f'<g transform="translate({x} {y}) scale({scale})">'
        + owl_character(entry)
        + prop_art(entry, index)
        + "</g>"
    )


def accent_svg(entry: base.Entry, index: int) -> str:
    return WORKDAY_ACCENT_SVG(entry, index)


def pack_document(items: tuple[base.Entry, ...]) -> dict[str, Any]:
    document = base.pack_document(items)
    document["pack_id"] = PACK_ID
    document["provenance"] = {
        "creator": "MascotRender project",
        "license": "MIT; bundled fonts separately SIL OFL 1.1",
        "source": f"generate_education_wise_owl_pack.py v{GENERATOR_VERSION}; original procedural owl compositions",
    }
    document["caption_validation"]["minimum_canvas_margin_px"] = 16
    return document


def sticker_document(entry: base.Entry, index: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sticker_id": f"education-wise-owl-{entry.slug}",
        "pack_id": PACK_ID,
        "phrase_id": entry.semantic_id,
        "recipe_id": f"education-owl-scene.{entry.motion}",
        "intent": entry.semantic_id,
        "alt_text": f"Sage the owl in a learning scene saying {entry.label}",
        "accessible_description": f"Sage uses a {entry.effect.replace('-', ' ')} learning cue with the phrase {entry.label}",
        "expression": entry.slug,
        "pose": entry.pose,
        "seed": 1,
        "text": {
            "content": entry.label,
            "style": f"{entry.slug}-main",
            "rotation_degrees": ROTATIONS[index % len(ROTATIONS)],
        },
        "animation": base.animation_document(entry, index),
    }


def author_sources(destination: Path) -> None:
    items = entries()
    pack_root = destination / PACK_ID
    base.copy_fonts(pack_root)
    for index, entry in enumerate(items):
        base.write_text(pack_root / "layers" / f"{index:03d}-scene-{entry.slug}.svg", scene_svg(entry, index))
        base.write_text(pack_root / "layers" / f"{index:03d}-accent-{entry.slug}.svg", accent_svg(entry, index))
        base.write_json(pack_root / "stickers" / f"{entry.slug}.json", sticker_document(entry, index))
    document = pack_document(items)
    # The reused pack schema expects the exact authored layer paths.
    for index, entry in enumerate(items):
        document["layers"][index * 2]["source"] = f"layers/{index:03d}-scene-{entry.slug}.svg"
        document["layers"][index * 2 + 1]["source"] = f"layers/{index:03d}-accent-{entry.slug}.svg"
    base.write_json(pack_root / "pack.json", document)
    base.write_json(
        pack_root / "triggers.json",
        {
            "schema_version": 1,
            "pack_id": PACK_ID,
            "selection_structure": "unicode-normalized-casefolded-trie",
            "entries": [
                {
                    "phrase_id": entry.semantic_id,
                    "sticker_id": f"education-wise-owl-{entry.slug}",
                    "triggers": [
                        {"text": alias, "locale": "en", "match": "exact-phrase", "weight": 1.0 if alias == entry.label.casefold().rstrip("!?.") else 0.84}
                        for alias in entry.aliases
                    ],
                }
                for entry in items
            ],
        },
    )
    base.write_json(
        destination / "generation-manifest.json",
        {
            "schema_version": 1,
            "generator": "generate_education_wise_owl_pack.py",
            "generator_version": GENERATOR_VERSION,
            "pack_id": PACK_ID,
            "pack_contract": "contracts/education-wise-owl-pack-v1.json",
            "content_matrix": "content/education-wise-owl-matrix-v1.json",
            "sticker_count": 100,
            "category_counts": dict(sorted(Counter(item.category for item in items).items())),
            "font_voice_count": len({item.font_voice for item in items}),
            "motion_family_count": len({item.motion for item in items}),
            "composition_system_count": len({item.layout for item in items}),
            "effect_family_count": len({item.effect for item in items}),
            "visual_prop_archetype_count": len({prop_kind(item.effect) for item in items}),
            "visible_sequence_numbers": 0,
            "single_fitted_text_layout_per_sticker": True,
            "independently_typeset_duplicate_text_blocks": 0,
            "production_use": "forbidden-until-owner-production-approval",
        },
    )


def build_contact_sheet(review_root: Path, items: tuple[base.Entry, ...]) -> Path:
    columns, cell_w, cell_h = 10, 176, 202
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_w + 40, rows * cell_h + 98), "#FBF7EF")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "WISE OWL ACADEMY · 100-STICKER REVIEW", fill=INK, font=base.review_font(34))
    draw.text((24, 58), "Sage identity · exact phrases · learning props · no visible numbering", fill="#6F6257", font=base.review_font(16))
    for index, entry in enumerate(items):
        x = 20 + (index % columns) * cell_w
        y = 90 + (index // columns) * cell_h
        draw.rounded_rectangle((x, y, x + 162, y + 188), radius=18, fill="#FFFFFF", outline="#E6DCCE", width=2)
        image = base.first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp").resize((150, 150), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + 6, y + 4))
        draw.text((x + 7, y + 158), entry.label, fill=INK, font=base.review_font(10))
        draw.text((x + 7, y + 174), entry.category, fill="#7B6F66", font=base.review_font(8))
    path = review_root / "contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_small_display_sheet(review_root: Path, items: tuple[base.Entry, ...]) -> Path:
    columns, cell_w, cell_h = 5, 520, 194
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (columns * cell_w + 40, rows * cell_h + 92), INK)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "ALL 100 · 80 PX STRESS FLOOR", fill="#FFFFFF", font=base.review_font(32))
    draw.text((24, 53), "100 px recommended default · 160 px showcase", fill="#C8D4E4", font=base.review_font(15))
    for index, entry in enumerate(items):
        x = 20 + (index % columns) * cell_w
        y = 82 + (index // columns) * cell_h
        draw.rounded_rectangle((x, y, x + 504, y + 180), radius=16, fill="#FFFFFF")
        source = base.first_frame(review_root / "reduced-motion" / f"{entry.slug}.webp")
        offset = 10
        for size in (80, 100, 160):
            image = source.resize((size, size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + offset, y + 5 + (160 - size) // 2))
            draw.text((x + offset, y + 164), f"{size}px", fill="#6F6257", font=base.review_font(8))
            offset += size + 18
        draw.text((x + 376, y + 56), entry.label, fill=INK, font=base.review_font(12))
        draw.text((x + 376, y + 78), entry.category, fill="#6F6257", font=base.review_font(9))
    path = review_root / "small-display-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_motion_sheet(review_root: Path, items: tuple[base.Entry, ...]) -> Path:
    columns, cell_w, cell_h = 10, 174, 148
    canvas = Image.new("RGBA", (columns * cell_w + 40, 10 * cell_h + 92), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "ALL 100 LOOPS · START / MID / CLOSURE", fill=INK, font=base.review_font(32))
    for index, entry in enumerate(items):
        x = 20 + (index % columns) * cell_w
        y = 78 + (index // columns) * cell_h
        draw.rounded_rectangle((x, y, x + 160, y + 134), radius=14, fill="#FFFFFF")
        frames = base.image_frames(review_root / "assets" / f"{entry.slug}.webp")
        for frame_index, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
            canvas.alpha_composite(frame.resize((48, 48), Image.Resampling.LANCZOS), (x + 4 + frame_index * 51, y + 4))
        draw.text((x + 6, y + 58), entry.label, fill=INK, font=base.review_font(9))
        draw.text((x + 6, y + 76), f"{entry.motion} · {prop_kind(entry.effect)}", fill="#65758B", font=base.review_font(8))
        draw.text((x + 6, y + 111), "S      M      C", fill="#8794A4", font=base.review_font(8))
    path = review_root / "motion-sample-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def build_animation_html(review_root: Path, items: tuple[base.Entry, ...]) -> Path:
    figures = "".join(
        f'<figure data-category="{entry.category}"><img src="assets/{entry.slug}.webp" alt="{entry.label} animated education sticker"><figcaption>{entry.label}<small>{entry.category} · {entry.motion}</small></figcaption></figure>'
        for entry in items
    )
    path = review_root / "animation-review.html"
    base.write_text(path, '<!doctype html><meta charset="utf-8"><title>Wise Owl Academy playback</title><style>body{font:16px system-ui;background:#fbf7ef;color:#173257;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px}figure{margin:0;background:white;border-radius:20px;padding:10px;text-align:center}img{width:100%;height:auto}figcaption{font-weight:800}small{display:block;color:#70645b;font-weight:500;margin-top:4px}</style><h1>Wise Owl Academy · all 100 animations</h1><p>Review Sage identity, exact text, prop semantics, small-size readability, motion and closure.</p><main>' + figures + '</main>')
    return path


def render_review(source_root: Path, review_root: Path, executable: Path) -> None:
    items = entries()
    pack_root = source_root / PACK_ID
    pack = pack_root / "pack.json"
    metrics: list[dict[str, Any]] = []
    for entry in items:
        sticker = pack_root / "stickers" / f"{entry.slug}.json"
        base.run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
        animated = review_root / "assets" / f"{entry.slug}.webp"
        reduced = review_root / "reduced-motion" / f"{entry.slug}.webp"
        thumbnail = review_root / "thumbnails" / f"{entry.slug}.webp"
        base.render(executable, pack, sticker, animated, 512, False)
        base.render(executable, pack, sticker, reduced, 512, True)
        base.render(executable, pack, sticker, thumbnail, 256, True)
        values = base.asset_metrics(animated)
        if not values["animated_webp"] or not values["visible_mid_cycle_change"] or not values["loop_closure"]:
            raise ValueError(f"animation gate failed: {animated}")
        if values["minimum_frame_margin_px"] < 16:
            raise ValueError(f"{animated} violates the 16px hard margin")
        values.update(
            {
                "semantic_id": entry.semantic_id,
                "label": entry.label,
                "category": entry.category,
                "font_voice": entry.font_voice,
                "layout": entry.layout,
                "effect": entry.effect,
                "prop_archetype": prop_kind(entry.effect),
                "motion": entry.motion,
                "animated_sha256": base.sha256(animated),
                "reduced_motion_sha256": base.sha256(reduced),
                "thumbnail_sha256": base.sha256(thumbnail),
            }
        )
        metrics.append(values)
    artifacts = [
        build_contact_sheet(review_root, items),
        build_small_display_sheet(review_root, items),
        build_motion_sheet(review_root, items),
        build_animation_html(review_root, items),
    ]
    artifact_hashes = {path.name: base.sha256(path) for path in artifacts}
    contract = ROOT / "contracts" / "education-wise-owl-pack-v1.json"
    matrix = ROOT / "content" / "education-wise-owl-matrix-v1.json"
    base.write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "education-wise-owl-development-review-v1",
            "review_status": "awaiting-owner-production-art-and-playback-review",
            "production_use": "forbidden-until-owner-production-approval",
            "artifact_hash_scope": "render-runtime-specific",
            "contract_sha256": base.sha256(contract),
            "matrix_sha256": base.sha256(matrix),
            "generator_sha256": base.sha256(Path(__file__).resolve()),
            "sticker_count": 100,
            "category_counts": dict(sorted(Counter(item.category for item in items).items())),
            "animated_sticker_count": sum(bool(item["animated_webp"]) for item in metrics),
            "visible_mid_cycle_sticker_count": sum(bool(item["visible_mid_cycle_change"]) for item in metrics),
            "loop_closed_sticker_count": sum(bool(item["loop_closure"]) for item in metrics),
            "reduced_motion_sticker_count": 100,
            "font_voice_count": len({item.font_voice for item in items}),
            "motion_family_count": len({item.motion for item in items}),
            "composition_system_count": len({item.layout for item in items}),
            "effect_family_count": len({item.effect for item in items}),
            "visual_prop_archetype_count": len({prop_kind(item.effect) for item in items}),
            "visible_sequence_number_count": 0,
            "independently_typeset_duplicate_text_block_count": 0,
            "minimum_frame_margin_px": min(item["minimum_frame_margin_px"] for item in metrics),
            "artifacts": artifact_hashes,
            "metrics": metrics,
            "owner_review_questions": [
                "Does Sage match the warm scholarly owl and cream die-cut visual language of the supplied reference?",
                "Do all 100 phrases remain exact and readable without visible catalogue numbering?",
                "Are prop, pose, caption placement, and motion sufficiently varied for production?",
            ],
        },
    )


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
    if not executable.is_file():
        raise FileNotFoundError(f"MascotRender CLI is missing: {executable}")
    base.PACK_ID = PACK_ID
    base.INK = INK
    base.CREAM = CREAM
    base.CATEGORY_PALETTES = CATEGORY_PALETTES
    base.entries = entries
    base.prop_kind = prop_kind
    base.scene_svg = scene_svg
    base.accent_svg = accent_svg
    with tempfile.TemporaryDirectory(prefix="education-wise-owl-") as directory:
        staging = Path(directory)
        source = staging / "source"
        review = staging / "review"
        author_sources(source)
        render_review(source, review, executable)
        base.replace_directory(source, args.source_output.resolve(), args.force)
        base.replace_directory(review, args.review_output.resolve(), args.force)
    print(args.source_output.resolve())
    print(args.review_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
