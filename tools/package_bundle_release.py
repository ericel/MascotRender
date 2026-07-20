#!/usr/bin/env python3
"""Create a deterministic, approval-bound public bundle release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path
from typing import Any


ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class ReleaseArchiveError(ValueError):
    """Raised when release inputs do not match their immutable records."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseArchiveError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReleaseArchiveError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseArchiveError(f"{field} must be a non-empty string")
    return value


def require_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReleaseArchiveError(f"{field} must be a non-negative integer")
    return value


def require_hash(value: object, field: str) -> str:
    digest = require_string(value, field)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ReleaseArchiveError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def safe_path(value: object, field: str) -> Path:
    text = require_string(value, field).replace("\\", "/")
    path = Path(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseArchiveError(f"{field} must be a safe relative path")
    return path


def verify_hash(path: Path, expected: object, field: str) -> None:
    expected_hash = require_hash(expected, field)
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ReleaseArchiveError(
            f"{path} SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
        )


def validate_release(
    distribution: Path,
    source_bundle: Path,
    approval_path: Path,
) -> tuple[str, list[Path], bytes]:
    distribution = distribution.resolve()
    source_bundle = source_bundle.resolve()
    approval_path = approval_path.resolve()
    plan_path = distribution / "publish-plan.json"
    plan = read_json(plan_path)
    approval = read_json(approval_path)

    if approval.get("authority") != "project-owner" or approval.get("decision") != "approved":
        raise ReleaseArchiveError("owner approval must be an approved project-owner decision")
    if approval.get("production_use") != "approved-for-public-production":
        raise ReleaseArchiveError("owner approval does not permit public production use")

    candidate = approval.get("candidate")
    artifacts = approval.get("candidate_artifacts")
    if not isinstance(candidate, dict) or not isinstance(artifacts, dict):
        raise ReleaseArchiveError("owner approval must declare candidate and candidate_artifacts")

    bundle_id = require_string(plan.get("bundle_id"), "publish-plan.bundle_id")
    object_count = require_integer(plan.get("object_count"), "publish-plan.object_count")
    if candidate.get("bundle_id") != bundle_id:
        raise ReleaseArchiveError("approved bundle ID does not match publish plan")
    if candidate.get("object_count") != object_count:
        raise ReleaseArchiveError("approved object count does not match publish plan")

    verify_hash(source_bundle / "catalogue.json", artifacts.get("catalogue.json"), "catalogue")
    verify_hash(source_bundle / "dictionary.json", artifacts.get("dictionary.json"), "dictionary")
    verify_hash(
        source_bundle / "build-report.json",
        artifacts.get("build-report.json"),
        "build-report",
    )
    channel_relative = Path("channels/micro-reactions-stable.json")
    verify_hash(
        distribution / channel_relative,
        artifacts.get(channel_relative.as_posix()),
        "channel",
    )
    verify_hash(
        distribution / "bundles" / bundle_id / "release.json",
        artifacts.get("release.json"),
        "release",
    )
    verify_hash(plan_path, artifacts.get("publish-plan.json"), "publish-plan")

    objects = plan.get("objects")
    if not isinstance(objects, list) or len(objects) != object_count:
        raise ReleaseArchiveError("publish-plan.objects does not match object_count")

    files: list[Path] = []
    expected_files = {Path("publish-plan.json")}
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            raise ReleaseArchiveError(f"publish-plan.objects[{index}] must be an object")
        local_path = safe_path(item.get("local_path"), f"objects[{index}].local_path")
        object_key = safe_path(item.get("object_key"), f"objects[{index}].object_key")
        if local_path != object_key:
            raise ReleaseArchiveError(f"objects[{index}] local_path and object_key differ")
        path = (distribution / local_path).resolve()
        try:
            path.relative_to(distribution)
        except ValueError as error:
            raise ReleaseArchiveError(f"objects[{index}] escapes the distribution") from error
        if not path.is_file():
            raise ReleaseArchiveError(f"missing distribution object: {local_path}")
        verify_hash(path, item.get("sha256"), f"objects[{index}].sha256")
        encoded_bytes = require_integer(
            item.get("encoded_bytes"),
            f"objects[{index}].encoded_bytes",
        )
        if path.stat().st_size != encoded_bytes:
            raise ReleaseArchiveError(f"{local_path} encoded byte count does not match")
        expected_files.add(local_path)
        files.append(local_path)

    actual_files = {
        path.relative_to(distribution)
        for path in distribution.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        extra = sorted(path.as_posix() for path in actual_files - expected_files)
        missing = sorted(path.as_posix() for path in expected_files - actual_files)
        raise ReleaseArchiveError(
            f"distribution file set differs from publish plan; extra={extra}, missing={missing}"
        )

    approval_bytes = approval_path.read_bytes()
    return bundle_id, sorted(expected_files), approval_bytes


def archive_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ARCHIVE_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build_archive(
    distribution: Path,
    files: list[Path],
    approval_bytes: bytes,
    bundle_id: str,
    output: Path,
) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    root = f"mascotrender-micro-reactions-{bundle_id}"
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative in files:
            archive.writestr(
                archive_info(f"{root}/{relative.as_posix()}"),
                (distribution / relative).read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
        archive.writestr(
            archive_info(f"{root}/owner-approval.json"),
            approval_bytes,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    return sha256_file(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", type=Path, required=True)
    parser.add_argument("--source-bundle", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--checksum",
        type=Path,
        help="checksum output (defaults to <output>.sha256)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_id, files, approval_bytes = validate_release(
        args.distribution,
        args.source_bundle,
        args.approval,
    )
    digest = build_archive(
        args.distribution.resolve(),
        files,
        approval_bytes,
        bundle_id,
        args.output.resolve(),
    )
    checksum = args.checksum or Path(f"{args.output}.sha256")
    checksum.parent.mkdir(parents=True, exist_ok=True)
    checksum.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "bundle_id": bundle_id,
                "distribution_object_count": len(files) - 1,
                "archive_entry_count": len(files) + 1,
                "archive": str(args.output),
                "sha256": digest,
                "checksum": str(checksum),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
