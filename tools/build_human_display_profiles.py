#!/usr/bin/env python3
"""Build animation-aware small-display profiles for the human sticker matrix.

The canonical 512x512 WebP assets remain the source of truth.  This tool
derives tray/stress assets by independently reframing the animated mascot
(including assistive devices) and the screen-space caption.  A single fixed
transform is used for each component for the complete animation timeline.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFont

from build_wahalao_human_dev_bundle import (
    FOUNDATION_IDS,
    MASTER_IDS,
    PHRASES,
    ROOT,
    prepare_pack,
    read_json,
    render,
    sticker_document,
    write_json,
)


PROFILE_ORDER = ("stress-80", "tray-96", "tray-100")
SAMPLE_PHRASES = (
    "chat.hello", "chat.haha", "chat.omg", "chat.thanks",
    "chat.sorry", "chat.no.wahala", "chat.well.done", "chat.love",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frames(path: Path) -> tuple[list[Image.Image], list[int], int]:
    source = Image.open(path)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(getattr(source, "n_frames", 1)):
        source.seek(index)
        frames.append(source.convert("RGBA").copy())
        durations.append(int(source.info.get("duration", 100)))
    return frames, durations, int(source.info.get("loop", 0))


def resample_to_timeline(
    frames: list[Image.Image], durations: list[int], target_durations: list[int]
) -> list[Image.Image]:
    if sum(durations) != sum(target_durations):
        raise ValueError(
            f"animation loop durations differ: source={sum(durations)}ms target={sum(target_durations)}ms"
        )
    source_ends: list[int] = []
    elapsed = 0
    for duration in durations:
        elapsed += duration
        source_ends.append(elapsed)
    result: list[Image.Image] = []
    target_time = 0
    source_index = 0
    for duration in target_durations:
        while source_index + 1 < len(source_ends) and target_time >= source_ends[source_index]:
            source_index += 1
        result.append(frames[source_index].copy())
        target_time += duration
    return result


def save_frames(path: Path, frames: list[Image.Image], durations: list[int], loop: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        lossless=True,
        quality=100,
        # Encoder effort changes file size only. Method 0 keeps the complete
        # lossless RGBA timeline while making the 1,845-asset review build fast.
        method=0,
        minimize_size=False,
    )


def alpha_union_bounds(frames: Iterable[Image.Image]) -> tuple[int, int, int, int]:
    union: tuple[int, int, int, int] | None = None
    for frame in frames:
        bounds = frame.getchannel("A").getbbox()
        if bounds is None:
            continue
        if union is None:
            union = bounds
        else:
            union = (
                min(union[0], bounds[0]), min(union[1], bounds[1]),
                max(union[2], bounds[2]), max(union[3], bounds[3]),
            )
    if union is None:
        raise ValueError("component has no visible pixels")
    return union


def extract_components(
    canonical: list[Image.Image], character: list[Image.Image]
) -> tuple[list[Image.Image], list[Image.Image], int]:
    if len(canonical) != len(character):
        raise ValueError(f"frame count mismatch: canonical={len(canonical)}, character={len(character)}")
    captions: list[Image.Image] = []
    overlap_pixels = 0
    for final_frame, character_frame in zip(canonical, character):
        final_alpha = final_frame.getchannel("A")
        character_alpha = character_frame.getchannel("A")
        caption_alpha = ImageChops.subtract(final_alpha, character_alpha)
        caption = final_frame.copy()
        caption.putalpha(caption_alpha)
        captions.append(caption)
        overlap = ImageChops.multiply(character_alpha, caption_alpha)
        overlap_pixels += sum(1 for value in overlap.getdata() if value)
    if not any(frame.getchannel("A").getbbox() for frame in captions):
        raise ValueError("caption extraction produced no visible pixels")
    return character, captions, overlap_pixels


def scaled_size(bounds: tuple[int, int, int, int], scale: float) -> tuple[int, int]:
    return max(1, round((bounds[2] - bounds[0]) * scale)), max(1, round((bounds[3] - bounds[1]) * scale))


def fit_scale(bounds: tuple[int, int, int, int], target_height: float, max_width: float) -> float:
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    return min(target_height / height, max_width / width)


def component_plan(
    size: int,
    layout: str,
    character_bounds: tuple[int, int, int, int],
    caption_bounds: tuple[int, int, int, int],
    profile: dict[str, Any],
) -> dict[str, Any]:
    min_height, max_height = (float(value) for value in profile["target_character_height"])
    target_height = size * ((min_height + max_height) / 2.0)
    character_scale = fit_scale(character_bounds, target_height, size * 0.86)
    character_size = scaled_size(character_bounds, character_scale)

    if layout in {"top", "bottom"}:
        caption_scale = fit_scale(caption_bounds, size * 0.19, size * 0.88)
        caption_size = scaled_size(caption_bounds, caption_scale)
        axis = 1
    else:
        caption_width = caption_bounds[2] - caption_bounds[0]
        caption_height = caption_bounds[3] - caption_bounds[1]
        caption_scale = min((size * 0.32) / caption_width, (size * 0.62) / caption_height)
        caption_size = scaled_size(caption_bounds, caption_scale)
        axis = 0

    preferred_span = round(size * float(profile["target_content_occupancy"]))
    # Pixel canvases are discrete: floor keeps 87/96 (= 0.90625) from
    # accidentally passing a nominal 0.90 ceiling.
    maximum_span = math.floor(size * 0.90)
    component_span = character_size[axis] + caption_size[axis]
    if component_span + 1 > maximum_span:
        # Captions are screen-space UI and may scale independently. Preserve the
        # mascot/device target first, then fit the caption into the remaining span.
        available_caption = max(size * 0.10, maximum_span - character_size[axis] - 1)
        caption_scale *= available_caption / caption_size[axis]
        caption_size = scaled_size(caption_bounds, caption_scale)
        component_span = character_size[axis] + caption_size[axis]
    gap = max(2, round(min(maximum_span - component_span, max(2.0, preferred_span - component_span))))
    span = component_span + gap
    if span > maximum_span + 0.01:
        gap = max(1, math.floor(maximum_span - component_span))
        span = component_span + gap

    origin = round((size - span) / 2)
    if layout == "top":
        caption_xy = ((size - caption_size[0]) // 2, origin)
        character_xy = ((size - character_size[0]) // 2, origin + caption_size[1] + gap)
    elif layout == "bottom":
        character_xy = ((size - character_size[0]) // 2, origin)
        caption_xy = ((size - caption_size[0]) // 2, origin + character_size[1] + gap)
    elif layout == "left":
        caption_xy = (origin, (size - caption_size[1]) // 2)
        character_xy = (origin + caption_size[0] + gap, (size - character_size[1]) // 2)
    elif layout == "right":
        character_xy = (origin, (size - character_size[1]) // 2)
        caption_xy = (origin + character_size[0] + gap, (size - caption_size[1]) // 2)
    else:
        raise ValueError(f"unsupported caption layout: {layout}")
    return {
        "character_scale": character_scale,
        "caption_scale": caption_scale,
        "character_size": character_size,
        "caption_size": caption_size,
        "character_xy": character_xy,
        "caption_xy": caption_xy,
        "gap_px": gap,
    }


def place_component(
    frame: Image.Image,
    source_bounds: tuple[int, int, int, int],
    target_size: tuple[int, int],
    target_xy: tuple[int, int],
    canvas_size: int,
) -> Image.Image:
    crop = frame.crop(source_bounds).resize(target_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.alpha_composite(crop, target_xy)
    return canvas


def maximum_visible_height(
    frames: list[Image.Image],
    source_bounds: tuple[int, int, int, int],
    target_size: tuple[int, int],
) -> int:
    result = 0
    for frame in frames:
        resized = frame.crop(source_bounds).resize(target_size, Image.Resampling.LANCZOS)
        bounds = resized.getchannel("A").getbbox()
        if bounds is not None:
            result = max(result, bounds[3] - bounds[1])
    return result


def compose_profile(
    size: int,
    layout: str,
    profile: dict[str, Any],
    character_frames: list[Image.Image],
    caption_frames: list[Image.Image],
    device_critical: bool,
) -> tuple[list[Image.Image], dict[str, Any]]:
    character_bounds = alpha_union_bounds(character_frames)
    caption_bounds = alpha_union_bounds(caption_frames)
    source_layout = layout
    plan = component_plan(size, layout, character_bounds, caption_bounds, profile)
    minimum_caption_height = math.ceil(
        size * float(profile.get("minimum_caption_visible_height_ratio", 0.10))
    )
    visible_caption_height = maximum_visible_height(
        caption_frames, caption_bounds, tuple(plan["caption_size"])
    )
    if layout in {"left", "right"} and visible_caption_height < minimum_caption_height:
        # A nominal side slot is not useful if fitting the phrase makes its
        # visible letter height unreadable. Keep short expressive side captions;
        # move longer phrases to a deterministic vertical slot.
        layout = "top" if layout == "left" else "bottom"
        plan = component_plan(size, layout, character_bounds, caption_bounds, profile)
        visible_caption_height = maximum_visible_height(
            caption_frames, caption_bounds, tuple(plan["caption_size"])
        )
    output_frames: list[Image.Image] = []
    frame_metrics: list[dict[str, Any]] = []
    for character, caption in zip(character_frames, caption_frames):
        character_layer = place_component(
            character, character_bounds, tuple(plan["character_size"]), tuple(plan["character_xy"]), size
        )
        caption_layer = place_component(
            caption, caption_bounds, tuple(plan["caption_size"]), tuple(plan["caption_xy"]), size
        )
        intersection = ImageChops.multiply(character_layer.getchannel("A"), caption_layer.getchannel("A"))
        overlap_pixels = sum(1 for value in intersection.getdata() if value)
        frame = Image.alpha_composite(character_layer, caption_layer)
        output_frames.append(frame)
        combined_bounds = frame.getchannel("A").getbbox()
        char_bounds = character_layer.getchannel("A").getbbox()
        if combined_bounds is None or char_bounds is None:
            raise ValueError("display-profile frame is unexpectedly empty")
        margins = (
            combined_bounds[0], combined_bounds[1],
            size - combined_bounds[2], size - combined_bounds[3],
        )
        combined_occupancy = max(
            combined_bounds[2] - combined_bounds[0],
            combined_bounds[3] - combined_bounds[1],
        ) / size
        char_height = (char_bounds[3] - char_bounds[1]) / size
        char_width = (char_bounds[2] - char_bounds[0]) / size
        height_pass = char_height + 1e-9 >= float(profile["target_character_height"][0])
        device_width_pass = device_critical and 0.72 - 1e-9 <= char_width <= 0.86 + 1e-9
        frame_metrics.append({
            "combined_occupancy": round(combined_occupancy, 4),
            "character_height_ratio": round(char_height, 4),
            "character_width_ratio": round(char_width, 4),
            "minimum_canvas_margin_px": min(margins),
            "caption_character_overlap_pixels": overlap_pixels,
            "character_gate_pass": height_pass or device_width_pass,
        })
    animation_bounds = alpha_union_bounds(output_frames)
    animation_union_occupancy = max(
        animation_bounds[2] - animation_bounds[0],
        animation_bounds[3] - animation_bounds[1],
    ) / size
    return output_frames, {
        "source_layout": source_layout,
        "resolved_layout": layout,
        "minimum_caption_height_px": minimum_caption_height,
        "maximum_visible_caption_height_px": visible_caption_height,
        "plan": plan,
        "animation_union_occupancy": round(animation_union_occupancy, 4),
        "frame_metrics": frame_metrics,
        "gate_pass": (
            0.72 - 1e-9 <= animation_union_occupancy <= 0.90 + 1e-9
            and all(
            metric["combined_occupancy"] <= 0.90 + 1e-9
            and metric["minimum_canvas_margin_px"] >= 1
            and metric["caption_character_overlap_pixels"] == 0
            and metric["character_gate_pass"]
            for metric in frame_metrics
            )
        ),
    }


def display_font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def build_contact_sheet(
    output: Path,
    profile_name: str,
    size: int,
    entries: dict[tuple[str, str], dict[str, Any]],
) -> Path:
    cell, left, top = max(112, size + 18), 70, 65
    sheet = Image.new("RGBA", (left + cell * len(SAMPLE_PHRASES), top + cell * len(MASTER_IDS)), (238, 243, 248, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((14, 12), f"Human library — {profile_name} ({size}px, first frame)", fill=(22, 43, 69, 255), font=display_font(22))
    for column, phrase_id in enumerate(SAMPLE_PHRASES):
        draw.text((left + column * cell + 4, 43), phrase_id.removeprefix("chat."), fill=(22, 43, 69, 255), font=display_font(10))
    for row, master_id in enumerate(MASTER_IDS):
        y = top + row * cell
        draw.text((14, y + cell // 2), master_id, fill=(22, 43, 69, 255), font=display_font(13))
        for column, phrase_id in enumerate(SAMPLE_PHRASES):
            x = left + column * cell
            draw.rounded_rectangle((x + 3, y + 3, x + cell - 3, y + cell - 3), 12, fill=(255, 255, 255, 255))
            entry = entries[(master_id, phrase_id)]
            image = Image.open(output / entry["path"]).convert("RGBA")
            sheet.alpha_composite(image, (x + (cell - size) // 2, y + (cell - size) // 2))
    path = output / f"{profile_name}-contact-sheet.png"
    sheet.save(path)
    return path


def build(args: argparse.Namespace) -> None:
    contract = read_json(args.contract.resolve())
    profiles = contract["display_profiles"]
    bundle = args.bundle.resolve()
    catalogue = read_json(bundle / "catalogue.json")
    human_entries = [
        entry for entry in catalogue["stickers"]
        if str(entry.get("approved_identity_source", "")) in MASTER_IDS
    ]
    by_key = {
        (str(entry["approved_identity_source"]), str(entry["phrase_id"])): entry
        for entry in human_entries
    }
    expected = len(MASTER_IDS) * len(PHRASES)
    if len(by_key) != expected:
        raise ValueError(f"canonical human matrix must contain {expected} unique assets")

    output = args.output.resolve()
    if output.exists():
        if not args.force:
            raise FileExistsError(f"output exists (use --force): {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    temporary = Path(tempfile.mkdtemp(prefix="human-display-profiles-", dir=output.parent))
    results: list[dict[str, Any]] = []
    aggregate_metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        for master_id in MASTER_IDS:
            source_root = args.masters.resolve() if master_id in FOUNDATION_IDS else args.wave2_masters.resolve()
            pack_path = prepare_pack(source_root / master_id, temporary / master_id)
            pack_id = str(read_json(pack_path)["pack_id"])
            for phrase_value in PHRASES:
                phrase_id = f"chat.{phrase_value['slug'].replace('-', '.')}"
                canonical_entry = by_key[(master_id, phrase_id)]
                document = sticker_document(master_id, pack_id, phrase_value)
                document.pop("text", None)
                if isinstance(document.get("animation"), dict):
                    document["animation"].pop("overlays", None)
                sticker_path = temporary / master_id / "stickers" / f"{phrase_value['slug']}.character-only.json"
                write_json(sticker_path, document)
                character_path = temporary / master_id / "renders" / f"{phrase_value['slug']}.webp"
                render(args.mascotrender.resolve(), pack_path, sticker_path, character_path, 512, 512, False)
                canonical_frames, durations, loop = load_frames(bundle / str(canonical_entry["path"]))
                character_frames, character_durations, character_loop = load_frames(character_path)
                if loop != character_loop or sum(durations) != sum(character_durations):
                    raise ValueError(
                        f"animation timing changed while isolating {master_id}/{phrase_id}: "
                        f"canonical={durations}/{loop}, character={character_durations}/{character_loop}"
                    )
                character_frames = resample_to_timeline(character_frames, character_durations, durations)
                character_frames, caption_frames, extraction_overlap = extract_components(canonical_frames, character_frames)
                if extraction_overlap:
                    raise ValueError(f"canonical caption overlaps character for {master_id}/{phrase_id}")
                for profile_name in PROFILE_ORDER:
                    profile = dict(profiles[profile_name])
                    profile["minimum_caption_visible_height_ratio"] = contract["caption_readability"]["minimum_maximum_visible_height_ratio"]
                    size = int(profile["width"])
                    frames, metrics = compose_profile(
                        size,
                        str(canonical_entry["caption_layout"]),
                        profile,
                        character_frames,
                        caption_frames,
                        master_id in set(contract["device_critical_characters"]),
                    )
                    relative = Path("assets") / profile_name / master_id.lower() / f"{phrase_value['slug']}.webp"
                    asset = output / relative
                    save_frames(asset, frames, durations, loop)
                    if not (b"ANIM" in asset.read_bytes() and b"ANMF" in asset.read_bytes()):
                        raise ValueError(f"profile output is not animated: {relative}")
                    entry = {
                        "profile": profile_name,
                        "width": size,
                        "height": size,
                        "character_id": master_id,
                        "phrase_id": phrase_id,
                        "caption_layout": metrics["resolved_layout"],
                        "source_caption_layout": metrics["source_layout"],
                        "path": relative.as_posix(),
                        "sha256": sha256(asset),
                        "encoded_bytes": asset.stat().st_size,
                        "frame_count": len(frames),
                        "metrics": metrics,
                    }
                    results.append(entry)
                    aggregate_metrics[profile_name].extend(metrics["frame_metrics"])
        if not all(entry["metrics"]["gate_pass"] for entry in results):
            failed_entries = [entry for entry in results if not entry["metrics"]["gate_pass"]]
            failures = [
                f"{entry['profile']}:{entry['character_id']}:{entry['phrase_id']}"
                for entry in failed_entries
            ]
            write_json(output / "gate-failures.json", {
                "failure_count": len(failed_entries),
                "failures": failed_entries,
            })
            raise ValueError(f"small-display occupancy gate failed ({len(failures)}): {failures[:20]}")

        lookup = {
            (entry["profile"], entry["character_id"], entry["phrase_id"]): entry
            for entry in results
        }
        sheets: dict[str, dict[str, str]] = {}
        for profile_name in PROFILE_ORDER:
            entries = {
                (master_id, phrase_id): lookup[(profile_name, master_id, phrase_id)]
                for master_id in MASTER_IDS for phrase_id in SAMPLE_PHRASES
            }
            sheet = build_contact_sheet(output, profile_name, int(profiles[profile_name]["width"]), entries)
            sheets[profile_name] = {"path": sheet.name, "sha256": sha256(sheet)}

        cards = []
        for profile_name in PROFILE_ORDER:
            for master_id in MASTER_IDS:
                for phrase_id in SAMPLE_PHRASES:
                    entry = lookup[(profile_name, master_id, phrase_id)]
                    cards.append(
                        f"<article><strong>{html.escape(profile_name)} · {html.escape(master_id)} · {html.escape(phrase_id)}</strong>"
                        f"<img src='{html.escape(entry['path'])}' alt='{html.escape(master_id + ' ' + phrase_id)}'></article>"
                    )
        (output / "animation-review.html").write_text(
            "<!doctype html><meta charset='utf-8'><title>Human small-display animation review</title>"
            "<style>body{font:13px system-ui;background:#eef3f8;color:#162b45;margin:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}article{background:white;padding:9px;border-radius:12px}img{display:block;margin:auto;image-rendering:auto}</style>"
            "<h1>Animation-aware human display profiles</h1><p>These are the real 80/96/100px animated WebP outputs, not scaled 512px previews.</p><div class='grid'>"
            + "".join(cards) + "</div>",
            encoding="utf-8",
        )
        profile_summary: dict[str, Any] = {}
        for profile_name, values in aggregate_metrics.items():
            profile_entries = [entry for entry in results if entry["profile"] == profile_name]
            profile_summary[profile_name] = {
                "frame_count": len(values),
                "minimum_combined_occupancy": min(value["combined_occupancy"] for value in values),
                "maximum_combined_occupancy": max(value["combined_occupancy"] for value in values),
                "minimum_character_height_ratio": min(value["character_height_ratio"] for value in values),
                "maximum_character_width_ratio": max(value["character_width_ratio"] for value in values),
                "minimum_canvas_margin_px": min(value["minimum_canvas_margin_px"] for value in values),
                "caption_character_overlap_pixels": sum(value["caption_character_overlap_pixels"] for value in values),
                "all_frame_gates_pass": all(value["character_gate_pass"] for value in values),
                "minimum_animation_union_occupancy": min(entry["metrics"]["animation_union_occupancy"] for entry in profile_entries),
                "maximum_animation_union_occupancy": max(entry["metrics"]["animation_union_occupancy"] for entry in profile_entries),
            }
        report = {
            "schema_version": 1,
            "review_status": "small-display-occupancy-candidate",
            "canonical_assets_modified": False,
            "source_bundle": str(bundle),
            "source_catalogue_sha256": sha256(bundle / "catalogue.json"),
            "contract": str(args.contract.resolve()),
            "contract_sha256": sha256(args.contract.resolve()),
            "identity_count": len(MASTER_IDS),
            "phrase_count": len(PHRASES),
            "profile_count": len(PROFILE_ORDER),
            "asset_count": len(results),
            "animated_asset_count": len(results),
            "all_assets_pass": True,
            "profiles": profile_summary,
            "contact_sheets": sheets,
            "animation_review": "animation-review.html",
        }
        write_json(output / "review.json", report)
        write_json(output / "catalogue.json", {"schema_version": 1, "assets": results})
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "generated" / "wahalao-human-dev-bundle-v7")
    parser.add_argument("--contract", type=Path, default=ROOT / "contracts" / "human-small-display-occupancy-v1.json")
    parser.add_argument("--masters", type=Path, default=ROOT / "art" / "human-pack-v1" / "masters")
    parser.add_argument("--wave2-masters", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--output", type=Path, default=ROOT / "generated" / "human-small-display-profiles-v1")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build(args)
    report = read_json(args.output.resolve() / "review.json")
    print(f"built {report['asset_count']} animated small-display assets at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
