#!/usr/bin/env python3
"""Validate human representation, rig, phrase, and motion contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from human_contracts import (
    read_json,
    sha256,
    validate_canonical_family,
    validate_contract_set,
    validate_production_rig,
    validate_production_standard,
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identities", type=Path, default=root / "examples/human-pilots/identities.json")
    parser.add_argument("--rig", type=Path, default=root / "contracts/humanoid-full-body-v1.json")
    parser.add_argument("--recipes", type=Path, default=root / "content/motion-recipes-core-v1.json")
    parser.add_argument("--lexicon", type=Path, default=root / "content/phrase-lexicon-core-v1.json")
    parser.add_argument("--production-standard", type=Path, default=root / "contracts/human-pack-production-v1.json")
    parser.add_argument("--production-rig", type=Path, default=root / "contracts/humanoid-production-v2.json")
    parser.add_argument("--canonical-family", type=Path, default=root / "contracts/human-canonical-family-v1.json")
    parser.add_argument("--canonical-asset", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identities, rig, recipes, phrases = validate_contract_set(
        args.identities.resolve(), args.rig.resolve(), args.recipes.resolve(), args.lexicon.resolve()
    )
    standard = validate_production_standard(read_json(args.production_standard.resolve()))
    production_rig = validate_production_rig(read_json(args.production_rig.resolve()))
    family = validate_canonical_family(
        read_json(args.canonical_family.resolve()),
        args.canonical_asset.resolve() if args.canonical_asset else None,
    )
    report = {
        "schema_version": 1,
        "status": "success",
        "asset_class": "technical-fixture",
        "production_use": "forbidden",
        "production_standard": standard["standard_id"],
        "production_rig": production_rig["rig_id"],
        "production_rig_joint_count": len(production_rig["joints"]),
        "canonical_family": family["family_id"],
        "canonical_family_status": family["status"],
        "canonical_family_scope": family["scope"],
        "identity_count": len(identities),
        "phrase_count": len(phrases),
        "recipe_count": len(recipes),
        "rig_joint_count": len(rig["joints"]),
        "skin_tone_scale": sorted({item["appearance"]["skin"]["tone_scale"] for item in identities}),
        "undertones": sorted({item["appearance"]["skin"]["undertone"] for item in identities}),
        "hair_textures": sorted({item["appearance"]["hair"]["texture"] for item in identities}),
        "body_builds": sorted({item["appearance"]["body"]["build"] for item in identities}),
        "source_sha256": {
            "identities": sha256(args.identities.resolve()),
            "rig": sha256(args.rig.resolve()),
            "recipes": sha256(args.recipes.resolve()),
            "lexicon": sha256(args.lexicon.resolve()),
            "production_standard": sha256(args.production_standard.resolve()),
            "production_rig": sha256(args.production_rig.resolve()),
            "canonical_family": sha256(args.canonical_family.resolve()),
        },
    }
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
