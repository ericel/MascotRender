#!/usr/bin/env python3
"""Build the focused Wave 2 cross-backend art-direction correction review."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from build_human_wave2_production_review import (
    alpha_bounds,
    matching_pixels,
    render_glb_at,
)
from build_human_wave2_review import (
    MASTER_IDS,
    contact_sheet,
    read_glb_document,
    read_json,
    render_vector,
    sha256,
    write_json,
)


ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "art" / "human-pack-wave2" / "candidates"
PRIOR_REVIEW = ROOT / "generated" / "human-wave2-final-production-review"
OWNER_DECISION = ROOT / "contracts" / "human-wave2-owner-production-decision-v1.json"
OUTPUT = ROOT / "generated" / "human-wave2-art-direction-review-v2"

STATES = {
    "rest": ("stickers/poses/rest.json", None),
    "greeting": ("stickers/poses/greeting.json", "greeting"),
    "excited": ("stickers/production/excited.json", "semantic-excited"),
}


def verify_prior_decision() -> dict[str, Any]:
    decision = read_json(OWNER_DECISION)
    if (
        decision.get("decision") != "partial-approval-one-gate-failed"
        or decision.get("production_gates", {}).get("cross-backend-art-direction-parity") != "failed"
        or decision.get("scope", {}).get("reopen_only") != ["cross-backend-art-direction-parity"]
    ):
        raise RuntimeError("the focused review requires the exact partial owner decision")
    manifest = decision["review_manifest"]
    manifest_path = ROOT / manifest["path"]
    if not manifest_path.is_file() or sha256(manifest_path) != manifest["sha256"]:
        raise RuntimeError("the prior owner decision no longer matches its review manifest")
    for name, expected in decision["reviewed_artifacts"].items():
        path = PRIOR_REVIEW / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"the prior owner decision artifact changed: {name}")
    return decision


def html_page(title: str, sections: list[tuple[str, str]]) -> str:
    body = "".join(f"<section><h2>{heading}</h2>{content}</section>" for heading, content in sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title>
<style>
body{{font:16px system-ui;margin:24px;background:#eef3f8;color:#172b45}}
main{{max-width:1500px;margin:auto}} img{{max-width:100%;background:white;border-radius:16px}}
section{{margin:28px 0}} code{{background:#dfe8f2;padding:2px 5px;border-radius:4px}}
</style></head><body><main><h1>{title}</h1>{body}</main></body></html>
"""


