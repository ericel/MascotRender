#!/usr/bin/env python3
"""Author and render the original Micro Reactions vector review cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
GENERATOR_VERSION = 2
OUTLINE = "#20324B"
WHITE = "#FFFDF8"
TEAR = "#60C9F8"
BLUSH = "#FF8FA8"


@dataclass(frozen=True)
class Creature:
    identity_id: str
    name: str
    archetype: str
    primary: str
    secondary: str
    light: str
    accent: str
    signature: str


@dataclass(frozen=True)
class Reaction:
    reaction_id: str
    label: str
    motion: str
    duration_ms: int


CREATURES = (
    Creature(
        "micro-sprig-001",
        "Sprig",
        "leaf-eared forest sprite",
        "#75D77B",
        "#329B62",
        "#DFF7C8",
        "#FFD65A",
        "leaf",
    ),
    Creature(
        "micro-cinder-002",
        "Cinder",
        "ember sprite with a flame crown",
        "#FF9D52",
        "#ED5C38",
        "#FFE2A8",
        "#FFD45C",
        "ember",
    ),
    Creature(
        "micro-ripple-003",
        "Ripple",
        "water sprite with external gills",
        "#69CFE4",
        "#318EBC",
        "#DDF8FF",
        "#74E1CB",
        "drop",
    ),
    Creature(
        "micro-orbit-004",
        "Orbit",
        "ringed space creature",
        "#A98BFF",
        "#6553C7",
        "#F0EAFF",
        "#FFD25F",
        "star",
    ),
    Creature(
        "micro-crumb-005",
        "Crumb",
        "round snack-loving burrow creature",
        "#E6B777",
        "#A96F48",
        "#FFF0D4",
        "#F58AA8",
        "crumb",
    ),
    Creature(
        "micro-mallow-006",
        "Mallow",
        "scalloped cloud creature",
        "#F5B8D2",
        "#C879A8",
        "#FFF2F8",
        "#8EDBF3",
        "puff",
    ),
)


REACTIONS = (
    Reaction("joy", "JOY", "pulse", 800),
    Reaction("laugh", "LAUGH", "laugh", 800),
    Reaction("love", "LOVE", "pulse", 900),
    Reaction("surprise", "SURPRISE", "pop", 800),
    Reaction("cry", "CRY", "sob", 900),
    Reaction("anger", "ANGER", "shake", 700),
    Reaction("suspicion", "SUSPICION", "lean", 1000),
    Reaction("exhausted", "EXHAUSTED", "breathe", 1200),
    Reaction("panic", "PANIC", "tremble", 700),
    Reaction("proud", "PROUD", "rise", 1000),
)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def svg(content: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">\n'
        f"{content.rstrip()}\n"
        "</svg>\n"
    )


def heart(cx: int, cy: int, scale: float, fill: str) -> str:
    x = cx
    y = cy
    s = scale
    return (
        f'<path d="M{x} {y + 18*s:.1f} '
        f'C{x - 42*s:.1f} {y - 8*s:.1f} {x - 34*s:.1f} {y - 40*s:.1f} {x} {y - 22*s:.1f} '
        f'C{x + 34*s:.1f} {y - 40*s:.1f} {x + 42*s:.1f} {y - 8*s:.1f} {x} {y + 18*s:.1f} Z" '
        f'fill="{fill}" stroke="{OUTLINE}" stroke-width="{max(4, int(7*s))}" '
        'stroke-linejoin="round"/>'
    )


def sparkle(cx: int, cy: int, radius: int, fill: str) -> str:
    inner = max(4, radius // 4)
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
        f'fill="{fill}" stroke="{OUTLINE}" stroke-width="5" stroke-linejoin="round"/>'
    )


def shadow_svg() -> str:
    return svg(
        f'<ellipse cx="256" cy="420" rx="118" ry="21" fill="{OUTLINE}" fill-opacity="0.18"/>'
    )


def body_svg(creature: Creature) -> str:
    stroke = f'stroke="{OUTLINE}" stroke-width="12" stroke-linejoin="round" stroke-linecap="round"'
    common_highlight = (
        f'<ellipse cx="216" cy="178" rx="54" ry="36" fill="{creature.light}" fill-opacity="0.30"/>'
    )
    if creature.identity_id == "micro-sprig-001":
        body = f"""
<path d="M170 155 C112 124 100 74 126 54 C177 56 204 86 202 139 Z" fill="{creature.secondary}" {stroke}/>
<path d="M342 155 C400 124 412 74 386 54 C335 56 308 86 310 139 Z" fill="{creature.secondary}" {stroke}/>
<path d="M256 112 C228 77 238 45 270 35 C292 70 282 99 256 112 Z" fill="{creature.accent}" {stroke}/>
<rect x="105" y="124" width="302" height="286" rx="137" fill="{creature.primary}" {stroke}/>
<path d="M126 326 Q256 382 386 326 Q364 407 256 414 Q148 407 126 326 Z" fill="{creature.secondary}" fill-opacity="0.55"/>
{common_highlight}
"""
    elif creature.identity_id == "micro-cinder-002":
        body = f"""
