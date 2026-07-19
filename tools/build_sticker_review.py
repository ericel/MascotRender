#!/usr/bin/env python3
"""Verify a MascotRender bundle and build its deterministic review gallery."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote


REVIEW_VERSION = 1
PROTOCOL = "mascotrender-bundle-v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CRITERIA = (
    ("caption_readability", "Caption is immediately readable at thumbnail size"),
    ("caption_clipping", "Caption and outline are not clipped"),
    ("transparency_edges", "Transparent edges and silhouette are clean"),
    ("expression_pose", "Expression and pose match the phrase"),
    ("animation_motion", "Animation is clean and preserves readability, or is N/A"),
    ("pack_coherence", "Palette, line weight, and styling match the pack"),
)


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
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


def require_int(value: object, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}: {value!r}")
    return value


def require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string: {value!r}")
    return value


def require_id(value: object, field: str) -> str:
    result = require_string(value, field)
    if not SAFE_ID.fullmatch(result):
        raise ValueError(f"{field} must be filesystem-safe: {result!r}")
    return result


def checked_file(
    bundle: Path,
    metadata: dict[str, object],
    field: str,
) -> Path:
    relative_value = require_string(metadata.get("path"), f"{field}.path")
    relative = Path(relative_value)
    if relative.is_absolute():
        raise ValueError(f"{field}.path must be relative: {relative_value!r}")
    path = (bundle / relative).resolve()
    try:
        path.relative_to(bundle)
    except ValueError as error:
        raise ValueError(f"{field}.path escapes the bundle: {relative_value!r}") from error
    if not path.is_file():
        raise FileNotFoundError(f"missing {field}: {path}")

    expected_size = require_int(metadata.get("encoded_bytes"), f"{field}.encoded_bytes")
    if path.stat().st_size != expected_size:
        raise ValueError(
            f"{field} size mismatch for {relative_value}: "
            f"expected {expected_size}, got {path.stat().st_size}"
        )
    expected_hash = require_string(metadata.get("sha256"), f"{field}.sha256")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"{field} SHA-256 mismatch for {relative_value}: "
            f"expected {expected_hash}, got {actual_hash}"
        )
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"{field} is not a WebP: {relative_value}")
    return path


def verify_bundle(
    bundle: Path,
    expected_count: int | None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    catalogue_path = bundle / "catalogue.json"
    report_path = bundle / "build-report.json"
    catalogue = read_json(catalogue_path)
    report = read_json(report_path)
    for label, document in (("catalogue", catalogue), ("build-report", report)):
        if document.get("schema_version") != 1 or document.get("protocol") != PROTOCOL:
            raise ValueError(
                f"{label} must declare schema_version 1 and protocol {PROTOCOL}"
            )
    stickers_value = catalogue.get("stickers")
    if not isinstance(stickers_value, list):
        raise ValueError("catalogue.stickers must be an array")

    catalogue_count = require_int(catalogue.get("sticker_count"), "sticker_count")
    if catalogue_count != len(stickers_value):
        raise ValueError("catalogue sticker_count does not match its sticker array")
    if expected_count is not None and catalogue_count != expected_count:
        raise ValueError(
            f"expected {expected_count} stickers, catalogue contains {catalogue_count}"
        )

    stickers: list[dict[str, object]] = []
    keys: set[tuple[str, str]] = set()
    animated_count = 0
    encoded_bytes = 0
    pack_ids: set[str] = set()
    for index, value in enumerate(stickers_value):
        if not isinstance(value, dict):
            raise ValueError(f"stickers[{index}] must be an object")
        pack_id = require_id(value.get("pack_id"), f"stickers[{index}].pack_id")
        sticker_id = require_id(value.get("sticker_id"), f"stickers[{index}].sticker_id")
        key = (pack_id, sticker_id)
        if key in keys:
            raise ValueError(f"duplicate catalogue entry: {pack_id}/{sticker_id}")
        keys.add(key)
        pack_ids.add(pack_id)
        require_string(value.get("text"), f"{pack_id}/{sticker_id}.text")
        require_string(value.get("alt_text"), f"{pack_id}/{sticker_id}.alt_text")
        require_string(value.get("phrase_id"), f"{pack_id}/{sticker_id}.phrase_id")
        require_int(value.get("width"), f"{pack_id}/{sticker_id}.width", 1)
        require_int(value.get("height"), f"{pack_id}/{sticker_id}.height", 1)

        animated = value.get("animated")
        if not isinstance(animated, bool):
            raise ValueError(f"{pack_id}/{sticker_id}.animated must be a boolean")
        if animated != isinstance(value.get("animation"), dict):
            raise ValueError(
                f"{pack_id}/{sticker_id} animation metadata is inconsistent"
            )
        if animated:
            animated_count += 1

        asset = checked_file(bundle, value, f"{pack_id}/{sticker_id} asset")
        thumbnail_value = value.get("thumbnail")
        if not isinstance(thumbnail_value, dict):
            raise ValueError(f"{pack_id}/{sticker_id}.thumbnail must be an object")
        require_int(
            thumbnail_value.get("width"),
            f"{pack_id}/{sticker_id}.thumbnail.width",
            1,
        )
        require_int(
            thumbnail_value.get("height"),
            f"{pack_id}/{sticker_id}.thumbnail.height",
            1,
        )
        thumbnail = checked_file(
            bundle,
            thumbnail_value,
            f"{pack_id}/{sticker_id} thumbnail",
        )
        reduced_value = value.get("reduced_motion")
        if not isinstance(reduced_value, dict):
            raise ValueError(f"{pack_id}/{sticker_id}.reduced_motion must be an object")
        if reduced_value.get("presentation") != "static-semantic-equivalent":
            raise ValueError(
                f"{pack_id}/{sticker_id}.reduced_motion presentation is invalid"
            )
        require_int(
            reduced_value.get("width"),
            f"{pack_id}/{sticker_id}.reduced_motion.width",
            1,
        )
        require_int(
            reduced_value.get("height"),
            f"{pack_id}/{sticker_id}.reduced_motion.height",
            1,
        )
        reduced = checked_file(
            bundle,
            reduced_value,
            f"{pack_id}/{sticker_id} reduced motion",
        )
        asset_animated = b"ANIM" in asset.read_bytes()
        if asset_animated != animated:
            raise ValueError(
                f"{pack_id}/{sticker_id} animation metadata does not match the WebP"
            )
        if b"ANIM" in thumbnail.read_bytes():
            raise ValueError(f"{pack_id}/{sticker_id} thumbnail must be a static poster")
        if b"ANIM" in reduced.read_bytes():
            raise ValueError(
                f"{pack_id}/{sticker_id} reduced motion must be a static semantic equivalent"
            )
        encoded_bytes += (
            asset.stat().st_size
            + thumbnail.stat().st_size
            + reduced.stat().st_size
        )
        stickers.append(value)

    declared_animated = require_int(
        catalogue.get("animated_sticker_count"), "animated_sticker_count"
    )
    if declared_animated != animated_count:
        raise ValueError("catalogue animated_sticker_count does not match its entries")
    expected_report = {
        "status": "success",
        "pack_count": len(pack_ids),
        "sticker_count": len(stickers),
        "animated_sticker_count": animated_count,
        "asset_count": len(stickers) * 3,
        "reduced_motion_sticker_count": len(stickers),
        "encoded_bytes": encoded_bytes,
    }
    for field, expected in expected_report.items():
        if report.get(field) != expected:
            raise ValueError(
                f"build-report {field} mismatch: expected {expected!r}, "
                f"got {report.get(field)!r}"
            )

    ordered = sorted(
        stickers,
        key=lambda item: (str(item["pack_id"]), str(item["sticker_id"])),
    )
    summary: dict[str, object] = {
        "schema_version": 1,
        "review_version": REVIEW_VERSION,
        "verification_status": "success",
        "catalogue_sha256": sha256_file(catalogue_path),
        "build_report_sha256": sha256_file(report_path),
        "pack_count": len(pack_ids),
        "sticker_count": len(stickers),
        "animated_sticker_count": animated_count,
        "asset_count": len(stickers) * 3,
        "reduced_motion_sticker_count": len(stickers),
        "encoded_bytes": encoded_bytes,
        "review_status": "awaiting_design_product_approval",
        "criteria": [
            {"id": criterion_id, "description": description}
            for criterion_id, description in CRITERIA
        ],
    }
    return ordered, summary


def relative_url(output: Path, target: Path) -> str:
    relative = os.path.relpath(target, output).replace(os.sep, "/")
    return quote(relative, safe="/.-_~")


def build_checklist(path: Path, stickers: list[dict[str, object]]) -> None:
    fields = [
        "pack_id",
        "sticker_id",
        "text",
        "expression",
        "pose",
        "animated",
        *(criterion_id for criterion_id, _ in CRITERIA),
        "decision",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for sticker in stickers:
            writer.writerow(
                {
                    "pack_id": sticker["pack_id"],
                    "sticker_id": sticker["sticker_id"],
                    "text": sticker["text"],
                    "expression": sticker.get("expression") or "",
                    "pose": sticker.get("pose") or "",
                    "animated": "yes" if sticker["animated"] else "no",
                    **{criterion_id: "" for criterion_id, _ in CRITERIA},
                    "decision": "",
                    "notes": "",
                }
            )


def build_gallery(
    path: Path,
    output: Path,
    bundle: Path,
    stickers: list[dict[str, object]],
    summary: dict[str, object],
) -> None:
    groups: dict[str, list[dict[str, object]]] = {}
    for sticker in stickers:
        groups.setdefault(str(sticker["pack_id"]), []).append(sticker)

    sections: list[str] = []
    for pack_id, pack_stickers in groups.items():
        cards: list[str] = []
        for sticker in pack_stickers:
            asset = bundle / str(sticker["path"])
            thumbnail_value = sticker["thumbnail"]
            assert isinstance(thumbnail_value, dict)
            thumbnail = bundle / str(thumbnail_value["path"])
            animation_badge = (
                '<span class="badge animated">animated</span>'
                if sticker["animated"]
                else '<span class="badge">static</span>'
            )
            metadata = " · ".join(
                value
                for value in (
                    str(sticker.get("expression") or ""),
                    str(sticker.get("pose") or ""),
                )
                if value
            )
            cards.append(
                f'''<article class="card" id="{html.escape(str(sticker["sticker_id"]), quote=True)}">
  <a class="preview" href="{relative_url(output, asset)}" target="_blank" rel="noopener">
    <img src="{relative_url(output, thumbnail)}" alt="{html.escape(str(sticker["alt_text"]), quote=True)}" loading="lazy">
  </a>
  <div class="card-body">
    <div class="badges">{animation_badge}</div>
    <h3>{html.escape(str(sticker["text"]))}</h3>
    <p class="id">{html.escape(str(sticker["sticker_id"]))}</p>
    <p class="meta">{html.escape(metadata)}</p>
  </div>
</article>'''
            )
        sections.append(
            f'''<section class="pack">
  <h2>{html.escape(pack_id)} <span>{len(pack_stickers)} stickers</span></h2>
  <div class="grid">{"".join(cards)}</div>
</section>'''
        )

    criteria = "".join(
        f"<li><code>{html.escape(criterion_id)}</code> — {html.escape(description)}</li>"
        for criterion_id, description in CRITERIA
    )
    document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MascotRender {summary["sticker_count"]}-sticker review</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background: #0c1018; color: #f3f6fc; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
header, main {{ width: min(1520px, calc(100% - 32px)); margin: 0 auto; }}
header {{ padding: 42px 0 26px; }}
h1 {{ margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3.5rem); }}
.lede, .instructions {{ color: #b8c2d6; line-height: 1.6; max-width: 900px; }}
.summary {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0; }}
.summary span, .badge {{ border: 1px solid #35425a; border-radius: 999px; padding: 6px 11px; background: #151d2b; }}
.download {{ color: #8fc3ff; }}
.criteria {{ background: #121927; border: 1px solid #27344b; border-radius: 14px; padding: 12px 24px; }}
.criteria li {{ margin: 8px 0; color: #c6d0e1; }}
.pack {{ margin: 34px 0 52px; }}
.pack h2 {{ display: flex; align-items: baseline; gap: 12px; border-bottom: 1px solid #27344b; padding-bottom: 10px; }}
.pack h2 span {{ color: #8190a8; font-size: .9rem; font-weight: 500; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; }}
.card {{ overflow: hidden; border: 1px solid #27344b; border-radius: 15px; background: #121927; }}
.preview {{ display: block; aspect-ratio: 1; background: repeating-conic-gradient(#e9edf4 0 25%, #cdd4df 0 50%) 50% / 24px 24px; }}
.preview img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
.card-body {{ padding: 14px; min-height: 154px; }}
.badges {{ height: 27px; }}
.badge {{ display: inline-block; padding: 3px 8px; color: #9eabc0; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; }}
.badge.animated {{ color: #b9f6cb; border-color: #296a43; background: #123322; }}
h3 {{ margin: 12px 0 5px; font-size: 1.15rem; }}
.id, .meta {{ margin: 4px 0; color: #8190a8; font-size: .82rem; overflow-wrap: anywhere; }}
code {{ color: #a9d1ff; }}
@media print {{ :root {{ color-scheme: light; background: white; color: black; }} .card, .criteria {{ break-inside: avoid; background: white; border-color: #bbb; }} .lede, .instructions, .criteria li, .id, .meta {{ color: #333; }} .preview {{ background: white; }} }}
</style>
</head>
<body>
<header>
  <h1>MascotRender {summary["sticker_count"]}-sticker review</h1>
  <p class="lede">This gallery was generated only after every catalogue path, byte count, SHA-256 hash, WebP signature, animation flag, thumbnail poster, and build-report total passed verification.</p>
  <div class="summary">
    <span>{summary["pack_count"]} packs</span><span>{summary["sticker_count"]} stickers</span><span>{summary["animated_sticker_count"]} animated</span><span>{summary["asset_count"]} verified WebPs</span>
  </div>
  <p class="instructions">Review every card at thumbnail size, then click it to inspect the full static or animated asset. Play all animated phrases side by side in <a class="download" href="animation-review.html">animation-review.html</a>. Record <code>pass</code>, <code>fail</code>, or <code>n/a</code> for each criterion in <a class="download" href="checklist.csv">checklist.csv</a>; set each decision to <code>approve</code> or <code>revise</code>.</p>
  <ul class="criteria">{criteria}</ul>
</header>
<main>{"".join(sections)}</main>
</body>
</html>
'''
    path.write_text(document, encoding="utf-8", newline="\n")


def build_animation_gallery(
    path: Path,
    output: Path,
    bundle: Path,
    stickers: list[dict[str, object]],
) -> None:
    groups: dict[str, list[dict[str, object]]] = {}
    for sticker in stickers:
        if sticker["animated"]:
            groups.setdefault(str(sticker["pack_id"]), []).append(sticker)
    sections = []
    for pack_id, animated in groups.items():
        cards = "".join(
            f'''<article><img class="motion" src="{relative_url(output, bundle / str(sticker["path"]))}" alt="{html.escape(str(sticker["alt_text"]), quote=True)}"><h3>{html.escape(str(sticker["text"]))}</h3><p>{html.escape(str(sticker["sticker_id"]))}</p></article>'''
            for sticker in animated
        )
        sections.append(
            f'<section><h2>{html.escape(pack_id)}</h2><div class="grid">{cards}</div></section>'
        )
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MascotRender animation review</title>
<style>:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;background:#0c1018;color:#f3f6fc}}body{{width:min(1200px,calc(100% - 32px));margin:32px auto}}a{{color:#8fc3ff}}section{{margin:36px 0}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}}article{{background:#121927;border:1px solid #27344b;border-radius:14px;overflow:hidden}}img{{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:repeating-conic-gradient(#e9edf4 0 25%,#cdd4df 0 50%) 50%/24px 24px}}h3,p{{margin:10px 14px}}p{{color:#8190a8;font-size:.8rem;overflow-wrap:anywhere}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}</style></head>
<body><h1>Animated sticker play-through</h1><p>Watch each four-sticker row through several loops. Check easing, caption readability during motion, synchronized body/text motion, and the last-to-first loop seam. <a href="index.html">Return to the complete contact sheet.</a></p>{"".join(sections)}</body></html>
'''
    path.write_text(document, encoding="utf-8", newline="\n")


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=project_root / "generated" / "bundle",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing review directory",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    bundle = args.input.resolve()
    if not bundle.is_dir():
        raise FileNotFoundError(f"bundle directory not found: {bundle}")
    if args.expected_count is not None and args.expected_count < 1:
        raise ValueError("--expected-count must be at least 1")
    destination = (
        args.output.resolve() if args.output is not None else bundle / "review"
    )
    if destination == bundle:
        raise ValueError("--output must not replace the input bundle")
    try:
        bundle.relative_to(destination)
    except ValueError:
        pass
    else:
        raise ValueError("--output must not be an ancestor of the input bundle")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent)
    )
    try:
        stickers, summary = verify_bundle(bundle, args.expected_count)
        build_checklist(staging / "checklist.csv", stickers)
        write_json(staging / "review-summary.json", summary)
        build_gallery(staging / "index.html", destination, bundle, stickers, summary)
        build_animation_gallery(
            staging / "animation-review.html",
            destination,
            bundle,
            stickers,
        )
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    print(
        f"verified {summary['sticker_count']} stickers and wrote review to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
