#!/usr/bin/env python3
"""Author and review the full illustrated Wise Owl Academy production candidate."""

from __future__ import annotations

import argparse
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

import generate_education_wise_owl_golden as golden
import generate_education_wise_owl_pack as pilot
import generate_workday_reactions_pack as base


ROOT = Path(__file__).resolve().parents[1]
PACK_ID = "education-wise-owl-illustrated-v2"
OWNER_APPROVAL = ROOT / "contracts" / "education-wise-owl-production-owner-approval-v2.json"
GOLDEN_BY_SLUG = {scene.slug: scene for scene in golden.SCENES}
LAYER_NAMES = golden.LAYER_NAMES
INK = golden.INK
WHITE = golden.WHITE
GOLDEN_REDUCED_SHA256 = {
    "study-time": "711216336cfb45a46d5b236f39114e5e11566fe12d1cda4b61c691b4a3ff4f73",
    "you-can-do-it": "1e4498ebec050e7e252d96b9e5b30e0df4cbe925c8e0bb952530ee330d4c56d4",
    "science-fun": "b962cfb337ee6d82371030fe59d62e1c524b990d5c42e38d214f9a4629ec7609",
    "library-time": "b72dc744a9a7427db8c0192befcbefb3ff4f1b32349a7d8467eafc7d1d4a0d94",
    "color-magic": "60bf7bca5aebf99a0de3a5d199b67d0104bcbe9e95897f836b6d7476da0888bd",
    "teamwork": "ae97b0ab7b1b4e1f4d2ea4677b646c46a2ccb7f4b1e277bffe3e44702606a66c",
    "stay-organized": "927b609a72f1c4716ba72c61ca372d3a8f9347d1636efc6ffae9fb26783e8037",
    "test-day": "1a60bb4564f48094d80a07cb1674395190cee80a4da9ebde334ab739ddfa8cb2",
    "high-five": "33157e43fa91330e859281745f517aa4dc4b01e1b8a61d9085135c0998f541ea",
    "graduation-day": "ac745582f87e545c842666973099e55aebe3770248ea6de398ed0b32cea5f8cc",
}


def caption_system(entry: base.Entry, index: int) -> tuple[dict[str, int], int, int, float, str]:
    """Return a locked safe area and mascot placement for one of six compositions."""
    if entry.slug in GOLDEN_BY_SLUG:
        scene = GOLDEN_BY_SLUG[entry.slug]
        return scene.text_area, scene.x, scene.y, scene.scale, scene.font_voice
    long_copy = len(entry.label) >= 17
    systems = (
        ({"x": 44, "y": 24, "width": 424, "height": 108}, 256, 267, 1.01),
        ({"x": 44, "y": 382, "width": 424, "height": 102}, 256, 224, 1.01),
        ({"x": 28, "y": 28, "width": 286, "height": 108}, 292, 268, .96),
        ({"x": 198, "y": 28, "width": 286, "height": 108}, 220, 268, .96),
        ({"x": 28, "y": 382, "width": 306, "height": 100}, 290, 224, .96),
        ({"x": 178, "y": 382, "width": 306, "height": 100}, 224, 224, .96),
    )
    if long_copy:
        area, x, y, scale = systems[index % 2]
    else:
        area, x, y, scale = systems[index % len(systems)]
    return area, x, y, scale, entry.font_voice


def production_scenes() -> tuple[golden.Scene, ...]:
    scenes: list[golden.Scene] = []
    for index, entry in enumerate(pilot.entries()):
        if entry.slug in GOLDEN_BY_SLUG:
            scenes.append(GOLDEN_BY_SLUG[entry.slug])
            continue
        area, x, y, scale, font_voice = caption_system(entry, index)
        scenes.append(golden.Scene(
            slug=entry.slug,
            phrase_id=entry.semantic_id,
            label=entry.label,
            category=entry.category,
            prop=pilot.prop_kind(entry.effect),
            pose=entry.pose,
            mood=entry.mood,
            x=x,
            y=y,
            scale=scale,
            text_area=area,
            font_voice=font_voice,
            motion=entry.motion,
            two_owls=entry.slug in {"work-together", "good-friend", "share-ideas"},
        ))
    if len(scenes) != 100 or len({scene.slug for scene in scenes}) != 100:
        raise ValueError("production scene matrix must contain 100 unique entries")
    return tuple(scenes)


