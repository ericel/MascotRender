#!/usr/bin/env python3
"""Build or verify a deterministic draft-v1 .mascot container."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_BYTES = 128 * 1024 * 1024
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def fail(message: str) -> None:
    raise ValueError(message)


def safe_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        fail(f"{label} is not a safe portable path")
    path = PurePosixPath(value)
    if (path.is_absolute() or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in path.parts)):
        fail(f"{label} is not a safe portable path: {value!r}")
    return path.as_posix()


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def validate_manifest(document: dict[str, Any]) -> list[dict[str, str]]:
    if document.get("format_version") != 1:
        fail("manifest format_version must be 1")
    for field in ("package_id", "package_version", "character_id", "status", "engine", "entry_points", "capabilities"):
        if field not in document:
            fail(f"manifest is missing {field}")
    if document["status"] not in {"technical-fixture", "review-candidate", "production"}:
        fail("manifest has an invalid status")
    files = document.get("files")
    if not isinstance(files, list) or len(files) < 2:
        fail("manifest requires at least two declared files")
    by_path: dict[str, dict[str, str]] = {}
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            fail(f"files[{index}] must be an object")
        path = safe_path(item.get("path"), f"files[{index}].path")
        sha = item.get("sha256")
        role = item.get("role")
        if path == "manifest.json" or path in by_path:
            fail(f"duplicate or reserved package path: {path}")
        if not isinstance(sha, str) or len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            fail(f"files[{index}].sha256 must be lowercase SHA-256")
        if not isinstance(role, str) or not role:
            fail(f"files[{index}].role is required")
        by_path[path] = {"path": path, "sha256": sha, "role": role}

    entry_points = document.get("entry_points")
    if not isinstance(entry_points, dict) or not {"identity", "rig"}.issubset(entry_points):
        fail("manifest requires identity and rig entry points")
    for name, value in entry_points.items():
        path = safe_path(value, f"entry_points.{name}")
        if path not in by_path:
            fail(f"entry point {name} is not declared in files: {path}")
    for group in ("licenses", "provenance"):
        values = document.get(group)
        if not isinstance(values, list) or not values:
            fail(f"manifest requires at least one {group} path")
        for index, value in enumerate(values):
            path = safe_path(value, f"{group}[{index}]")
            if path not in by_path:
                fail(f"{group} path is not declared in files: {path}")
    if document["status"] == "production":
        for name in ("accessibility", "review"):
            if name not in entry_points:
                fail(f"production package requires entry_points.{name}")
    return [by_path[path] for path in sorted(by_path)]


def zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build(source: Path, manifest_path: Path, output: Path) -> None:
    source = source.resolve()
    manifest_path = manifest_path.resolve()
    if not source.is_dir() or not manifest_path.is_file():
        fail("source directory and manifest file must exist")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        fail("manifest must be a JSON object")
    declared = validate_manifest(document)
    payloads: dict[str, bytes] = {}
    total = 0
    for item in declared:
        path = source.joinpath(*PurePosixPath(item["path"]).parts)
        if path.is_symlink() or not path.is_file():
            fail(f"declared package file is missing or is a symlink: {item['path']}")
        payload = path.read_bytes()
        if len(payload) > MAX_FILE_BYTES:
            fail(f"declared package file exceeds size limit: {item['path']}")
        if digest(payload) != item["sha256"]:
            fail(f"SHA-256 mismatch for {item['path']}")
        payloads[item["path"]] = payload
        total += len(payload)
    if total > MAX_PACKAGE_BYTES:
        fail("declared package payload exceeds size limit")

    manifest_payload = canonical_json(document)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", allowZip64=False) as archive:
            entries = {"manifest.json": manifest_payload, **payloads}
            for path in sorted(entries):
                archive.writestr(zip_info(path), entries[path])
        temporary_path.replace(output)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def verify(package: Path) -> dict[str, Any]:
    package = package.resolve()
    if not package.is_file() or package.stat().st_size > MAX_PACKAGE_BYTES:
        fail("package is missing or exceeds size limit")
    with zipfile.ZipFile(package, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or names != sorted(names):
            fail("package entries must be unique and bytewise sorted")
        for name in names:
            safe_path(name, "archive entry")
        for info in archive.infolist():
            if info.compress_type != zipfile.ZIP_STORED:
                fail(f"draft-v1 entry is not stored: {info.filename}")
            if info.flag_bits & 0x1:
                fail(f"encrypted entries are not supported: {info.filename}")
            if info.date_time != FIXED_ZIP_TIME:
                fail(f"entry timestamp is not deterministic: {info.filename}")
            if info.file_size > MAX_FILE_BYTES:
                fail(f"archive entry exceeds size limit: {info.filename}")
        if "manifest.json" not in names:
            fail("package has no manifest.json")
        document = json.loads(archive.read("manifest.json").decode("utf-8"))
        if not isinstance(document, dict):
            fail("manifest must be a JSON object")
        declared = validate_manifest(document)
        expected = {"manifest.json", *(item["path"] for item in declared)}
        if set(names) != expected:
            fail("archive contains missing or undeclared entries")
        total = 0
        for item in declared:
            info = archive.getinfo(item["path"])
            if info.is_dir() or info.file_size > MAX_FILE_BYTES:
                fail(f"invalid declared archive entry: {item['path']}")
            payload = archive.read(info)
            total += len(payload)
            if digest(payload) != item["sha256"]:
                fail(f"SHA-256 mismatch for {item['path']}")
        if total > MAX_PACKAGE_BYTES:
            fail("package payload exceeds size limit")
    return document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    builder = subparsers.add_parser("build", help="build a deterministic package")
    builder.add_argument("--source", type=Path, required=True)
    builder.add_argument("--manifest", type=Path, required=True)
    builder.add_argument("--output", type=Path, required=True)
    verifier = subparsers.add_parser("verify", help="verify a package")
    verifier.add_argument("--input", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        build(args.source, args.manifest, args.output)
        document = verify(args.output)
        print(f"built {document['package_id']}@{document['package_version']} at {args.output.resolve()}")
    else:
        document = verify(args.input)
        print(f"valid {document['package_id']}@{document['package_version']}: {args.input.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
