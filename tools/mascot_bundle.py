#!/usr/bin/env python3
"""Validate and stage storage-neutral MascotRender distribution bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


PROTOCOL = "mascotrender-bundle-v1"
IMMUTABLE_CACHE_CONTROL = "public,max-age=31536000,immutable"
POINTER_CACHE_CONTROL = "no-cache,max-age=0,must-revalidate"
ASSET_ROOTS = frozenset({"assets", "thumbnails", "reduced-motion"})
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PHRASE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.][a-z0-9-]+)+$")


class BundleError(ValueError):
    """Raised when a source bundle violates the public distribution contract."""


def read_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise BundleError(f"cannot read {path}: {error}") from error
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise BundleError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise BundleError(f"{path} must contain a JSON object")
    return payload, value


def write_json(path: Path, value: object) -> bytes:
    payload = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BundleError(f"{field} must be a non-empty string")
    return value.strip()


def require_integer(
    value: object,
    field: str,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        range_text = f">= {minimum}" if maximum is None else f"between {minimum} and {maximum}"
        raise BundleError(f"{field} must be an integer {range_text}")
    return value


def require_sha256(value: object, field: str) -> str:
    digest = require_string(value, field)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise BundleError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def safe_relative_path(value: object, field: str) -> Path:
    text = require_string(value, field).replace("\\", "/")
    path = Path(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError(f"{field} must be a safe relative path")
    return path


def checked_asset(
    bundle: Path,
    metadata: dict[str, Any],
    field: str,
    expected_root: str,
) -> tuple[Path, str, int]:
    relative = safe_relative_path(metadata.get("path"), f"{field}.path")
    if relative.parts[0] != expected_root or expected_root not in ASSET_ROOTS:
        raise BundleError(f"{field}.path must stay inside {expected_root}/")
    source = (bundle / relative).resolve()
    try:
        source.relative_to(bundle)
    except ValueError as error:
        raise BundleError(f"{field}.path escapes the bundle") from error
    if not source.is_file():
        raise BundleError(f"{field} is missing: {relative.as_posix()}")
    expected_hash = require_sha256(metadata.get("sha256"), f"{field}.sha256")
    actual_hash = sha256_file(source)
    if actual_hash != expected_hash:
        raise BundleError(
            f"{field} SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
        )
    expected_bytes = require_integer(metadata.get("encoded_bytes"), f"{field}.encoded_bytes", 1)
    actual_bytes = source.stat().st_size
    if actual_bytes != expected_bytes:
        raise BundleError(
            f"{field} byte-size mismatch: expected {expected_bytes}, got {actual_bytes}"
        )
    require_integer(metadata.get("width"), f"{field}.width", 1, 4096)
    require_integer(metadata.get("height"), f"{field}.height", 1, 4096)
    return source, actual_hash, actual_bytes


def validate_bundle(bundle: Path) -> dict[str, Any]:
    bundle = bundle.resolve()
    catalogue_bytes, catalogue = read_json(bundle / "catalogue.json")
    dictionary_bytes, dictionary = read_json(bundle / "dictionary.json")
    _, report = read_json(bundle / "build-report.json")
    for label, document in (
        ("catalogue", catalogue),
        ("dictionary", dictionary),
        ("build-report", report),
    ):
        if document.get("schema_version") != 1 or document.get("protocol") != PROTOCOL:
            raise BundleError(f"{label} must declare schema_version 1 and {PROTOCOL}")

    require_integer(catalogue.get("bundle_version"), "catalogue.bundle_version", 1)
    require_sha256(catalogue.get("source_sha256"), "catalogue.source_sha256")
    stickers = catalogue.get("stickers")
    if not isinstance(stickers, list) or not stickers:
        raise BundleError("catalogue.stickers must be a non-empty array")
    sticker_count = require_integer(catalogue.get("sticker_count"), "catalogue.sticker_count", 1)
    if sticker_count != len(stickers):
        raise BundleError("catalogue.sticker_count does not match catalogue.stickers")

    sticker_ids: set[str] = set()
    phrase_ids: set[str] = set()
    pack_ids: set[str] = set()
    animated_count = 0
    encoded_bytes = 0
    asset_records: list[dict[str, Any]] = []
    for index, value in enumerate(stickers):
        if not isinstance(value, dict):
            raise BundleError(f"catalogue.stickers[{index}] must be an object")
        sticker_id = require_string(value.get("sticker_id"), f"stickers[{index}].sticker_id")
        pack_id = require_string(value.get("pack_id"), f"stickers[{index}].pack_id")
        phrase_id = require_string(value.get("phrase_id"), f"stickers[{index}].phrase_id")
        require_string(value.get("alt_text"), f"stickers[{index}].alt_text")
        if not SAFE_ID.fullmatch(sticker_id) or not SAFE_ID.fullmatch(pack_id):
            raise BundleError(f"{sticker_id}: pack_id and sticker_id must be filesystem-safe")
        if not PHRASE_ID.fullmatch(phrase_id):
            raise BundleError(f"{sticker_id}.phrase_id is not a valid semantic phrase ID")
        if not isinstance(value.get("text"), str):
            raise BundleError(f"{sticker_id}.text must be a string")
        if value.get("media_type") != "image/webp":
            raise BundleError(f"{sticker_id}.media_type must be image/webp")
        if sticker_id in sticker_ids:
            raise BundleError(f"duplicate sticker_id: {sticker_id}")
        sticker_ids.add(sticker_id)
        phrase_ids.add(phrase_id)
        pack_ids.add(pack_id)
        animated = value.get("animated")
        if not isinstance(animated, bool):
            raise BundleError(f"{sticker_id}.animated must be a boolean")
        animated_count += int(animated)

        primary_source, primary_hash, primary_bytes = checked_asset(
            bundle, value, sticker_id, "assets"
        )
        thumbnail = value.get("thumbnail")
        reduced = value.get("reduced_motion")
        if not isinstance(thumbnail, dict) or not isinstance(reduced, dict):
            raise BundleError(f"{sticker_id} must declare thumbnail and reduced_motion")
        if reduced.get("presentation") != "static-semantic-equivalent":
            raise BundleError(
                f"{sticker_id}.reduced_motion must use static-semantic-equivalent"
            )
        thumbnail_source, thumbnail_hash, thumbnail_bytes = checked_asset(
            bundle, thumbnail, f"{sticker_id}.thumbnail", "thumbnails"
        )
        reduced_source, reduced_hash, reduced_bytes = checked_asset(
            bundle, reduced, f"{sticker_id}.reduced_motion", "reduced-motion"
        )
        encoded_bytes += primary_bytes + thumbnail_bytes + reduced_bytes
        asset_records.extend(
            (
                {
                    "sticker_id": sticker_id,
                    "source": primary_source,
                    "sha256": primary_hash,
                    "encoded_bytes": primary_bytes,
                    "metadata": value,
                    "field": "primary",
                },
                {
                    "sticker_id": sticker_id,
                    "source": thumbnail_source,
                    "sha256": thumbnail_hash,
                    "encoded_bytes": thumbnail_bytes,
                    "metadata": thumbnail,
                    "field": "thumbnail",
                },
                {
                    "sticker_id": sticker_id,
                    "source": reduced_source,
                    "sha256": reduced_hash,
                    "encoded_bytes": reduced_bytes,
                    "metadata": reduced,
                    "field": "reduced_motion",
                },
            )
        )

    declared_animated = require_integer(
        catalogue.get("animated_sticker_count"),
        "catalogue.animated_sticker_count",
    )
    if declared_animated != animated_count:
        raise BundleError("catalogue.animated_sticker_count does not match stickers")

    entries = dictionary.get("entries")
    if dictionary.get("matching") != "casefolded full phrase with Unicode word boundaries":
        raise BundleError("dictionary.matching is unsupported")
    if not isinstance(entries, list) or not entries:
        raise BundleError("dictionary.entries must be a non-empty array")
    if require_integer(dictionary.get("trigger_count"), "dictionary.trigger_count", 1) != len(entries):
        raise BundleError("dictionary.trigger_count does not match dictionary.entries")
    triggers: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise BundleError(f"dictionary.entries[{index}] must be an object")
        trigger = require_string(entry.get("trigger"), f"dictionary.entries[{index}].trigger")
        if trigger in triggers:
            raise BundleError(f"duplicate dictionary trigger: {trigger}")
        triggers.add(trigger)
        if entry.get("match") != "unicode-word-boundary":
            raise BundleError(f"dictionary entry {trigger!r} has an unsupported match mode")
        terminal_phrase_ids = entry.get("phrase_ids")
        if not isinstance(terminal_phrase_ids, list) or not terminal_phrase_ids:
            raise BundleError(f"dictionary entry {trigger!r} must contain phrase_ids")
        normalized_phrase_ids = [
            require_string(phrase_id, f"dictionary entry {trigger!r} phrase_id")
            for phrase_id in terminal_phrase_ids
        ]
        if len(normalized_phrase_ids) != len(set(normalized_phrase_ids)):
            raise BundleError(f"dictionary entry {trigger!r} contains duplicate phrase_ids")
        for normalized in normalized_phrase_ids:
            if normalized not in phrase_ids:
                raise BundleError(
                    f"dictionary entry {trigger!r} references unknown phrase {normalized}"
                )

    expected_assets = sticker_count * 3
    if report.get("status") != "success":
        raise BundleError("build-report.status must be success")
    expected_report = {
        "pack_count": len(pack_ids),
        "sticker_count": sticker_count,
        "animated_sticker_count": animated_count,
        "asset_count": expected_assets,
        "reduced_motion_sticker_count": sticker_count,
        "encoded_bytes": encoded_bytes,
    }
    for field, expected in expected_report.items():
        if report.get(field) != expected:
            raise BundleError(
                f"build-report.{field} must be {expected}, got {report.get(field)!r}"
            )

    return {
        "bundle": bundle,
        "catalogue": catalogue,
        "catalogue_bytes": catalogue_bytes,
        "dictionary": dictionary,
        "dictionary_bytes": dictionary_bytes,
        "asset_records": asset_records,
        "sticker_count": sticker_count,
        "animated_sticker_count": animated_count,
        "phrase_count": len(phrase_ids),
        "trigger_count": len(entries),
        "catalogue_sha256": sha256_bytes(catalogue_bytes),
        "dictionary_sha256": sha256_bytes(dictionary_bytes),
    }


def object_extension(source: Path) -> str:
    suffix = source.suffix.lower()
    return suffix if suffix and len(suffix) <= 10 else ".bin"


def content_type(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return "application/json; charset=utf-8"
    if path.suffix.lower() == ".webp":
        return "image/webp"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


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


def stage_release(
    validated: dict[str, Any],
    destination: Path,
    channel: str,
    previous_plan_path: Path | None,
    force: bool,
) -> dict[str, Any]:
    if not channel or not channel[0].isalpha() or any(
        not (character.islower() or character.isdigit() or character in "._-")
        for character in channel
    ):
        raise BundleError("--channel must be a lowercase filesystem-safe identifier")

    catalogue = json.loads(json.dumps(validated["catalogue"]))
    bundle_version = require_integer(catalogue.get("bundle_version"), "bundle_version", 1)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        sticker_by_id = {
            str(sticker["sticker_id"]): sticker for sticker in catalogue["stickers"]
        }
        copied_objects: dict[str, Path] = {}
        for record in validated["asset_records"]:
            source = Path(record["source"])
            digest = str(record["sha256"])
            object_key = f"objects/sha256/{digest[:2]}/{digest}{object_extension(source)}"
            target = staging / object_key
            if object_key not in copied_objects:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                copied_objects[object_key] = target
            source_sticker_id = str(record["sticker_id"])
            sticker = sticker_by_id[source_sticker_id]
            if record["field"] == "primary":
                sticker["path"] = object_key
            else:
                sticker[str(record["field"])]["path"] = object_key

        catalogue_payload = json_bytes(catalogue)
        dictionary_payload = json_bytes(validated["dictionary"])
        identity_digest = hashlib.sha256()
        identity_digest.update(PROTOCOL.encode())
        identity_digest.update(b"\0")
        identity_digest.update(sha256_bytes(catalogue_payload).encode())
        identity_digest.update(b"\0")
        identity_digest.update(sha256_bytes(dictionary_payload).encode())
        bundle_id = f"mascotrender-b{bundle_version}-{identity_digest.hexdigest()[:12]}"
        bundle_root = staging / "bundles" / bundle_id
        catalogue_path = bundle_root / "catalogue.json"
        dictionary_path = bundle_root / "dictionary.json"
        catalogue_path.parent.mkdir(parents=True, exist_ok=True)
        catalogue_path.write_bytes(catalogue_payload)
        dictionary_path.write_bytes(dictionary_payload)
        release = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "bundle_id": bundle_id,
            "catalogue": {
                "path": f"bundles/{bundle_id}/catalogue.json",
                "sha256": sha256_bytes(catalogue_payload),
            },
            "dictionary": {
                "path": f"bundles/{bundle_id}/dictionary.json",
                "sha256": sha256_bytes(dictionary_payload),
            },
            "sticker_count": validated["sticker_count"],
            "animated_sticker_count": validated["animated_sticker_count"],
        }
        release_path = bundle_root / "release.json"
        release_payload = write_json(release_path, release)
        pointer = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "channel": channel,
            "bundle_id": bundle_id,
            "release_path": f"bundles/{bundle_id}/release.json",
            "release_sha256": sha256_bytes(release_payload),
        }
        pointer_path = staging / "channels" / f"{channel}.json"
        write_json(pointer_path, pointer)

        previous: set[tuple[str, str]] = set()
        if previous_plan_path is not None:
            _, previous_plan = read_json(previous_plan_path.resolve())
            previous = {
                (str(item.get("object_key", "")), str(item.get("sha256", "")))
                for item in previous_plan.get("objects", [])
                if isinstance(item, dict)
            }

        objects: list[dict[str, Any]] = []
        staged_files = sorted(
            path for path in staging.rglob("*")
            if path.is_file() and path.name != "publish-plan.json"
        )
        for path in staged_files:
            relative = path.relative_to(staging).as_posix()
            digest = sha256_file(path)
            immutable = not relative.startswith("channels/")
            objects.append(
                {
                    "local_path": relative,
                    "object_key": relative,
                    "sha256": digest,
                    "encoded_bytes": path.stat().st_size,
                    "content_type": content_type(path),
                    "cache_control": (
                        IMMUTABLE_CACHE_CONTROL if immutable else POINTER_CACHE_CONTROL
                    ),
                    "action": "skip" if (relative, digest) in previous else "upload",
                }
            )
        plan = {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "bundle_id": bundle_id,
            "channel": channel,
            "object_count": len(objects),
            "upload_count": sum(item["action"] == "upload" for item in objects),
            "skip_count": sum(item["action"] == "skip" for item in objects),
            "objects": objects,
        }
        write_json(staging / "publish-plan.json", plan)
        replace_directory(staging, destination, force)
        return plan
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Verify a source bundle")
    validate.add_argument("--bundle", type=Path, required=True)
    stage = subparsers.add_parser(
        "stage",
        help="Create content-addressed objects, an immutable release, and a channel pointer",
    )
    stage.add_argument("--bundle", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    stage.add_argument("--channel", default="stable")
    stage.add_argument("--previous-plan", type=Path)
    stage.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validated = validate_bundle(args.bundle)
    if args.command == "validate":
        print(
            json.dumps(
                {
                    "status": "success",
                    "protocol": PROTOCOL,
                    "sticker_count": validated["sticker_count"],
                    "animated_sticker_count": validated["animated_sticker_count"],
                    "phrase_count": validated["phrase_count"],
                    "trigger_count": validated["trigger_count"],
                    "catalogue_sha256": validated["catalogue_sha256"],
                    "dictionary_sha256": validated["dictionary_sha256"],
                },
                indent=2,
            )
        )
        return 0
    plan = stage_release(
        validated,
        args.output,
        args.channel,
        args.previous_plan,
        args.force,
    )
    print(
        f"staged {plan['bundle_id']} with {plan['upload_count']} uploads "
        f"and {plan['skip_count']} unchanged objects at {args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BundleError as error:
        print(f"mascot-bundle: {error}", file=sys.stderr)
        raise SystemExit(2) from error
