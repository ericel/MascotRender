#!/usr/bin/env python3
"""Validate and batch-render generated MascotRender packs into a WebP bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BUNDLE_VERSION = 3
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
STOP_WORDS = frozenset({"a", "an", "and", "he", "it", "of", "she", "the", "to"})


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
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


def source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def normalize_trigger(content: str) -> str:
    characters = []
    previous_space = False
    for character in content.casefold():
        if character.isalnum() or character in {"'", "-"}:
            characters.append(character)
            previous_space = False
        elif not previous_space:
            characters.append(" ")
            previous_space = True
    return "".join(characters).strip()


def semantic_phrase_id(
    sticker: dict[str, object],
    pack_id: str,
    sticker_id: str,
) -> str:
    authored = sticker.get("phrase_id")
    if isinstance(authored, str) and authored.strip():
        return authored.strip()
    prefix = f"{pack_id}-"
    slug = sticker_id[len(prefix):] if sticker_id.startswith(prefix) else sticker_id
    return f"chat.{slug.replace('-', '.')}"


def check_id(value: object, field: str, source: Path) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} must be filesystem-safe in {source}: {value!r}")
    return value


def run_cli(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{details}")


def render_one(
    executable: Path,
    pack_file: Path,
    sticker_file: Path,
    output: Path,
    width: int,
    height: int,
    quality: float,
    lossless: bool,
    first_frame_only: bool,
) -> None:
    command = [
        str(executable),
        "render",
        "--pack",
        str(pack_file),
        "--sticker",
        str(sticker_file),
        "--output",
        str(output),
        "--width",
        str(width),
        "--height",
        str(height),
        "--quality",
        str(quality),
    ]
    if lossless:
        command.append("--lossless")
    if first_frame_only:
        command.append("--first-frame-only")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_cli(command)


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


def find_default_executable(project_root: Path) -> Path:
    candidates = (
        project_root / "build" / "build" / "Release" / "mascotrender",
        project_root / "build" / "Release" / "mascotrender",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    discovered = shutil.which("mascotrender")
    if discovered:
        return Path(discovered)
    return candidates[0]


def build_bundle(args: argparse.Namespace, staging: Path) -> tuple[int, int]:
    input_root = args.input.resolve()
    executable = args.mascotrender.resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError(f"mascotrender executable not found or not executable: {executable}")

    pack_files = sorted(input_root.glob("*/pack.json"))
    if not pack_files:
        raise FileNotFoundError(f"no */pack.json files found under {input_root}")

    catalogue: list[dict[str, object]] = []
    dictionary: dict[str, set[str]] = {}
    for pack_file in pack_files:
        pack = read_json(pack_file)
        pack_id = check_id(pack.get("pack_id"), "pack_id", pack_file)
        sticker_files = sorted((pack_file.parent / "stickers").glob("*.json"))
        if not sticker_files:
            raise FileNotFoundError(f"pack contains no sticker JSON files: {pack_file.parent}")

        for sticker_file in sticker_files:
            sticker = read_json(sticker_file)
            sticker_id = check_id(sticker.get("sticker_id"), "sticker_id", sticker_file)
            if sticker.get("pack_id") != pack_id:
                raise ValueError(f"sticker pack_id mismatch: {sticker_file}")
            text_value = sticker.get("text")
            content = text_value.get("content", "") if isinstance(text_value, dict) else ""
            if not isinstance(content, str):
                raise ValueError(f"text.content must be a string: {sticker_file}")

            run_cli(
                [
                    str(executable),
                    "validate",
                    "--pack",
                    str(pack_file),
                    "--sticker",
                    str(sticker_file),
                ]
            )

            asset_relative = Path("assets") / pack_id / f"{sticker_id}.webp"
            thumbnail_relative = Path("thumbnails") / pack_id / f"{sticker_id}.webp"
            reduced_relative = Path("reduced-motion") / pack_id / f"{sticker_id}.webp"
            asset = staging / asset_relative
            thumbnail = staging / thumbnail_relative
            reduced = staging / reduced_relative
            render_one(
                executable,
                pack_file,
                sticker_file,
                asset,
                args.width,
                args.height,
                args.quality,
                args.lossless,
                False,
            )
            render_one(
                executable,
                pack_file,
                sticker_file,
                thumbnail,
                args.thumbnail_size,
                args.thumbnail_size,
                args.quality,
                args.lossless,
                True,
            )
            render_one(
                executable,
                pack_file,
                sticker_file,
                reduced,
                args.width,
                args.height,
                args.quality,
                args.lossless,
                True,
            )

            animation = sticker.get("animation")
            animation_metadata = animation if isinstance(animation, dict) else None
            phrase_id = semantic_phrase_id(sticker, pack_id, sticker_id)

            trigger = normalize_trigger(content)
            # Two-character chat phrases such as NO and OK are deliberate
            # semantic entries. One-character slang aliases remain forbidden;
            # richer alias safety lives in the versioned phrase lexicon.
            if trigger and (len(trigger) < 2 or trigger in STOP_WORDS):
                raise ValueError(f"unsafe trigger {trigger!r} in {sticker_file}")
            if trigger:
                dictionary.setdefault(trigger, set()).add(phrase_id)

            catalogue.append(
                {
                    "pack_id": pack_id,
                    "sticker_id": sticker_id,
                    "text": content,
                    "alt_text": sticker.get("alt_text", ""),
                    "phrase_id": phrase_id,
                    "recipe_id": sticker.get("recipe_id"),
                    "expression": sticker.get("expression"),
                    "pose": sticker.get("pose"),
                    "camera": sticker.get("camera"),
                    "seed": sticker.get("seed"),
                    "animated": animation_metadata is not None,
                    "animation": animation_metadata,
                    "media_type": "image/webp",
                    "width": args.width,
                    "height": args.height,
                    "path": asset_relative.as_posix(),
                    "sha256": sha256_file(asset),
                    "encoded_bytes": asset.stat().st_size,
                    "thumbnail": {
                        "width": args.thumbnail_size,
                        "height": args.thumbnail_size,
                        "path": thumbnail_relative.as_posix(),
                        "sha256": sha256_file(thumbnail),
                        "encoded_bytes": thumbnail.stat().st_size,
                    },
                    "reduced_motion": {
                        "presentation": "static-semantic-equivalent",
                        "width": args.width,
                        "height": args.height,
                        "path": reduced_relative.as_posix(),
                        "sha256": sha256_file(reduced),
                        "encoded_bytes": reduced.stat().st_size,
                    },
                }
            )

    catalogue.sort(key=lambda item: (str(item["pack_id"]), str(item["sticker_id"])))
    ordered_dictionary = [
        {
            "trigger": trigger,
            "match": "unicode-word-boundary",
            "phrase_ids": sorted(items),
        }
        for trigger, items in sorted(dictionary.items())
    ]
    write_json(
        staging / "catalogue.json",
        {
            "schema_version": 1,
            "protocol": "mascotrender-bundle-v1",
            "bundle_version": BUNDLE_VERSION,
            "source_sha256": source_digest(input_root),
            "sticker_count": len(catalogue),
            "animated_sticker_count": sum(
                1 for sticker in catalogue if sticker["animated"]
            ),
            "stickers": catalogue,
        },
    )
    write_json(
        staging / "dictionary.json",
        {
            "schema_version": 1,
            "protocol": "mascotrender-bundle-v1",
            "matching": "casefolded full phrase with Unicode word boundaries",
            "trigger_count": len(ordered_dictionary),
            "entries": ordered_dictionary,
        },
    )
    total_bytes = sum(path.stat().st_size for path in staging.rglob("*.webp"))
    write_json(
        staging / "build-report.json",
        {
            "schema_version": 1,
            "protocol": "mascotrender-bundle-v1",
            "status": "success",
            "pack_count": len(pack_files),
            "sticker_count": len(catalogue),
            "animated_sticker_count": sum(
                1 for sticker in catalogue if sticker["animated"]
            ),
            "asset_count": len(catalogue) * 3,
            "reduced_motion_sticker_count": len(catalogue),
            "encoded_bytes": total_bytes,
            "render": {
                "width": args.width,
                "height": args.height,
                "thumbnail_size": args.thumbnail_size,
                "webp_quality": args.quality,
                "lossless": args.lossless,
            },
        },
    )
    return len(pack_files), len(catalogue)


def parse_args(argv: list[str]) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project_root / "generated" / "mascots")
    parser.add_argument("--output", type=Path, default=project_root / "generated" / "bundle")
    parser.add_argument(
        "--mascotrender",
        type=Path,
        default=find_default_executable(project_root),
        help="Path to the mascotrender CLI",
    )
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--thumbnail-size", type=int, default=256)
    parser.add_argument("--quality", type=float, default=90.0)
    parser.add_argument("--lossless", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.width < 1 or args.width > 4096 or args.height < 1 or args.height > 4096:
        raise ValueError("--width and --height must be between 1 and 4096")
    if args.thumbnail_size < 1 or args.thumbnail_size > 4096:
        raise ValueError("--thumbnail-size must be between 1 and 4096")
    if args.quality < 0.0 or args.quality > 100.0:
        raise ValueError("--quality must be between 0 and 100")

    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        pack_count, sticker_count = build_bundle(args, staging)
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    print(f"rendered {sticker_count} stickers from {pack_count} packs into {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