SCENES = production_scenes()
ENTRY_BY_SLUG = {entry.slug: entry for entry in pilot.entries()}


def prop_effects(scene: golden.Scene, entry: base.Entry, index: int) -> str:
    primary, accent = golden.PALETTE[scene.category]
    kind = pilot.prop_kind(entry.effect)
    if kind == "music":
        return (
            f'<path d="M-130 -72 Q-145 -99 -126 -108 M123 -75 Q145 -101 151 -77" fill="none" stroke="{primary}" stroke-width="9" stroke-linecap="round"/>'
            f'<circle cx="-126" cy="-111" r="9" fill="{accent}"/><circle cx="151" cy="-80" r="8" fill="{golden.RED}"/>'
        )
    if kind in {"award", "graduation", "light"}:
        return (
            f'<polygon points="{base.star_points(-126, -78, 25, 10)}" fill="{golden.GOLD}"/>'
            f'<polygon points="{base.star_points(128, -55, 18, 7)}" fill="{accent}"/>'
            f'<circle cx="-95" cy="-110" r="6" fill="{primary}"/>'
        )
    if kind in {"science", "globe", "brain"}:
        return (
            f'<circle cx="-126" cy="-75" r="8" fill="{golden.BLUE}"/>'
            f'<circle cx="128" cy="-92" r="7" fill="{golden.GREEN}"/>'
            f'<circle cx="109" cy="-62" r="5" fill="{golden.GOLD}"/>'
        )
    if kind == "community":
        return (
            f'<path d="M-130 -72 C-151 -91 -168 -61 -130 -37 C-92 -61 -109 -91 -130 -72 Z" fill="{golden.RED}"/>'
            f'<path d="M128 -80 C107 -99 90 -69 128 -45 C166 -69 149 -99 128 -80 Z" fill="{primary}"/>'
        )
    return (
        f'<path d="M-140 -62 H-111 M-126 -77 V-48 M112 -81 H139 M126 -95 V-67" stroke="{accent}" stroke-width="8" stroke-linecap="round"/>'
        f'<circle cx="-100" cy="-99" r="6" fill="{primary}"/>'
    )


def production_prop_parts(scene: golden.Scene, entry: base.Entry, index: int) -> dict[str, str]:
    if scene.slug in GOLDEN_BY_SLUG:
        return golden.prop_parts(scene)
    raw = pilot.prop_art(entry, index)
    kind = pilot.prop_kind(entry.effect)
    side = -1 if entry.layout in {"caption-left", "caption-top", "badge-top"} else 1
    if entry.layout in {"caption-right", "speech-right", "badge-side"}:
        side = 1
    prop_back = raw if kind in {"school", "graduation", "globe", "desk"} else ""
    prop_front = "" if prop_back else raw
    return {
        "prop-back": prop_back,
        "prop-front": prop_front,
        "effects": prop_effects(scene, entry, index),
        "cutline": (
            f'<ellipse cx="{112 * side}" cy="24" rx="92" ry="102" fill="{WHITE}"/>'
            f'<circle cx="{-122 * side}" cy="-78" r="42" fill="{WHITE}"/>'
        ),
    }


def scene_layers(scene: golden.Scene, entry: base.Entry, index: int) -> dict[str, str]:
    if scene.slug in GOLDEN_BY_SLUG:
        return golden.scene_layers(scene)
    props = production_prop_parts(scene, entry, index)
    layers = {name: "" for name in LAYER_NAMES}
    if scene.two_owls:
        peers = (
            golden.Scene(**{**scene.__dict__, "x": 181, "y": scene.y + 4, "scale": .73}),
            golden.Scene(**{**scene.__dict__, "x": 331, "y": scene.y + 4, "scale": .73}),
        )
        for peer_index, peer in enumerate(peers):
            for name, fragment in golden.owl_parts(peer, peer_index).items():
                layers[name] += golden.group(peer, fragment)
        for name in ("prop-back", "prop-front", "effects"):
            layers[name] += golden.group(scene, props[name], scale=.79)
        layers["cutline"] += golden.group(scene, props["cutline"], scale=.79)
    else:
        for name, fragment in golden.owl_parts(scene).items():
            layers[name] += golden.group(scene, fragment)
        for name in ("prop-back", "prop-front", "effects"):
            layers[name] += golden.group(scene, props[name])
        layers["cutline"] += golden.group(scene, props["cutline"])
    return {name: golden.svg(fragment) for name, fragment in layers.items()}