<path d="M256 44 C303 78 327 112 318 151 C354 128 383 151 381 191 C415 216 420 274 394 315 C374 382 327 415 256 415 C169 415 111 366 111 286 C111 235 132 197 169 172 C157 124 193 89 218 130 C220 90 232 62 256 44 Z" fill="{creature.primary}" {stroke}/>
<path d="M256 44 C289 79 288 115 266 146 C301 137 326 154 328 185 C294 169 266 172 244 195 C214 168 184 168 157 185 C159 153 180 136 211 145 C205 105 221 70 256 44 Z" fill="{creature.secondary}"/>
<path d="M136 315 Q256 392 376 315 Q351 415 256 415 Q161 415 136 315 Z" fill="{creature.secondary}" fill-opacity="0.48"/>
{common_highlight}
"""
    elif creature.identity_id == "micro-ripple-003":
        body = f"""
<g fill="{creature.secondary}" {stroke}>
  <ellipse cx="104" cy="196" rx="34" ry="52"/><ellipse cx="87" cy="260" rx="34" ry="52"/><ellipse cx="105" cy="324" rx="34" ry="52"/>
  <ellipse cx="408" cy="196" rx="34" ry="52"/><ellipse cx="425" cy="260" rx="34" ry="52"/><ellipse cx="407" cy="324" rx="34" ry="52"/>
</g>
<rect x="108" y="108" width="296" height="302" rx="118" fill="{creature.primary}" {stroke}/>
<path d="M131 340 Q256 390 381 340 Q356 410 256 414 Q156 410 131 340 Z" fill="{creature.secondary}" fill-opacity="0.50"/>
<circle cx="128" cy="194" r="12" fill="{creature.accent}"/><circle cx="384" cy="194" r="12" fill="{creature.accent}"/>
{common_highlight}
"""
    elif creature.identity_id == "micro-orbit-004":
        body = f"""
<path d="M64 270 Q256 116 448 270 Q256 424 64 270 Z" fill="none" stroke="{creature.accent}" stroke-width="22" stroke-linecap="round"/>
<path d="M257 112 Q245 75 278 55" fill="none" stroke="{OUTLINE}" stroke-width="12" stroke-linecap="round"/>
<circle cx="286" cy="48" r="20" fill="{creature.accent}" {stroke}/>
<circle cx="256" cy="259" r="151" fill="{creature.primary}" {stroke}/>
<path d="M132 315 Q256 382 380 315 Q357 398 256 413 Q155 398 132 315 Z" fill="{creature.secondary}" fill-opacity="0.50"/>
{common_highlight}
"""
    elif creature.identity_id == "micro-crumb-005":
        body = f"""
<circle cx="144" cy="143" r="66" fill="{creature.secondary}" {stroke}/>
<circle cx="368" cy="143" r="66" fill="{creature.secondary}" {stroke}/>
<circle cx="144" cy="143" r="35" fill="{creature.light}"/>
<circle cx="368" cy="143" r="35" fill="{creature.light}"/>
<rect x="103" y="119" width="306" height="291" rx="139" fill="{creature.primary}" {stroke}/>
<ellipse cx="188" cy="300" rx="59" ry="46" fill="{creature.light}" fill-opacity="0.72"/>
<ellipse cx="324" cy="300" rx="59" ry="46" fill="{creature.light}" fill-opacity="0.72"/>
<path d="M133 344 Q256 402 379 344 Q352 415 256 415 Q160 415 133 344 Z" fill="{creature.secondary}" fill-opacity="0.42"/>
{common_highlight}
"""
    else:
        body = f"""
