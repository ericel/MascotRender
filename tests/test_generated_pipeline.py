#!/usr/bin/env python3
"""End-to-end test for procedural pack generation and batch rendering."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )


def run_expect_failure(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {' '.join(command)}")


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--reviewer", type=Path, required=True)
    parser.add_argument("--bundle-tool", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--font-source", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="mascotrender-pipeline-") as temporary:
        root = Path(temporary)
        generated_a = root / "generated-a"
        generated_b = root / "generated-b"
        generated_species = root / "generated-species"
        bundle_a = root / "bundle-a"
        bundle_b = root / "bundle-b"

        generate_base = [
            args.python,
            str(args.generator),
            "--count",
            "2",
            "--seed",
            "123456789",
            "--font-source",
            str(args.font_source),
        ]
        run(generate_base + ["--output", str(generated_a)])
        run(generate_base + ["--output", str(generated_b)])
        if tree_digest(generated_a) != tree_digest(generated_b):
            raise AssertionError("same seed did not generate byte-identical mascot packs")

        run(
            [
                args.python,
                str(args.generator),
                "--count",
                "5",
                "--seed",
                "20260713",
                "--font-source",
                str(args.font_source),
                "--output",
                str(generated_species),
            ]
        )
        species_manifest = json.loads(
            (generated_species / "generation-manifest.json").read_text()
        )
        if species_manifest["generator_version"] != 7:
            raise AssertionError("unexpected mascot generator version")
        primary_colors = {
            item["palette"]["primary"] for item in species_manifest["packs"]
        }
        if len(primary_colors) != 5:
            raise AssertionError("canonical species must have distinct primary colors")
        expected_preferences: dict[str, list[str]] = {}
        for species, number in (
            ("cat", 1),
            ("bear", 2),
            ("bunny", 3),
            ("robot", 4),
            ("alien", 5),
        ):
            pack_root = generated_species / f"generated-{species}-{number:03d}"
            pack = json.loads((pack_root / "pack.json").read_text())
            body_layers = {
                layer["id"]: layer for layer in pack["layers"]
            }
            for body_id in ("body-front", "body-round"):
                if "collision_bounds" not in body_layers[body_id]:
                    raise AssertionError(
                        f"{species} {body_id} has no collision bounds"
                    )
            if pack.get("text_clearance") != 14:
                raise AssertionError(f"{species} has unexpected text clearance")
            bottom = pack["text_slots"]["bottom"]
            if bottom["y"] + bottom["height"] > 464:
                raise AssertionError(f"{species} bottom caption lacks safe margin")
            for sticker_path in (pack_root / "stickers").glob("*.json"):
                sticker = json.loads(sticker_path.read_text())
                preferences = sticker["text"]["preferred_slots"]
                if sticker_path.name in expected_preferences:
                    if preferences != expected_preferences[sticker_path.name]:
                        raise AssertionError(
                            "caption placement contains a species override"
                        )
                else:
                    expected_preferences[sticker_path.name] = preferences
                if preferences not in (["top", "bottom"], ["bottom", "top"]):
                    raise AssertionError(
                        f"{species} has invalid caption preferences"
                    )
        alien_eyes = (
            generated_species
            / "generated-alien-005"
            / "layers"
            / "22-eyes-surprised.svg"
        ).read_text()
        bunny_eyes = (
            generated_species
            / "generated-bunny-003"
            / "layers"
            / "22-eyes-surprised.svg"
        ).read_text()
        if alien_eyes.count("<ellipse") != 3 or bunny_eyes.count("<ellipse") != 2:
            raise AssertionError("alien and bunny expression rigs are not distinct")
        alien_body = (
            generated_species
            / "generated-alien-005"
            / "layers"
            / "10-body-front.svg"
        ).read_text()
        if '<rect x="122" y="118" width="268" height="272"' not in alien_body:
            raise AssertionError("alien does not use the shared rounded-square body")
        if 'fill-opacity="0.65"' in alien_body or 'r="6"' in alien_body:
            raise AssertionError("alien contains out-of-family decorative details")

        render_base = [
            args.python,
            str(args.renderer),
            "--mascotrender",
            str(args.cli),
            "--quality",
            "90",
            "--width",
            "128",
            "--height",
            "128",
            "--thumbnail-size",
            "64",
        ]
        run(render_base + ["--input", str(generated_a), "--output", str(bundle_a)])
        run(render_base + ["--input", str(generated_b), "--output", str(bundle_b)])
        if tree_digest(bundle_a) != tree_digest(bundle_b):
            raise AssertionError("same generated input did not render a byte-identical bundle")

        review_a = bundle_a / "review"
        review_b = bundle_b / "review"
        review_base = [
            args.python,
            str(args.reviewer),
            "--expected-count",
            "20",
        ]
        run(review_base + ["--input", str(bundle_a)])
        run(review_base + ["--input", str(bundle_b)])
        if tree_digest(review_a) != tree_digest(review_b):
            raise AssertionError("same bundle did not produce a byte-identical review")

        release_a = root / "release-a"
        release_b = root / "release-b"
        run(
            [
                args.python,
                str(args.bundle_tool),
                "validate",
                "--bundle",
                str(bundle_a),
            ]
        )
        run(
            [
                args.python,
                str(args.bundle_tool),
                "stage",
                "--bundle",
                str(bundle_a),
                "--output",
                str(release_a),
                "--channel",
                "stable",
            ]
        )
        run(
            [
                args.python,
                str(args.bundle_tool),
                "stage",
                "--bundle",
                str(bundle_a),
                "--output",
                str(release_b),
                "--channel",
                "stable",
                "--previous-plan",
                str(release_a / "publish-plan.json"),
            ]
        )
        publish_plan = json.loads((release_b / "publish-plan.json").read_text())
        if (
            publish_plan["upload_count"] != 0
            or publish_plan["skip_count"] != publish_plan["object_count"]
        ):
            raise AssertionError("unchanged content was not skipped by incremental staging")
        pointer = json.loads((release_b / "channels" / "stable.json").read_text())
        release = json.loads(
            (release_b / pointer["release_path"]).read_text()
        )
        distributed_catalogue = json.loads(
            (release_b / release["catalogue"]["path"]).read_text()
        )
        if not all(
            item["path"].startswith("objects/sha256/")
            and item["thumbnail"]["path"].startswith("objects/sha256/")
            and item["reduced_motion"]["path"].startswith("objects/sha256/")
            for item in distributed_catalogue["stickers"]
        ):
            raise AssertionError("release catalogue is not content-addressed")
        pointer_object = next(
            item
            for item in publish_plan["objects"]
            if item["object_key"] == "channels/stable.json"
        )
        if pointer_object["cache_control"] != "no-cache,max-age=0,must-revalidate":
            raise AssertionError("mutable channel pointer has unsafe cache policy")
        if any(
            item["cache_control"] != "public,max-age=31536000,immutable"
            for item in publish_plan["objects"]
            if item["object_key"] != "channels/stable.json"
        ):
            raise AssertionError("immutable release object has unsafe cache policy")
        dictionary_variant_bundle = root / "bundle-dictionary-variant"
        shutil.copytree(bundle_a, dictionary_variant_bundle)
        dictionary_variant = json.loads(
            (dictionary_variant_bundle / "dictionary.json").read_text()
        )
        dictionary_variant["entries"][0]["trigger"] += "-variant"
        (dictionary_variant_bundle / "dictionary.json").write_text(
            json.dumps(dictionary_variant, indent=2) + "\n"
        )
        release_variant = root / "release-dictionary-variant"
        run(
            [
                args.python,
                str(args.bundle_tool),
                "stage",
                "--bundle",
                str(dictionary_variant_bundle),
                "--output",
                str(release_variant),
                "--channel",
                "stable",
            ]
        )
        variant_pointer = json.loads(
            (release_variant / "channels" / "stable.json").read_text()
        )
        if variant_pointer["bundle_id"] == pointer["bundle_id"]:
            raise AssertionError("dictionary change reused an immutable bundle ID")

        manifest = json.loads((generated_a / "generation-manifest.json").read_text())
        catalogue = json.loads((bundle_a / "catalogue.json").read_text())
        dictionary = json.loads((bundle_a / "dictionary.json").read_text())
        report = json.loads((bundle_a / "build-report.json").read_text())
        review_summary = json.loads((review_a / "review-summary.json").read_text())

        corrupt_bundle = root / "bundle-corrupt"
        shutil.copytree(bundle_a, corrupt_bundle)
        first_thumbnail = corrupt_bundle / catalogue["stickers"][0]["thumbnail"]["path"]
        corrupted = bytearray(first_thumbnail.read_bytes())
        corrupted[-1] ^= 0x01
        first_thumbnail.write_bytes(corrupted)
        run_expect_failure(review_base + ["--input", str(corrupt_bundle), "--force"])
        run_expect_failure(
            [
                args.python,
                str(args.bundle_tool),
                "validate",
                "--bundle",
                str(corrupt_bundle),
            ]
        )
        if (
            manifest["pack_count"] != 2
            or manifest["sticker_count"] != 20
            or manifest["animated_sticker_count"] != 8
        ):
            raise AssertionError("unexpected generation manifest counts")
        if (
            catalogue["sticker_count"] != 20
            or catalogue["animated_sticker_count"] != 8
            or len(catalogue["stickers"]) != 20
        ):
            raise AssertionError("unexpected catalogue counts")
        animated = [item for item in catalogue["stickers"] if item["animated"]]
        if len(animated) != 8:
            raise AssertionError(f"expected 8 animated stickers, got {len(animated)}")
        for item in animated:
            asset = bundle_a / item["path"]
            thumbnail = bundle_a / item["thumbnail"]["path"]
            reduced = bundle_a / item["reduced_motion"]["path"]
            if b"ANIM" not in asset.read_bytes():
                raise AssertionError(f"animated asset has no ANIM chunk: {asset}")
            if b"ANIM" in thumbnail.read_bytes():
                raise AssertionError(f"thumbnail must be a static poster: {thumbnail}")
            if b"ANIM" in reduced.read_bytes():
                raise AssertionError(
                    f"reduced-motion output must be static: {reduced}"
                )
            if item["animation"]["duration_ms"] != 800:
                raise AssertionError("unexpected animation metadata")
        if any(
            item["width"] != 128
            or item["height"] != 128
            or item["thumbnail"]["width"] != 64
            or item["thumbnail"]["height"] != 64
            for item in catalogue["stickers"]
        ):
            raise AssertionError("unexpected integration-test output dimensions")
        if dictionary["trigger_count"] != 10 or len(dictionary["entries"]) != 10:
            raise AssertionError("unexpected dictionary counts")
        if any(
            set(entry) != {"trigger", "match", "phrase_ids"}
            or not entry["phrase_ids"]
            for entry in dictionary["entries"]
        ):
            raise AssertionError("Trie dictionary terminals are not semantic phrase IDs")
        if (
            report["asset_count"] != 60
            or report["reduced_motion_sticker_count"] != 20
            or report["animated_sticker_count"] != 8
            or report["status"] != "success"
        ):
            raise AssertionError("unexpected build report")
        if (
            review_summary["verification_status"] != "success"
            or review_summary["review_status"]
            != "awaiting_design_product_approval"
            or review_summary["pack_count"] != 2
            or review_summary["sticker_count"] != 20
            or review_summary["animated_sticker_count"] != 8
            or review_summary["asset_count"] != 60
            or review_summary["reduced_motion_sticker_count"] != 20
        ):
            raise AssertionError("unexpected review summary")

        with (review_a / "checklist.csv").open(encoding="utf-8", newline="") as source:
            checklist = list(csv.DictReader(source))
        if len(checklist) != 20:
            raise AssertionError("review checklist does not contain every sticker")
        expected_keys = {
            (str(item["pack_id"]), str(item["sticker_id"]))
            for item in catalogue["stickers"]
        }
        checklist_keys = {(row["pack_id"], row["sticker_id"]) for row in checklist}
        if checklist_keys != expected_keys:
            raise AssertionError("review checklist entries do not match the catalogue")
        gallery = (review_a / "index.html").read_text(encoding="utf-8")
        if gallery.count('<article class="card"') != 20:
            raise AssertionError("review gallery does not contain every sticker")
        if gallery.count('<span class="badge animated">') != 8:
            raise AssertionError("review gallery has incorrect animation badges")
        animation_gallery = (review_a / "animation-review.html").read_text(
            encoding="utf-8"
        )
        if animation_gallery.count('class="motion"') != 8:
            raise AssertionError("animation review does not contain every animation")

        webps = sorted(bundle_a.rglob("*.webp"))
        if len(webps) != 60:
            raise AssertionError(f"expected 60 rendered WebPs, got {len(webps)}")
        for webp in webps:
            data = webp.read_bytes()
            if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
                raise AssertionError(f"invalid WebP output: {webp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