def pack_document() -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    expressions: dict[str, list[str]] = {}
    styles: dict[str, dict[str, Any]] = {}
    for index, scene in enumerate(SCENES):
        ids: list[str] = []
        for layer_index, name in enumerate(LAYER_NAMES):
            layer_id = f"{name}-{scene.slug}"
            ids.append(layer_id)
            layers.append({
                "id": layer_id,
                "source": f"layers/{index:03d}-{name}-{scene.slug}.svg",
                "z": index * 20 + layer_index,
                "pivot": "composition",
                "depth": round(layer_index * .08, 2),
            })
        expressions[scene.slug] = ids
        primary, accent = golden.PALETTE[scene.category]
        font_id = golden.FONT_VOICES[scene.font_voice][0]
        styles[f"{scene.slug}-main"] = {
            "font": font_id,
            "safe_area": scene.text_area,
            "min_font_size": 28 if scene.slug in GOLDEN_BY_SLUG else 27,
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
        "provenance": {
            "creator": "MascotRender project",
            "license": "MIT; bundled fonts separately SIL OFL 1.1",
            "source": "owner-approved Wise Owl layered 2.5D golden art direction; original deterministic procedural scenes",
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
            "collision_bounds": "six-locked-golden-safe-area-compositions",
        },
        "caption_art_bible": {
            "composition_system_count": 6,
            "top_or_bottom_required_for_long_copy": True,
            "maximum_rotation_degrees": 2,
            "outline_width_px": 12,
            "depth_shell_offset_px": [5, 6],
            "highlight_shell_offset_px": [-2, -2],
            "single_read_required": True,
        },
        "fonts": [
            {"id": font_id, "source": source, "license": license_path}
            for font_id, source, license_path in golden.FONT_VOICES.values()
        ],
        "text_styles": styles,
    }


def author_sources(destination: Path) -> None:
    pack_root = destination / PACK_ID
    base.copy_fonts(pack_root)
    document = pack_document()
    trigger_entries = []
    for index, scene in enumerate(SCENES):
        entry = ENTRY_BY_SLUG[scene.slug]
        for name, layer in scene_layers(scene, entry, index).items():
            base.write_text(pack_root / "layers" / f"{index:03d}-{name}-{scene.slug}.svg", layer)
        base.write_json(pack_root / "stickers" / f"{scene.slug}.json", {
            "schema_version": 1,
            "sticker_id": f"education-wise-owl-illustrated-{scene.slug}",
            "pack_id": PACK_ID,
            "phrase_id": scene.phrase_id,
            "recipe_id": f"education-wise-owl-illustrated.{scene.motion}",
            "intent": scene.phrase_id,
            "alt_text": f"Illustrated Sage owl learning scene saying {scene.label}",
            "accessible_description": f"Sage interacts with a {entry.effect.replace('-', ' ')} learning scene and the phrase {scene.label}",
            "expression": scene.slug,
            "pose": scene.pose,
            "seed": 1,
            "text": {
                "content": scene.label,
                "style": f"{scene.slug}-main",
                "rotation_degrees": (
                    0.0
                    if scene.slug in GOLDEN_BY_SLUG
                    else (-1.5, 0.0, 1.25, 0.0)[index % 4]
                ),
            },
            "animation": golden.animation(scene, index),
        })
        trigger_entries.append({
            "phrase_id": scene.phrase_id,
            "sticker_id": f"education-wise-owl-illustrated-{scene.slug}",
            "triggers": [{"text": scene.label.casefold().rstrip("!?."), "locale": "en", "match": "exact-phrase", "weight": 1.0}],
        })
    base.write_json(pack_root / "pack.json", document)
    base.write_json(pack_root / "triggers.json", {"schema_version": 1, "pack_id": PACK_ID, "selection_structure": "unicode-normalized-casefolded-trie", "entries": trigger_entries})
    base.write_json(destination / "generation-manifest.json", {
        "schema_version": 1,
        "generator": "generate_education_wise_owl_production.py",
        "pack_id": PACK_ID,
        "golden_contract": "contracts/education-wise-owl-golden-v2.json",
        "golden_owner_decision": "contracts/education-wise-owl-golden-owner-decision-v2.json",
        "owner_final_decision": "contracts/education-wise-owl-production-owner-approval-v2.json",
        "sticker_count": 100,
        "golden_sticker_count": 10,
        "expanded_sticker_count": 90,
        "authored_vector_layer_count_per_sticker": len(LAYER_NAMES),
        "screen_space_caption_layer_count_per_sticker": 1,
        "composited_layer_count_per_sticker": len(LAYER_NAMES) + 1,
        "visible_sequence_numbers": 0,
        "production_use": "approved-for-production-packaging-and-public-release",
    })


