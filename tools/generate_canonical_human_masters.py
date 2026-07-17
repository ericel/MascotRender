#!/usr/bin/env python3
"""Generate five original layered SVG production-review candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
INK = "#162B45"
WHITE = "#FFF8EE"
CANVAS = 512
VECTOR_STATUS = "owner-vector-parity-approved"
PRODUCTION_USE = "forbidden"
EXPRESSIONS = ("happy", "laughing", "surprised", "thinking", "confident", "sorry", "excited")
POSES = ("rest", "greeting", "farewell", "agreement", "disagreement", "gratitude", "concern", "surprise", "celebration")


MASTERS: dict[str, dict[str, Any]] = {
    "H01": {
        "name": "H01", "mode": "child", "skin": "#754329", "skin_light": "#9A6040",
        "hair": "#211714", "primary": "#F5B82E", "secondary": "#E85D89", "accent": "#23B6A6",
        "pants": "#2879A8", "shoe": "#E94E64", "head": (256, 143, 68, 72),
        "torso": (206, 215, 100, 96), "ground": 451,
        "identity": "Black girl child with coily two-puff protective hairstyle",
        "device": "device.none",
    },
    "H04": {
        "name": "H04", "mode": "prosthesis", "skin": "#754329", "skin_light": "#9A6040",
        "hair": "#201714", "primary": "#238C8F", "secondary": "#173D5E", "accent": "#E6F1E9",
        "pants": "#252A34", "shoe": "#E9EEE8", "head": (256, 104, 53, 59),
        "torso": (180, 168, 152, 137), "ground": 465,
        "identity": "Black young adult man with articulated below-knee prosthesis",
        "device": "prosthesis.lower-leg.right",
    },
    "H07": {
        "name": "H07", "mode": "wheelchair", "skin": "#B87542", "skin_light": "#D89965",
        "hair": "#171719", "primary": "#D9C6A5", "secondary": "#65704D", "accent": "#294E72",
        "pants": "#315D82", "shoe": "#E8D8B9", "head": (256, 128, 58, 62),
        "torso": (194, 195, 124, 125), "ground": 465,
        "identity": "Southeast Asian adult man using a manual wheelchair",
        "device": "wheelchair.manual",
        "device_review_resolution": "project-owner-approved-seated-geometry-and-footrest-relationship",
    },
    "H12": {
        "name": "H12", "mode": "hearing-aid", "skin": "#E2AD7D", "skin_light": "#F1C49B",
        "hair": "#2B292C", "hair_grey": "#7D7B80", "primary": "#9970A8", "secondary": "#F2E7D7", "accent": "#5BD1C6",
        "pants": "#203B5D", "shoe": "#1C2633", "head": (256, 115, 59, 65),
        "torso": (195, 188, 122, 142), "ground": 465,
        "identity": "East Asian middle-aged woman with visible behind-the-ear hearing aid",
        "device": "hearing-aid.behind-ear.right",
        "hair_intent": "naturally greying straight bob with a visible side part and swept fringe",
        "head_covering": False,
    },
    "H13": {
        "name": "H13", "mode": "rollator", "skin": "#714027", "skin_light": "#965F43",
        "hair": "#B8B1AA", "hair_dark": "#69635F", "primary": "#643A78", "secondary": "#E87522", "accent": "#F2A13A",
        "pants": "#187B83", "shoe": "#724277", "head": (256, 106, 60, 63),
        "torso": (186, 178, 140, 155), "ground": 465,
        "identity": "Black senior woman with natural grey coily hair using a rollator",
        "device": "rollator.four-wheel",
        "framing_overrides": {"three-quarter": ("body_center", .96, 0, 28)},
    },
}


def svg_document(content: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">\n'
        '<defs><linearGradient id="softShade" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".24"/>'
        '<stop offset="1" stop-color="#10243A" stop-opacity=".14"/></linearGradient></defs>\n'
        f'{content}\n</svg>\n'
    )


def ellipse(cx: float, cy: float, rx: float, ry: float, fill: str, stroke: str = INK, sw: int = 6, extra: str = "") -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def rect(x: float, y: float, w: float, h: float, r: float, fill: str, stroke: str = INK, sw: int = 6, extra: str = "") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def path(d: str, fill: str = "none", stroke: str = INK, sw: int = 6, extra: str = "") -> str:
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def line(points: list[tuple[float, float]], color: str, width: int, outline: int = 0) -> str:
    value = " ".join(f"{x},{y}" for x, y in points)
    result = ""
    if outline:
        result += f'<polyline points="{value}" fill="none" stroke="{INK}" stroke-width="{width + outline}" stroke-linecap="round" stroke-linejoin="round"/>'
    result += f'<polyline points="{value}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
    return result


def face_layer(d: dict[str, Any]) -> str:
    hx, hy, rx, ry = d["head"]
    mode = d["mode"]
    eye_y = hy + 4
    spacing = rx * (0.43 if mode != "wheelchair" else 0.46)
    eye_profiles = {
        "child": (12, 15), "prosthesis": (9, 12), "wheelchair": (12, 9),
        "hearing-aid": (9, 11), "rollator": (9, 11),
    }
    eye_rx, eye_ry = d.get("eye_profile", eye_profiles.get(mode, (10, 12)))
    if mode == "prosthesis":
        brows = [
            path(f"M{hx-spacing-15} {eye_y-17} L{hx-spacing+13} {eye_y-23}", sw=7),
            path(f"M{hx+spacing-13} {eye_y-23} L{hx+spacing+15} {eye_y-17}", sw=7),
        ]
    elif mode == "wheelchair":
        brows = [
            path(f"M{hx-spacing-15} {eye_y-17} Q{hx-spacing} {eye_y-21} {hx-spacing+15} {eye_y-17}", sw=4),
            path(f"M{hx+spacing-15} {eye_y-17} Q{hx+spacing} {eye_y-21} {hx+spacing+15} {eye_y-17}", sw=4),
        ]
    else:
        brows = [
            path(f"M{hx-spacing-14} {eye_y-18} Q{hx-spacing} {eye_y-25} {hx-spacing+14} {eye_y-18}", sw=5),
            path(f"M{hx+spacing-14} {eye_y-18} Q{hx+spacing} {eye_y-25} {hx+spacing+14} {eye_y-18}", sw=5),
        ]
    parts = [
        *brows,
        ellipse(hx-spacing, eye_y, eye_rx, eye_ry, WHITE, INK, 4),
        ellipse(hx+spacing, eye_y, eye_rx, eye_ry, WHITE, INK, 4),
        ellipse(hx-spacing+1, eye_y+2, 4, 6, INK, INK, 0),
        ellipse(hx+spacing+1, eye_y+2, 4, 6, INK, INK, 0),
        path(f"M{hx} {eye_y+8} q{-6 if mode == 'wheelchair' else -4} 10 {7 if mode == 'wheelchair' else 4} 12", stroke=d["skin_light"], sw=4),
        ellipse(hx-rx*.58, hy+24, 10, 6, "#E58A78", "none", 0, 'opacity=".45"'),
        ellipse(hx+rx*.58, hy+24, 10, 6, "#E58A78", "none", 0, 'opacity=".45"'),
    ]
    if mode == "prosthesis":
        parts += [
            path(f"M{hx-rx*.62} {hy+25} Q{hx} {hy+68} {hx+rx*.62} {hy+23}", stroke=d["hair"], sw=7),
            path(f"M{hx-18} {hy+31} Q{hx} {hy+40} {hx+18} {hy+30}", stroke=d["hair"], sw=4),
            path(f"M{hx-25} {hy+34} Q{hx} {hy+52} {hx+27} {hy+32}", stroke="#FFFFFF", sw=4),
            path(f"M{hx-8} {hy+52} L{hx} {hy+60} L{hx+8} {hy+52}", fill=d["hair"], sw=3),
        ]
    elif mode == "wheelchair":
        parts += [
            path(f"M{hx-27} {hy+33} Q{hx-2} {hy+51} {hx+31} {hy+28}", stroke=INK, sw=6),
            path(f"M{hx-14} {hy+37} Q{hx+2} {hy+44} {hx+18} {hy+33}", stroke="#FFFFFF", sw=3),
        ]
    elif mode == "hearing-aid":
        parts += [
            path(f"M{hx-22} {hy+35} Q{hx} {hy+49} {hx+23} {hy+34}", stroke=INK, sw=5),
            path(f"M{hx-10} {hy+39} Q{hx} {hy+44} {hx+11} {hy+38}", stroke="#FFFFFF", sw=3),
        ]
    else:
        parts += [
            path(f"M{hx-25} {hy+35} Q{hx} {hy+55} {hx+27} {hy+31}", stroke=INK, sw=6),
            path(f"M{hx-15} {hy+39} Q{hx} {hy+48} {hx+16} {hy+36}", stroke="#FFFFFF", sw=3),
        ]
    if mode == "rollator":
        parts += [
            ellipse(hx-spacing, eye_y, 19, 17, "none", INK, 4),
            ellipse(hx+spacing, eye_y, 19, 17, "none", INK, 4),
            path(f"M{hx-spacing+19} {eye_y} L{hx+spacing-19} {eye_y}", sw=4),
        ]
    parts.extend(face_accessories(d, hx, hy, spacing, eye_y))
    return "\n".join(parts)


def face_accessories(
    d: dict[str, Any], hx: float, hy: float, spacing: float, eye_y: float
) -> list[str]:
    parts: list[str] = []
    if d.get("glasses"):
        parts.extend([
            ellipse(hx-spacing, eye_y, 18, 16, "none", INK, 4),
            ellipse(hx+spacing, eye_y, 18, 16, "none", INK, 4),
            path(f"M{hx-spacing+18} {eye_y} L{hx+spacing-18} {eye_y}", sw=4),
        ])
    facial_hair = d.get("facial_hair")
    if facial_hair == "close-beard":
        parts.append(path(
            f"M{hx-34} {hy+27} Q{hx} {hy+69} {hx+34} {hy+26}",
            stroke=d["hair"], sw=7,
        ))
    elif facial_hair == "moustache":
        parts.extend([
            path(f"M{hx-4} {hy+29} Q{hx-17} {hy+22} {hx-28} {hy+31}", stroke=d["hair"], sw=6),
            path(f"M{hx+4} {hy+29} Q{hx+17} {hy+22} {hx+28} {hy+31}", stroke=d["hair"], sw=6),
        ])
    return parts


def expression_face_layer(d: dict[str, Any], expression: str) -> str:
    """Author a complete character-specific face for a semantic expression."""
    hx, hy, rx, _ = d["head"]
    mode = d["mode"]
    eye_y = hy + 4
    spacing = rx * (0.43 if mode != "wheelchair" else 0.46)
    eye_profiles = {
        "child": (12, 15), "prosthesis": (9, 12), "wheelchair": (12, 9),
        "hearing-aid": (9, 11), "rollator": (9, 11),
    }
    erx, ery = d.get("eye_profile", eye_profiles.get(mode, (10, 12)))
    parts: list[str] = []
    if expression == "laughing":
        for center in (hx-spacing, hx+spacing):
            parts.append(path(f"M{center-erx} {eye_y} Q{center} {eye_y+ery*.75} {center+erx} {eye_y}", sw=5))
    else:
        scale_y = 1.35 if expression in {"surprised", "excited"} else .62 if expression == "confident" else 1.0
        for index, center in enumerate((hx-spacing, hx+spacing)):
            parts.append(ellipse(center, eye_y, erx, ery*scale_y, WHITE, INK, 4))
            glance = 4 if expression == "thinking" else 1
            parts.append(ellipse(center+glance, eye_y+2, 4, 6*scale_y, INK, INK, 0))
    brow_shapes = {
        "surprised": -29, "excited": -25, "sorry": -13,
        "thinking": -20, "confident": -15,
    }
    brow_y = eye_y + brow_shapes.get(expression, -20)
    if expression == "sorry":
        parts.extend([
            path(f"M{hx-spacing-14} {brow_y-5} Q{hx-spacing+2} {brow_y-11} {hx-spacing+14} {brow_y}", sw=5),
            path(f"M{hx+spacing-14} {brow_y} Q{hx+spacing-2} {brow_y-11} {hx+spacing+14} {brow_y-5}", sw=5),
        ])
    elif expression == "thinking":
        parts.extend([
            path(f"M{hx-spacing-14} {brow_y+5} L{hx-spacing+14} {brow_y-2}", sw=5),
            path(f"M{hx+spacing-14} {brow_y-2} L{hx+spacing+14} {brow_y-2}", sw=5),
        ])
    else:
        parts.extend([
            path(f"M{hx-spacing-14} {brow_y} Q{hx-spacing} {brow_y-6} {hx-spacing+14} {brow_y}", sw=5),
            path(f"M{hx+spacing-14} {brow_y} Q{hx+spacing} {brow_y-6} {hx+spacing+14} {brow_y}", sw=5),
        ])
    parts.append(path(f"M{hx} {eye_y+8} q-4 10 5 12", stroke=d["skin_light"], sw=4))
    mouth_y = hy + 36
    if expression == "surprised":
        parts.append(ellipse(hx, mouth_y+5, 12, 16, "#5B2730", INK, 5))
    elif expression == "laughing":
        parts.append(path(f"M{hx-28} {mouth_y-2} Q{hx} {mouth_y+39} {hx+29} {mouth_y-3} Z", fill="#5B2730", sw=5))
        parts.append(path(f"M{hx-15} {mouth_y+18} Q{hx} {mouth_y+27} {hx+16} {mouth_y+17}", stroke="#E98A86", sw=5))
    elif expression == "sorry":
        parts.append(path(f"M{hx-24} {mouth_y+14} Q{hx} {mouth_y-5} {hx+24} {mouth_y+14}", sw=6))
    elif expression == "thinking":
        parts.append(path(f"M{hx-18} {mouth_y+5} Q{hx+3} {mouth_y+1} {hx+22} {mouth_y+8}", sw=5))
    elif expression == "confident":
        parts.append(path(f"M{hx-24} {mouth_y+2} Q{hx+5} {mouth_y+24} {hx+29} {mouth_y-3}", sw=6))
    else:
        depth = 29 if expression == "excited" else 20
        parts.append(path(f"M{hx-27} {mouth_y} Q{hx} {mouth_y+depth} {hx+28} {mouth_y-2}", sw=6))
    if mode == "prosthesis":
        parts.append(path(f"M{hx-rx*.62} {hy+25} Q{hx} {hy+68} {hx+rx*.62} {hy+23}", stroke=d["hair"], sw=7))
    if mode == "rollator":
        parts.extend([
            ellipse(hx-spacing, eye_y, 19, 17, "none", INK, 4),
            ellipse(hx+spacing, eye_y, 19, 17, "none", INK, 4),
            path(f"M{hx-spacing+19} {eye_y} L{hx+spacing-19} {eye_y}", sw=4),
        ])
    parts.extend(face_accessories(d, hx, hy, spacing, eye_y))
    return "\n".join(parts)


def head_layer(d: dict[str, Any]) -> str:
    hx, hy, rx, ry = d["head"]
    return "\n".join([
        ellipse(hx-rx*.94, hy+5, 12, 20, d["skin"], INK, 5),
        ellipse(hx+rx*.94, hy+5, 12, 20, d["skin"], INK, 5),
        ellipse(hx, hy, rx, ry, d["skin"], INK, 7),
        path(f"M{hx-rx*.72} {hy-ry*.48} Q{hx-rx*.25} {hy-ry*.78} {hx+rx*.62} {hy-ry*.52}", stroke=d["skin_light"], sw=5, extra='opacity=".45"'),
    ])


def hair_layers(d: dict[str, Any]) -> tuple[str, str]:
    hx, hy, rx, ry = d["head"]
    mode = d["mode"]
    style = d.get("hair_style")
    if style == "short-loose-curls":
        curls = "".join(
            ellipse(hx-46+i*15, hy-ry+8+(i%2)*5, 18, 17, d["hair"], INK, 4)
            for i in range(7)
        )
        return "", curls + path(
            f"M{hx-rx+5} {hy-39} Q{hx} {hy-ry-24} {hx+rx-2} {hy-37}",
            fill=d["hair"], sw=5,
        )
    if style == "long-wavy":
        back = path(
            f"M{hx-rx-13} {hy-40} Q{hx-rx-27} {hy+70} {hx-48} {hy+116} "
            f"L{hx+48} {hy+116} Q{hx+rx+27} {hy+70} {hx+rx+13} {hy-40} Z",
            fill=d["hair"], sw=7,
        )
        front = path(
            f"M{hx-rx+3} {hy-36} Q{hx-20} {hy-ry-24} {hx+rx+2} {hy-31} "
            f"Q{hx+25} {hy-55} {hx-9} {hy-60} Q{hx-39} {hy-55} {hx-rx+3} {hy-36} Z",
            fill=d["hair"], sw=6,
        )
        front += path(f"M{hx-38} {hy-37} Q{hx-55} {hy+16} {hx-43} {hy+65}", stroke=d["hair_highlight"], sw=6)
        front += path(f"M{hx+38} {hy-36} Q{hx+54} {hy+16} {hx+42} {hy+66}", stroke=d["hair_highlight"], sw=6)
        return back, front
    if style == "shoulder-wave":
        back = path(
            f"M{hx-rx-10} {hy-38} Q{hx-rx-20} {hy+35} {hx-39} {hy+78} "
            f"L{hx+35} {hy+78} Q{hx+rx+18} {hy+34} {hx+rx+10} {hy-38} Z",
            fill=d["hair"], sw=7,
        )
        front = path(
            f"M{hx-rx+4} {hy-32} Q{hx-24} {hy-ry-25} {hx+rx+3} {hy-35} "
            f"Q{hx+16} {hy-61} {hx-15} {hy-63} Q{hx-43} {hy-55} {hx-rx+4} {hy-32} Z",
            fill=d["hair"], sw=6,
        )
        front += path(f"M{hx+35} {hy-35} Q{hx+51} {hy+4} {hx+36} {hy+55}", stroke=d["hair_highlight"], sw=6)
        return back, front
    if style == "voluminous-curls":
        positions = [(-58,-42,27),(-38,-66,28),(-8,-76,29),(24,-70,30),(52,-48,29),(-62,-12,27),(60,-13,27)]
        curls = "".join(ellipse(hx+x, hy+y, r, r, d["hair"], INK, 4) for x,y,r in positions)
        return "", curls
    if style == "coily-taper":
        top = "".join(ellipse(hx-43+i*14, hy-ry+5+(i%2)*4, 16, 16, d["hair"], INK, 4) for i in range(7))
        return "", top + path(f"M{hx-rx+15} {hy-34} Q{hx} {hy-68} {hx+rx-13} {hy-32}", fill=d["hair"], sw=5)
    if style == "bald":
        return "", path(f"M{hx-rx*.62} {hy-ry*.57} Q{hx} {hy-ry*.76} {hx+rx*.62} {hy-ry*.57}", stroke=d["skin_light"], sw=4, extra='opacity=".55"')
    if style == "silver-swept":
        front = path(
            f"M{hx-rx+3} {hy-30} Q{hx-30} {hy-ry-28} {hx+rx+4} {hy-37} "
            f"Q{hx+18} {hy-66} {hx-20} {hy-63} Q{hx-44} {hy-55} {hx-rx+3} {hy-30} Z",
            fill=d["hair"], sw=6,
        )
        front += path(f"M{hx-28} {hy-55} Q{hx+2} {hy-65} {hx+35} {hy-43}", stroke=d["hair_highlight"], sw=5)
        return "", front
    if style == "swept-wave":
        back = path(
            f"M{hx-rx+2} {hy-27} Q{hx-rx-8} {hy-ry+9} {hx-34} {hy-ry-15} "
            f"Q{hx+3} {hy-ry-35} {hx+rx+3} {hy-35} L{hx+rx-4} {hy-6} "
            f"Q{hx+20} {hy-38} {hx-rx+2} {hy-27} Z",
            fill=d["hair"], sw=6,
        )
        front = path(
            f"M{hx-rx+5} {hy-30} Q{hx-25} {hy-ry-26} {hx+rx+3} {hy-38} "
            f"Q{hx+13} {hy-65} {hx-20} {hy-63} Q{hx-45} {hy-53} {hx-rx+5} {hy-30} Z",
            fill=d["hair"], sw=6,
        )
        front += path(f"M{hx-30} {hy-54} Q{hx+2} {hy-67} {hx+35} {hy-43}", stroke=d["hair_highlight"], sw=5)
        return back, front
    if style == "straight-undercut":
        return "", path(
            f"M{hx-rx+5} {hy-23} Q{hx-32} {hy-ry-31} {hx+rx+6} {hy-40} "
            f"Q{hx+25} {hy-67} {hx-17} {hy-66} Q{hx-48} {hy-55} {hx-rx+5} {hy-23} Z",
            fill=d["hair"], sw=6,
        ) + path(f"M{hx-9} {hy-62} Q{hx+22} {hy-58} {hx+44} {hy-39}", stroke=d["hair_highlight"], sw=4)
    if style == "head-covering":
        back = path(
            f"M{hx-rx-15} {hy-35} Q{hx-rx-28} {hy+54} {hx-57} {hy+104} "
            f"Q{hx} {hy+123} {hx+57} {hy+104} Q{hx+rx+28} {hy+54} {hx+rx+15} {hy-35} Z",
            fill=d["hair"], sw=7,
        )
        front = path(
            f"M{hx-rx+2} {hy-27} Q{hx} {hy-ry-31} {hx+rx-2} {hy-27} "
            f"L{hx+rx-10} {hy-3} Q{hx} {hy-30} {hx-rx+10} {hy-3} Z",
            fill=d["hair"], sw=6,
        )
        front += path(f"M{hx-rx-2} {hy-4} Q{hx-rx-8} {hy+45} {hx-40} {hy+87}", stroke=d["hair_highlight"], sw=5)
        front += path(f"M{hx+rx+2} {hy-4} Q{hx+rx+8} {hy+45} {hx+40} {hy+87}", stroke=d["hair_highlight"], sw=5)
        front += path(f"M{hx-43} {hy+72} Q{hx} {hy+91} {hx+43} {hy+72}", stroke=d["hair_highlight"], sw=4)
        return back, front
    if mode == "child":
        back = ellipse(hx-60, hy-60, 41, 43, d["hair"], INK, 6) + ellipse(hx+60, hy-60, 41, 43, d["hair"], INK, 6)
        curls = "".join(ellipse(hx-45+i*15, hy-ry+10+(i%2)*5, 18, 17, d["hair"], INK, 4) for i in range(7))
        front = curls + path(f"M{hx-54} {hy-47} Q{hx} {hy-78} {hx+55} {hy-43}", fill=d["hair"], sw=6)
        return back, front
    if mode == "hearing-aid":
        back = path(f"M{hx-rx-16} {hy-30} Q{hx-rx-24} {hy+50} {hx-42} {hy+75} L{hx+45} {hy+73} Q{hx+rx+23} {hy+45} {hx+rx+10} {hy-34} Z", fill=d["hair"], sw=7)
        front = path(f"M{hx-rx+5} {hy-35} Q{hx-15} {hy-ry-20} {hx+rx} {hy-30} Q{hx+36} {hy-55} {hx+3} {hy-59} Q{hx-30} {hy-60} {hx-rx+5} {hy-35} Z", fill=d["hair"], sw=6)
        front += path(f"M{hx+7} {hy-60} Q{hx-13} {hy-55} {hx-rx+8} {hy-30}", stroke=d["hair_grey"], sw=5)
        front += path(f"M{hx+7} {hy-60} Q{hx+31} {hy-54} {hx+rx-3} {hy-31}", stroke=d["hair_grey"], sw=4)
        front += path(f"M{hx+5} {hy-58} Q{hx-5} {hy-43} {hx-24} {hy-34}", stroke="#B1ADB1", sw=3)
        front += path(f"M{hx-22} {hy-54} Q{hx-38} {hy-42} {hx-rx+7} {hy-20}", stroke=d["hair_grey"], sw=8)
        return back, front
    if mode == "rollator":
        circles = []
        for x, y, r in [(-48,-50,25),(-25,-67,24),(0,-72,25),(26,-66,24),(49,-48,25),(-56,-24,22),(55,-22,22)]:
            circles.append(ellipse(hx+x, hy+y, r, r, d["hair"], INK, 4))
            circles.append(path(f"M{hx+x-r*.4} {hy+y} q{r*.4} {-r*.5} {r*.8} 0", stroke="#E9E4DD", sw=3))
        return "", "".join(circles)
    if mode == "prosthesis":
        curls = "".join(ellipse(hx-45+i*15, hy-ry+8+(i%2)*3, 18, 16, d["hair"], INK, 4) for i in range(7))
        return "", curls + path(f"M{hx-rx+8} {hy-45} Q{hx} {hy-82} {hx+rx-4} {hy-43}", fill=d["hair"], sw=5)
    # Wheelchair master: a visible short straight crop with a side-swept front,
    # not a one-pixel cap that disappears at sticker size.
    return "", path(
        f"M{hx-rx+2} {hy-18} L{hx-rx+4} {hy-43} "
        f"Q{hx-22} {hy-ry-23} {hx+rx+3} {hy-35} "
        f"Q{hx+35} {hy-52} {hx-5} {hy-58} "
        f"Q{hx-37} {hy-54} {hx-rx+2} {hy-18} Z",
        fill=d["hair"], sw=6,
    ) + path(f"M{hx-17} {hy-53} Q{hx+5} {hy-49} {hx+28} {hy-35}", stroke="#4B3B35", sw=4)


def wave2_profile_hair(d: dict[str, Any], profile_x: float) -> tuple[str, str]:
    """Return attached back/front hair geometry for authored Wave 2 side views."""
    _, hy, rx, ry = d["head"]
    style = d.get("hair_style")
    hair = d["hair"]
    highlight = d["hair_highlight"]
    if style == "bald":
        return "", path(f"M{profile_x-rx*.35} {hy-ry*.7} Q{profile_x} {hy-ry*.84} {profile_x+rx*.28} {hy-ry*.68}", stroke=d["skin_light"], sw=4, extra='opacity=".55"')
    if style == "head-covering":
        back = path(
            f"M{profile_x-rx*.5} {hy-ry*.62} Q{profile_x-rx*.72} {hy+38} {profile_x-rx*.48} {hy+103} "
            f"Q{profile_x+12} {hy+116} {profile_x+rx*.46} {hy+77} L{profile_x+rx*.44} {hy-15} Z",
            fill=hair, sw=7,
        )
        front = path(f"M{profile_x-rx*.18} {hy-ry*.72} Q{profile_x+rx*.28} {hy-ry*.86} {profile_x+rx*.48} {hy-19}", stroke=highlight, sw=5)
        front += path(f"M{profile_x-rx*.36} {hy+45} Q{profile_x-7} {hy+78} {profile_x+rx*.33} {hy+68}", stroke=highlight, sw=4)
        return back, front
    if style in {"long-wavy", "shoulder-wave"}:
        length = 112 if style == "long-wavy" else 76
        back = path(
            f"M{profile_x-rx*.46} {hy-ry*.62} Q{profile_x-rx*.72} {hy+20} {profile_x-rx*.48} {hy+length} "
            f"Q{profile_x+8} {hy+length+13} {profile_x+rx*.4} {hy+length-18} L{profile_x+rx*.42} {hy-14} Z",
            fill=hair, sw=7,
        )
        front = path(f"M{profile_x-rx*.2} {hy-ry*.72} Q{profile_x+rx*.18} {hy-ry*.9} {profile_x+rx*.48} {hy-25}", stroke=highlight, sw=5)
        return back, front
    if style == "voluminous-curls":
        back = "".join(ellipse(profile_x+x, hy+y, r, r, hair, INK, 4) for x, y, r in [(-28,-45,28),(0,-68,30),(28,-50,29),(-32,-12,27)])
        return back, path(f"M{profile_x-12} {hy-61} Q{profile_x+18} {hy-69} {profile_x+35} {hy-38}", stroke=highlight, sw=4)
    if style in {"short-loose-curls", "coily-taper"}:
        cap = "".join(ellipse(profile_x-28+i*14, hy-ry+8+(i%2)*4, 16, 16, hair, INK, 4) for i in range(5))
        return "", cap
    # Swept and undercut styles use a compact, attached cap.
    front = path(
        f"M{profile_x-rx*.48} {hy-22} Q{profile_x-rx*.25} {hy-ry-25} {profile_x+rx*.44} {hy-35} "
        f"Q{profile_x+rx*.24} {hy-ry-2} {profile_x-rx*.48} {hy-22} Z",
        fill=hair, sw=6,
    )
    front += path(f"M{profile_x-8} {hy-ry+7} Q{profile_x+18} {hy-ry+8} {profile_x+rx*.34} {hy-39}", stroke=highlight, sw=4)
    return "", front


def wave2_back_hair(d: dict[str, Any]) -> str:
    """Build a back-view identity silhouette without front-face openings."""
    hx, hy, rx, ry = d["head"]
    style = d.get("hair_style")
    if style == "bald":
        return ""
    if style == "head-covering":
        return path(
            f"M{hx-rx-15} {hy-34} Q{hx-rx-27} {hy+55} {hx-57} {hy+104} "
            f"Q{hx-28} {hy+120} {hx} {hy+112} Q{hx+28} {hy+120} {hx+57} {hy+104} "
            f"Q{hx+rx+27} {hy+55} {hx+rx+15} {hy-34} Z",
            fill=d["hair"], sw=7,
        ) + path(f"M{hx} {hy-ry+9} Q{hx-8} {hy+36} {hx} {hy+93}", stroke=d["hair_highlight"], sw=4)
    if style in {"long-wavy", "shoulder-wave"}:
        length = 116 if style == "long-wavy" else 79
        return path(
            f"M{hx-rx-12} {hy-40} Q{hx-rx-24} {hy+62} {hx-47} {hy+length} "
            f"Q{hx-24} {hy+length+14} {hx} {hy+length-1} Q{hx+24} {hy+length+14} {hx+47} {hy+length} "
            f"Q{hx+rx+24} {hy+62} {hx+rx+12} {hy-40} Z",
            fill=d["hair"], sw=7,
        ) + path(f"M{hx} {hy-ry+6} Q{hx-10} {hy+26} {hx} {hy+length-9}", stroke=d["hair_highlight"], sw=4)
    back, front = hair_layers(d)
    return back + front


def standing_legs(d: dict[str, Any]) -> tuple[str, str]:
    mode = d["mode"]
    if mode == "child":
        screen_left = rect(217, 305, 33, 123, 15, d["skin"], INK, 6) + rect(201, 416, 57, 29, 14, d["shoe"], INK, 6) + path("M210 425 L248 425", stroke=d["accent"], sw=5)
        screen_right = rect(262, 305, 33, 123, 15, d["skin"], INK, 6) + rect(255, 416, 57, 29, 14, d["shoe"], INK, 6) + path("M264 425 L302 425", stroke=d["accent"], sw=5)
        return screen_right, screen_left
    if d.get("wave2"):
        x, y, w, h = d["torso"]
        hip_y = y + h - 8
        ground = d["ground"]
        leg_width = d.get("leg_width", max(28, min(42, w * .26)))
        gap = d.get("leg_gap", max(17, w * .15))
        left_x = 256-gap-leg_width
        right_x = 256+gap
        leg_height = ground-hip_y-18
        shoe_width = leg_width+24
        screen_left = rect(left_x, hip_y, leg_width, leg_height, leg_width*.38, d["pants"], INK, 6)
        screen_left += rect(left_x-12, ground-28, shoe_width, 28, 13, d["shoe"], INK, 6)
        screen_right = rect(right_x, hip_y, leg_width, leg_height, leg_width*.38, d["pants"], INK, 6)
        screen_right += rect(right_x-3, ground-28, shoe_width, 28, 13, d["shoe"], INK, 6)
        return screen_right, screen_left
    screen_right = path("M254 303 L301 302 Q305 362 297 442 L260 442 Z", fill=d["pants"], sw=7) + rect(250, 432, 61, 28, 13, d["shoe"], INK, 6)
    if mode == "prosthesis":
        screen_left = path("M211 303 L248 303 L245 355 Q230 369 216 354 Z", fill=d["skin"], sw=7)
    else:
        screen_left = path("M211 302 Q210 360 215 442 L252 442 L258 303 Z", fill=d["pants"], sw=7) + rect(202, 432, 61, 28, 13, d["shoe"], INK, 6)
    return screen_right, screen_left


def torso_layer(d: dict[str, Any]) -> str:
    x, y, w, h = d["torso"]
    mode = d["mode"]
    clothing_style = d.get("clothing_style")
    if mode == "child":
        shirt = rect(x, y, w, h, 29, d["primary"], INK, 7)
        shirt += path(f"M{x+18} {y+15} Q{x+w/2} {y+34} {x+w-18} {y+15}", stroke="#FFD966", sw=5)
        skirt = path("M202 294 L310 294 L324 350 L188 350 Z", fill=d["pants"], sw=7)
        shirt += path("M244 255 C244 240 268 240 268 255 C268 272 256 279 256 279 C256 279 244 270 244 255 Z", fill=d["secondary"], stroke="none", sw=0)
        return shirt + skirt
    body = rect(x, y, w, h, 30, d["primary"], INK, 7)
    body += path(f"M{x+18} {y+18} Q{x+w/2} {y+43} {x+w-18} {y+18}", stroke=d["secondary"], sw=8)
    body += path(f"M{x+w*.18} {y+18} Q{x+w*.5} {y+8} {x+w*.82} {y+18}", stroke=d["accent"], sw=5)
    if clothing_style == "hoodie":
        body += path(f"M{x+w*.27} {y+4} Q{x+w*.5} {y+44} {x+w*.73} {y+4}", stroke=d["secondary"], sw=8)
        body += rect(x+w*.27, y+h*.58, w*.46, h*.25, 14, d["secondary"], INK, 4)
    elif clothing_style == "layered-jacket":
        body += path(f"M{x+w*.5} {y+7} L{x+w*.5} {y+h-8}", stroke=d["secondary"], sw=6)
        body += path(f"M{x+w*.18} {y+18} L{x+w*.42} {y+58} M{x+w*.82} {y+18} L{x+w*.58} {y+58}", stroke=d["accent"], sw=7)
    elif clothing_style == "modest-tunic":
        body += path(f"M{x+18} {y+h*.56} Q{x+w*.5} {y+h*.72} {x+w-18} {y+h*.56}", stroke=d["secondary"], sw=7)
        body += path(f"M{x+w*.5} {y+10} L{x+w*.5} {y+h-9}", stroke=d["accent"], sw=4)
    elif clothing_style == "graphic-tee":
        body += ellipse(x+w*.5, y+h*.48, 22, 22, d["secondary"], INK, 4)
        body += path(f"M{x+w*.5-11} {y+h*.48} L{x+w*.5+11} {y+h*.48}", stroke=d["accent"], sw=5)
    elif clothing_style == "cardigan":
        body += path(f"M{x+w*.33} {y+10} L{x+w*.33} {y+h-10} M{x+w*.67} {y+10} L{x+w*.67} {y+h-10}", stroke=d["secondary"], sw=6)
        body += path(f"M{x+w*.33} {y+11} L{x+w*.5} {y+47} L{x+w*.67} {y+11}", stroke=d["accent"], sw=5)
    elif mode == "prosthesis":
        body += path(f"M{x+14} {y+12} L{x+32} {y+h-12} M{x+w-14} {y+12} L{x+w-32} {y+h-12}", stroke=d["secondary"], sw=8)
        body += path(f"M{x+w/2} {y+8} L{x+w/2} {y+h-8}", stroke=d["accent"], sw=4)
    elif mode == "hearing-aid":
        body += path(f"M{x+w*.28} {y+10} L{x+w*.28} {y+h-10} M{x+w*.72} {y+10} L{x+w*.72} {y+h-10}", stroke=d["secondary"], sw=6)
        body += "".join(ellipse(x+w*.28, y+36+i*25, 3, 3, INK, "none", 0) for i in range(4))
        body += path(f"M{x+w*.28} {y+11} L{x+w*.48} {y+48} L{x+w*.36} {y+79}", stroke=d["secondary"], sw=5)
        body += path(f"M{x+w*.72} {y+11} L{x+w*.52} {y+48} L{x+w*.64} {y+79}", stroke=d["secondary"], sw=5)
    elif mode == "rollator":
        body += path(f"M{x+8} {y+48} Q{x+w/2} {y+78} {x+w-8} {y+48}", stroke=d["secondary"], sw=10)
        body += path(f"M{x+25} {y+58} Q{x+w/2} {y+90} {x+w-25} {y+58}", stroke=d["accent"], sw=5)
        for dx in (42, 62, 82, 102):
            body += path(f"M{x+dx} {y+55} l7 7 l-7 7 l-7 -7 Z", fill=d["accent"], stroke="none", sw=0)
    elif mode == "wheelchair":
        body += path(f"M{x+18} {y+12} L{x+w*.44} {y+h-14} M{x+w-18} {y+12} L{x+w*.56} {y+h-14}", stroke=d["secondary"], sw=8)
        body += path(f"M{x+w*.44} {y+22} L{x+w*.56} {y+22} L{x+w*.56} {y+h-18} L{x+w*.44} {y+h-18} Z", fill=d["accent"], stroke=INK, sw=3)
    else:
        body += path(f"M{x+18} {y+52} Q{x+w/2} {y+65} {x+w-18} {y+52}", stroke="url(#softShade)", sw=12)
    return body


def arm(d: dict[str, Any], side: str, pose: str) -> str:
    x, y, w, _ = d["torso"]
    # Character-anatomical left appears on screen-right in an unmirrored front view.
    sx = x+w-8 if side == "left" else x+8
    sy = y+34
    direction = 1 if side == "left" else -1
    raised = pose in {"greeting", "farewell", "surprise", "celebration"}
    if d.get("device") == "white-cane.orientation" and side == "right":
        # The character-right hand owns the cane for every semantic pose.
        # Keeping it stable prevents a wave or celebration from detaching the
        # hand from the grip while the free hand remains expressive.
        elbow = (sx+direction*28, sy+70)
        hand = (sx+direction*22, sy+120)
        raised = False
    elif d.get("device") == "white-cane.orientation" and pose == "greeting" and side == "left":
        elbow = (sx+direction*36, sy-32)
        hand = (sx+direction*48, sy-90)
    elif pose == "greeting" and side == "right":
        elbow = (sx+direction*36, sy-32)
        hand = (sx+direction*48, sy-90)
    elif pose == "farewell" and side == "left":
        elbow = (sx+direction*36, sy-32)
        hand = (sx+direction*48, sy-90)
    elif pose == "celebration":
        elbow = (sx+direction*34, sy-42)
        hand = (sx+direction*52, sy-104)
    elif pose == "surprise":
        elbow = (sx+direction*28, sy+8)
        hand = (256+direction*58, d["head"][1]+30)
    elif pose == "agreement":
        elbow = (sx+direction*20, sy+35)
        hand = (256+direction*45, sy+10)
    elif pose == "disagreement":
        elbow = (sx+direction*16, sy+45)
        hand = (256-direction*38, sy+73)
    elif pose == "gratitude":
        elbow = (sx+direction*18, sy+47)
        hand = (256+direction*10, sy+62)
    elif pose == "concern":
        elbow = (sx+direction*24, sy+22)
        hand = (256+direction*38, d["head"][1]+43)
    elif pose == "greeting" and side == "left" and d["mode"] == "rollator":
        elbow, hand = (sx+22, sy+40), (335, 300)
    elif d["mode"] == "rollator":
        elbow = (sx+direction*20, sy+42)
        hand = (335, 300) if side == "left" else (177, 300)
    elif d["mode"] == "wheelchair":
        elbow = (sx+direction*28, sy+72)
        hand = (256+direction*72, 332)
    else:
        elbow = (sx+direction*28, sy+70)
        hand = (sx+direction*22, sy+120)
    sleeve_end = ((sx+elbow[0])/2, (sy+elbow[1])/2)
    result = line([(sx,sy), sleeve_end, elbow], d["primary"], 24, 8)
    result += line([elbow, hand], d["skin"], 18, 7)
    result += ellipse(hand[0], hand[1], 13 if raised else 11, 15 if raised else 13, d["skin_light"], INK, 5)
    if raised:
        for offset in (-12, -4, 4, 12):
            result += path(
                f"M{hand[0]+offset*.35} {hand[1]-6} "
                f"L{hand[0]+offset*1.15} {hand[1]-28+abs(offset)*.15}",
                stroke=d["skin"], sw=6,
            )
    return result


def prosthesis_layers(d: dict[str, Any]) -> dict[str, str]:
    return {
        "device-prosthesis-socket-right": rect(214, 346, 30, 35, 12, "#30343B", INK, 5),
        "device-prosthesis-pylon-right": path("M229 379 L229 434", stroke="#66717E", sw=13)
        + path("M229 382 L229 432", stroke="#B8C1C8", sw=5),
        "device-prosthetic-foot-right": rect(191, 426, 58, 31, 14, "#B9C5CB", INK, 6)
        + path("M199 438 L235 438", stroke=d["primary"], sw=5),
    }


def wheel_part(cx: int, cy: int, outer: int, inner: int, spoke_step: int = 30) -> tuple[str, str]:
    wheel = ellipse(cx, cy, outer, outer, "none", INK, 12)
    pushrim = ellipse(cx, cy, inner, inner, "none", "#7F8992", 5)
    for angle in range(0, 360, spoke_step):
        import math
        x = cx + math.cos(math.radians(angle))*inner
        y = cy + math.sin(math.radians(angle))*inner
        pushrim += path(f"M{cx} {cy} L{x:.1f} {y:.1f}", stroke="#8B949C", sw=2)
    return wheel, pushrim


def wheelchair_layers(d: dict[str, Any]) -> tuple[dict[str, str], str, str]:
    screen_left_wheel, screen_left_pushrim = wheel_part(154, 393, 78, 62)
    screen_right_wheel, screen_right_pushrim = wheel_part(376, 398, 66, 52)
    parts = {
        "device-wheel-left": screen_right_wheel,
        "device-pushrim-left": screen_right_pushrim,
        "device-wheel-right": screen_left_wheel,
        "device-pushrim-right": screen_left_pushrim,
        "device-wheelchair-frame": path("M168 265 L182 381 L350 382 L362 300", stroke="#434B52", sw=12)
        + rect(182, 292, 170, 28, 12, "#252D34", INK, 5)
        + path("M182 306 L170 450 M350 306 L372 450", stroke="#5F6870", sw=7)
        + ellipse(170, 451, 18, 18, "#242A30", INK, 5)
        + ellipse(373, 451, 18, 18, "#242A30", INK, 5),
        "device-wheelchair-footrest": path("M208 412 L340 412 L354 431 L225 431 Z", fill="#353D44", stroke=INK, sw=6),
    }
    # Character-left is screen-right. Both knees visibly bend before the feet
    # settle on the footrest instead of projecting as straight planks.
    leg_left = path("M276 300 Q294 334 278 365 L294 404", fill="none", stroke=d["pants"], sw=34) + rect(269, 392, 58, 28, 13, d["shoe"], INK, 6)
    leg_right = path("M236 300 Q218 334 236 365 L220 404", fill="none", stroke=d["pants"], sw=34) + rect(191, 392, 58, 28, 13, d["shoe"], INK, 6)
    return parts, leg_left, leg_right


def rollator_layers(d: dict[str, Any]) -> dict[str, str]:
    def wheel(cx: int, cy: int, radius: int, fill: str, stroke_width: int) -> str:
        # The asymmetric hub mark makes in-place wheel rotation observable in
        # motion-review output without adding noisy spokes at sticker sizes.
        return ellipse(cx, cy, radius, radius, fill, INK, stroke_width) + path(
            f"M{cx} {cy} L{cx} {cy-radius+4}", stroke=d["accent"], sw=max(3, stroke_width-1)
        )

    return {
        "device-rollator-frame": path("M168 300 L185 449 M344 300 L327 449 M168 300 L344 300", stroke="#5A3470", sw=10)
        + path("M183 355 L329 355", stroke="#8D59A3", sw=7)
        + rect(177, 347, 158, 55, 12, "#252D34", INK, 6)
        + path("M181 402 L168 451 M331 402 L344 451", stroke="#5A3470", sw=10),
        "device-rollator-handle-left": rect(309, 288, 52, 18, 9, "#242A31", INK, 5),
        "device-rollator-handle-right": rect(151, 288, 52, 18, 9, "#242A31", INK, 5),
        "device-rollator-wheel-front-left": wheel(347, 451, 18, "#252A30", 5),
        "device-rollator-wheel-front-right": wheel(165, 451, 18, "#252A30", 5),
        "device-rollator-wheel-rear-left": wheel(319, 438, 12, "#414850", 4),
        "device-rollator-wheel-rear-right": wheel(193, 438, 12, "#414850", 4),
    }


def hearing_aid_layers(d: dict[str, Any]) -> dict[str, str]:
    hx, hy, rx, _ = d["head"]
    return {
        "device-hearing-case-right": ellipse(hx-rx-14, hy-7, 7, 11, "#D5E6E4", INK, 4),
        "device-hearing-tube-right": path(f"M{hx-rx+3} {hy-22} Q{hx-rx-18} {hy-20} {hx-rx-14} {hy+8}", stroke=d["accent"], sw=7),
        "device-hearing-earpiece-right": path(f"M{hx-rx-14} {hy+8} Q{hx-rx-10} {hy+22} {hx-rx-2} {hy+25}", stroke=d["accent"], sw=9),
    }


def white_cane_layers(d: dict[str, Any]) -> dict[str, str]:
    x, y, _, h = d["torso"]
    grip_x = x - 14
    grip_y = y + h + 35
    tip_x = grip_x + 66
    tip_y = d["ground"] - 2
    return {
        "device-white-cane-grip": rect(grip_x-8, grip_y-17, 16, 34, 8, "#263451", INK, 4),
        "device-white-cane-shaft": path(
            f"M{grip_x} {grip_y+10} L{tip_x} {tip_y-13}", stroke=INK, sw=15
        ) + path(
            f"M{grip_x} {grip_y+10} L{tip_x} {tip_y-13}", stroke="#F6F4EA", sw=9
        ) + path(
            f"M{tip_x-16} {tip_y-48} L{tip_x} {tip_y-13}", stroke=INK, sw=15
        ) + path(f"M{tip_x-16} {tip_y-48} L{tip_x} {tip_y-13}", stroke="#E85D68", sw=9),
        "device-white-cane-tip": ellipse(tip_x, tip_y, 10, 7, "#303944", INK, 4),
    }


def build_layers(d: dict[str, Any]) -> dict[str, str]:
    mode = d["mode"]
    layers: dict[str, str] = {layer_id: "" for layer_id in LAYER_ORDER}
    layers.update({
        "shadow": ellipse(256, d["ground"]+7, 105 if mode != "wheelchair" else 180, 14, "#AAB2BD", "none", 0, 'opacity=".65"'),
        "torso": torso_layer(d),
        "head": head_layer(d),
        "face-friendly": face_layer(d),
        "arm-left-rest": arm(d, "left", "rest"),
        "arm-right-rest": arm(d, "right", "rest"),
    })
    for expression in EXPRESSIONS:
        if expression != "happy":
            layers[f"face-{expression}"] = expression_face_layer(d, expression)
    for pose in POSES:
        if pose != "rest":
            layers[f"arm-left-{pose}"] = arm(d, "left", pose)
            layers[f"arm-right-{pose}"] = arm(d, "right", pose)
    hair_back, hair_front = hair_layers(d)
    layers["hair-back"] = hair_back
    layers["hair-front"] = hair_front
    if mode == "wheelchair":
        parts, left, right = wheelchair_layers(d)
        layers.update(parts)
        layers["leg-left"], layers["leg-right"] = left, right
    else:
        left, right = standing_legs(d)
        layers["leg-left"], layers["leg-right"] = left, right
    if mode == "rollator":
        layers.update(rollator_layers(d))
    if mode == "hearing-aid":
        layers.update(hearing_aid_layers(d))
    if mode == "prosthesis":
        layers.update(prosthesis_layers(d))
    if d["device"] == "white-cane.orientation":
        layers.update(white_cane_layers(d))
    return layers


def build_lod100_layers(d: dict[str, Any]) -> dict[str, str]:
    mode = d["mode"]
    if mode == "prosthesis":
        return {
            "device-prosthesis-socket-right": rect(211, 344, 36, 40, 12, "#263451", INK, 6),
            "device-prosthesis-pylon-right": path("M229 380 L229 435", stroke="#D6E0E4", sw=11),
            "device-prosthetic-foot-right": rect(188, 424, 64, 34, 14, "#8FC9D0", INK, 7),
        }
    if mode == "wheelchair":
        _, left_pushrim = wheel_part(376, 398, 66, 52, 60)
        _, right_pushrim = wheel_part(154, 393, 78, 62, 60)
        return {
            "device-pushrim-left": left_pushrim,
            "device-pushrim-right": right_pushrim,
        }
    if mode == "hearing-aid":
        hx, hy, rx, _ = d["head"]
        return {
            "device-hearing-case-right": ellipse(hx-rx-14, hy-7, 10, 14, "#D5E6E4", INK, 5),
            "device-hearing-tube-right": path(f"M{hx-rx+3} {hy-22} Q{hx-rx-19} {hy-18} {hx-rx-14} {hy+9}", stroke=d["accent"], sw=10),
            "device-hearing-earpiece-right": path(f"M{hx-rx-14} {hy+8} Q{hx-rx-9} {hy+23} {hx-rx-1} {hy+25}", stroke=d["accent"], sw=11),
        }
    if mode == "rollator":
        return {
            "device-rollator-handle-left": rect(306, 285, 58, 23, 10, "#242A31", INK, 6),
            "device-rollator-handle-right": rect(148, 285, 58, 23, 10, "#242A31", INK, 6),
            "device-rollator-wheel-front-left": ellipse(347, 451, 21, 21, "#252A30", INK, 6),
            "device-rollator-wheel-front-right": ellipse(165, 451, 21, 21, "#252A30", INK, 6),
        }
    return {}


def turnaround_content(d: dict[str, Any], layers: dict[str, str], view: str) -> str:
    """Build authored orthographic technical views without reusing a camera crop."""
    hx, hy, rx, ry = d["head"]
    x, y, w, h = d["torso"]
    shadow = ellipse(256, d["ground"]+7, 105 if d["mode"] != "wheelchair" else 180, 14, "#AAB2BD", "none", 0, 'opacity=".65"')
    device_ids = [layer_id for layer_id in LAYER_ORDER if layer_id.startswith("device-") and layers.get(layer_id)]
    devices = "".join(layers[layer_id] for layer_id in device_ids)
    if view == "front":
        selected = [layer_id for layer_id in LAYER_ORDER if layers.get(layer_id) and not layer_id.startswith("face-") and not layer_id.startswith("arm-")]
        return "".join(layers[layer_id] for layer_id in selected) + layers["face-friendly"] + layers["arm-left-rest"] + layers["arm-right-rest"]
    if view == "three-quarter":
        body_ids = ["leg-left", "leg-right", "torso", "hair-back"]
        body = "".join(layers[layer_id] for layer_id in body_ids if layers.get(layer_id))
        face_x = hx + 13
        head = ellipse(face_x, hy, rx*.9, ry, d["skin"], INK, 7)
        hair_translate = face_x - hx*.92 if d.get("wave2") else 13
        hair = f'<g transform="translate({hair_translate:.2f} 0) scale(.92 1)">{layers["hair-front"]}</g>'
        face = "".join([
            ellipse(face_x-15, hy+4, 9, 12, WHITE, INK, 4),
            ellipse(face_x+24, hy+4, 7, 10, WHITE, INK, 4),
            ellipse(face_x-12, hy+6, 4, 6, INK, INK, 0),
            ellipse(face_x+26, hy+6, 3, 5, INK, INK, 0),
            path(f"M{face_x+4} {hy+12} Q{face_x+18} {hy+18} {face_x+9} {hy+24}", stroke=d["skin_light"], sw=4),
            path(f"M{face_x-17} {hy+36} Q{face_x+8} {hy+52} {face_x+30} {hy+31}", sw=6),
        ])
        return shadow + f'<g transform="translate(38 0) scale(.86 1)">{devices}{body}{layers["arm-left-rest"]}{layers["arm-right-rest"]}</g>' + head + hair + face
    if view == "side":
        profile_x = 258
        torso_width = max(58, w*.5)
        body = rect(profile_x-torso_width/2, y, torso_width, h, 25, d["primary"], INK, 7)
        body += path(f"M{profile_x-torso_width*.3} {y+20} L{profile_x+torso_width*.3} {y+20}", stroke=d["secondary"], sw=7)
        head = ellipse(profile_x, hy, rx*.58, ry, d["skin"], INK, 7)
        profile = ellipse(profile_x+rx*.2, hy+2, 9, 12, WHITE, INK, 4)
        profile += ellipse(profile_x+rx*.24, hy+4, 4, 6, INK, INK, 0)
        profile += path(f"M{profile_x+rx*.5} {hy+8} q12 8 0 16", stroke=d["skin_light"], sw=5)
        profile += path(f"M{profile_x+2} {hy+37} Q{profile_x+18} {hy+48} {profile_x+31} {hy+34}", sw=5)
        if d.get("wave2"):
            hair_back, hair_front = wave2_profile_hair(d, profile_x)
        else:
            hair_back = ""
            hair_front = f'<g transform="translate(2 0) scale(.64 1)">{layers["hair-front"]}</g>'
        if d["mode"] == "wheelchair":
            lower = ellipse(254, 394, 76, 76, "none", INK, 12) + ellipse(254, 394, 60, 60, "none", "#7F8992", 5)
            lower += path("M220 292 L230 379 L308 379 L318 306 M233 322 L215 450", stroke="#434B52", sw=10)
            lower += path("M258 302 Q282 338 260 370 L287 407", stroke=d["pants"], sw=32) + rect(269, 394, 55, 27, 13, d["shoe"], INK, 6)
        else:
            lower = rect(236, y+h-7, 34, max(45, d["ground"]-(y+h)+5), 14, d["pants"], INK, 6)
            lower += rect(230, d["ground"]-22, 61, 27, 13, d["shoe"], INK, 6)
            if d["mode"] == "rollator":
                lower += path("M290 300 L310 451 M290 300 L350 300", stroke="#5A3470", sw=10)
                lower += ellipse(312, 451, 18, 18, "#252A30", INK, 5) + ellipse(342, 438, 12, 12, "#414850", INK, 4)
        arm_side = path(f"M{profile_x} {y+35} Q{profile_x+35} {y+95} {profile_x+20} {y+150}", stroke=d["skin"], sw=20)
        cane_side = ""
        if d.get("device") == "white-cane.orientation":
            grip_x, grip_y = profile_x+20, y+150
            tip_x, tip_y = profile_x+69, d["ground"]-1
            cane_side = rect(grip_x-7, grip_y-15, 14, 30, 7, "#263451", INK, 4)
            cane_side += path(f"M{grip_x} {grip_y+9} L{tip_x} {tip_y-12}", stroke="#F6F4EA", sw=10)
            cane_side += path(f"M{tip_x-12} {tip_y-42} L{tip_x} {tip_y-12}", stroke="#E85D68", sw=10)
            cane_side += ellipse(tip_x, tip_y, 9, 6, "#303944", INK, 4)
        return shadow + lower + body + arm_side + cane_side + hair_back + head + hair_front + profile
    if view == "back":
        if d["mode"] == "wheelchair":
            lower = devices + layers["leg-left"] + layers["leg-right"]
        else:
            lower = layers["leg-left"] + layers["leg-right"] + devices
        back_torso = rect(x, y, w, h, 30, d["primary"], INK, 7)
        back_torso += path(f"M{x+18} {y+22} Q{x+w/2} {y+38} {x+w-18} {y+22}", stroke=d["secondary"], sw=8)
        back_head = ellipse(hx, hy, rx, ry, d["skin"], INK, 7)
        if d.get("wave2"):
            hair = wave2_back_hair(d)
        else:
            hair_back, hair_front = hair_layers(d)
            hair = hair_back + hair_front
        arms = arm(d, "left", "rest") + arm(d, "right", "rest")
        return shadow + lower + arms + back_torso + back_head + hair
    raise ValueError(f"unknown turnaround view: {view}")


LAYER_ORDER = [
    "shadow", "device-wheel-left", "device-pushrim-left", "device-wheel-right",
    "device-pushrim-right", "device-wheelchair-frame", "hair-back", "leg-left", "leg-right",
    "device-prosthesis-socket-right", "device-prosthesis-pylon-right", "device-prosthetic-foot-right", "torso",
    "head", "hair-front", "face-friendly",
    *[f"face-{expression}" for expression in EXPRESSIONS if expression != "happy"],
    *[f"arm-{side}-{pose}" for pose in POSES for side in ("left", "right")],
    "device-wheelchair-footrest",
    "device-white-cane-grip", "device-white-cane-shaft", "device-white-cane-tip",
    "device-hearing-case-right", "device-hearing-tube-right", "device-hearing-earpiece-right",
    "device-rollator-frame", "device-rollator-handle-left", "device-rollator-handle-right",
    "device-rollator-wheel-rear-left", "device-rollator-wheel-rear-right",
    "device-rollator-wheel-front-left", "device-rollator-wheel-front-right",
]

DEVICE_BINDINGS: dict[str, dict[str, str]] = {
    "device.none": {},
    "white-cane.orientation": {
        "grip": "device-white-cane-grip",
        "shaft": "device-white-cane-shaft",
        "tip": "device-white-cane-tip",
    },
    "prosthesis.lower-leg.right": {
        "socket.right": "device-prosthesis-socket-right",
        "pylon.right": "device-prosthesis-pylon-right",
        "prosthetic-foot.right": "device-prosthetic-foot-right",
    },
    "wheelchair.manual": {
        "frame": "device-wheelchair-frame",
        "wheel.left": "device-wheel-left",
        "wheel.right": "device-wheel-right",
        "pushrim.left": "device-pushrim-left",
        "pushrim.right": "device-pushrim-right",
        "footrest": "device-wheelchair-footrest",
    },
    "hearing-aid.behind-ear.right": {
        "case.right": "device-hearing-case-right",
        "tube.right": "device-hearing-tube-right",
        "earpiece.right": "device-hearing-earpiece-right",
    },
    "rollator.four-wheel": {
        "frame": "device-rollator-frame",
        "handle.left": "device-rollator-handle-left",
        "handle.right": "device-rollator-handle-right",
        "wheel.front-left": "device-rollator-wheel-front-left",
        "wheel.front-right": "device-rollator-wheel-front-right",
        "wheel.rear-left": "device-rollator-wheel-rear-left",
        "wheel.rear-right": "device-rollator-wheel-rear-right",
    },
}


def pivots(d: dict[str, Any]) -> dict[str, dict[str, float]]:
    hx, hy, _, _ = d["head"]
    x, y, w, h = d["torso"]
    if d["mode"] == "wheelchair":
        hip_y = 302
        foot_y = 407
    else:
        hip_y = y+h-10
        foot_y = d["ground"]
    points = {
        "root": {"x": 256, "y": d["ground"]}, "hips": {"x": 256, "y": hip_y},
        "torso": {"x": 256, "y": y+h*.55}, "chest": {"x": 256, "y": y+h*.28},
        "neck": {"x": 256, "y": y},
        "head": {"x": hx, "y": hy}, "shoulder_left": {"x": x+w-8, "y": y+34},
        "shoulder_right": {"x": x+8, "y": y+34}, "elbow_left": {"x": x+w+20, "y": y+104},
        "elbow_right": {"x": x-20, "y": y+104}, "wrist_left": {"x": x+w+14, "y": y+142},
        "wrist_right": {"x": x-14, "y": y+142}, "hand_left": {"x": x+w+14, "y": y+154},
        "hand_right": {"x": x-14, "y": y+154}, "ear_right": {"x": hx-d["head"][2], "y": hy},
        "hip_left": {"x": 280, "y": hip_y},
        "hip_right": {"x": 232, "y": hip_y}, "knee_left": {"x": 280, "y": (hip_y+foot_y)*.55},
        "knee_right": {"x": 232, "y": (hip_y+foot_y)*.55}, "ankle_left": {"x": 280, "y": foot_y-20},
        "ankle_right": {"x": 232, "y": foot_y-20}, "foot_left": {"x": 280, "y": foot_y},
        "foot_right": {"x": 232, "y": foot_y}, "device": {"x": 256, "y": d["ground"]},
    }
    if d["device"] == "white-cane.orientation":
        points["device_cane_grip"] = {"x": x-14, "y": y+h+35}
    if d["mode"] == "wheelchair":
        points.update({
            "device_wheel_left": {"x": 376, "y": 398},
            "device_wheel_right": {"x": 154, "y": 393},
        })
    if d["mode"] == "rollator":
        points.update({
            "device_wheel_front_left": {"x": 347, "y": 451},
            "device_wheel_front_right": {"x": 165, "y": 451},
            "device_wheel_rear_left": {"x": 319, "y": 438},
            "device_wheel_rear_right": {"x": 193, "y": 438},
        })
    return points


def pack_document(master_id: str, d: dict[str, Any], layers: dict[str, str], lod_layers: dict[str, str], identity_sha: str) -> dict[str, Any]:
    ps = pivots(d)
    items = []
    for z, layer_id in enumerate(LAYER_ORDER):
        if not layers[layer_id]:
            continue
        item: dict[str, Any] = {"id": layer_id, "source": f"layers/{z:02d}-{layer_id}.svg", "z": z*10, "depth": z*.015}
        if layer_id in lod_layers:
            item["lod_sources"] = {"100": f"layers-lod100/{z:02d}-{layer_id}.svg"}
        if d["mode"] == "wheelchair" and layer_id in {
            "device-wheel-left", "device-pushrim-left",
            "device-wheel-right", "device-pushrim-right",
        }:
            side = "left" if layer_id.endswith("left") else "right"
            item.update({"parent": "device-wheelchair-frame", "pivot": f"device_wheel_{side}"})
        elif d["mode"] == "wheelchair" and layer_id == "device-wheelchair-footrest":
            item.update({"parent": "device-wheelchair-frame", "pivot": "device"})
        elif d["mode"] == "rollator" and layer_id.startswith("device-rollator-wheel-"):
            side = layer_id.removeprefix("device-rollator-wheel-").replace("-", "_")
            item.update({"parent": "device-rollator-frame", "pivot": f"device_wheel_{side}"})
        elif d["mode"] == "rollator" and layer_id.startswith("device-rollator-handle-"):
            item.update({"parent": "device-rollator-frame", "pivot": "device"})
        elif layer_id == "hair-back":
            # Keep back hair as a torso sibling so z-order remains behind the
            # head in scene-graph renderers. Head motion recipes bind it to the
            # same semantic head transform explicitly.
            item.update({"parent": "torso", "pivot": "head"})
        elif layer_id.startswith("hair") or layer_id.startswith("face"):
            item.update({"parent": "head", "pivot": "head"})
        elif layer_id == "device-prosthesis-socket-right":
            item.update({"parent": "leg-right", "pivot": "knee_right"})
        elif layer_id == "device-prosthesis-pylon-right":
            item.update({"parent": "device-prosthesis-socket-right", "pivot": "ankle_right"})
        elif layer_id == "device-prosthetic-foot-right":
            item.update({"parent": "device-prosthesis-pylon-right", "pivot": "foot_right"})
        elif layer_id.startswith("device-hearing-"):
            item.update({"parent": "head", "pivot": "ear_right"})
        elif layer_id == "device-white-cane-grip":
            item.update({"parent": "torso", "pivot": "device_cane_grip"})
        elif layer_id == "device-white-cane-shaft":
            item.update({"parent": "device-white-cane-grip", "pivot": "device_cane_grip"})
        elif layer_id == "device-white-cane-tip":
            item.update({"parent": "device-white-cane-shaft", "pivot": "device_cane_grip"})
        elif layer_id.startswith("arm"):
            item.update({"parent": "torso", "pivot": "shoulder_left" if "left" in layer_id else "shoulder_right"})
        elif layer_id.startswith("leg"):
            item.update({"parent": "torso", "pivot": "hip_left" if "left" in layer_id else "hip_right"})
        elif layer_id == "head":
            item.update({"parent": "torso", "pivot": "neck", "collision_bounds": {"x": d["head"][0]-d["head"][2]-18, "y": d["head"][1]-d["head"][3]-26, "width": d["head"][2]*2+36, "height": d["head"][3]*2+48}})
        elif layer_id == "torso":
            item.update({"pivot": "hips", "collision_bounds": {"x": 60, "y": 28, "width": 392, "height": 445}})
        # Depth is local to the parent and therefore accumulates. Device parts
        # that belong to one rigid assembly must not each add another parallax
        # offset. Keep expressive face/hair separation while preserving every
        # attachment and hand/device contact.
        if layer_id == "shadow":
            item["depth"] = 0.0
        elif layer_id == "torso":
            item["depth"] = .18
        elif layer_id == "head":
            item["depth"] = .08
        elif layer_id == "hair-back":
            item["depth"] = .025
        elif layer_id.startswith("hair") or layer_id.startswith("face"):
            item["depth"] = .02
        elif layer_id.startswith("leg") or layer_id.startswith("arm"):
            item["depth"] = 0.0 if d["mode"] in {"wheelchair", "rollator"} else .015
        elif layer_id.startswith("device-prosthesis") or layer_id == "device-prosthetic-foot-right":
            item["depth"] = 0.0
        elif layer_id.startswith("device-hearing-"):
            item["depth"] = 0.0
        elif layer_id.startswith("device-white-cane-"):
            item["depth"] = 0.0
        elif layer_id == "device-wheelchair-frame":
            item["depth"] = .18
        elif layer_id.startswith("device-wheel") or layer_id.startswith("device-pushrim") or layer_id == "device-wheelchair-footrest":
            item["depth"] = 0.0
        elif layer_id == "device-rollator-frame":
            item["depth"] = .18
        elif layer_id.startswith("device-rollator-"):
            item["depth"] = 0.0
        items.append(item)
    base = [
        layer_id for layer_id in LAYER_ORDER
        if layers[layer_id] and not layer_id.startswith("face-") and not layer_id.startswith("arm-")
    ]
    expression_bindings = {"friendly": ["face-friendly"], "happy": ["face-friendly"]}
    expression_bindings.update({
        expression: [f"face-{expression}"] for expression in EXPRESSIONS if expression != "happy"
    })
    pose_bindings = {"neutral": ["arm-left-rest", "arm-right-rest"]}
    pose_bindings.update({
        pose: [f"arm-left-{pose}", f"arm-right-{pose}"] for pose in POSES
    })
    return {
        "schema_version": 1, "pack_id": f"human-canonical-{master_id.lower()}",
        "character_identity": {"character_id": master_id, "contract_version": 1, "contract_sha256": identity_sha,
                               "required_features": ["human", "canonical-family-v1", "full-body", "semantic-rig-v2", d["device"]]},
        "rig": {"contract_id": "humanoid-production-v2", "contract_version": 2,
                "device_profile": d["device"],
                "device_bindings": DEVICE_BINDINGS[d["device"]],
                "pose_bindings": {"greeting": {"root": "torso", "head": "head", "face": "face-friendly", "gesture.primary": "arm-right-greeting", "gesture.secondary": "arm-left-greeting", "ground.contact": "shadow", "gaze.target": "head"}}},
        "canvas": {"width": CANVAS, "height": CANVAS}, "layers": items, "base_layers": base,
        "expressions": expression_bindings,
        "poses": pose_bindings,
        "provenance": {"creator": "MascotRender project", "license": "MIT", "source": "Original deterministic semantic vector art authored in the MascotRender repository"},
        "anchors": {"face_center": {"x": d["head"][0], "y": d["head"][1]}, "bust_center": {"x": 256, "y": d["torso"][1]+30},
                    "body_center": {"x": 256, "y": (d["head"][1]+d["ground"])/2}, "ground_contact": {"x": 256, "y": d["ground"]}},
        "pivots": ps, "avoid_regions": [], "text_clearance": 10,
    }


FRAMINGS = {
    "face-closeup": ("face_center", 1.55, 0, 60), "bust": ("bust_center", 1.22, 0, 40),
    "three-quarter": ("body_center", 1.05, 0, 25), "full-body": ("body_center", .91, 0, 18),
    "dynamic-full-body": ("body_center", .84, 0, 18),
}


def loop_track(target: str, property_name: str, middle: float) -> dict[str, Any]:
    return {
        "target": target,
        "property": property_name,
        "keyframes": [
            {"at_ms": 0, "value": 0, "easing": "ease_in_out"},
            {"at_ms": 400, "value": middle, "easing": "ease_in_out"},
            {"at_ms": 800, "value": 0},
        ],
    }


def device_motion_tracks(master_id: str) -> list[dict[str, Any]]:
    if master_id == "H05":
        return [
            {
                "target": "device-white-cane-grip",
                "property": "rotation_degrees",
                "keyframes": [
                    {"at_ms": 0, "value": -12, "easing": "ease_in_out"},
                    {"at_ms": 200, "value": -28, "easing": "ease_in_out"},
                    {"at_ms": 600, "value": -12, "easing": "ease_in_out"},
                    {"at_ms": 800, "value": -12},
                ],
            },
        ]
    if master_id == "H04":
        return [
            loop_track("torso", "translate_y", -12),
            loop_track("device-prosthesis-socket-right", "rotation_degrees", 10),
            loop_track("device-prosthesis-pylon-right", "rotation_degrees", -8),
            loop_track("device-prosthetic-foot-right", "rotation_degrees", 7),
            {"target": "shadow", "property": "scale_x", "keyframes": [
                {"at_ms": 0, "value": 1, "easing": "ease_in_out"},
                {"at_ms": 400, "value": .72, "easing": "ease_in_out"},
                {"at_ms": 800, "value": 1},
            ]},
        ]
    if master_id == "H07":
        return [
            loop_track("device-wheel-left", "rotation_degrees", 28),
            loop_track("device-pushrim-left", "rotation_degrees", 28),
            loop_track("device-wheel-right", "rotation_degrees", 28),
            loop_track("device-pushrim-right", "rotation_degrees", 28),
            loop_track("torso", "translate_x", 3),
            loop_track("device-wheelchair-frame", "translate_x", 3),
        ]
    if master_id == "H12":
        return [
            loop_track("head", "rotation_degrees", 7),
            loop_track("hair-back", "rotation_degrees", 7),
        ]
    if master_id == "H13":
        return [
            loop_track("device-rollator-wheel-front-left", "rotation_degrees", 24),
            loop_track("device-rollator-wheel-front-right", "rotation_degrees", 24),
            loop_track("device-rollator-wheel-rear-left", "rotation_degrees", 24),
            loop_track("device-rollator-wheel-rear-right", "rotation_degrees", 24),
            loop_track("torso", "translate_x", 3),
            loop_track("device-rollator-frame", "translate_x", 3),
        ]
    return []


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_master(root: Path, master_id: str, d: dict[str, Any]) -> dict[str, Any]:
    target = root / master_id
    layers = build_layers(d)
    lod_layers = build_lod100_layers(d)
    status = str(d.get("status", VECTOR_STATUS))
    production_use = str(d.get("production_use", PRODUCTION_USE))
    identity = {
        "schema_version": 1, "character_id": master_id, "family_id": "human-character-library-canonical-family",
        "family_version": 1, "status": status, "identity_direction": d["identity"],
        "device_profile": d["device"], "concept_reference_sha256": "76ca14b9669995efe6cf61196dc6df794391de8bba81a63e362b06286e5b31b8",
        "production_use": production_use,
        "palette": {"skin": d["skin"], "skin_light": d["skin_light"], "hair": d["hair"], "primary": d["primary"], "secondary": d["secondary"], "accent": d["accent"], "outline": INK},
        "provenance": {"creator": "MascotRender project", "license": "MIT", "source": "original deterministic semantic SVG authored in this repository from project-owner-approved identity direction"},
    }
    if status in {VECTOR_STATUS, "owner-vector-identity-approved"}:
        identity["vector_parity_approval"] = {
            "date": "2026-07-16" if d.get("wave2") else "2026-07-15",
            "authority": "project-owner",
            "decision": "approved",
            "scope": "owner-identity-cohort-gate" if d.get("wave2") else "canonical-vector-parity",
        }
    else:
        identity["review_gate"] = {
            "decision": "pending-owner-identity-review",
            "production_use": "forbidden-until-all-production-gates",
        }
    if "representation" in d:
        identity["representation"] = d["representation"]
    if "authored_demographics" in d:
        identity["authored_demographics"] = d["authored_demographics"]
    if "hair_intent" in d:
        identity["hair_intent"] = d["hair_intent"]
        identity["head_covering"] = d["head_covering"]
    if "device_review_resolution" in d:
        identity["device_review_resolution"] = d["device_review_resolution"]
    write_json(target / "identity.json", identity)
    identity_sha = sha(target / "identity.json")
    pack = pack_document(master_id, d, layers, lod_layers, identity_sha)
    write_json(target / "pack.json", pack)
    flat_pack = json.loads(json.dumps(pack))
    for layer in flat_pack["layers"]:
        layer["depth"] = 0
    flat_pack["provenance"]["source"] = "Flat 2D projection of the canonical semantic vector source"
    write_json(target / "pack-flat.json", flat_pack)
    source_groups = []
    layer_manifest = []
    lod_manifest = []
    for z, layer_id in enumerate(LAYER_ORDER):
        content = layers[layer_id]
        if not content:
            continue
        layer_path = target / "layers" / f"{z:02d}-{layer_id}.svg"
        write_text(layer_path, svg_document(content))
        visible_in_master = layer_id == "face-friendly" or layer_id in {"arm-left-greeting", "arm-right-greeting"}
        hidden = ' style="display:none"' if (layer_id.startswith("face-") or layer_id.startswith("arm-")) and not visible_in_master else ""
        source_groups.append(f'<g id="{layer_id}" data-semantic-layer="true"{hidden}>{content}</g>')
        layer_manifest.append({"id": layer_id, "path": layer_path.relative_to(target).as_posix(), "sha256": sha(layer_path)})
        if layer_id in lod_layers:
            lod_path = target / "layers-lod100" / f"{z:02d}-{layer_id}.svg"
            write_text(lod_path, svg_document(lod_layers[layer_id]))
            lod_manifest.append({"id": layer_id, "maximum_dimension": 100, "path": lod_path.relative_to(target).as_posix(), "sha256": sha(lod_path)})
    write_text(target / "master.svg", svg_document("\n".join(source_groups)))
    turnaround_records = []
    for view in ("front", "three-quarter", "side", "back"):
        turnaround_path = target / "turnarounds" / f"{view}.svg"
        write_text(turnaround_path, svg_document(turnaround_content(d, layers, view)))
        turnaround_records.append({
            "view": view, "path": turnaround_path.relative_to(target).as_posix(),
            "sha256": sha(turnaround_path), "authored_geometry": False,
            "asset_class": "legacy-synthetic-technical-fixture",
            "production_use": "forbidden",
        })
    write_json(target / "turnaround-manifest.json", {
        "schema_version": 1, "character_id": master_id,
        "views": turnaround_records, "same_world_scale": True,
        "camera_projection": "orthographic-technical-art",
        "review_disposition": "rejected-for-production; production turnarounds are rendered from hierarchy-preserving authored GLB rotations",
    })
    for framing, default_camera in FRAMINGS.items():
        anchor, zoom, ox, oy = d.get("framing_overrides", {}).get(framing, default_camera)
        write_json(target / "stickers" / f"{framing}.json", {
            "schema_version": 1, "sticker_id": f"{master_id.lower()}-{framing}", "pack_id": pack["pack_id"],
            "alt_text": f"{master_id} canonical human master in {framing} framing", "expression": "friendly", "pose": "greeting", "seed": 1,
            "camera": {"framing": framing, "target": anchor, "zoom": zoom, "offset_x": ox, "offset_y": oy},
        })
    write_json(target / "stickers" / "canonical-scale.json", {
        "schema_version": 1, "sticker_id": f"{master_id.lower()}-canonical-scale", "pack_id": pack["pack_id"],
        "alt_text": f"{master_id} at the canonical shared world scale and baseline", "expression": "friendly", "pose": "greeting", "seed": 1,
        "camera": {"framing": "full-body", "target": "ground_contact", "zoom": .82, "offset_x": 0, "offset_y": 194},
    })
    expression_pose = {
        "happy": "agreement", "laughing": "celebration", "surprised": "surprise",
        "thinking": "concern", "confident": "agreement", "sorry": "gratitude",
        "excited": "celebration",
    }
    # Production review must be able to judge facial construction without a
    # simultaneous pose change, and pose construction without a simultaneous
    # expression change.  Keep the combined presentations for sticker use, but
    # author orthogonal evidence inputs as well.
    for expression in EXPRESSIONS:
        write_json(target / "stickers" / "expressions" / f"{expression}.json", {
            "schema_version": 1, "sticker_id": f"{master_id.lower()}-expression-{expression}",
            "pack_id": pack["pack_id"],
            "alt_text": f"{master_id} {expression} facial expression in the neutral rest pose",
            "expression": expression, "pose": "rest", "seed": 1,
            "camera": {"framing": "full-body", "target": "body_center", "zoom": .91, "offset_x": 0, "offset_y": 18},
        })
    for pose in POSES:
        write_json(target / "stickers" / "poses" / f"{pose}.json", {
            "schema_version": 1, "sticker_id": f"{master_id.lower()}-pose-{pose}",
            "pack_id": pack["pack_id"],
            "alt_text": f"{master_id} demonstrating the {pose} pose with a stable friendly expression",
            "expression": "friendly", "pose": pose, "seed": 1,
            "camera": {"framing": "full-body", "target": "body_center", "zoom": .91, "offset_x": 0, "offset_y": 18},
        })
    depth_base = {
        "schema_version": 1, "pack_id": pack["pack_id"], "expression": "friendly",
        "pose": "rest", "seed": 1,
        "camera": {"framing": "full-body", "target": "body_center", "zoom": .91, "offset_x": 0, "offset_y": 18},
    }
    for name, view in (("layered-rest", (0, 0)), ("parallax-left", (-56, -10)), ("parallax-right", (56, -10))):
        sticker = dict(depth_base)
        sticker.update({
            "sticker_id": f"{master_id.lower()}-depth-{name}",
            "alt_text": f"{master_id} layered depth review: {name}",
            "view": {"x": view[0], "y": view[1]},
        })
        write_json(target / "stickers" / "depth" / f"{name}.json", sticker)
    depth_motion = dict(depth_base)
    depth_motion.update({
        "sticker_id": f"{master_id.lower()}-depth-motion",
        "alt_text": f"{master_id} layered depth hop with responsive contact shadow and parallax",
        "view": {"x": 0, "y": -8},
        "animation": {
            "duration_ms": 800, "fps": 8, "loop": "loop",
            "tracks": [
                {"target": "torso", "property": "translate_y", "keyframes": [
                    {"at_ms": 0, "value": 0}, {"at_ms": 400, "value": -16, "easing": "ease_out"}, {"at_ms": 800, "value": 0, "easing": "ease_in_out"}]},
                {"target": "head", "property": "translate_y", "keyframes": [
                    {"at_ms": 0, "value": 0}, {"at_ms": 400, "value": -21, "easing": "ease_out"}, {"at_ms": 800, "value": 0, "easing": "ease_in_out"}]},
                {"target": "shadow", "property": "scale_x", "keyframes": [
                    {"at_ms": 0, "value": 1}, {"at_ms": 400, "value": .66, "easing": "ease_in_out"}, {"at_ms": 800, "value": 1, "easing": "ease_in_out"}]},
                {"target": "$view", "property": "view_x", "keyframes": [
                    {"at_ms": 0, "value": -18}, {"at_ms": 400, "value": 18, "easing": "ease_in_out"}, {"at_ms": 800, "value": -18, "easing": "ease_in_out"}]},
            ],
        },
    })
    write_json(target / "stickers" / "depth" / "animated-depth.json", depth_motion)
    accessibility_entries = []
    for expression, pose in expression_pose.items():
        base_sticker = {
            "schema_version": 1, "sticker_id": f"{master_id.lower()}-{expression}",
            "pack_id": pack["pack_id"], "alt_text": f"{master_id} expressing {expression} in a {pose} pose",
            "expression": expression, "pose": pose, "seed": 1,
            "camera": {"framing": "full-body", "target": "body_center", "zoom": .91, "offset_x": 0, "offset_y": 18},
        }
        write_json(target / "stickers" / "production" / f"{expression}.json", base_sticker)
        reduced = dict(base_sticker)
        reduced["sticker_id"] = f"{master_id.lower()}-{expression}-reduced-motion"
        reduced["alt_text"] = f"{base_sticker['alt_text']}; reduced-motion static presentation"
        write_json(target / "stickers" / "reduced-motion" / f"{expression}.json", reduced)
        accessibility_entries.append({
            "expression": expression, "pose": pose,
            "standard": f"stickers/production/{expression}.json",
            "reduced_motion": f"stickers/reduced-motion/{expression}.json",
            "reduced_motion_behavior": "static-semantic-equivalent",
        })
    write_json(target / "accessibility.json", {
        "schema_version": 1, "character_id": master_id, "default_motion_policy": "standard",
        "prefers_reduced_motion_policy": "static-semantic-equivalent",
        "presentations": accessibility_entries,
    })
    tracks = device_motion_tracks(master_id)
    if tracks:
        write_json(target / "stickers" / "device-motion-check.json", {
            "schema_version": 1, "sticker_id": f"{master_id.lower()}-device-motion-check", "pack_id": pack["pack_id"],
            "alt_text": f"{master_id} semantic assistive-device motion and attachment check", "expression": "friendly", "pose": "neutral", "seed": 1,
            "camera": {"framing": "full-body", "target": "body_center", "zoom": .91, "offset_x": 0, "offset_y": 18},
            "animation": {"duration_ms": 800, "fps": 8, "loop": "loop", "tracks": tracks},
        })
    manifest = {
        "schema_version": 1, "master_id": master_id, "status": status,
        "production_use": production_use, "master_svg": "master.svg", "master_sha256": sha(target / "master.svg"),
        "layer_count": len(layer_manifest), "layers": layer_manifest,
        "lod_layer_count": len(lod_manifest), "lod_layers": lod_manifest,
        "production_expression_count": len(EXPRESSIONS), "production_pose_count": len(POSES),
        "reduced_motion_presentation_count": len(accessibility_entries),
        "turnaround_view_count": len(turnaround_records), "turnarounds": turnaround_records,
        "claimed_backends": ["flat-2d", "layered-2.5d", "filament-glb"],
        "flat_pack": "pack-flat.json", "layered_pack": "pack.json", "glb": f"{master_id}-production.glb",
    }
    write_json(target / "source-manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "art/human-pack-v1/masters")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output.name + ".staging-", dir=output.parent))
    try:
        manifests = [generate_master(staging, master_id, MASTERS[master_id]) for master_id in sorted(MASTERS)]
        write_json(staging / "generation-manifest.json", {
            "schema_version": 1, "family_id": "human-character-library-canonical-family", "family_version": 1,
            "status": VECTOR_STATUS, "production_use": PRODUCTION_USE,
            "concept_reference_sha256": "76ca14b9669995efe6cf61196dc6df794391de8bba81a63e362b06286e5b31b8",
            "master_count": len(manifests), "masters": manifests,
        })
        write_json(staging / "representation-review.json", {
            "schema_version": 1, "family_id": "human-character-library-canonical-family",
            "date": "2026-07-15", "review_role": "project-owner-and-product-identity-reviewer",
            "reviewer": "project-owner", "decision": "approved",
            "disposition": "respectful-and-non-stereotyped-for-human-pack-production",
            "members": sorted(MASTERS),
            "scope": ["age", "body-proportion", "complexion", "hair", "identity", "assistive-device-integration"],
            "public_feedback_policy": "representation defects remain release-blocking regressions and may be corrected after public feedback",
        })
        write_json(staging / "provenance.json", {
            "schema_version": 1, "family_id": "human-character-library-canonical-family",
            "creator": "MascotRender project", "copyright_holder": "MascotRender project owner",
            "license": "MIT", "license_file": "LICENSE",
            "source_class": "original-deterministic-repository-authored-svg-and-glb",
            "reference_use": "project-owner-approved identity direction; production geometry is independently generated",
            "distribution_authority": {"date": "2026-07-15", "authority": "project-owner", "decision": "approved-for-public-release"},
        })
        # The Blender sources and authored production GLBs are independent DCC
        # assets.  Regenerating deterministic SVGs must never delete them.
        if output.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {output}")
            for master_id in MASTERS:
                previous = output / master_id
                current = staging / master_id
                for suffix in (".blend", "-production.glb"):
                    asset = previous / f"{master_id}{suffix}"
                    if asset.is_file():
                        shutil.copy2(asset, current / asset.name)
            shutil.rmtree(output)
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"generated {len(MASTERS)} canonical layered SVG production-review candidates in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