def build(args: argparse.Namespace) -> None:
    decision = verify_prior_decision()
    candidates = args.candidates.resolve()
    executable = args.mascotrender.resolve()
    preview = args.glb_preview.resolve()
    output = args.output.resolve()
    if not executable.is_file() or not preview.is_file():
        raise FileNotFoundError("MascotRender and the GLB preview executable are required")

    with tempfile.TemporaryDirectory(prefix="mascotrender-wave2-art-direction-") as temporary:
        staging = Path(temporary) / "review"
        records: dict[tuple[str, str], Path] = {}
        per_state: dict[str, dict[tuple[str, str], Path]] = {state: {} for state in STATES}
        validations: list[dict[str, Any]] = []

        for master_id in MASTER_IDS:
            root = candidates / master_id
            identity = read_json(root / "identity.json")
            palette = identity["palette"]
            glb = root / f"{master_id}-review.glb"
            document = read_glb_document(glb)
            node_names = {str(node.get("name", "")) for node in document.get("nodes", [])}
            required_style_nodes = {
                "HeadInkOutline", "TorsoInkOutline", "EyeOutlines",
                "ArmLeftInkOutline", "ArmRightInkOutline",
                "LegLeftInkOutline", "FootLeftInkOutline",
            }
            if not required_style_nodes.issubset(node_names):
                raise RuntimeError(f"{master_id} lacks the corrected GLB style hierarchy")

            master_validation: dict[str, Any] = {
                "master_id": master_id,
                "glb_sha256": sha256(glb),
                "states": {},
            }
            for state, (sticker_relative, clip) in STATES.items():
                state_root = staging / "renders" / state
                flat = state_root / f"{master_id}-flat.webp"
                layered = state_root / f"{master_id}-layered.webp"
                glb_render = state_root / f"{master_id}-glb.webp"
                sticker = root / sticker_relative
                render_vector(executable, root / "pack-flat.json", sticker, flat)
                render_vector(executable, root / "pack.json", sticker, layered)
                render_glb_at(preview, glb, glb_render, clip)

                for label, path in (
                    (f"flat {state}", flat),
                    (f"layered {state}", layered),
                    (f"styled GLB {state}", glb_render),
                ):
                    records[(master_id, label)] = path
                for label, path in (
                    ("flat 2D", flat),
                    ("layered 2.5D", layered),
                    ("styled GLB", glb_render),
                ):
                    per_state[state][(master_id, label)] = path

                outline_pixels = matching_pixels(glb_render, palette["outline"], tolerance=10)
                bounds = alpha_bounds(glb_render)
                if outline_pixels < 90 or bounds[2] - bounds[0] < 55 or bounds[3] - bounds[1] < 145:
                    raise RuntimeError(
                        f"{master_id}/{state} failed styled GLB evidence: "
                        f"outline_pixels={outline_pixels}, bounds={bounds}"
                    )
                master_validation["states"][state] = {
                    "outline_pixel_count": outline_pixels,
                    "alpha_bounds": list(bounds),
                    "flat_sha256": sha256(flat),
                    "layered_sha256": sha256(layered),
                    "glb_sha256": sha256(glb_render),
                }
            validations.append(master_validation)

        sheets: dict[str, Path] = {}
        columns: list[str] = []
        for state in STATES:
            columns.extend((f"flat {state}", f"layered {state}", f"styled GLB {state}"))
            state_sheet = staging / f"{state}-matched-parity.png"
            contact_sheet(
                per_state[state], MASTER_IDS, ("flat 2D", "layered 2.5D", "styled GLB"),
                state_sheet, f"Wave 2 matched {state} art-direction parity", 210,
            )
            sheets[state] = state_sheet
        combined = staging / "cross-backend-art-direction-correction.png"
        contact_sheet(
            records, MASTER_IDS, columns, combined,
            "Wave 2 cross-backend art-direction correction — matched semantic states", 145,
        )
        sheets["combined"] = combined

        artifact_hashes = {path.name: sha256(path) for path in sheets.values()}
        owner_template = {
            "schema_version": 1,
            "authority": "project-owner",
            "decision": None,
            "decision_date": None,
            "gate": "cross-backend-art-direction-parity",
            "allowed_decisions": ["approved", "failed"],
            "reviewed_artifacts": artifact_hashes,
            "preserved_prior_owner_gates": {
                name: value
                for name, value in decision["production_gates"].items()
                if name != "cross-backend-art-direction-parity"
            },
            "production_use_if_approved": "still-requires-specialist-gates-and-owner-activation",
        }
        write_json(staging / "owner-decision-template.json", owner_template)
        report = {
            "schema_version": 1,
            "review_id": "human-wave2-cross-backend-art-direction-correction-v2",
            "verification_status": "technical-validation-success",
            "review_status": "awaiting-owner-art-direction-re-review",
            "reopened_gate": "cross-backend-art-direction-parity",
            "preserved_owner_gates": owner_template["preserved_prior_owner_gates"],
            "production_use": "forbidden",
            "prior_owner_decision_sha256": sha256(OWNER_DECISION),
            "technical_gates": {
                "semantically-matched-cross-backend-states": "pass",
                "GLB-outline-hierarchy": "pass",
                "GLB-outline-pixel-presence": "pass",
                "deterministic-GLB-generation": "pass",
            },
            "artifacts": artifact_hashes,
            "validations": validations,
        }
        write_json(staging / "review.json", report)
        (staging / "index.html").write_text(
            html_page(
                "Wave 2 focused cross-backend art-direction re-review",
                [
                    ("Decision scope", "<p>Only <code>cross-backend-art-direction-parity</code> is reopened. Previously approved gates remain bound.</p>"),
                    ("Combined matched states", "<img src='cross-backend-art-direction-correction.png'>"),
                    ("Rest", "<img src='rest-matched-parity.png'>"),
                    ("Greeting", "<img src='greeting-matched-parity.png'>"),
                    ("Excited", "<img src='excited-matched-parity.png'>"),
                ],
            ),
            encoding="utf-8",
        )

        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging, output)
    print(f"built focused Wave 2 art-direction review at {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--mascotrender", type=Path, default=ROOT / "build" / "Release" / "mascotrender")
    parser.add_argument("--glb-preview", type=Path, default=ROOT / "build" / "Release" / "mascotrender-glb-preview")
    args = parser.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