<path d="M128 190 C93 154 113 103 161 109 C171 61 231 53 256 91 C286 52 344 65 351 111 C400 105 421 158 385 192 C430 219 421 279 384 295 C414 342 377 389 334 378 C315 424 260 428 236 391 C198 427 146 404 148 365 C96 365 77 310 116 280 C75 246 86 202 128 190 Z" fill="{creature.primary}" {stroke}/>
<path d="M120 322 Q256 390 392 322 Q365 405 256 417 Q147 405 120 322 Z" fill="{creature.secondary}" fill-opacity="0.42"/>
{common_highlight}
"""
    return svg(body)


def signature_effects(creature: Creature, reaction_id: str) -> str:
    strong = reaction_id in {"joy", "love", "surprise", "anger", "panic", "proud"}
    if creature.signature == "leaf":
        return (
            f'<path d="M91 226 Q64 194 81 169 Q119 178 119 218 Q105 230 91 226 Z" fill="{creature.secondary}" stroke="{OUTLINE}" stroke-width="6"/>'
            f'<path d="M421 334 Q450 304 470 326 Q460 365 422 367 Q409 350 421 334 Z" fill="{creature.accent}" stroke="{OUTLINE}" stroke-width="6"/>'
        )
    if creature.signature == "ember":
        return (
            f'<path d="M83 321 Q61 286 89 263 Q117 287 96 322 Z" fill="{creature.accent}" stroke="{OUTLINE}" stroke-width="6"/>'
            + (f'<circle cx="428" cy="180" r="12" fill="{creature.secondary}"/>' if strong else "")
        )
    if creature.signature == "drop":
        return (
            f'<path d="M79 193 Q100 220 79 242 Q58 220 79 193 Z" fill="{creature.accent}" stroke="{OUTLINE}" stroke-width="5"/>'
            f'<circle cx="437" cy="345" r="13" fill="{creature.light}" stroke="{OUTLINE}" stroke-width="5"/>'
        )
    if creature.signature == "star":
        return sparkle(84, 198, 19, creature.accent) + (
            f'<circle cx="433" cy="335" r="10" fill="{creature.light}" stroke="{OUTLINE}" stroke-width="5"/>'
        )
    if creature.signature == "crumb":
        return (
            f'<circle cx="83" cy="224" r="9" fill="{creature.secondary}"/>'
            f'<circle cx="99" cy="199" r="7" fill="{creature.accent}"/>'
            f'<circle cx="430" cy="345" r="10" fill="{creature.secondary}"/>'
        )
    return (
        f'<circle cx="83" cy="231" r="20" fill="{creature.light}" stroke="{OUTLINE}" stroke-width="5"/>'
        f'<circle cx="425" cy="340" r="15" fill="{creature.accent}" stroke="{OUTLINE}" stroke-width="5"/>'
    )


def reaction_svg(creature: Creature, reaction_id: str) -> str:
    dark = OUTLINE
    parts: list[str] = [signature_effects(creature, reaction_id)]
    if reaction_id == "joy":
        parts.extend(
            (
                f'<path d="M177 241 Q208 208 239 241" fill="none" stroke="{dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<path d="M273 241 Q304 208 335 241" fill="none" stroke="{dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<path d="M207 284 Q256 345 305 284 Q300 352 256 360 Q212 352 207 284 Z" fill="{creature.light}" stroke="{dark}" stroke-width="10" stroke-linejoin="round"/>',
                sparkle(394, 151, 22, creature.accent),
            )
        )
    elif reaction_id == "laugh":
        parts.extend(
            (
                f'<path d="M176 235 Q208 207 240 235" fill="none" stroke="{dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<path d="M272 235 Q304 207 336 235" fill="none" stroke="{dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<path d="M201 279 Q256 367 311 279 Z" fill="{dark}" stroke="{dark}" stroke-width="9" stroke-linejoin="round"/>',
                f'<path d="M222 327 Q256 350 290 327" fill="none" stroke="{BLUSH}" stroke-width="15" stroke-linecap="round"/>',
                f'<path d="M160 245 Q143 278 168 297 Q191 274 176 245 Z" fill="{TEAR}"/>',
                f'<path d="M352 245 Q369 278 344 297 Q321 274 336 245 Z" fill="{TEAR}"/>',
            )
        )
    elif reaction_id == "love":
        parts.extend(
            (
                heart(208, 236, 0.72, BLUSH),
                heart(304, 236, 0.72, BLUSH),
                f'<path d="M214 302 Q256 337 298 302" fill="none" stroke="{dark}" stroke-width="12" stroke-linecap="round"/>',
                heart(405, 166, 0.58, creature.accent),
                heart(106, 323, 0.40, BLUSH),
            )
        )
    elif reaction_id == "surprise":
        parts.extend(
            (
                f'<ellipse cx="207" cy="238" rx="32" ry="39" fill="{WHITE}" stroke="{dark}" stroke-width="9"/>',
                f'<ellipse cx="305" cy="238" rx="32" ry="39" fill="{WHITE}" stroke="{dark}" stroke-width="9"/>',
                f'<circle cx="207" cy="244" r="12" fill="{dark}"/>',
                f'<circle cx="305" cy="244" r="12" fill="{dark}"/>',
                f'<ellipse cx="256" cy="319" rx="27" ry="37" fill="{dark}"/>',
                f'<path d="M153 174 L130 144 M359 174 L382 144 M256 151 L256 113" fill="none" stroke="{dark}" stroke-width="10" stroke-linecap="round"/>',
            )
        )
    elif reaction_id == "cry":
        parts.extend(
            (
                f'<path d="M174 221 Q207 194 240 224" fill="none" stroke="{dark}" stroke-width="11" stroke-linecap="round"/>',
                f'<path d="M272 224 Q305 194 338 221" fill="none" stroke="{dark}" stroke-width="11" stroke-linecap="round"/>',
                f'<path d="M180 246 Q208 261 236 246" fill="none" stroke="{dark}" stroke-width="10" stroke-linecap="round"/>',
                f'<path d="M276 246 Q304 261 332 246" fill="none" stroke="{dark}" stroke-width="10" stroke-linecap="round"/>',
                f'<path d="M184 259 Q203 305 184 353 Q157 312 176 267 Z" fill="{TEAR}"/>',
                f'<path d="M328 259 Q309 305 328 353 Q355 312 336 267 Z" fill="{TEAR}"/>',
                f'<path d="M220 331 Q256 298 292 331" fill="none" stroke="{dark}" stroke-width="12" stroke-linecap="round"/>',
            )
        )
    elif reaction_id == "anger":
        parts.extend(
            (
                f'<path d="M174 205 L238 232 M338 205 L274 232" fill="none" stroke="{dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<ellipse cx="210" cy="252" rx="23" ry="26" fill="{WHITE}" stroke="{dark}" stroke-width="8"/>',
                f'<ellipse cx="302" cy="252" rx="23" ry="26" fill="{WHITE}" stroke="{dark}" stroke-width="8"/>',
                f'<circle cx="215" cy="256" r="10" fill="{dark}"/><circle cx="297" cy="256" r="10" fill="{dark}"/>',
                f'<path d="M220 326 Q256 304 292 326" fill="none" stroke="{dark}" stroke-width="13" stroke-linecap="round"/>',
                f'<path d="M115 178 Q75 156 102 124 M397 178 Q437 156 410 124" fill="none" stroke="{creature.secondary}" stroke-width="13" stroke-linecap="round"/>',
            )
        )
    elif reaction_id == "suspicion":
        parts.extend(
            (
                f'<path d="M170 215 Q207 197 242 220" fill="none" stroke="{dark}" stroke-width="12" stroke-linecap="round"/>',
                f'<path d="M274 205 L337 223" fill="none" stroke="{dark}" stroke-width="12" stroke-linecap="round"/>',
                f'<ellipse cx="207" cy="251" rx="28" ry="31" fill="{WHITE}" stroke="{dark}" stroke-width="8"/>',
                f'<path d="M278 252 Q304 265 330 252" fill="none" stroke="{dark}" stroke-width="10" stroke-linecap="round"/>',
                f'<circle cx="220" cy="253" r="10" fill="{dark}"/>',
                f'<path d="M226 323 Q258 329 290 318" fill="none" stroke="{dark}" stroke-width="11" stroke-linecap="round"/>',
                f'<path d="M389 211 L420 199 M394 235 L429 238" fill="none" stroke="{creature.accent}" stroke-width="9" stroke-linecap="round"/>',
            )
        )
    elif reaction_id == "exhausted":
        parts.extend(
            (
                f'<path d="M176 244 Q208 260 240 244 M272 244 Q304 260 336 244" fill="none" stroke="{dark}" stroke-width="12" stroke-linecap="round"/>',
                f'<ellipse cx="256" cy="325" rx="31" ry="25" fill="{dark}"/>',
                f'<path d="M176 286 L222 292 M290 292 L336 286" fill="none" stroke="{BLUSH}" stroke-width="8" stroke-linecap="round"/>',
                f'<circle cx="395" cy="207" r="13" fill="{creature.light}" stroke="{dark}" stroke-width="5"/>',
                f'<circle cx="421" cy="177" r="9" fill="{creature.light}" stroke="{dark}" stroke-width="5"/>',
            )
        )
    elif reaction_id == "panic":
        parts.extend(
            (
                f'<ellipse cx="207" cy="242" rx="32" ry="42" fill="{WHITE}" stroke="{dark}" stroke-width="9"/>',
                f'<ellipse cx="305" cy="242" rx="32" ry="42" fill="{WHITE}" stroke="{dark}" stroke-width="9"/>',
                f'<circle cx="207" cy="252" r="9" fill="{dark}"/><circle cx="305" cy="252" r="9" fill="{dark}"/>',
                f'<path d="M216 326 Q231 304 246 326 Q261 348 276 326 Q291 304 306 326" fill="none" stroke="{dark}" stroke-width="11" stroke-linecap="round"/>',
                f'<path d="M147 177 L121 153 M139 211 L102 206 M365 177 L391 153 M373 211 L410 206" fill="none" stroke="{creature.secondary}" stroke-width="10" stroke-linecap="round"/>',
            )
        )
    elif reaction_id == "proud":
        parts.extend(
            (
                f'<path d="M174 205 Q208 181 242 203 M270 203 Q304 181 338 205" fill="none" stroke="{dark}" stroke-width="11" stroke-linecap="round"/>',
                f'<path d="M180 239 Q207 217 234 239 Q207 257 180 239 Z" fill="{WHITE}" stroke="{dark}" stroke-width="8" stroke-linejoin="round"/>',
                f'<path d="M278 239 Q305 217 332 239 Q305 257 278 239 Z" fill="{WHITE}" stroke="{dark}" stroke-width="8" stroke-linejoin="round"/>',
                f'<circle cx="211" cy="235" r="9" fill="{dark}"/><circle cx="309" cy="235" r="9" fill="{dark}"/>',
                f'<path d="M180 283 Q201 270 222 283 M290 283 Q311 270 332 283" fill="none" stroke="{BLUSH}" stroke-width="9" stroke-linecap="round"/>',
                f'<path d="M211 306 Q250 342 304 296" fill="none" stroke="{dark}" stroke-width="13" stroke-linecap="round"/>',
                f'<circle cx="256" cy="372" r="28" fill="{creature.accent}" stroke="{dark}" stroke-width="7"/>',
                sparkle(256, 372, 14, WHITE),
                sparkle(168, 156, 15, creature.accent),
                sparkle(256, 133, 23, creature.light),
                sparkle(348, 156, 15, creature.accent),
            )
        )
    else:
        raise ValueError(f"unsupported reaction: {reaction_id}")
    return svg("\n".join(parts))


def keyframe(at_ms: int, value: float, easing: str = "ease_in_out") -> dict[str, Any]:
    return {"at_ms": at_ms, "value": value, "easing": easing}


def track(target: str, property_name: str, frames: list[dict[str, Any]]) -> dict[str, Any]:
    return {"target": target, "property": property_name, "keyframes": frames}


def animation_document(reaction: Reaction, creature_index: int) -> dict[str, Any]:
    duration = reaction.duration_ms
    middle = duration // 2
    direction = -1 if creature_index % 2 == 0 else 1
    tracks: list[dict[str, Any]] = []
    if reaction.motion == "pulse":
        scale = 1.045 if reaction.reaction_id == "love" else 1.04
        if creature_index == 3:
            scale = 1.018
        tracks.extend(
            (
                track("body", "scale_x", [keyframe(0, 1), keyframe(middle, scale, "back_out"), keyframe(duration, 1)]),
                track("body", "scale_y", [keyframe(0, 1), keyframe(middle, scale, "back_out"), keyframe(duration, 1)]),
                track("shadow", "scale_x", [keyframe(0, 1), keyframe(middle, 0.94), keyframe(duration, 1)]),
            )
        )
    elif reaction.motion == "laugh":
        tracks.append(
            track(
                "body",
                "rotation_degrees",
                [
                    keyframe(0, 0),
                    keyframe(duration // 4, 4 * direction, "ease_out"),
                    keyframe(middle, -4 * direction),
                    keyframe(3 * duration // 4, 3 * direction),
                    keyframe(duration, 0),
                ],
            )
        )
    elif reaction.motion == "pop":
        pop_scale = 1.02 if creature_index == 3 else 1.045
        tracks.extend(
            (
                track("body", "scale_x", [keyframe(0, 1), keyframe(duration // 3, pop_scale, "back_out"), keyframe(duration, 1)]),
                track("body", "scale_y", [keyframe(0, 1), keyframe(duration // 3, pop_scale, "back_out"), keyframe(duration, 1)]),
            )
        )
    elif reaction.motion == "sob":
        tracks.append(
            track("body", "translate_y", [keyframe(0, 0), keyframe(middle, 7, "ease_out"), keyframe(duration, 0)])
        )
    elif reaction.motion == "shake":
        tracks.append(
            track(
                "body",
                "translate_x",
                [keyframe(0, 0), keyframe(duration // 4, -7), keyframe(middle, 7), keyframe(3 * duration // 4, -4), keyframe(duration, 0)],
            )
        )
    elif reaction.motion == "lean":
        tracks.append(
            track("body", "rotation_degrees", [keyframe(0, 0), keyframe(middle, 4 * direction), keyframe(duration, 0)])
        )
    elif reaction.motion == "breathe":
        tracks.extend(
            (
                track("body", "translate_y", [keyframe(0, 0), keyframe(middle, 5), keyframe(duration, 0)]),
                track("body", "scale_y", [keyframe(0, 1), keyframe(middle, 0.985), keyframe(duration, 1)]),
            )
        )
    elif reaction.motion == "tremble":
        tracks.append(
            track(
                "body",
                "rotation_degrees",
                [keyframe(0, 0), keyframe(duration // 4, -3), keyframe(middle, 3), keyframe(3 * duration // 4, -3), keyframe(duration, 0)],
            )
        )
    else:
        rise = -4 if creature_index == 3 else -8
        tracks.extend(
            (
                track("body", "translate_y", [keyframe(0, 0), keyframe(middle, rise, "ease_out"), keyframe(duration, 0)]),
                track("shadow", "scale_x", [keyframe(0, 1), keyframe(middle, 0.86), keyframe(duration, 1)]),
            )
        )
    return {
        "duration_ms": duration,
        "fps": 10,
        "loop": "loop",
        "tracks": tracks,
    }


def pack_document(creature: Creature) -> dict[str, Any]:
    layers: list[dict[str, Any]] = [
        {"id": "shadow", "source": "layers/00-shadow.svg", "z": 0, "depth": 0.0},
        {
            "id": "body",
            "source": "layers/10-body.svg",
            "z": 100,
            "depth": 0.14,
            "pivot": "body",
            "collision_bounds": {"x": 64, "y": 32, "width": 384, "height": 394},
        },
    ]
    expressions: dict[str, list[str]] = {}
    for index, reaction in enumerate(REACTIONS, start=20):
        layer_id = f"reaction-{reaction.reaction_id}"
        layers.append(
            {
                "id": layer_id,
                "source": f"layers/{index:02d}-{layer_id}.svg",
                "z": index * 10,
                "depth": 0.025,
                "parent": "body",
                "pivot": "face",
            }
        )
        expressions[reaction.reaction_id] = [layer_id]
    return {
        "schema_version": 1,
        "pack_id": creature.identity_id,
        "canvas": {"width": 512, "height": 512},
        "layers": layers,
        "base_layers": ["shadow"],
        "expressions": expressions,
        "poses": {"reaction": ["body"]},
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT",
            "source": f"generate_micro_reactions_pack.py v{GENERATOR_VERSION}; original procedural SVG",
        },
        "anchors": {
            "face_center": {"x": 256, "y": 270},
            "body_center": {"x": 256, "y": 258},
            "ground_contact": {"x": 256, "y": 420},
        },
        "pivots": {
            "body": {"x": 256, "y": 274},
            "face": {"x": 256, "y": 260},
        },
        "avoid_regions": [],
        "text_clearance": 16,
    }


def sticker_document(creature: Creature, creature_index: int, reaction: Reaction) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sticker_id": f"{creature.identity_id}-{reaction.reaction_id}",
        "pack_id": creature.identity_id,
        "phrase_id": f"reaction.{reaction.reaction_id}",
        "recipe_id": f"micro-reactions.{reaction.motion}",
        "alt_text": f"{creature.name}, a {creature.archetype}, reacting with {reaction.label.lower()}",
        "expression": reaction.reaction_id,
        "pose": "reaction",
        "seed": 1,
        "animation": animation_document(reaction, creature_index),
    }


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")


def render(
    executable: Path,
    pack: Path,
    sticker: Path,
    output: Path,
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
        "512",
        "--height",
        "512",
        "--quality",
        "100",
        "--lossless",
    ]
    if first_frame_only:
        command.append("--first-frame-only")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(command)


def author_sources(destination: Path) -> None:
    for creature_index, creature in enumerate(CREATURES):
        pack_root = destination / creature.identity_id
        write_text(pack_root / "layers" / "00-shadow.svg", shadow_svg())
        write_text(pack_root / "layers" / "10-body.svg", body_svg(creature))
        for layer_index, reaction in enumerate(REACTIONS, start=20):
            write_text(
                pack_root / "layers" / f"{layer_index:02d}-reaction-{reaction.reaction_id}.svg",
                reaction_svg(creature, reaction.reaction_id),
            )
            write_json(
                pack_root / "stickers" / f"{reaction.reaction_id}.json",
                sticker_document(creature, creature_index, reaction),
            )
        write_json(pack_root / "pack.json", pack_document(creature))
        write_json(
            pack_root / "identity.json",
            {
                "schema_version": 1,
                "identity_id": creature.identity_id,
                "display_name": creature.name,
                "archetype": creature.archetype,
                "palette": {
                    "primary": creature.primary,
                    "secondary": creature.secondary,
                    "light": creature.light,
                    "accent": creature.accent,
                    "outline": OUTLINE,
                },
                "required_features": [
                    "face-dominant-silhouette",
                    f"{creature.signature}-secondary-anatomy",
                    "navy-rounded-outline",
                    "transparent-background",
                ],
                "production_use": "forbidden-until-selected-glb-and-final-pack-review",
            },
        )
    write_json(
        destination / "generation-manifest.json",
        {
            "schema_version": 1,
            "generator": "generate_micro_reactions_pack.py",
            "generator_version": GENERATOR_VERSION,
            "pack_contract": "contracts/micro-reactions-pack-v1.json",
            "emotion_matrix": "content/micro-reactions-emotion-matrix-v1.json",
            "identity_count": len(CREATURES),
            "sticker_count": len(CREATURES) * len(REACTIONS),
            "production_use": "forbidden-until-selected-glb-and-final-pack-review",
            "packs": [
                {
                    "pack_id": creature.identity_id,
                    "display_name": creature.name,
                    "archetype": creature.archetype,
                    "primary": creature.primary,
                    "signature": creature.signature,
                }
                for creature in CREATURES
            ],
        },
    )


def alpha_metrics(path: Path) -> dict[str, Any]:
    frame_hashes: list[str] = []
    frame_margins: list[int] = []
    union: tuple[int, int, int, int] | None = None
    with Image.open(path) as image:
        frame_count = getattr(image, "n_frames", 1)
        for frame_index in range(frame_count):
            image.seek(frame_index)
            rgba = image.convert("RGBA")
            frame_hashes.append(hashlib.sha256(rgba.tobytes()).hexdigest())
            bounds = rgba.getchannel("A").getbbox()
            if bounds is None:
                continue
            left, top, right, bottom = bounds
            frame_margins.append(min(left, top, rgba.width - right, rgba.height - bottom))
            if union is None:
                union = bounds
            else:
                union = (
                    min(union[0], left),
                    min(union[1], top),
                    max(union[2], right),
                    max(union[3], bottom),
                )
    if union is None:
        raise ValueError(f"rendered asset has no visible pixels: {path}")
    return {
        "frame_count": len(frame_hashes),
        "minimum_frame_margin_px": min(frame_margins),
        "union_alpha_bounds": list(union),
        "union_width_ratio": round((union[2] - union[0]) / 512, 4),
        "union_height_ratio": round((union[3] - union[1]) / 512, 4),
        "visible_mid_cycle_change": len(set(frame_hashes)) > 1,
        "animated_webp": b"ANIM" in path.read_bytes() and b"ANMF" in path.read_bytes(),
    }


def load_review_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ROOT / "content" / "fonts" / "sticker-display-v1" / "lilita-one" / "LilitaOne-Regular.ttf",
        ROOT / "examples" / "cat" / "fonts" / "changa-one" / "ChangaOne-Regular.ttf",
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def poster(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def rounded_cell(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    image: Image.Image,
    label: str | None,
    image_size: int,
    font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=24, fill="#FFFFFF", outline="#DCE4ED", width=2)
    left, top, right, bottom = box
    resized = image.copy()
    resized.thumbnail((image_size, image_size), Image.Resampling.LANCZOS)
    x = left + (right - left - resized.width) // 2
    y = top + 12 + (bottom - top - resized.height - (32 if label else 0)) // 2
    canvas.alpha_composite(resized, (x, y))
    if label:
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (left + (right - left - (bounds[2] - bounds[0])) // 2, bottom - 34),
            label,
            fill=OUTLINE,
            font=font,
        )


def build_review_sheets(review_root: Path) -> dict[str, str]:
    label_font = load_review_font(22)
    header_font = load_review_font(24)
    title_font = load_review_font(34)

    lineup = Image.new("RGBA", (1900, 390), "#EEF3F8")
    draw = ImageDraw.Draw(lineup)
    draw.text((32, 18), "MICRO REACTIONS · ORIGINAL IDENTITY LINEUP", fill=OUTLINE, font=title_font)
    for index, creature in enumerate(CREATURES):
        asset = review_root / "reduced-motion" / creature.identity_id / f"{creature.identity_id}-joy.webp"
        rounded_cell(
            lineup,
            (28 + index * 310, 72, 318 + index * 310, 365),
            poster(asset),
            f"{creature.name} · {creature.signature}",
            235,
            label_font,
        )
    lineup_path = review_root / "identity-lineup.png"
    lineup.convert("RGB").save(lineup_path, optimize=True)

    matrix = Image.new("RGBA", (2070, 1325), "#EEF3F8")
    draw = ImageDraw.Draw(matrix)
    draw.text((30, 16), "MICRO REACTIONS · 6 IDENTITIES × 10 SEMANTICS", fill=OUTLINE, font=title_font)
    for column, reaction in enumerate(REACTIONS):
        bounds = draw.textbbox((0, 0), reaction.label, font=header_font)
        draw.text(
            (175 + column * 188 + (178 - (bounds[2] - bounds[0])) // 2, 66),
            reaction.label,
            fill=OUTLINE,
            font=header_font,
        )
    for row, creature in enumerate(CREATURES):
        y = 105 + row * 200
        draw.text((25, y + 78), creature.name.upper(), fill=OUTLINE, font=header_font)
        for column, reaction in enumerate(REACTIONS):
            asset = (
                review_root
                / "reduced-motion"
                / creature.identity_id
                / f"{creature.identity_id}-{reaction.reaction_id}.webp"
            )
            rounded_cell(
                matrix,
                (170 + column * 188, y, 348 + column * 188, y + 182),
                poster(asset),
                None,
                162,
                label_font,
            )
    matrix_path = review_root / "reaction-matrix.png"
    matrix.convert("RGB").save(matrix_path, optimize=True)

    small_paths: list[Path] = []
    for display_size in (80, 100, 160):
        small = Image.new("RGBA", (2070, 1325), "#25364D")
        draw = ImageDraw.Draw(small)
        draw.text(
            (30, 16),
            f"CONTROLLED SMALL-DISPLAY READABILITY · ALL REACTIONS · {display_size} PX",
            fill="#FFFFFF",
            font=title_font,
        )
        for column, reaction in enumerate(REACTIONS):
            bounds = draw.textbbox((0, 0), reaction.label, font=header_font)
            draw.text(
                (175 + column * 188 + (178 - (bounds[2] - bounds[0])) // 2, 66),
                reaction.label,
                fill="#FFFFFF",
                font=header_font,
            )
        for row, creature in enumerate(CREATURES):
            y = 105 + row * 200
            draw.text((25, y + 78), creature.name.upper(), fill="#FFFFFF", font=header_font)
            for column, reaction in enumerate(REACTIONS):
                asset = (
                    review_root
                    / "reduced-motion"
                    / creature.identity_id
                    / f"{creature.identity_id}-{reaction.reaction_id}.webp"
                )
                image = poster(asset)
                image = image.resize(
                    (display_size, display_size),
                    Image.Resampling.LANCZOS,
                )
                left = 170 + column * 188
                top = y
                right = left + 178
                bottom = top + 182
                draw.rounded_rectangle(
                    (left, top, right, bottom),
                    radius=24,
                    fill="#F7FAFC",
                    outline="#DCE4ED",
                    width=2,
                )
                small.alpha_composite(
                    image,
                    (
                        left + (right - left - display_size) // 2,
                        top + (bottom - top - display_size) // 2,
                    ),
                )
        small_path = review_root / f"small-display-all-reactions-{display_size}px.png"
        small.convert("RGB").save(small_path, optimize=True)
        small_paths.append(small_path)
    return {
        path.name: sha256(path)
        for path in (lineup_path, matrix_path, *small_paths)
    }


def build_animation_html(review_root: Path) -> Path:
    figures: list[str] = []
    for creature in CREATURES:
        for reaction in REACTIONS:
            relative = f"assets/{creature.identity_id}/{creature.identity_id}-{reaction.reaction_id}.webp"
            figures.append(
                f'<figure><img src="{relative}" alt="{creature.name} {reaction.label}">'
                f"<figcaption>{creature.name} · {reaction.label}</figcaption></figure>"
            )
    html = (
        "<!doctype html><meta charset=\"utf-8\"><title>Micro Reactions animation review</title>"
        "<style>body{font:16px system-ui;background:#eef3f8;color:#20324b;margin:24px}"
        "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}"
        "figure{margin:0;background:white;border-radius:20px;padding:12px;text-align:center}"
        "img{width:100%;height:auto}figcaption{font-weight:700}</style>"
        "<h1>Micro Reactions · animation playback</h1><main>"
        + "".join(figures)
        + "</main>"
    )
    path = review_root / "animation-review.html"
    write_text(path, html)
    return path


def render_review(source_root: Path, review_root: Path, executable: Path) -> None:
    metrics: list[dict[str, Any]] = []
    for creature in CREATURES:
        pack = source_root / creature.identity_id / "pack.json"
        for reaction in REACTIONS:
            sticker = source_root / creature.identity_id / "stickers" / f"{reaction.reaction_id}.json"
            run([str(executable), "validate", "--pack", str(pack), "--sticker", str(sticker)])
            asset = (
                review_root
                / "assets"
                / creature.identity_id
                / f"{creature.identity_id}-{reaction.reaction_id}.webp"
            )
            reduced = (
                review_root
                / "reduced-motion"
                / creature.identity_id
                / f"{creature.identity_id}-{reaction.reaction_id}.webp"
            )
            render(executable, pack, sticker, asset, False)
            render(executable, pack, sticker, reduced, True)
            values = alpha_metrics(asset)
            if values["minimum_frame_margin_px"] < 16:
                raise ValueError(
                    f"{asset} violates the 16 px hard margin: "
                    f"{values['minimum_frame_margin_px']} px"
                )
            if not values["animated_webp"] or not values["visible_mid_cycle_change"]:
                raise ValueError(f"{asset} does not contain visible animation")
            values.update(
                {
                    "identity_id": creature.identity_id,
                    "reaction_id": reaction.reaction_id,
                    "asset_sha256": sha256(asset),
                    "reduced_motion_sha256": sha256(reduced),
                }
            )
            metrics.append(values)

    artifacts = build_review_sheets(review_root)
    animation_html = build_animation_html(review_root)
    artifacts[animation_html.name] = sha256(animation_html)
    contract = ROOT / "contracts" / "micro-reactions-pack-v1.json"
    matrix = ROOT / "content" / "micro-reactions-emotion-matrix-v1.json"
    write_json(
        review_root / "review.json",
        {
            "schema_version": 1,
            "review_id": "micro-reactions-reaction-correction-v2",
            "review_status": "owner-approved",
            "production_use": "forbidden-until-selected-glb-and-final-pack-review",
            "owner_approval": (
                "contracts/"
                "micro-reactions-reaction-and-orbit-2_5d-owner-approval-v1.json"
            ),
            "contract_sha256": sha256(contract),
            "emotion_matrix_sha256": sha256(matrix),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "identity_count": len(CREATURES),
            "reaction_count": len(REACTIONS),
            "sticker_count": len(metrics),
            "animated_sticker_count": sum(bool(value["animated_webp"]) for value in metrics),
            "minimum_frame_margin_px": min(int(value["minimum_frame_margin_px"]) for value in metrics),
            "minimum_union_width_ratio": min(float(value["union_width_ratio"]) for value in metrics),
            "minimum_union_height_ratio": min(float(value["union_height_ratio"]) for value in metrics),
            "distinct_primary_palette_count": len({creature.primary for creature in CREATURES}),
            "distinct_signature_count": len({creature.signature for creature in CREATURES}),
            "controlled_small_display_evidence": {
                "identity_count": len(CREATURES),
                "reaction_count": len(REACTIONS),
                "sizes_px": [80, 100, 160],
                "rendered_comparison_count": len(CREATURES) * len(REACTIONS) * 3,
                "same_reaction_positions_across_size_sheets": True,
            },
            "artifacts": artifacts,
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-output",
        type=Path,
        default=ROOT / "art" / "micro-reactions-v1" / "candidates",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=ROOT / "generated" / "micro-reactions-v1-review",
    )
    parser.add_argument(
        "--mascotrender",
        type=Path,
        default=ROOT / "build" / "Release" / "mascotrender",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    executable = args.mascotrender.resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError(f"mascotrender executable is unavailable: {executable}")
    source_destination = args.source_output.resolve()
    review_destination = args.review_output.resolve()
    source_destination.parent.mkdir(parents=True, exist_ok=True)
    review_destination.parent.mkdir(parents=True, exist_ok=True)
    source_staging = Path(
        tempfile.mkdtemp(prefix=f"{source_destination.name}.staging-", dir=source_destination.parent)
    )
    review_staging = Path(
        tempfile.mkdtemp(prefix=f"{review_destination.name}.staging-", dir=review_destination.parent)
    )
    try:
        author_sources(source_staging)
        render_review(source_staging, review_staging, executable)
        replace_directory(source_staging, source_destination, args.force)
        replace_directory(review_staging, review_destination, args.force)
    finally:
        if source_staging.exists():
            shutil.rmtree(source_staging)
        if review_staging.exists():
            shutil.rmtree(review_staging)
    print(
        f"authored {len(CREATURES)} identities and rendered "
        f"{len(CREATURES) * len(REACTIONS)} animated review stickers at {review_destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
