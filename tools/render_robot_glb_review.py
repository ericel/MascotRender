#!/usr/bin/env python3
"""Render the rest pose and four MR-112 clips for visual review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageDraw


SAMPLES = [
    ("rest", "", 0.0),
    ("idle", "idle", 0.5),
    ("hello", "hello", 0.3),
    ("hop", "hop", 0.3),
    ("celebrate", "celebrate", 0.5),
]

CLIPS = {
    "idle": 1.0,
    "hello": 0.9,
    "hop": 0.9,
    "celebrate": 1.0,
}
ANIMATION_FRAME_COUNT = 13
ANIMATION_SIZE = 320

PALETTE = {
    "gold": (255, 209, 102),
    "orange": (228, 155, 54),
    "mint": (122, 225, 210),
    "ink": (60, 48, 66),
}


def file_record(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "file": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def render_command(
    renderer: Path,
    source: Path,
    destination: Path,
    *,
    size: int,
    animation: str = "",
    time: float = 0.0,
) -> list[str]:
    command = [
        str(renderer),
        "--input",
        str(source),
        "--output",
        str(destination),
        "--width",
        str(size),
        "--height",
        str(size),
        "--span",
        "4.4",
        "--center-y",
        "0.35",
    ]
    if animation:
        command.extend(["--animation", animation, "--time", str(time)])
    return command


def run_renderer(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"renderer exited with {completed.returncode}:\n{completed.stdout}"
        )


def matching_pixels(image: Image.Image, target: tuple[int, int, int], tolerance=3):
    matches = []
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.getpixel((x, y))
            if alpha > 200 and all(
                abs(actual - expected) <= tolerance
                for actual, expected in zip((red, green, blue), target)
            ):
                matches.append((x, y))
    return matches


def validate_rest_frame(image: Image.Image) -> dict[str, object]:
    counts = {name: len(matching_pixels(image, color)) for name, color in PALETTE.items()}
    missing = [name for name, count in counts.items() if count < 100]
    if missing:
        raise RuntimeError(f"rest frame is missing approved palette colors: {missing}")

    mint_pixels = matching_pixels(image, PALETTE["mint"])
    top_mint = sum(y < image.height * 0.2 for _, y in mint_pixels)
    bottom_mint = sum(y > image.height * 0.8 for _, y in mint_pixels)
    if top_mint < 100 or top_mint <= bottom_mint:
        raise RuntimeError("rest frame orientation guard failed: mint antenna is not on top")

    alpha_bounds = image.getchannel("A").getbbox()
    if alpha_bounds is None or alpha_bounds[1] >= image.height * 0.3:
        raise RuntimeError("rest frame orientation/visibility guard failed")
    return {"palette_pixel_counts": counts, "alpha_bounds": list(alpha_bounds)}


def write_review_images(output: Path, rendered: list[tuple[str, Path]]) -> dict[str, object]:
    frames = [(label, Image.open(path).convert("RGBA")) for label, path in rendered]
    rest_validation = validate_rest_frame(frames[0][1])

    white = Image.new("RGBA", frames[0][1].size, (255, 255, 255, 255))
    white.alpha_composite(frames[0][1])
    white_path = output / "robot-004-rest-white.png"
    white.convert("RGB").save(white_path, optimize=True)

    tile_size = 320
    label_height = 38
    sheet = Image.new(
        "RGB", (tile_size * len(frames), tile_size + label_height), (244, 247, 251)
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, frame) in enumerate(frames):
        tile = Image.new("RGBA", (tile_size, tile_size), (244, 247, 251, 255))
        resized = frame.resize((tile_size, tile_size), Image.Resampling.LANCZOS)
        tile.alpha_composite(resized)
        sheet.paste(tile.convert("RGB"), (index * tile_size, 0))
        text_bounds = draw.textbbox((0, 0), label)
        text_width = text_bounds[2] - text_bounds[0]
        draw.text(
            (index * tile_size + (tile_size - text_width) * 0.5, tile_size + 10),
            label,
            fill=PALETTE["ink"],
        )
    sheet_path = output / "robot-004-contact-sheet.png"
    sheet.save(sheet_path, optimize=True)

    return {
        "rest_validation": rest_validation,
        "white_background": file_record(white_path),
        "contact_sheet": file_record(sheet_path),
    }


def frame_delta(left: Image.Image, right: Image.Image) -> float:
    difference = ImageChops.difference(left.convert("RGBA"), right.convert("RGBA"))
    histogram = difference.histogram()
    total = sum((index % 256) * count for index, count in enumerate(histogram))
    return total / (left.width * left.height * 4.0)


def decoded_frame_hash(frame: Image.Image) -> str:
    return hashlib.sha256(frame.convert("RGBA").tobytes()).hexdigest()


def write_animation_review(
    renderer: Path, source: Path, output: Path
) -> tuple[list[dict[str, object]], dict[str, object]]:
    animation_records: list[dict[str, object]] = []
    motion_rows: list[tuple[str, list[Image.Image], float]] = []

    with tempfile.TemporaryDirectory(prefix="mascotrender-robot-frames-") as temporary:
        frame_directory = Path(temporary)
        for clip, clip_duration in CLIPS.items():
            frames: list[Image.Image] = []
            times = [
                clip_duration * index / (ANIMATION_FRAME_COUNT - 1)
                for index in range(ANIMATION_FRAME_COUNT)
            ]
            for index, time in enumerate(times):
                frame_path = frame_directory / f"{clip}-{index:02d}.webp"
                run_renderer(
                    render_command(
                        renderer,
                        source,
                        frame_path,
                        size=ANIMATION_SIZE,
                        animation=clip,
                        time=time,
                    )
                )
                frames.append(Image.open(frame_path).convert("RGBA"))

            frame_duration_ms = round(clip_duration * 1000 / (len(frames) - 1))
            encoded_path = output / f"robot-004-{clip}-animated.webp"
            durations = [frame_duration_ms] * (len(frames) - 1) + [20]
            frames[0].save(
                encoded_path,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                lossless=True,
                method=6,
            )

            encoded = Image.open(encoded_path)
            encoded_frames: list[Image.Image] = []
            encoded_durations: list[int] = []
            for index in range(encoded.n_frames):
                encoded.seek(index)
                encoded_frames.append(encoded.convert("RGBA"))
                encoded_durations.append(int(encoded.info.get("duration", 0)))
            payload = encoded_path.read_bytes()
            deltas = [
                frame_delta(left, right)
                for left, right in zip(encoded_frames, encoded_frames[1:])
            ]
            loop_delta = frame_delta(encoded_frames[0], encoded_frames[-1])
            moving_steps = sum(delta > 0.05 for delta in deltas)
            if b"ANIM" not in payload or b"ANMF" not in payload:
                raise RuntimeError(f"{clip} output is not an animated WebP")
            if encoded.n_frames != ANIMATION_FRAME_COUNT:
                raise RuntimeError(
                    f"{clip} has {encoded.n_frames} frames, expected {ANIMATION_FRAME_COUNT}"
                )
            if moving_steps < ANIMATION_FRAME_COUNT // 2:
                raise RuntimeError(f"{clip} animation is effectively static")
            if loop_delta > 0.01:
                raise RuntimeError(
                    f"{clip} loop does not close: mean channel delta {loop_delta:.4f}"
                )

            animation_records.append(
                {
                    "clip": clip,
                    "clip_duration_seconds": clip_duration,
                    "frame_count": encoded.n_frames,
                    "frame_durations_ms": encoded_durations,
                    "sample_times_seconds": times,
                    "mean_channel_deltas": deltas,
                    "moving_steps": moving_steps,
                    "loop_closure_mean_channel_delta": loop_delta,
                    "decoded_frame_sha256": [
                        decoded_frame_hash(frame) for frame in encoded_frames
                    ],
                    **file_record(encoded_path),
                }
            )
            motion_rows.append((clip, encoded_frames, clip_duration))

    tile_size = 200
    label_height = 28
    sample_indices = [0, 3, 6, 9, 12]
    sheet = Image.new(
        "RGB",
        (tile_size * len(sample_indices), (tile_size + label_height) * len(motion_rows)),
        (244, 247, 251),
    )
    draw = ImageDraw.Draw(sheet)
    for row, (clip, frames, clip_duration) in enumerate(motion_rows):
        row_y = row * (tile_size + label_height)
        for column, frame_index in enumerate(sample_indices):
            tile = Image.new("RGBA", (tile_size, tile_size), (244, 247, 251, 255))
            tile.alpha_composite(
                frames[frame_index].resize(
                    (tile_size, tile_size), Image.Resampling.LANCZOS
                )
            )
            sheet.paste(tile.convert("RGB"), (column * tile_size, row_y))
            time = clip_duration * frame_index / (ANIMATION_FRAME_COUNT - 1)
            label = f"{clip}  t={time:.2f}s"
            draw.text(
                (column * tile_size + 8, row_y + tile_size + 7),
                label,
                fill=PALETTE["ink"],
            )
    motion_sheet_path = output / "robot-004-animation-motion-sheet.png"
    sheet.save(motion_sheet_path, optimize=True)

    html_path = output / "robot-004-animation-review.html"
    cards = "\n".join(
        f'<figure><img src="robot-004-{clip}-animated.webp" alt="{clip} animation">'
        f"<figcaption>{clip}</figcaption></figure>"
        for clip in CLIPS
    )
    html_path.write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>robot-004 animation review</title>"
        "<style>body{margin:0;background:#f4f7fb;color:#3c3042;font:16px system-ui}"
        "h1{text-align:center}main{display:grid;grid-template-columns:repeat(2,320px);"
        "gap:24px;justify-content:center}figure{margin:0;text-align:center}"
        "img{width:320px;height:320px}figcaption{font-weight:700}</style>"
        "<h1>robot-004 animation playback</h1><main>"
        + cards
        + "</main>",
        encoding="utf-8",
    )
    return animation_records, {
        "motion_sheet": file_record(motion_sheet_path),
        "browser_review": file_record(html_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    # Review directories are reproducible outputs. Remove current and legacy
    # names so an obsolete debug render cannot be mistaken for a deliverable.
    for pattern in ("robot-004-*", "review.json", "rest-white.png", "contact-sheet.png"):
        for stale in args.output.glob(pattern):
            if stale.is_file():
                stale.unlink()

    manifest = {"asset": str(args.input), "samples": []}
    rendered: list[tuple[str, Path]] = []
    for label, animation, time in SAMPLES:
        destination = args.output / f"robot-004-{label}.webp"
        run_renderer(
            render_command(
                args.renderer,
                args.input,
                destination,
                size=512,
                animation=animation,
                time=time,
            )
        )
        rendered.append((label, destination))
        payload = destination.read_bytes()
        manifest["samples"].append(
            {
                "label": label,
                "animation": animation or None,
                "time_seconds": time,
                "file": destination.name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    manifest["review_images"] = write_review_images(args.output, rendered)
    manifest["animations"], manifest["animation_review"] = write_animation_review(
        args.renderer, args.input, args.output
    )

    (args.output / "review.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {len(SAMPLES)} robot review frames and {len(CLIPS)} animations "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
