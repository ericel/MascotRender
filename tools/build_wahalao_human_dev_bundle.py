#!/usr/bin/env python3
"""Build a local Wahalao bundle with the production 15-character human library.

The bundle combines the existing reviewed mascot pack with the approved
41-phrase human matrix. Foundation and Wave 2 identities are both bound to
their public-release owner decisions. Trie entries contain semantic phrase IDs;
character selection happens after matching and never inspects demographics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
FOUNDATION_IDS = ("H01", "H04", "H07", "H12", "H13")
WAVE2_IDS = ("H02", "H03", "H05", "H06", "H08", "H09", "H10", "H11", "H14", "H15")
MASTER_IDS = tuple(f"H{index:02d}" for index in range(1, 16))
CAPTION_LAYOUTS = ("top", "right", "bottom", "left")
BUNDLE_VERSION = 8
PROTOCOL = "mascotrender-bundle-v1"
MATCHING = "casefolded full phrase with Unicode word boundaries"
FONT_SET_ROOT = ROOT / "content" / "fonts" / "sticker-display-v1"
FONT_VOICES = {
    "punch": {
        "source": "changa-one/ChangaOne-Regular.ttf",
        "license": "changa-one/OFL.txt",
        "min_size": 20,
        "max_size": 48,
        "motion": "text_pop",
    },
    "comic-slant": {
        "source": "bangers/Bangers-Regular.ttf",
        "license": "bangers/OFL.txt",
        "min_size": 22,
        "max_size": 54,
        "motion": "text_wobble",
    },
    "rounded": {
        "source": "lilita-one/LilitaOne-Regular.ttf",
        "license": "lilita-one/OFL.txt",
        "min_size": 20,
        "max_size": 50,
        "motion": "text_pulse",
    },
    "handwritten": {
        "source": "kalam/Kalam-Bold.ttf",
        "license": "kalam/OFL.txt",
        "min_size": 20,
        "max_size": 46,
        "motion": "text_float",
    },
}

def phrase(
    slug: str,
    text: str,
    triggers: tuple[str, ...],
    expression: str,
    pose: str,
    motion: str,
    layout: str,
    framing: str = "dynamic-full-body",
) -> dict[str, Any]:
    semantic = {
        "sorry": ("apology", "apologetically"),
        "love": ("affection", "affectionately"),
    }.get(slug, (pose, "expressively"))
    return {
        "slug": slug,
        "text": text,
        "triggers": triggers,
        "expression": expression,
        "pose": pose,
        "motion": motion,
        "layout": layout,
        "framing": framing,
        "intent": semantic[0],
        "accessible_tone": semantic[1],
        "audience_class": "general",
    }


# Phrase semantics deliberately drive expression, pose, motion, framing, and
# caption composition independently. This is a representative chat matrix,
# not a cross-product that produces thousands of visually redundant stickers.
PHRASES: tuple[dict[str, Any], ...] = (
    phrase("big-mood", "BIG MOOD", ("big mood",), "confident", "rest", "calm", "right", "three-quarter"),
    phrase("hello", "HELLO!", ("hello", "hi", "hey", "hiya"), "happy", "greeting", "wave", "top", "full-body"),
    phrase("haha", "HAHA", ("haha", "hehe", "rofl"), "laughing", "celebration", "laugh", "left", "three-quarter"),
    phrase("lol", "LOL", ("lol", "lmao", "laugh"), "laughing", "celebration", "laugh", "top", "bust"),
    phrase("yes", "YES", ("yes", "yup", "yep", "yessir"), "confident", "agreement", "nod", "right", "three-quarter"),
    phrase("no", "NO", ("no", "nah", "nope"), "confident", "disagreement", "shake", "left", "bust"),
    phrase("okay", "OKAY", ("okay", "ok", "aight"), "happy", "agreement", "calm", "bottom", "full-body"),
    phrase("facts", "FACTS", ("facts", "true", "period", "periodt", "valid"), "confident", "agreement", "nod", "top", "three-quarter"),
    phrase("no-cap", "NO CAP", ("no cap", "nocap", "real"), "confident", "agreement", "nod", "left", "three-quarter"),
    phrase("omg", "OMG!", ("omg", "wow", "crazy", "insane", "wild"), "surprised", "surprise", "shock", "right", "bust"),
    phrase("sus", "SUS", ("sus", "shook", "sheesh"), "thinking", "concern", "think", "top", "three-quarter"),
    phrase("for-real", "FOR REAL", ("for real", "fr", "frfr", "based"), "confident", "agreement", "nod", "bottom", "three-quarter"),
    phrase("vibes", "VIBES", ("vibes", "mood", "chill", "cool"), "happy", "rest", "calm", "left", "three-quarter"),
    phrase("slay", "SLAY!", ("slay", "bussin", "fire", "lit", "dope"), "excited", "celebration", "celebrate", "right", "full-body"),
    phrase("win", "WIN!", ("win", "dub", "goat", "epic"), "excited", "celebration", "celebrate", "top", "full-body"),
    phrase("right-now", "RIGHT NOW", ("right now", "rn"), "confident", "agreement", "nod", "bottom", "three-quarter"),
    phrase("tbh", "TBH", ("tbh", "ngl", "imo", "imho"), "thinking", "concern", "think", "right", "bust"),
    phrase("wdym", "WDYM?", ("wdym", "wym", "huh", "what"), "surprised", "concern", "think", "left", "bust"),
    phrase("brb", "BRB", ("brb", "afk"), "happy", "farewell", "farewell", "top", "full-body"),
    phrase("on-my-way", "ON MY WAY", ("on my way", "omw", "otw", "gtg", "g2g"), "excited", "greeting", "wave", "bottom", "full-body"),
    phrase("thanks", "THANKS", ("thanks", "thx", "ty", "tysm", "appreciate"), "happy", "gratitude", "gratitude", "right", "three-quarter"),
    phrase("sorry", "SORRY", ("sorry", "sry", "my bad"), "sorry", "gratitude", "apology", "left", "three-quarter"),
    phrase("no-problem", "NO PROBLEM", ("no problem", "np", "nw", "you are welcome"), "happy", "agreement", "calm", "top", "three-quarter"),
    phrase("good-morning", "GOOD MORNING", ("good morning", "gm", "morning"), "excited", "greeting", "wave", "bottom", "full-body"),
    phrase("good-night", "GOOD NIGHT", ("good night", "gn", "gnight", "goodnight"), "happy", "farewell", "farewell", "right", "full-body"),
    phrase("bye", "BYE", ("bye", "cya", "ttyl", "peace"), "happy", "farewell", "farewell", "left", "full-body"),
    phrase("love", "LOVE", ("love", "xoxo", "kiss", "hug", "ily", "ilysm"), "happy", "gratitude", "love", "top", "bust"),
    phrase("wahala", "WAHALA!", ("wahala", "trouble", "problem"), "surprised", "surprise", "dramatic", "bottom", "dynamic-full-body"),
    phrase("no-wahala", "NO WAHALA", ("no wahala",), "happy", "agreement", "calm", "right", "three-quarter"),
    phrase("no-vex", "NO VEX", ("no vex", "calm down", "easy"), "confident", "agreement", "calm", "left", "three-quarter"),
    phrase("chai", "CHAI!", ("chai",), "surprised", "surprise", "shock", "top", "bust"),
    phrase("abeg", "ABEG!", ("abeg", "please", "beg"), "sorry", "gratitude", "plead", "bottom", "three-quarter"),
    phrase("omo", "OMO!", ("omo", "eish", "haba"), "surprised", "surprise", "shock", "right", "bust"),
    phrase("chale", "CHALE!", ("chale", "charley"), "happy", "greeting", "wave", "left", "full-body"),
    phrase("no-stress", "NO STRESS", ("no stress",), "confident", "rest", "calm", "top", "three-quarter"),
    phrase("lets-go", "LET'S GO!", ("let's go", "lets go"), "excited", "celebration", "celebrate", "bottom", "full-body"),
    phrase("nice-one", "NICE ONE", ("nice one",), "happy", "agreement", "nod", "right", "three-quarter"),
    phrase("oh-wow", "OH, WOW!", ("oh wow",), "surprised", "surprise", "shock", "left", "bust"),
    phrase("thank-you", "THANK YOU", ("thank you",), "happy", "gratitude", "gratitude", "top", "three-quarter"),
    phrase("well-done", "WELL DONE!", ("well done",), "confident", "celebration", "celebrate", "bottom", "full-body"),
    phrase("you-got-this", "YOU GOT THIS!", ("you got this",), "excited", "celebration", "celebrate", "right", "full-body"),
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")


def verify_approved_review(review_root: Path) -> dict[str, Any]:
    report = read_json(review_root / "release-review.json")
    if report.get("review_status") != "public-release-approved":
        raise ValueError("canonical human review is not public-release-approved")
    if report.get("production_use") != "public-release":
        raise ValueError("canonical human review is not approved for public release")
    if report.get("master_count") != len(FOUNDATION_IDS):
        raise ValueError("canonical human review does not contain the five approved masters")
    if report.get("blocking_findings"):
        raise ValueError("canonical human review contains blocking findings")
    decision = report.get("prior_bound_owner_decision")
    if not isinstance(decision, dict) or decision.get("decision") != "approved":
        raise ValueError("canonical human owner decision is not approved")
    reviewed = decision.get("reviewed_artifacts")
    if not isinstance(reviewed, dict) or not reviewed:
        raise ValueError("canonical human owner decision has no artifact hashes")
    for relative, expected in reviewed.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("canonical human owner decision contains an invalid artifact hash")
        path = review_root / relative
        if sha256_file(path) != expected:
            raise ValueError(f"approved review artifact changed: {relative}")
    return report


def verify_wave2_owner_approval(review_root: Path) -> dict[str, Any]:
    identity_decision = read_json(ROOT / "contracts" / "human-canonical-expansion-wave2-owner-approval.json")
    if identity_decision.get("decision") != "approved" or set(identity_decision.get("approved_members", [])) != set(WAVE2_IDS):
        raise ValueError("Wave 2 owner vector identity approval is incomplete")
    for relative, expected in identity_decision.get("approved_artifacts", {}).items():
        if sha256_file(review_root / relative) != expected:
            raise ValueError(f"Wave 2 owner-approved artifact changed: {relative}")

    activation = read_json(ROOT / "contracts" / "human-wave2-production-activation-v1.json")
    if (
        activation.get("decision") != "approved-for-production-release"
        or activation.get("production_use") != "public-release"
        or activation.get("public_release_activation") != "approved"
        or set(activation.get("approved_members", [])) != set(WAVE2_IDS)
    ):
        raise ValueError("Wave 2 production activation is incomplete")
    production_gates = activation.get("production_gates")
    if not isinstance(production_gates, dict) or any(value != "approved" for value in production_gates.values()):
        raise ValueError("Wave 2 production activation contains an open production gate")

    eligibility = read_json(ROOT / "content" / "human-phrase-eligibility-v1.json")
    phrases = eligibility.get("phrases")
    if not isinstance(phrases, list) or len(phrases) != len(PHRASES):
        raise ValueError("Wave 2 phrase life-stage compatibility is incomplete")
    expected = {f"chat.{phrase_value['slug'].replace('-', '.')}" for phrase_value in PHRASES}
    if {str(value.get("phrase_id")) for value in phrases} != expected:
        raise ValueError("Wave 2 phrase eligibility does not match the development matrix")
    return {
        "review_status": identity_decision.get("review_status"),
        "production_use": activation.get("production_use"),
        "activation_decision": activation.get("decision"),
    }


def phrase_id(phrase_value: dict[str, Any]) -> str:
    return f"chat.{str(phrase_value['slug']).replace('-', '.')}"


def infer_phrase_id(sticker_id: str) -> str:
    for phrase_value in sorted(PHRASES, key=lambda value: len(str(value["slug"])), reverse=True):
        if sticker_id.endswith(f"-{phrase_value['slug']}"):
            return phrase_id(phrase_value)
    raise ValueError(f"cannot infer semantic phrase ID for base sticker {sticker_id}")


def add_reduced_motion_asset(staging: Path, record: dict[str, Any]) -> None:
    sticker_id = str(record["sticker_id"])
    pack_id = str(record["pack_id"])
    source = staging / str(record["path"])
    relative = Path("reduced-motion") / pack_id / f"{sticker_id}.webp"
    destination = staging / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.seek(0)
        image.convert("RGBA").save(destination, "WEBP", lossless=True, quality=100, method=6)
    record["reduced_motion"] = {
        "presentation": "static-semantic-equivalent",
        "width": 512,
        "height": 512,
        "path": relative.as_posix(),
        "sha256": sha256_file(destination),
        "encoded_bytes": destination.stat().st_size,
    }


def verify_font_set() -> dict[str, Any]:
    manifest = read_json(FONT_SET_ROOT / "manifest.json")
    declared = manifest.get("fonts")
    if not isinstance(declared, list) or len(declared) != len(FONT_VOICES):
        raise ValueError("sticker display font manifest is incomplete")
    seen: set[str] = set()
    for entry in declared:
        if not isinstance(entry, dict):
            raise ValueError("sticker display font manifest entry is invalid")
        font_id = str(entry.get("id", ""))
        if font_id not in FONT_VOICES or font_id in seen:
            raise ValueError(f"unexpected or duplicate display font: {font_id}")
        seen.add(font_id)
        source = (FONT_SET_ROOT / str(entry.get("source", ""))).resolve()
        license_file = (FONT_SET_ROOT / str(entry.get("license_file", ""))).resolve()
        if FONT_SET_ROOT.resolve() not in source.parents or source.suffix.lower() != ".ttf":
            raise ValueError(f"display font must be a pack-local static TTF: {font_id}")
        if FONT_SET_ROOT.resolve() not in license_file.parents:
            raise ValueError(f"display font license escapes the font set: {font_id}")
        if not source.is_file() or not license_file.is_file():
            raise ValueError(f"display font or complete license is missing: {font_id}")
        if sha256_file(source) != entry.get("sha256"):
            raise ValueError(f"display font hash mismatch: {font_id}")
    return manifest


def caption_voice(phrase_value: dict[str, Any]) -> str:
    slug = str(phrase_value["slug"])
    if slug in {
        "haha", "lol", "omg", "slay", "win", "wahala", "chai", "omo",
        "lets-go", "oh-wow", "well-done", "you-got-this",
    }:
        return "comic-slant"
    if slug in {
        "hello", "thanks", "sorry", "good-morning", "good-night", "bye",
        "love", "abeg", "thank-you",
    }:
        return "handwritten"
    if slug in {
        "big-mood", "okay", "vibes", "no-problem", "no-wahala", "no-vex",
        "no-stress", "nice-one",
    }:
        return "rounded"
    return "punch"


def prepare_pack(master_source: Path, destination: Path) -> Path:
    shutil.copytree(master_source, destination)
    font_dir = destination / "fonts" / "sticker-display-v1"
    shutil.copytree(FONT_SET_ROOT, font_dir)

    pack_path = destination / "pack.json"
    pack = read_json(pack_path)
    # Rasterized per-layer alpha bounds let the engine build a conservative
    # union across the real animation timeline. This replaces the early broad
    # torso rectangle that could not distinguish a face from a wheelchair,
    # cane, prosthesis, hearing aid, or rollator.
    collision_cache: dict[Path, dict[str, int] | None] = {}
    collision_dir = destination / ".collision-bounds"
    collision_dir.mkdir(parents=True, exist_ok=True)
    for index, layer in enumerate(pack.get("layers", [])):
        layer_id = str(layer.get("id", ""))
        if layer_id == "shadow" or layer_id.startswith("face-") or layer.get("screen_space") is True:
            layer.pop("collision_bounds", None)
            continue
        source = (destination / str(layer["source"])).resolve()
        if source not in collision_cache:
            raster = collision_dir / f"{index:03d}.png"
            run(["rsvg-convert", "--width", "128", "--height", "128", "--output", str(raster), str(source)])
            bounds = Image.open(raster).convert("RGBA").getchannel("A").getbbox()
            collision_cache[source] = None if bounds is None else {
                "x": max(0, bounds[0]*4-4),
                "y": max(0, bounds[1]*4-4),
                "width": min(512, bounds[2]*4+4)-max(0, bounds[0]*4-4),
                "height": min(512, bounds[3]*4+4)-max(0, bounds[1]*4-4),
            }
        bounds = collision_cache[source]
        if bounds:
            layer["collision_bounds"] = bounds
        else:
            layer.pop("collision_bounds", None)
    shutil.rmtree(collision_dir)
    pack["fonts"] = [
        {
            "id": voice,
            "source": f"fonts/sticker-display-v1/{config['source']}",
            "license": f"fonts/sticker-display-v1/{config['license']}",
        }
        for voice, config in FONT_VOICES.items()
    ]
    pack["text_styles"] = {
        f"caption-{voice}": {
            "font": voice,
            "safe_area": {"x": 36, "y": 400, "width": 440, "height": 84},
            "min_font_size": config["min_size"],
            "max_font_size": config["max_size"],
            "max_lines": 2,
            "fill": {"r": 255, "g": 255, "b": 255},
            "outline": {
                "width": 5,
                "color": {"r": 22, "g": 43, "b": 69},
            },
        }
        for voice, config in FONT_VOICES.items()
    }
    pack["text_slots"] = {
        "bottom": {"x": 24, "y": 404, "width": 464, "height": 84},
        "top": {"x": 24, "y": 24, "width": 464, "height": 84},
        "left": {"x": 24, "y": 144, "width": 184, "height": 176},
        "right": {"x": 304, "y": 144, "width": 184, "height": 176},
    }
    pack["text_clearance"] = 14
    pack["caption_validation"] = {
        "minimum_canvas_margin_px": 16,
        "maximum_lines": 2,
        "must_remain_inside_canvas_for_every_frame": True,
        "may_overlap_character": False,
        "may_overlap_assistive_device": False,
        "must_pass_sizes_px": [80, 96, 100],
        "collision_bounds": "union-of-rasterized-semantic-layer-bounds-across-animation",
    }
    write_json(pack_path, pack)
    return pack_path


def animation_track(
    target: str,
    property_name: str,
    duration_ms: int,
    values: tuple[tuple[int, float, str], ...],
) -> dict[str, Any]:
    return {
        "target": target,
        "property": property_name,
        "keyframes": [
            {"at_ms": at_ms, "value": value, "easing": easing}
            for at_ms, value, easing in values
        ],
    }


def animation_document(phrase_value: dict[str, Any]) -> dict[str, Any]:
    motion = str(phrase_value["motion"])
    pose = str(phrase_value["pose"])
    duration = {
        "calm": 1200,
        "wave": 900,
        "farewell": 900,
        "laugh": 800,
        "nod": 700,
        "shake": 700,
        "think": 900,
        "shock": 800,
        "celebrate": 850,
        "gratitude": 900,
        "apology": 1000,
        "love": 900,
        "dramatic": 800,
        "plead": 900,
    }[motion]
    tracks: list[dict[str, Any]] = []
    if motion == "calm":
        tracks.append(animation_track("head", "translate_y", duration, ((0, 0, "ease_in_out"), (600, -7, "ease_in_out"), (1200, 0, "ease_in_out"))))
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (600, -3, "ease_in_out"), (1200, 0, "ease_in_out"))))
    elif motion in {"wave", "farewell"}:
        side = "right" if motion == "wave" else "left"
        target = f"arm-{side}-{pose}"
        tracks.append(animation_track(target, "rotation_degrees", duration, ((0, 0, "ease_in_out"), (300, -10, "ease_out"), (600, 10, "ease_in_out"), (900, 0, "ease_in_out"))))
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (450, -4, "ease_in_out"), (900, 0, "ease_in_out"))))
    elif motion == "laugh":
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (200, -5, "ease_out"), (400, 4, "ease_in_out"), (600, -3, "ease_in_out"), (800, 0, "ease_in_out"))))
        tracks.append(animation_track(f"arm-left-{pose}", "translate_y", duration, ((0, 0, "ease_in_out"), (400, -8, "ease_out"), (800, 0, "ease_in_out"))))
    elif motion == "nod":
        tracks.append(animation_track("head", "translate_y", duration, ((0, 0, "ease_in_out"), (230, 8, "ease_out"), (460, -2, "ease_in_out"), (700, 0, "ease_in_out"))))
    elif motion == "shake":
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (175, -10, "ease_out"), (350, 10, "ease_in_out"), (525, -6, "ease_in_out"), (700, 0, "ease_in_out"))))
    elif motion == "think":
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (450, -7, "ease_in_out"), (900, 0, "ease_in_out"))))
    elif motion == "shock":
        tracks.append(animation_track("head", "scale_x", duration, ((0, 1, "ease_in_out"), (220, 1.08, "back_out"), (800, 1, "ease_in_out"))))
        tracks.append(animation_track("head", "scale_y", duration, ((0, 1, "ease_in_out"), (220, 1.08, "back_out"), (800, 1, "ease_in_out"))))
    elif motion == "celebrate":
        tracks.append(animation_track(f"arm-left-{pose}", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (300, -7, "ease_out"), (600, 5, "ease_in_out"), (850, 0, "ease_in_out"))))
        tracks.append(animation_track(f"arm-right-{pose}", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (300, 7, "ease_out"), (600, -5, "ease_in_out"), (850, 0, "ease_in_out"))))
    elif motion in {"gratitude", "apology"}:
        bend = 6 if motion == "gratitude" else 9
        middle = 360 if motion == "gratitude" else 400
        hold = 540 if motion == "gratitude" else 650
        tracks.append(animation_track("head", "rotation_degrees", duration, ((0, 0, "ease_in_out"), (middle, bend, "ease_in_out"), (hold, bend, "linear"), (duration, 0, "ease_in_out"))))
    elif motion == "love":
        tracks.append(animation_track("head", "scale_x", duration, ((0, 1, "ease_in_out"), (300, 1.05, "ease_out"), (900, 1, "ease_in_out"))))
        tracks.append(animation_track("head", "scale_y", duration, ((0, 1, "ease_in_out"), (300, 1.05, "ease_out"), (900, 1, "ease_in_out"))))
    elif motion == "dramatic":
        tracks.append(animation_track("head", "translate_x", duration, ((0, 0, "ease_in_out"), (200, -8, "ease_out"), (400, 8, "ease_in_out"), (600, -5, "ease_in_out"), (800, 0, "ease_in_out"))))
    elif motion == "plead":
        tracks.append(animation_track(f"arm-left-{pose}", "translate_y", duration, ((0, 0, "ease_in_out"), (450, -5, "ease_in_out"), (900, 0, "ease_in_out"))))
        tracks.append(animation_track(f"arm-right-{pose}", "translate_y", duration, ((0, 0, "ease_in_out"), (450, -5, "ease_in_out"), (900, 0, "ease_in_out"))))
    else:
        raise ValueError(f"unknown motion recipe: {motion}")
    animation: dict[str, Any] = {
        "duration_ms": duration,
        "fps": 10,
        "loop": "loop",
        "tracks": tracks,
    }
    voice = caption_voice(phrase_value)
    animation["overlays"] = [str(FONT_VOICES[voice]["motion"])]
    return animation


def sticker_document(master_id: str, pack_id: str, phrase: dict[str, Any]) -> dict[str, Any]:
    base_layout = str(phrase["layout"])
    layout = CAPTION_LAYOUTS[
        (CAPTION_LAYOUTS.index(base_layout) + MASTER_IDS.index(master_id))
        % len(CAPTION_LAYOUTS)
    ]
    side_layout = layout in {"left", "right"}
    framing = str(phrase["framing"])
    base_zoom = {
        "face-closeup": 1.12,
        "bust": 1.06,
        "three-quarter": 0.96,
        "full-body": 0.94,
        "dynamic-full-body": 0.92,
    }[framing]
    identity_scale = 0.90 if master_id in {"H06", "H13"} else 1.0
    zoom = max(0.5, base_zoom * (0.58 if side_layout else 0.64) * identity_scale)
    voice = caption_voice(phrase)
    offset_x = 112 if layout == "left" else -112 if layout == "right" else 0
    preferred = {
        "top": ["top", "bottom", "left", "right"],
        "bottom": ["bottom", "top", "right", "left"],
        "left": ["left", "top", "bottom", "right"],
        "right": ["right", "top", "bottom", "left"],
    }[layout]
    sticker: dict[str, Any] = {
        "schema_version": 1,
        "sticker_id": f"human-canonical-{master_id.lower()}-{phrase['slug']}",
        "pack_id": pack_id,
        "phrase_id": phrase_id(phrase),
        "recipe_id": f"human.{phrase['motion']}",
        "alt_text": f"{master_id} {phrase['accessible_tone']} saying {phrase['text']}",
        "intent": phrase["intent"],
        "pose_implementation": phrase["pose"],
        "audience_class": phrase["audience_class"],
        "accessible_description": f"{master_id} {phrase['accessible_tone']} saying {phrase['text']}",
        "expression": phrase["expression"],
        "pose": phrase["pose"],
        "seed": 1,
        "camera": {
            "framing": framing,
            "target": "body_center",
            "zoom": round(zoom, 3),
            "offset_x": offset_x,
            "offset_y": 70 if layout == "top" else -50 if layout == "bottom" else 0,
        },
        "text": {
            "content": phrase["text"],
            "style": f"caption-{voice}",
            "placement": "auto",
            "preferred_slots": preferred,
        },
        "animation": animation_document(phrase),
    }
    return sticker


def render(
    executable: Path,
    pack: Path,
    sticker: Path,
    output: Path,
    width: int,
    height: int,
    first_frame_only: bool,
) -> None:
    command = [
        str(executable), "render",
        "--pack", str(pack),
        "--sticker", str(sticker),
        "--output", str(output),
        "--width", str(width),
        "--height", str(height),
        "--quality", "100",
        "--lossless",
    ]
    if first_frame_only:
        command.append("--first-frame-only")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(command)


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


def build(args: argparse.Namespace, staging: Path) -> None:
    base_bundle = args.base_bundle.resolve()
    review_root = args.review.resolve()
    masters_root = args.masters.resolve()
    wave2_masters_root = args.wave2_masters.resolve()
    executable = args.mascotrender.resolve()
    selected_master_ids = tuple(args.only_master) if args.only_master else MASTER_IDS
    if not selected_master_ids or any(value not in MASTER_IDS for value in selected_master_ids) or len(set(selected_master_ids)) != len(selected_master_ids):
        raise ValueError("--only-master values must be unique canonical H01-H15 IDs")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError(f"mascotrender executable is unavailable: {executable}")
    review = verify_approved_review(review_root)
    wave2_approval = verify_wave2_owner_approval(args.wave2_approved_review.resolve())
    font_manifest = verify_font_set()

    base_catalogue = read_json(base_bundle / "catalogue.json")
    base_dictionary = read_json(base_bundle / "dictionary.json")
    shutil.copytree(base_bundle, staging, dirs_exist_ok=True)
    policy_root = staging / "content"
    policy_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "content" / "human-character-selection-v1.json", policy_root / "human-character-selection-v1.json")
    shutil.copyfile(ROOT / "content" / "human-phrase-eligibility-v1.json", policy_root / "human-phrase-eligibility-v1.json")
    catalogue = [dict(item) for item in base_catalogue.get("stickers", [])]
    catalogue_by_sticker_id: dict[str, dict[str, Any]] = {}
    for record in catalogue:
        sticker_id = str(record["sticker_id"])
        record["phrase_id"] = str(record.get("phrase_id") or infer_phrase_id(sticker_id))
        record["content_status"] = "public-release"
        add_reduced_motion_asset(staging, record)
        catalogue_by_sticker_id[sticker_id] = record

    entries: dict[str, set[str]] = {}
    for entry in base_dictionary.get("entries", []):
        trigger = str(entry["trigger"])
        phrase_ids = entries.setdefault(trigger, set())
        semantic_ids = entry.get("phrase_ids")
        if isinstance(semantic_ids, list):
            phrase_ids.update(str(value) for value in semantic_ids)
        else:
            for reference in entry.get("stickers", []):
                sticker_id = str(reference["sticker_id"])
                record = catalogue_by_sticker_id.get(sticker_id)
                if record is None:
                    raise ValueError(
                        f"base dictionary references unknown sticker {sticker_id}"
                    )
                phrase_ids.add(str(record["phrase_id"]))

    authoring_root = staging.parent / f"{staging.name}.human-input"
    try:
        for master_id in selected_master_ids:
            source_root = masters_root if master_id in FOUNDATION_IDS else wave2_masters_root
            pack_path = prepare_pack(
                source_root / master_id,
                authoring_root / master_id,
            )
            pack = read_json(pack_path)
            pack_id = str(pack["pack_id"])
            for phrase in PHRASES:
                sticker = sticker_document(master_id, pack_id, phrase)
                sticker_path = authoring_root / master_id / "stickers" / "wahalao-dev" / f"{phrase['slug']}.json"
                write_json(sticker_path, sticker)
                run([str(executable), "validate", "--pack", str(pack_path), "--sticker", str(sticker_path)])

                thumbnail_sticker = dict(sticker)
                thumbnail_sticker.pop("animation", None)
                thumbnail_sticker_path = sticker_path.with_name(f"{phrase['slug']}.thumbnail.json")
                write_json(thumbnail_sticker_path, thumbnail_sticker)
                run([str(executable), "validate", "--pack", str(pack_path), "--sticker", str(thumbnail_sticker_path)])

                sticker_id = str(sticker["sticker_id"])
                asset_relative = Path("assets") / pack_id / f"{sticker_id}.webp"
                thumbnail_relative = Path("thumbnails") / pack_id / f"{sticker_id}.webp"
                reduced_relative = Path("reduced-motion") / pack_id / f"{sticker_id}.webp"
                asset = staging / asset_relative
                thumbnail = staging / thumbnail_relative
                reduced = staging / reduced_relative
                render(executable, pack_path, sticker_path, asset, 512, 512, False)
                render(executable, pack_path, thumbnail_sticker_path, thumbnail, 256, 256, False)
                render(executable, pack_path, thumbnail_sticker_path, reduced, 512, 512, False)

                animated = isinstance(sticker.get("animation"), dict)
                catalogue.append({
                    "pack_id": pack_id,
                    "sticker_id": sticker_id,
                    "text": phrase["text"],
                    "alt_text": sticker["alt_text"],
                    "phrase_id": sticker["phrase_id"],
                    "recipe_id": sticker["recipe_id"],
                    "expression": sticker["expression"],
                    "pose": sticker["pose"],
                    "intent": sticker["intent"],
                    "pose_implementation": sticker["pose_implementation"],
                    "audience_class": sticker["audience_class"],
                    "accessible_description": sticker["accessible_description"],
                    "camera": sticker["camera"],
                    "caption_layout": sticker["text"]["preferred_slots"][0],
                    "font_voice": caption_voice(phrase),
                    "caption_motion": FONT_VOICES[caption_voice(phrase)]["motion"],
                    "seed": 1,
                    "animated": animated,
                    "animation": sticker.get("animation"),
                    "media_type": "image/webp",
                    "width": 512,
                    "height": 512,
                    "path": asset_relative.as_posix(),
                    "sha256": sha256_file(asset),
                    "encoded_bytes": asset.stat().st_size,
                    "thumbnail": {
                        "width": 256,
                        "height": 256,
                        "path": thumbnail_relative.as_posix(),
                        "sha256": sha256_file(thumbnail),
                        "encoded_bytes": thumbnail.stat().st_size,
                    },
                    "reduced_motion": {
                        "presentation": "static-semantic-equivalent",
                        "width": 512,
                        "height": 512,
                        "path": reduced_relative.as_posix(),
                        "sha256": sha256_file(reduced),
                        "encoded_bytes": reduced.stat().st_size,
                    },
                    "content_status": "public-release",
                    "approved_identity_source": master_id,
                })
                for trigger in phrase["triggers"]:
                    entries.setdefault(str(trigger), set()).add(str(sticker["phrase_id"]))
    finally:
        if authoring_root.exists():
            shutil.rmtree(authoring_root)

    catalogue.sort(key=lambda item: (str(item["pack_id"]), str(item["sticker_id"])))
    dictionary_entries = [
        {
            "trigger": trigger,
            "match": "unicode-word-boundary",
            "phrase_ids": sorted(items),
        }
        for trigger, items in sorted(entries.items())
    ]
    source_digest = hashlib.sha256()
    source_digest.update(str(base_catalogue.get("source_sha256", "")).encode("utf-8"))
    source_digest.update(sha256_file(review_root / "release-review.json").encode("ascii"))
    source_digest.update(json.dumps(PHRASES, sort_keys=True).encode("utf-8"))
    source_digest.update(sha256_file(ROOT / "content" / "human-phrase-eligibility-v1.json").encode("ascii"))
    source_digest.update(sha256_file(ROOT / "contracts" / "human-canonical-expansion-wave2-owner-approval.json").encode("ascii"))
    source_digest.update(sha256_file(ROOT / "contracts" / "human-wave2-production-activation-v1.json").encode("ascii"))
    source_digest.update(sha256_file(FONT_SET_ROOT / "manifest.json").encode("ascii"))
    generator_sha256 = sha256_file(Path(__file__).resolve())
    source_digest.update(generator_sha256.encode("ascii"))

    animated_count = sum(1 for sticker in catalogue if sticker.get("animated") is True)
    write_json(staging / "catalogue.json", {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "bundle_version": BUNDLE_VERSION,
        "source_sha256": source_digest.hexdigest(),
        "sticker_count": len(catalogue),
        "animated_sticker_count": animated_count,
        "stickers": catalogue,
    })
    write_json(staging / "dictionary.json", {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "matching": MATCHING,
        "human_selection_policy": "human-uniform-deterministic-rotation-v1",
        "human_selection_policy_path": "content/human-character-selection-v1.json",
        "human_selection_eligibility_field": "production_eligible",
        "demographic_inference": False,
        "trigger_count": len(dictionary_entries),
        "entries": dictionary_entries,
    })
    total_bytes = sum(path.stat().st_size for path in staging.rglob("*.webp"))
    write_json(staging / "build-report.json", {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "status": "success",
        "content_status": "public-release",
        "base_bundle_version": base_catalogue.get("bundle_version"),
        "bundle_version": BUNDLE_VERSION,
        "pack_count": len({str(item["pack_id"]) for item in catalogue}),
        "human_pack_count": len(selected_master_ids),
        "human_phrase_count": len(PHRASES),
        "human_sticker_count": len(selected_master_ids) * len(PHRASES),
        "human_animated_sticker_count": len(selected_master_ids) * len(PHRASES),
        "caption_layouts": sorted({str(phrase_value["layout"]) for phrase_value in PHRASES}),
        "caption_validation": {
            "mode": "strict-animation-aware-semantic-layer-union",
            "minimum_canvas_margin_px": 16,
            "may_overlap_character": False,
            "may_overlap_assistive_device": False,
            "small_size_review_px": [80, 96, 100],
        },
        "semantic_metadata": {
            "apology_intent": "chat.sorry",
            "affection_intent": "chat.love",
            "pose_implementation_is_explicit": True,
            "accessible_description_is_required": True,
        },
        "font_voices": sorted(FONT_VOICES),
        "caption_motions": sorted({str(value["motion"]) for value in FONT_VOICES.values()}),
        "font_manifest_sha256": sha256_file(FONT_SET_ROOT / "manifest.json"),
        "font_upstream_revision": font_manifest.get("upstream_revision"),
        "generator_sha256": generator_sha256,
        "motion_recipes": sorted({str(phrase_value["motion"]) for phrase_value in PHRASES}),
        "camera_framings": sorted({str(phrase_value["framing"]) for phrase_value in PHRASES}),
        "sticker_count": len(catalogue),
        "animated_sticker_count": animated_count,
        "asset_count": len(catalogue) * 3,
        "reduced_motion_sticker_count": len(catalogue),
        "encoded_bytes": total_bytes,
        "human_review_status": review.get("review_status"),
        "human_review_sha256": sha256_file(review_root / "release-review.json"),
        "wave2_vector_review_status": wave2_approval.get("review_status"),
        "wave2_production_use": wave2_approval.get("production_use"),
        "wave2_activation_decision": wave2_approval.get("activation_decision"),
        "wave2_owner_approval_sha256": sha256_file(ROOT / "contracts" / "human-canonical-expansion-wave2-owner-approval.json"),
        "wave2_production_activation_sha256": sha256_file(ROOT / "contracts" / "human-wave2-production-activation-v1.json"),
        "phrase_eligibility_sha256": sha256_file(ROOT / "content" / "human-phrase-eligibility-v1.json"),
        "render": {
            "width": 512,
            "height": 512,
            "thumbnail_size": 256,
            "webp_quality": 100,
            "lossless": True,
        },
    })


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-bundle", type=Path, default=ROOT / "generated" / "bundle")
    parser.add_argument("--review", type=Path, default=ROOT / "generated" / "canonical-human-production-review")
    parser.add_argument("--masters", type=Path, default=ROOT / "art" / "human-pack-v1" / "masters")
    parser.add_argument("--wave2-masters", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--wave2-approved-review", type=Path, default=ROOT / "generated" / "human-wave2-review")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "wahalao-human-dev-bundle")
    parser.add_argument("--only-master", action="append", choices=MASTER_IDS, help="Build only the selected canonical master; repeat for a focused validation build")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        build(args, staging)
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    report = read_json(destination / "build-report.json")
    print(
        f"built local Wahalao development bundle with {report['sticker_count']} stickers "
        f"({report['animated_sticker_count']} animated) at {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
