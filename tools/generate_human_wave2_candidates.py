#!/usr/bin/env python3
"""Author the ten Human Expansion Wave 2 vector review candidates."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from generate_canonical_human_masters import generate_master, write_json


ROOT = Path(__file__).resolve().parent.parent
STATUS = "public-release-approved"
PRODUCTION_USE = "public-release"


def member(**values: Any) -> dict[str, Any]:
    values.update({"mode": "standing", "wave2": True, "status": STATUS, "production_use": PRODUCTION_USE, "device": values.get("device", "device.none")})
    values.setdefault("hair_highlight", values["hair"])
    return values


WAVE2: dict[str, dict[str, Any]] = {
    "H02": member(
        skin="#B86F45", skin_light="#D89164", hair="#352019", hair_highlight="#6B3C2B",
        primary="#1F9B92", secondary="#F1C34A", accent="#F06C62", pants="#C7A66B", shoe="#24435C",
        head=(256, 126, 60, 66), torso=(199, 201, 114, 108), ground=459, leg_width=31, leg_gap=18,
        eye_profile=(11, 13), hair_style="short-loose-curls", clothing_style="hoodie",
        identity="Latino pre-teen boy with warm medium complexion, short loose curls, and an energetic hoodie silhouette",
        authored_demographics={"life_stage": "pre-teen", "gender_presentation": "masculine"},
        representation={"heritage_context": ["Latino"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=.86, glb_head=(1.25, 1.22), glb_torso=(1.12, 1.02),
    ),
    "H03": member(
        skin="#A9653E", skin_light="#CE8B61", hair="#251817", hair_highlight="#684034",
        primary="#7654A8", secondary="#E2A4D2", accent="#F2A33A", pants="#2D3043", shoe="#7858A8",
        head=(256, 111, 58, 64), torso=(204, 183, 104, 126), ground=463, leg_width=29, leg_gap=17,
        eye_profile=(10, 12), hair_style="long-wavy", clothing_style="layered-jacket",
        identity="South Asian teen girl with medium warm complexion, long wavy hair, and a contemporary layered outfit",
        authored_demographics={"life_stage": "teen", "gender_presentation": "feminine"},
        representation={"heritage_context": ["South Asian"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=.95, glb_head=(1.18, 1.20), glb_torso=(1.05, 1.14),
    ),
    "H05": member(
        skin="#E2B192", skin_light="#F0C9AF", hair="#873E2B", hair_highlight="#C56A49",
        primary="#537A52", secondary="#E5B84A", accent="#4D8EBA", pants="#273D52", shoe="#E6E0D5",
        head=(256, 104, 55, 61), torso=(207, 170, 98, 139), ground=465, leg_width=29, leg_gap=18,
        eye_profile=(9, 11), hair_style="swept-wave", clothing_style="layered-jacket", device="white-cane.orientation",
        identity="White young adult man with light cool complexion, swept auburn hair, and an orientation white cane integrated into the rig",
        authored_demographics={"life_stage": "young-adult", "gender_presentation": "masculine", "assistive_devices": ["white-cane.orientation"]},
        representation={"heritage_context": ["White"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=1.05, glb_head=(1.12, 1.16), glb_torso=(1.00, 1.24),
    ),
    "H06": member(
        skin="#AD704C", skin_light="#D19369", hair="#2A1917", hair_highlight="#6A3A31",
        primary="#C95449", secondary="#F0B63B", accent="#2CA59B", pants="#243B59", shoe="#D9874E",
        head=(256, 108, 62, 66), torso=(173, 181, 166, 145), ground=465, leg_width=39, leg_gap=16,
        eye_profile=(10, 12), hair_style="voluminous-curls", clothing_style="graphic-tee",
        identity="Latina adult woman with medium olive complexion, short voluminous curls, and a strong rounded silhouette",
        authored_demographics={"life_stage": "adult", "gender_presentation": "feminine"},
        representation={"heritage_context": ["Latina"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=.98, glb_head=(1.23, 1.22), glb_torso=(1.58, 1.22),
    ),
    "H08": member(
        skin="#C58A62", skin_light="#E1AD84", hair="#426B4B", hair_highlight="#7E9B65",
        primary="#6F8A4B", secondary="#D7A742", accent="#A65A54", pants="#3C493D", shoe="#2E3831",
        head=(256, 111, 59, 65), torso=(190, 181, 132, 158), ground=465, leg_width=33, leg_gap=16,
        eye_profile=(10, 12), hair_style="head-covering", clothing_style="modest-tunic",
        identity="Middle Eastern adult woman with light-medium olive complexion and an authored modest head covering and tunic",
        authored_demographics={"life_stage": "adult", "gender_presentation": "feminine"},
        representation={"heritage_context": ["Middle Eastern"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        hair_intent="not-hair: an individually authored everyday draped hijab; never inferred from heritage metadata",
        head_covering={
            "authored_term": "everyday draped hijab",
            "undercap": "not-visible",
            "coverage": ["hair", "ears", "neck", "upper-shoulders"],
            "construction": "face opening follows the hairline; two side panels join a rounded shoulder drape with a rear center fold",
            "material_behavior": "soft opaque fabric with restrained folds; remains attached to the head-and-shoulder rig during motion",
            "cultural_review_status": "owner-release-accepted-specialist-follow-up-open",
        },
        glb_height_scale=.98, glb_head=(1.19, 1.22), glb_torso=(1.30, 1.35),
    ),
    "H09": member(
        skin="#87513D", skin_light="#B4765C", hair="#201718", hair_highlight="#57403B",
        primary="#365D87", secondary="#E56A62", accent="#E9B542", pants="#2F3442", shoe="#CF6C62",
        head=(256, 105, 63, 67), torso=(168, 178, 176, 151), ground=465, leg_width=42, leg_gap=15,
        eye_profile=(11, 12), hair_style="coily-taper", clothing_style="hoodie",
        identity="Mixed-heritage young adult with medium-deep neutral complexion, coily tapered hair, and a soft broad androgynous silhouette",
        authored_demographics={"life_stage": "young-adult", "gender_presentation": "androgynous"},
        representation={"heritage_context": ["Mixed heritage"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=.99, glb_head=(1.26, 1.24), glb_torso=(1.68, 1.28),
    ),
    "H10": member(
        skin="#D6A17D", skin_light="#EBC2A4", hair="#4A2D23", hair_highlight="#7B5142",
        primary="#8A5B3E", secondary="#4F7690", accent="#D8A746", pants="#2D3541", shoe="#5A4438",
        head=(256, 102, 61, 64), torso=(169, 174, 174, 151), ground=465, leg_width=43, leg_gap=16,
        eye_profile=(10, 11), hair_style="bald", clothing_style="graphic-tee", facial_hair="close-beard",
        identity="White middle-aged man with light warm complexion, bald head, close beard, and a broad stocky silhouette",
        authored_demographics={"life_stage": "middle-aged", "gender_presentation": "masculine"},
        representation={"heritage_context": ["White"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=1.02, glb_head=(1.22, 1.20), glb_torso=(1.66, 1.28),
    ),
    "H11": member(
        skin="#A86640", skin_light="#CB8A61", hair="#AAA7A3", hair_highlight="#E1DDD7",
        primary="#3F6585", secondary="#D29B46", accent="#6FA59A", pants="#4A4038", shoe="#3B342F",
        head=(256, 96, 54, 60), torso=(207, 162, 98, 138), ground=465, leg_width=28, leg_gap=19,
        eye_profile=(9, 11), hair_style="silver-swept", clothing_style="cardigan", facial_hair="moustache", glasses=True,
        identity="South Asian senior man with medium warm complexion, silver swept hair, moustache, glasses, and a tall slim silhouette",
        authored_demographics={"life_stage": "senior", "gender_presentation": "masculine"},
        representation={"heritage_context": ["South Asian"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=1.08, glb_head=(1.08, 1.15), glb_torso=(.98, 1.28),
    ),
    "H14": member(
        skin="#D6A57C", skin_light="#EAC29E", hair="#17191E", hair_highlight="#45505D",
        primary="#294C70", secondary="#D95B55", accent="#49B5B2", pants="#202B39", shoe="#E8E4DA",
        head=(256, 104, 56, 61), torso=(190, 170, 132, 139), ground=465, leg_width=35, leg_gap=18,
        eye_profile=(10, 10), hair_style="straight-undercut", clothing_style="layered-jacket",
        identity="East Asian young adult man with light-medium neutral complexion, a straight undercut, and an athletic bomber-jacket silhouette",
        authored_demographics={"life_stage": "young-adult", "gender_presentation": "masculine"},
        representation={"heritage_context": ["East Asian"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=1.04, glb_head=(1.14, 1.16), glb_torso=(1.30, 1.22),
    ),
    "H15": member(
        skin="#B87542", skin_light="#D99A68", hair="#1C1718", hair_highlight="#654034",
        primary="#2C9990", secondary="#F0BE4A", accent="#E7675F", pants="#2F5574", shoe="#E7D9C4",
        head=(256, 108, 58, 63), torso=(193, 178, 126, 145), ground=465, leg_width=33, leg_gap=17,
        eye_profile=(10, 11), hair_style="shoulder-wave", clothing_style="cardigan",
        identity="Southeast Asian young adult woman with warm medium complexion, shoulder-length asymmetrical waves, and a relaxed contemporary cardigan silhouette",
        authored_demographics={"life_stage": "young-adult", "gender_presentation": "feminine"},
        representation={"heritage_context": ["Southeast Asian"], "rendering_source": "appearance-only", "review_status": "owner-vector-identity-approved"},
        glb_height_scale=1.01, glb_head=(1.17, 1.18), glb_torso=(1.24, 1.26),
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output.name + ".staging-", dir=output.parent))
    try:
        manifests = [generate_master(staging, master_id, WAVE2[master_id]) for master_id in sorted(WAVE2)]
        write_json(staging / "generation-manifest.json", {
            "schema_version": 1,
            "expansion_id": "human-canonical-expansion-wave2",
            "family_id": "human-character-library-canonical-family",
            "status": STATUS,
            "production_use": PRODUCTION_USE,
            "master_count": len(manifests),
            "members": sorted(WAVE2),
            "masters": manifests,
        })
        write_json(staging / "representation-review.json", {
            "schema_version": 1,
            "expansion_id": "human-canonical-expansion-wave2",
            "decision": "owner-production-release-approved",
            "production_use": PRODUCTION_USE,
            "members": sorted(WAVE2),
            "review_requirements": [
                "identity-coherence", "age-and-body-readability", "non-stereotyped-presentation",
                "head-covering-construction", "white-cane-hand-and-ground-contact",
            ],
            "specialist_follow_up": {
                "H05-orientation-white-cane-specialist-review": "non-blocking-post-release-advisory",
                "H08-head-covering-cultural-detail-review": "non-blocking-post-release-advisory",
                "specialist_approval_claimed": False,
            },
        })
        if output.exists():
            if not args.force:
                raise FileExistsError(f"output exists (use --force): {output}")
            shutil.rmtree(output)
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"generated {len(WAVE2)} Wave 2 human identity candidates at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