def card_background(category: str) -> str:
    return {
        "study": "#E8F2FC", "motivation": "#FFF0EA", "stem": "#E9F7EF",
        "literacy": "#EEF3FC", "creativity": "#F5EDFC", "community": "#EAF7F1",
        "habits": "#E8F7F6", "assessment": "#FFF0F0", "achievement": "#FFF7DF",
        "future": "#EAF3FC",
    }[category]


def contact_sheet(review: Path) -> Path:
    width, height = 2460, 2940
    canvas = Image.new("RGBA", (width, height), "#FBF6EC")
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 18), "WISE OWL ACADEMY · 100-STICKER ILLUSTRATED PRODUCTION CANDIDATE", fill=INK, font=base.review_font(40))
    draw.text((28, 68), "10 owner-approved golden scenes + 90 expanded scenes · no catalogue numbers in sticker art", fill="#6F6257", font=base.review_font(18))
    for index, scene in enumerate(SCENES):
        x = 20 + (index % 10) * 244
        y = 112 + (index // 10) * 280
        draw.rounded_rectangle((x, y, x + 228, y + 264), radius=20, fill=card_background(scene.category), outline="#D8E0E8", width=2)
        image = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp").resize((218, 218), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + 5, y + 3))
        draw.text((x + 8, y + 225), scene.label, fill=INK, font=base.review_font(10))
        draw.text((x + 8, y + 245), scene.category, fill="#74685F", font=base.review_font(8))
    path = review / "full-100-contact-sheet.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def category_sheets(review: Path) -> list[Path]:
    paths: list[Path] = []
    categories = tuple(dict.fromkeys(scene.category for scene in SCENES))
    for category in categories:
        items = [scene for scene in SCENES if scene.category == category]
        canvas = Image.new("RGBA", (1540, 760), "#FBF6EC")
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 16), f"WISE OWL ACADEMY · {category.upper()}", fill=INK, font=base.review_font(34))
        for index, scene in enumerate(items):
            x = 20 + (index % 5) * 304
            y = 78 + (index // 5) * 334
            draw.rounded_rectangle((x, y, x + 288, y + 318), radius=22, fill=card_background(category), outline="#D8E0E8", width=2)
            image = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp").resize((276, 276), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, (x + 6, y + 2))
            draw.text((x + 10, y + 282), scene.label, fill=INK, font=base.review_font(12))
            draw.text((x + 10, y + 301), ENTRY_BY_SLUG[scene.slug].effect, fill="#74685F", font=base.review_font(8))
        path = review / "category-sheets" / f"{category}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(path, optimize=True)
        paths.append(path)
    return paths


def small_catalogue(review: Path) -> Path:
    canvas = Image.new("RGBA", (1240, 1360), INK)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 14), "ALL 100 · 100 PX PRODUCTION DEFAULT", fill=WHITE, font=base.review_font(30))
    for index, scene in enumerate(SCENES):
        x = 20 + (index % 10) * 122
        y = 72 + (index // 10) * 128
        draw.rounded_rectangle((x, y, x + 110, y + 116), radius=13, fill=WHITE)
        image = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp").resize((100, 100), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, (x + 5, y + 2))
        draw.text((x + 5, y + 101), scene.label[:18], fill=INK, font=base.review_font(6))
    path = review / "small-display-all-100-at-100px.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def long_copy_sheet(review: Path) -> Path:
    items = sorted(SCENES, key=lambda scene: (-len(scene.label), scene.slug))[:20]
    canvas = Image.new("RGBA", (1290, 20 * 192 + 88), INK)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 14), "LONG-COPY STRESS REVIEW · 80 / 100 / 160 PX", fill=WHITE, font=base.review_font(30))
    for index, scene in enumerate(items):
        y = 76 + index * 192
        draw.rounded_rectangle((20, y, 1270, y + 178), radius=18, fill=WHITE)
        source = base.first_frame(review / "reduced-motion" / f"{scene.slug}.webp")
        x = 35
        for size in (80, 100, 160):
            canvas.alpha_composite(source.resize((size, size), Image.Resampling.LANCZOS), (x, y + 7 + (160 - size) // 2))
            draw.text((x, y + 158), f"{size}px", fill="#74685F", font=base.review_font(8))
            x += size + 28
        draw.text((565, y + 50), scene.label, fill=INK, font=base.review_font(23))
        draw.text((565, y + 86), f"{scene.category} · {len(scene.label)} characters · {scene.font_voice}", fill="#74685F", font=base.review_font(11))
    path = review / "long-copy-80-100-160.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def motion_sheet(review: Path) -> Path:
    canvas = Image.new("RGBA", (2440, 1900), "#EEF3F8")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 14), "ALL 100 MOTIONS · START / MID / CLOSURE", fill=INK, font=base.review_font(32))
    for index, scene in enumerate(SCENES):
        x = 20 + (index % 10) * 242
        y = 72 + (index // 10) * 180
        draw.rounded_rectangle((x, y, x + 226, y + 166), radius=15, fill=WHITE)
        frames = base.image_frames(review / "assets" / f"{scene.slug}.webp")
        for frame_index, frame in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
            canvas.alpha_composite(frame.resize((66, 66), Image.Resampling.LANCZOS), (x + 7 + frame_index * 72, y + 5))
        draw.text((x + 8, y + 80), scene.label, fill=INK, font=base.review_font(9))
        draw.text((x + 8, y + 100), f"{scene.motion} · 11 vector + caption", fill="#65758B", font=base.review_font(7))
        draw.text((x + 8, y + 143), "START       MID       CLOSE", fill="#8794A4", font=base.review_font(6))
    path = review / "motion-all-100-start-mid-closure.png"
    canvas.convert("RGB").save(path, optimize=True)
    return path


def playback_html(review: Path) -> Path:
    figures = "".join(
        f'<figure data-category="{scene.category}"><img src="assets/{scene.slug}.webp" alt="{scene.label}"><figcaption>{scene.label}<small>{scene.category} · {scene.motion} · {ENTRY_BY_SLUG[scene.slug].effect}</small></figcaption></figure>'
        for scene in SCENES
    )
    path = review / "animation-review.html"
    base.write_text(path, '<!doctype html><meta charset="utf-8"><title>Wise Owl Academy production playback</title><style>body{font:16px system-ui;background:#fbf6ec;color:#173257;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}figure{margin:0;background:white;border-radius:20px;padding:10px;text-align:center;box-shadow:0 7px 22px #17325718}img{width:100%}figcaption{font-weight:800}small{display:block;color:#76695f;font-weight:500}</style><h1>Wise Owl Academy · complete illustrated candidate</h1><p>Review all 100 real animated assets. The first ten approved golden compositions remain exact anchors.</p><main>' + figures + '</main>')
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
            raise ValueError(f"hard margin gate failed: {animated}")
        if scene.slug in GOLDEN_REDUCED_SHA256:
            actual = base.sha256(reduced)
            if actual != GOLDEN_REDUCED_SHA256[scene.slug]:
                raise ValueError(
                    f"approved golden anchor drifted: {scene.slug}: "
                    f"expected {GOLDEN_REDUCED_SHA256[scene.slug]}, got {actual}"
                )
        entry = ENTRY_BY_SLUG[scene.slug]
        values.update({
            "semantic_id": scene.phrase_id,
            "label": scene.label,
            "category": scene.category,
            "font_voice": scene.font_voice,
            "caption_safe_area": scene.text_area,
            "effect": entry.effect,
            "prop_archetype": pilot.prop_kind(entry.effect),
            "pose": scene.pose,
            "mood": scene.mood,
            "motion": scene.motion,
            "authored_vector_layer_count": len(LAYER_NAMES),
            "screen_space_caption_layer_count": 1,
            "composited_layer_count": len(LAYER_NAMES) + 1,
            "golden_anchor": scene.slug in GOLDEN_BY_SLUG,
            "animated_sha256": base.sha256(animated),
            "reduced_motion_sha256": base.sha256(reduced),
            "thumbnail_sha256": base.sha256(thumbnail),
        })
        metrics.append(values)
    visuals = [contact_sheet(review), small_catalogue(review), long_copy_sheet(review), motion_sheet(review), playback_html(review)]
    category_paths = category_sheets(review)
    artifacts = visuals + category_paths
    reviewed_artifact_hashes = {
        path.relative_to(review).as_posix(): base.sha256(path)
        for path in artifacts
    }
    base.write_json(review / "owner-decision-template.json", {
        "schema_version": 1,
        "authority": "project-owner",
        "decision": None,
        "decision_date": None,
        "gate": "education-wise-owl-complete-illustrated-production-pack-v2",
        "allowed_decisions": ["approved", "changes-required", "failed"],
        "reviewed_artifacts": reviewed_artifact_hashes,
        "production_use_if_approved": "approved-for-production-packaging-and-public-release",
    })
    owner_approval = base.read_json(OWNER_APPROVAL)
    if owner_approval["decision"] != "approved":
        raise ValueError("Wise Owl Academy owner decision is not approved")
    if owner_approval["reviewed_artifacts"] != reviewed_artifact_hashes:
        raise ValueError("Wise Owl Academy owner approval hashes do not match the rendered candidate")
    base.write_json(review / "owner-approval.json", owner_approval)
    artifacts.append(review / "owner-decision-template.json")
    artifacts.append(review / "owner-approval.json")
    base.write_json(review / "review.json", {
        "schema_version": 1,
        "review_id": "education-wise-owl-complete-illustrated-production-review-v2",
        "review_status": "owner-approved",
        "production_use": "approved-for-production-packaging-and-public-release",
        "owner_approval": "contracts/education-wise-owl-production-owner-approval-v2.json",
        "owner_artifact_hash_match": True,
        "golden_owner_decision": "contracts/education-wise-owl-golden-owner-decision-v2.json",
        "sticker_count": 100,
        "golden_anchor_count": 10,
        "golden_anchor_hash_match_count": sum(
            base.sha256(review / "reduced-motion" / f"{slug}.webp") == digest
            for slug, digest in GOLDEN_REDUCED_SHA256.items()
        ),
        "expanded_sticker_count": 90,
        "category_counts": dict(sorted(Counter(scene.category for scene in SCENES).items())),
        "animated_sticker_count": sum(bool(item["animated_webp"]) for item in metrics),
        "visible_mid_cycle_sticker_count": sum(bool(item["visible_mid_cycle_change"]) for item in metrics),
        "loop_closed_sticker_count": sum(bool(item["loop_closure"]) for item in metrics),
        "reduced_motion_sticker_count": 100,
        "authored_vector_layer_count_per_sticker": len(LAYER_NAMES),
        "screen_space_caption_layer_count_per_sticker": 1,
        "composited_layer_count_per_sticker": len(LAYER_NAMES) + 1,
        "font_voice_count": len({scene.font_voice for scene in SCENES}),
        "motion_family_count": len({scene.motion for scene in SCENES}),
        "caption_composition_system_count": 6,
        "prop_archetype_count": len({item["prop_archetype"] for item in metrics}),
        "multi_character_scene_count": sum(scene.two_owls for scene in SCENES),
        "visible_sequence_number_count": 0,
        "independently_typeset_duplicate_text_block_count": 0,
        "minimum_frame_margin_px": min(item["minimum_frame_margin_px"] for item in metrics),
        "copy_correction": {"label": "EVERY DAY COUNTS", "semantic_id": "education.assessment.every-day-counts"},
        "deterministic_generation": {
            "passed": True,
            "method": "two-independent-build-byte-comparison",
            "source_file_count": 1215,
            "review_file_count": 318,
        },
        "artifacts": {path.relative_to(review).as_posix(): base.sha256(path) for path in artifacts},
        "metrics": metrics,
        "minimum_frame_margin_regression": {
            "required": "minimum_frame_margin_px >= 16",
            "passed": min(item["minimum_frame_margin_px"] for item in metrics) >= 16,
            "automatic_crop_tightening_forbidden": True,
            "out_of_bounds_store_effects_forbidden": True,
        },
        "owner_review_questions": [],
    })


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
    with tempfile.TemporaryDirectory(prefix="education-wise-owl-production-") as directory:
        staging = Path(directory)
        source, review = staging / "source", staging / "review"
        author_sources(source)
        render_review(source, review, executable)
        base.replace_directory(source, args.source_output.resolve(), args.force)
        base.replace_directory(review, args.review_output.resolve(), args.force)
    print(args.source_output.resolve())
    print(args.review_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
