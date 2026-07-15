#!/usr/bin/env python3
"""Generate deterministic full-body human pilot packs from identity contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from human_contracts import sha256, validate_contract_set


GENERATOR_VERSION = 1
MASK64 = (1 << 64) - 1


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def svg(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">\n' + body.rstrip() + "\n</svg>\n"
    )


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def identity_seed(identity: dict[str, Any], seed: int) -> int:
    digest = hashlib.sha256(identity["mascot_id"].encode("utf-8")).digest()
    return splitmix64(seed + int.from_bytes(digest[:8], "big"))


def geometry(identity: dict[str, Any]) -> dict[str, float]:
    appearance = identity["appearance"]
    body = appearance["body"]
    height_shift = {"tall": -9.0, "medium": 0.0, "short": 9.0}[body["height_class"]]
    head_width = 150.0 * float(appearance["face"]["width_ratio"])
    torso_width = 102.0 * float(body["shoulder_ratio"])
    hip_width = 86.0 * float(body["hip_ratio"])
    return {
        "head_x": 256.0 - head_width * 0.5,
        "head_y": 105.0 + height_shift,
        "head_width": head_width,
        "head_height": 150.0,
        "face_y": 180.0 + height_shift,
        "neck_y": 251.0 + height_shift,
        "torso_x": 256.0 - torso_width * 0.5,
        "torso_y": 252.0 + height_shift,
        "torso_width": torso_width,
        "torso_height": 112.0,
        "hip_width": hip_width,
        "hip_y": 354.0 + height_shift,
        "foot_y": 432.0 + height_shift,
        "shoulder_left": 256.0 - torso_width * 0.47,
        "shoulder_right": 256.0 + torso_width * 0.47,
    }


def shadow_layer(identity: dict[str, Any], g: dict[str, float]) -> str:
    dark = identity["appearance"]["skin"]["shadow_color"]
    return svg(
        f'<ellipse cx="256" cy="{g["foot_y"] + 13:.1f}" rx="86" ry="15" '
        f'fill="{dark}" fill-opacity="0.25"/>'
    )


def legs_layers(identity: dict[str, Any], g: dict[str, float]) -> tuple[str, str]:
    presentation = identity["presentation"]
    pants = presentation["secondary_color"]
    accent = presentation["accent_color"]
    hip_half = g["hip_width"] * 0.5
    left_x = 256.0 - hip_half * 0.48
    right_x = 256.0 + hip_half * 0.48

    def leg(x: float) -> str:
        return svg(
            f'<path d="M{x - 21:.1f} {g["hip_y"]:.1f} L{x + 16:.1f} {g["hip_y"]:.1f} '
            f'L{x + 13:.1f} {g["foot_y"] - 12:.1f} L{x - 18:.1f} {g["foot_y"] - 12:.1f} Z" fill="{pants}"/>\n'
            f'<rect x="{x - 24:.1f}" y="{g["foot_y"] - 18:.1f}" width="48" height="23" rx="11" fill="{accent}"/>'
        )

    return leg(left_x), leg(right_x)


def torso_layer(identity: dict[str, Any], g: dict[str, float]) -> str:
    skin = identity["appearance"]["skin"]
    presentation = identity["presentation"]
    body = identity["appearance"]["body"]
    radius = 30 if body["build"] in {"soft", "stocky"} else 24
    return svg(
        f'<rect x="240" y="{g["neck_y"] - 14:.1f}" width="32" height="34" rx="13" fill="{skin["base_color"]}"/>\n'
        f'<rect x="{g["torso_x"]:.1f}" y="{g["torso_y"]:.1f}" width="{g["torso_width"]:.1f}" '
        f'height="{g["torso_height"]:.1f}" rx="{radius}" fill="{presentation["primary_color"]}"/>\n'
        f'<path d="M{g["torso_x"] + 12:.1f} {g["torso_y"] + 23:.1f} '
        f'Q256 {g["torso_y"] + 48:.1f} {g["torso_x"] + g["torso_width"] - 12:.1f} {g["torso_y"] + 23:.1f}" '
        f'fill="none" stroke="{presentation["accent_color"]}" stroke-width="9" stroke-linecap="round"/>\n'
        f'<rect x="{256 - g["hip_width"] * 0.5:.1f}" y="{g["hip_y"] - 13:.1f}" '
        f'width="{g["hip_width"]:.1f}" height="25" rx="12" fill="{presentation["secondary_color"]}"/>'
    )


def head_layer(identity: dict[str, Any], g: dict[str, float]) -> str:
    skin = identity["appearance"]["skin"]
    x = g["head_x"]
    y = g["head_y"]
    width = g["head_width"]
    return svg(
        f'<ellipse cx="{x - 1:.1f}" cy="{y + 80:.1f}" rx="13" ry="22" fill="{skin["shadow_color"]}"/>\n'
        f'<ellipse cx="{x + width + 1:.1f}" cy="{y + 80:.1f}" rx="13" ry="22" fill="{skin["shadow_color"]}"/>\n'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{g["head_height"]:.1f}" '
        f'rx="62" fill="{skin["base_color"]}"/>\n'
        f'<path d="M{x + 29:.1f} {y + 24:.1f} Q{x + width * 0.5:.1f} {y + 4:.1f} '
        f'{x + width - 29:.1f} {y + 24:.1f}" fill="none" stroke="{skin["highlight_color"]}" '
        'stroke-width="8" stroke-linecap="round" opacity="0.72"/>'
    )


def hair_layers(identity: dict[str, Any], g: dict[str, float]) -> tuple[str, str]:
    hair = identity["appearance"]["hair"]
    base = hair["base_color"]
    highlight = hair["highlight_color"]
    style = hair["style"]
    x = g["head_x"]
    y = g["head_y"]
    width = g["head_width"]
    cx = 256.0
    back: list[str] = []
    front: list[str] = []
    if style == "afro":
        back.append(f'<ellipse cx="{cx:.1f}" cy="{y + 60:.1f}" rx="{width * 0.62:.1f}" ry="91" fill="{base}"/>')
        for dx, dy, radius in ((-62, 4, 30), (-28, -11, 34), (10, -14, 35), (48, 0, 31)):
            front.append(f'<circle cx="{cx + dx}" cy="{y + dy}" r="{radius}" fill="{base}"/>')
    elif style in {"locs", "braids", "long-layers"}:
        back.append(f'<rect x="{x - 13:.1f}" y="{y + 18:.1f}" width="{width + 26:.1f}" height="185" rx="52" fill="{base}"/>')
        if style in {"locs", "braids"}:
            for dx in (-58, -35, 35, 58):
                front.append(f'<path d="M{cx + dx} {y + 34:.1f} Q{cx + dx * 1.1:.1f} {y + 112:.1f} {cx + dx * 1.08:.1f} {y + 190:.1f}" fill="none" stroke="{highlight}" stroke-width="{9 if style == "braids" else 13}" stroke-linecap="round"/>')
        front.append(f'<path d="M{x + 12:.1f} {y + 42:.1f} Q{cx:.1f} {y - 20:.1f} {x + width - 12:.1f} {y + 42:.1f}" fill="{base}"/>')
    elif style == "covered-wrap":
        back.append(f'<rect x="{x - 10:.1f}" y="{y - 5:.1f}" width="{width + 20:.1f}" height="174" rx="66" fill="{base}"/>')
        front.extend((
            f'<path d="M{x + 5:.1f} {y + 51:.1f} Q{cx:.1f} {y - 28:.1f} {x + width - 5:.1f} {y + 51:.1f} L{x + width - 18:.1f} {y + 80:.1f} Q{cx:.1f} {y + 26:.1f} {x + 18:.1f} {y + 80:.1f} Z" fill="{highlight}"/>',
            f'<circle cx="{cx:.1f}" cy="{y - 5:.1f}" r="18" fill="{base}"/>',
        ))
    elif style in {"short-curls", "short-twists"}:
        for row, (dy, count, radius) in enumerate(((0, 7, 18), (18, 8, 17), (34, 7, 16))):
            span = width * (0.84 - row * 0.06)
            for index in range(count):
                px = cx - span * 0.5 + span * index / max(1, count - 1)
                front.append(f'<circle cx="{px:.1f}" cy="{y + dy:.1f}" r="{radius}" fill="{base if index % 2 == 0 else highlight}"/>')
    elif style == "bob":
        back.append(f'<rect x="{x - 9:.1f}" y="{y + 4:.1f}" width="{width + 18:.1f}" height="142" rx="55" fill="{base}"/>')
        front.append(f'<path d="M{x + 5:.1f} {y + 50:.1f} Q{cx:.1f} {y - 18:.1f} {x + width - 5:.1f} {y + 50:.1f} Q{cx + 28:.1f} {y + 35:.1f} {cx:.1f} {y + 75:.1f} Q{cx - 28:.1f} {y + 34:.1f} {x + 5:.1f} {y + 50:.1f} Z" fill="{base}"/>')
    else:
        front.append(f'<path d="M{x + 3:.1f} {y + 53:.1f} Q{cx:.1f} {y - 25:.1f} {x + width - 3:.1f} {y + 53:.1f} Q{cx + 36:.1f} {y + 24:.1f} {cx:.1f} {y + 67:.1f} Q{cx - 34:.1f} {y + 27:.1f} {x + 3:.1f} {y + 53:.1f} Z" fill="{base}"/>')
        front.append(f'<path d="M{x + 30:.1f} {y + 26:.1f} Q{cx:.1f} {y - 4:.1f} {x + width - 30:.1f} {y + 25:.1f}" fill="none" stroke="{highlight}" stroke-width="8" stroke-linecap="round" opacity="0.72"/>')
    return svg("\n".join(back) or "<!-- intentionally empty hair-back layer -->"), svg("\n".join(front))


def face_layer(identity: dict[str, Any], g: dict[str, float], expression: str) -> str:
    appearance = identity["appearance"]
    face = appearance["face"]
    dark = appearance["hair"]["base_color"]
    accent = identity["presentation"]["accent_color"]
    head_width = g["head_width"]
    spacing = head_width * float(face["eye_spacing_ratio"])
    eye_y = g["head_y"] + 72
    left = 256.0 - spacing * 0.5
    right = 256.0 + spacing * 0.5
    shape = face["eye_shape"]
    if expression in {"friendly", "joyful", "grateful", "loving"}:
        eyes = (
            f'<path d="M{left - 14:.1f} {eye_y:.1f} Q{left:.1f} {eye_y - 14:.1f} {left + 14:.1f} {eye_y:.1f}" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round"/>\n'
            f'<path d="M{right - 14:.1f} {eye_y:.1f} Q{right:.1f} {eye_y - 14:.1f} {right + 14:.1f} {eye_y:.1f}" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round"/>'
        )
    elif expression in {"shocked", "dramatic", "pleading"}:
        ry = 18 if expression != "pleading" else 15
        eyes = (
            f'<ellipse cx="{left:.1f}" cy="{eye_y:.1f}" rx="13" ry="{ry}" fill="#FFF8EE"/><circle cx="{left:.1f}" cy="{eye_y + 3:.1f}" r="7" fill="{dark}"/>\n'
            f'<ellipse cx="{right:.1f}" cy="{eye_y:.1f}" rx="13" ry="{ry}" fill="#FFF8EE"/><circle cx="{right:.1f}" cy="{eye_y + 3:.1f}" r="7" fill="{dark}"/>'
        )
    elif expression == "regretful":
        eyes = (
            f'<path d="M{left - 14:.1f} {eye_y - 5:.1f} Q{left:.1f} {eye_y + 8:.1f} {left + 14:.1f} {eye_y - 5:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>\n'
            f'<path d="M{right - 14:.1f} {eye_y - 5:.1f} Q{right:.1f} {eye_y + 8:.1f} {right + 14:.1f} {eye_y - 5:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
        )
    elif shape in {"monolid", "hooded"}:
        eyes = (
            f'<path d="M{left - 15:.1f} {eye_y:.1f} Q{left:.1f} {eye_y - 8:.1f} {left + 15:.1f} {eye_y:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>\n'
            f'<path d="M{right - 15:.1f} {eye_y:.1f} Q{right:.1f} {eye_y - 8:.1f} {right + 15:.1f} {eye_y:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
        )
    else:
        eyes = (
            f'<ellipse cx="{left:.1f}" cy="{eye_y:.1f}" rx="10" ry="14" fill="{dark}"/>\n'
            f'<ellipse cx="{right:.1f}" cy="{eye_y:.1f}" rx="10" ry="14" fill="{dark}"/>'
        )

    nose_width = {"broad": 14, "rounded": 11, "medium": 9, "low-bridge": 7, "narrow": 6, "strong-bridge": 8}[face["nose_profile"]]
    nose = f'<path d="M{256 - nose_width:.1f} {eye_y + 20:.1f} Q256 {eye_y + 34:.1f} {256 + nose_width:.1f} {eye_y + 20:.1f}" fill="none" stroke="{accent}" stroke-width="5" stroke-linecap="round"/>'
    mouth_y = eye_y + 52
    lip_width = {"full": 30, "wide": 34, "medium": 25, "soft": 23, "balanced": 26}[face["lip_profile"]]
    if expression in {"friendly", "joyful", "grateful", "loving", "confident"}:
        mouth = f'<path d="M{256 - lip_width:.1f} {mouth_y - 4:.1f} Q256 {mouth_y + 22:.1f} {256 + lip_width:.1f} {mouth_y - 4:.1f}" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round"/>'
    elif expression in {"shocked", "dramatic"}:
        mouth = f'<ellipse cx="256" cy="{mouth_y + 5:.1f}" rx="15" ry="19" fill="{dark}"/>'
    elif expression in {"regretful", "pleading"}:
        mouth = f'<path d="M{256 - lip_width * 0.65:.1f} {mouth_y + 8:.1f} Q256 {mouth_y - 5:.1f} {256 + lip_width * 0.65:.1f} {mouth_y + 8:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
    elif expression == "firm":
        mouth = f'<path d="M{256 - lip_width * 0.65:.1f} {mouth_y + 2:.1f} L{256 + lip_width * 0.65:.1f} {mouth_y + 2:.1f}" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
    else:
        mouth = f'<path d="M{256 - lip_width * 0.6:.1f} {mouth_y:.1f} Q256 {mouth_y + 8:.1f} {256 + lip_width * 0.6:.1f} {mouth_y:.1f}" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'

    accessories = identity["presentation"]["accessories"]
    glasses = ""
    if "glasses-round" in accessories:
        glasses = (
            f'<circle cx="{left:.1f}" cy="{eye_y:.1f}" r="22" fill="none" stroke="{dark}" stroke-width="4"/>\n'
            f'<circle cx="{right:.1f}" cy="{eye_y:.1f}" r="22" fill="none" stroke="{dark}" stroke-width="4"/>\n'
            f'<path d="M{left + 22:.1f} {eye_y:.1f} L{right - 22:.1f} {eye_y:.1f}" stroke="{dark}" stroke-width="4"/>'
        )
    return svg("\n".join((eyes, nose, mouth, glasses)))


POSE_POINTS: dict[str, dict[str, tuple[tuple[float, float], tuple[float, float]]]] = {
    "neutral": {"left": ((198, 326), (205, 370)), "right": ((314, 326), (307, 370))},
    "wave": {"left": ((198, 328), (205, 370)), "right": ((334, 246), (335, 184))},
    "laugh": {"left": ((177, 302), (151, 272)), "right": ((335, 302), (361, 272))},
    "agree": {"left": ((198, 327), (222, 348)), "right": ((314, 327), (290, 348))},
    "disagree": {"left": ((202, 310), (282, 342)), "right": ((310, 310), (230, 342))},
    "shock": {"left": ((178, 255), (167, 198)), "right": ((334, 255), (345, 198))},
    "gratitude": {"left": ((208, 310), (249, 326)), "right": ((304, 310), (263, 326))},
    "apology": {"left": ((205, 316), (246, 345)), "right": ((307, 316), (266, 345))},
    "love": {"left": ((204, 305), (249, 315)), "right": ((308, 305), (263, 315))},
    "dramatic": {"left": ((172, 265), (145, 220)), "right": ((340, 265), (367, 220))},
    "plead": {"left": ((209, 317), (250, 336)), "right": ((303, 317), (262, 336))},
    "farewell": {"left": ((198, 328), (205, 370)), "right": ((334, 246), (335, 184))},
}


def arm_layer(identity: dict[str, Any], g: dict[str, float], pose: str, side: str) -> str:
    skin = identity["appearance"]["skin"]
    clothing = identity["presentation"]["primary_color"]
    shoulder = (g["shoulder_left"], g["torso_y"] + 30) if side == "left" else (g["shoulder_right"], g["torso_y"] + 30)
    elbow, hand = POSE_POINTS[pose][side]
    return svg(
        f'<path d="M{shoulder[0]:.1f} {shoulder[1]:.1f} L{elbow[0]:.1f} {elbow[1]:.1f}" fill="none" stroke="{clothing}" stroke-width="31" stroke-linecap="round"/>\n'
        f'<path d="M{elbow[0]:.1f} {elbow[1]:.1f} L{hand[0]:.1f} {hand[1]:.1f}" fill="none" stroke="{skin["base_color"]}" stroke-width="21" stroke-linecap="round"/>\n'
        f'<circle cx="{hand[0]:.1f}" cy="{hand[1]:.1f}" r="12" fill="{skin["highlight_color"]}"/>'
    )


EXPRESSIONS = ("friendly", "joyful", "confident", "firm", "neutral", "shocked", "grateful", "regretful", "loving", "dramatic", "pleading")


def pack_document(identity: dict[str, Any], rig: dict[str, Any], g: dict[str, float]) -> dict[str, Any]:
    mascot_id = identity["mascot_id"]
    layers: list[dict[str, Any]] = [
        {"id": "shadow", "source": "layers/00-shadow.svg", "z": 0, "depth": -0.4},
        {"id": "hair-back", "source": "layers/05-hair-back.svg", "z": 5, "parent": "head", "pivot": "head", "depth": -0.1},
        {"id": "leg-left", "source": "layers/10-leg-left.svg", "z": 10, "parent": "torso", "pivot": "hip_left", "depth": 0.0},
        {"id": "leg-right", "source": "layers/11-leg-right.svg", "z": 11, "parent": "torso", "pivot": "hip_right", "depth": 0.0},
        {"id": "torso", "source": "layers/20-torso.svg", "z": 20, "pivot": "hips", "depth": 0.05, "collision_bounds": {"x": max(0, int(g["torso_x"] - 18)), "y": int(g["torso_y"] - 18), "width": int(g["torso_width"] + 36), "height": int(g["foot_y"] - g["torso_y"] + 32)}},
        {"id": "head", "source": "layers/30-head.svg", "z": 30, "parent": "torso", "pivot": "neck", "depth": 0.18, "collision_bounds": {"x": max(0, int(g["head_x"] - 16)), "y": max(0, int(g["head_y"] - 26)), "width": int(g["head_width"] + 32), "height": int(g["head_height"] + 42)}},
        {"id": "hair-front", "source": "layers/31-hair-front.svg", "z": 31, "parent": "head", "pivot": "head", "depth": 0.24},
    ]
    expressions: dict[str, list[str]] = {}
    next_z = 40
    for expression in EXPRESSIONS:
        layer_id = f"face-{expression}"
        layers.append({"id": layer_id, "source": f"layers/{next_z:02d}-{layer_id}.svg", "z": next_z, "parent": "head", "pivot": "head", "depth": 0.28})
        expressions[expression] = [layer_id]
        next_z += 1

    poses: dict[str, list[str]] = {}
    pose_bindings: dict[str, dict[str, str]] = {}
    next_z = 60
    for pose in POSE_POINTS:
        left = f"arm-left-{pose}"
        right = f"arm-right-{pose}"
        layers.extend((
            {"id": left, "source": f"layers/{next_z:02d}-{left}.svg", "z": next_z, "parent": "torso", "pivot": "shoulder_left", "depth": 0.12},
            {"id": right, "source": f"layers/{next_z + 1:02d}-{right}.svg", "z": next_z + 1, "parent": "torso", "pivot": "shoulder_right", "depth": 0.13},
        ))
        poses[pose] = [left, right]
        pose_bindings[pose] = {
            "root": "torso",
            "head": "head",
            "face": "head",
            "gesture.primary": right,
            "gesture.secondary": left,
            "ground.contact": "shadow",
            "gaze.target": "head",
        }
        next_z += 2

    return {
        "schema_version": 1,
        "pack_id": mascot_id,
        "character_identity": {
            "character_id": mascot_id,
            "contract_version": 1,
            "contract_sha256": hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "required_features": ["human", "full_body", "screen_space_caption", "semantic_camera", "normalized_humanoid_rig"],
        },
        "rig": {"contract_id": rig["rig_id"], "contract_version": 1, "pose_bindings": pose_bindings},
        "canvas": {"width": 512, "height": 512},
        "layers": layers,
        "base_layers": ["shadow", "hair-back", "leg-left", "leg-right", "torso", "head", "hair-front"],
        "expressions": expressions,
        "poses": poses,
        "provenance": {"creator": "MascotRender human pilot generator", "license": "CC0-1.0 generated sample artwork; font separately SIL OFL 1.1", "source": f"generate_human_pilots.py v{GENERATOR_VERSION}; identity={mascot_id}"},
        "anchors": {
            "face_center": {"x": 256, "y": round(g["face_y"], 2)},
            "bust_center": {"x": 256, "y": round(g["torso_y"] - 20, 2)},
            "body_center": {"x": 256, "y": round((g["head_y"] + g["foot_y"]) * 0.5, 2)},
            "ground_contact": {"x": 256, "y": round(g["foot_y"], 2)},
            "caption_top": {"x": 256, "y": 48},
            "gaze_target": {"x": 256, "y": round(g["face_y"] - 10, 2)},
        },
        "pivots": {
            "root": {"x": 256, "y": round(g["foot_y"], 2)},
            "hips": {"x": 256, "y": round(g["hip_y"], 2)},
            "torso": {"x": 256, "y": round(g["torso_y"] + 50, 2)},
            "neck": {"x": 256, "y": round(g["neck_y"], 2)},
            "head": {"x": 256, "y": round(g["face_y"], 2)},
            "shoulder_left": {"x": round(g["shoulder_left"], 2), "y": round(g["torso_y"] + 30, 2)},
            "shoulder_right": {"x": round(g["shoulder_right"], 2), "y": round(g["torso_y"] + 30, 2)},
            "elbow_left": {"x": 198, "y": 326}, "elbow_right": {"x": 314, "y": 326},
            "hand_left": {"x": 205, "y": 370}, "hand_right": {"x": 307, "y": 370},
            "hip_left": {"x": round(256 - g["hip_width"] * 0.24, 2), "y": round(g["hip_y"], 2)},
            "hip_right": {"x": round(256 + g["hip_width"] * 0.24, 2), "y": round(g["hip_y"], 2)},
            "foot_left": {"x": round(256 - g["hip_width"] * 0.24, 2), "y": round(g["foot_y"], 2)},
            "foot_right": {"x": round(256 + g["hip_width"] * 0.24, 2), "y": round(g["foot_y"], 2)},
        },
        "text_slots": {"top": {"x": 48, "y": 10, "width": 416, "height": 82}},
        "avoid_regions": [],
        "text_clearance": 10,
        "fonts": [{"id": "display", "source": "fonts/changa-one/ChangaOne-Regular.ttf", "license": "fonts/changa-one/OFL.txt"}],
        "text_styles": {"caption": {"font": "display", "safe_area": {"x": 48, "y": 10, "width": 416, "height": 82}, "min_font_size": 22, "max_font_size": 52, "max_lines": 2, "fill": {"r": 255, "g": 255, "b": 255}, "outline": {"width": 5, "color": {"r": 24, "g": 30, "b": 48}}}},
    }


def compiled_animation(recipe: dict[str, Any], bindings: dict[str, str]) -> dict[str, Any]:
    animation: dict[str, Any] = {
        "duration_ms": recipe["duration_ms"],
        "fps": recipe["fps"],
        "loop": recipe["loop"],
        "tracks": [
            {**track, "target": bindings[track["target"]]}
            for track in recipe["tracks"]
        ],
    }
    if recipe.get("text_pop"):
        animation["overlays"] = ["text_pop"]
    return animation


def sticker_document(identity: dict[str, Any], phrase: dict[str, Any], recipe: dict[str, Any], rig: dict[str, Any], pack: dict[str, Any], seed: int, index: int) -> dict[str, Any]:
    framing = rig["camera_framings"][recipe["camera_framing"]]
    bindings = pack["rig"]["pose_bindings"][recipe["pose"]]
    phrase_slug = phrase["phrase_id"].replace(".", "-")
    return {
        "schema_version": 1,
        "sticker_id": f'{identity["mascot_id"]}-{phrase_slug}',
        "pack_id": identity["mascot_id"],
        "phrase_id": phrase["phrase_id"],
        "recipe_id": recipe["recipe_id"],
        "alt_text": f'{identity["display_name"]} saying {phrase["caption"]}',
        "expression": recipe["expression"],
        "pose": recipe["pose"],
        "seed": splitmix64(seed + index),
        "camera": {"framing": recipe["camera_framing"], **framing},
        "text": {"content": phrase["caption"], "style": "caption", "placement": "auto", "preferred_slots": ["top"]},
        "animation": compiled_animation(recipe, bindings),
    }


def copy_font(source: Path, destination: Path) -> str:
    required = ("ChangaOne-Regular.ttf", "OFL.txt", "METADATA.pb", "UPSTREAM.md")
    target = destination / "fonts" / "changa-one"
    target.mkdir(parents=True, exist_ok=True)
    for name in required:
        if not (source / name).is_file():
            raise FileNotFoundError(f"required approved font asset is missing: {source / name}")
        shutil.copy2(source / name, target / name)
    return hashlib.sha256((target / required[0]).read_bytes()).hexdigest()


def generate_pack(root: Path, identity: dict[str, Any], rig: dict[str, Any], recipes: dict[str, dict[str, Any]], phrases: list[dict[str, Any]], seed: int, font_source: Path) -> dict[str, Any]:
    pack_root = root / identity["mascot_id"]
    layers = pack_root / "layers"
    g = geometry(identity)
    write_text(layers / "00-shadow.svg", shadow_layer(identity, g))
    left_leg, right_leg = legs_layers(identity, g)
    write_text(layers / "10-leg-left.svg", left_leg)
    write_text(layers / "11-leg-right.svg", right_leg)
    write_text(layers / "20-torso.svg", torso_layer(identity, g))
    write_text(layers / "30-head.svg", head_layer(identity, g))
    hair_back, hair_front = hair_layers(identity, g)
    write_text(layers / "05-hair-back.svg", hair_back)
    write_text(layers / "31-hair-front.svg", hair_front)
    next_index = 40
    for expression in EXPRESSIONS:
        write_text(layers / f"{next_index:02d}-face-{expression}.svg", face_layer(identity, g, expression))
        next_index += 1
    next_index = 60
    for pose in POSE_POINTS:
        write_text(layers / f"{next_index:02d}-arm-left-{pose}.svg", arm_layer(identity, g, pose, "left"))
        write_text(layers / f"{next_index + 1:02d}-arm-right-{pose}.svg", arm_layer(identity, g, pose, "right"))
        next_index += 2

    font_hash = copy_font(font_source, pack_root)
    write_json(pack_root / "identity.json", identity)
    write_json(pack_root / "rig.json", rig)
    pack = pack_document(identity, rig, g)
    write_json(pack_root / "pack.json", pack)
    derived_seed = identity_seed(identity, seed)
    for index, phrase in enumerate(phrases):
        recipe = recipes[phrase["recipe_id"]]
        sticker = sticker_document(identity, phrase, recipe, rig, pack, derived_seed, index)
        write_json(pack_root / "stickers" / f'{phrase["phrase_id"].replace(".", "-")}.json', sticker)
    return {
        "pack_id": identity["mascot_id"],
        "asset_class": "technical-fixture",
        "production_use": "forbidden",
        "display_name": identity["display_name"],
        "pack": f'{identity["mascot_id"]}/pack.json',
        "identity": f'{identity["mascot_id"]}/identity.json',
        "sticker_count": len(phrases),
        "animated_sticker_count": len(phrases),
        "skin_tone_scale": identity["appearance"]["skin"]["tone_scale"],
        "hair_texture": identity["appearance"]["hair"]["texture"],
        "body_build": identity["appearance"]["body"]["build"],
        "font_sha256": font_hash,
    }


def replace_directory(staging: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        raise FileExistsError(f"output already exists (use --force): {destination}")
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


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identities", type=Path, default=root / "examples/human-pilots/identities.json")
    parser.add_argument("--rig", type=Path, default=root / "contracts/humanoid-full-body-v1.json")
    parser.add_argument("--recipes", type=Path, default=root / "content/motion-recipes-core-v1.json")
    parser.add_argument("--lexicon", type=Path, default=root / "content/phrase-lexicon-core-v1.json")
    parser.add_argument("--font-source", type=Path, default=root / "examples/cat/fonts/changa-one")
    parser.add_argument("--output", type=Path, default=root / "generated/human-pilots")
    parser.add_argument("--count", type=int, default=12, help="Number of curated identities to generate (1-12)")
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identities, rig, recipes, phrases = validate_contract_set(
        args.identities.resolve(), args.rig.resolve(), args.recipes.resolve(), args.lexicon.resolve()
    )
    if args.count < 1 or args.count > len(identities):
        raise ValueError(f"--count must be between 1 and {len(identities)}")
    if args.seed < 0 or args.seed > MASK64:
        raise ValueError("--seed must be an unsigned 64-bit integer")
    selected = identities[:args.count]
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        packs = [generate_pack(staging, identity, rig, recipes, phrases, args.seed, args.font_source.resolve()) for identity in selected]
        write_json(staging / "phrase-lexicon.json", {"schema_version": 1, "lexicon_id": "chat-core-v1", "phrases": phrases})
        write_json(staging / "motion-recipes.json", {"schema_version": 1, "library_id": "human-core-v1", "recipes": list(recipes.values())})
        write_json(staging / "generation-manifest.json", {
            "schema_version": 1,
            "asset_class": "technical-fixture",
            "production_use": "forbidden",
            "generator_version": GENERATOR_VERSION,
            "seed": args.seed,
            "rig_id": rig["rig_id"],
            "pack_count": len(packs),
            "phrase_count": len(phrases),
            "sticker_count": len(packs) * len(phrases),
            "animated_sticker_count": len(packs) * len(phrases),
            "source_sha256": {"identities": sha256(args.identities.resolve()), "rig": sha256(args.rig.resolve()), "recipes": sha256(args.recipes.resolve()), "lexicon": sha256(args.lexicon.resolve())},
            "packs": packs,
        })
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    print(f"generated {len(selected)} full-body human packs and {len(selected) * len(phrases)} stickers in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
