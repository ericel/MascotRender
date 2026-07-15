#!/usr/bin/env python3
"""Shared validation and compilation helpers for human mascot pilots."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


COLOR = re.compile(r"^#[0-9A-F]{6}$")
SAFE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9-]+)+$")
REQUIRED_FRAMINGS = {
    "face-closeup",
    "bust",
    "three-quarter",
    "full-body",
    "dynamic-full-body",
}
REQUIRED_SEMANTIC_TARGETS = {
    "root",
    "head",
    "face",
    "gesture.primary",
    "gesture.secondary",
    "ground.contact",
    "gaze.target",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_color(value: object, label: str) -> None:
    require(isinstance(value, str) and COLOR.fullmatch(value) is not None,
            f"{label} must be an uppercase #RRGGBB color")


def validate_rig(rig: dict[str, Any]) -> dict[str, Any]:
    require(rig.get("schema_version") == 1, "rig schema_version must be 1")
    require(rig.get("rig_id") == "humanoid-full-body-v1", "unexpected rig_id")
    joints = rig.get("joints")
    require(isinstance(joints, list) and len(joints) >= 12, "rig requires at least 12 joints")
    by_id: dict[str, dict[str, Any]] = {}
    for joint in joints:
        require(isinstance(joint, dict), "rig joint must be an object")
        joint_id = joint.get("id")
        require(isinstance(joint_id, str) and joint_id and joint_id not in by_id,
                f"duplicate or empty rig joint {joint_id!r}")
        require(isinstance(joint.get("pivot"), str) and joint["pivot"],
                f"joint {joint_id} requires a pivot")
        by_id[joint_id] = joint
    roots = [joint for joint in joints if joint.get("parent") is None]
    require(len(roots) == 1 and roots[0]["id"] == "root", "rig requires one root joint")
    for joint_id, joint in by_id.items():
        parent = joint.get("parent")
        require(parent is None or parent in by_id, f"joint {joint_id} has unknown parent {parent}")
        visited = {joint_id}
        while parent is not None:
            require(parent not in visited, f"rig parent graph contains a cycle at {joint_id}")
            visited.add(parent)
            parent = by_id[parent].get("parent")

    targets = rig.get("semantic_targets")
    require(isinstance(targets, dict), "rig semantic_targets must be an object")
    require(REQUIRED_SEMANTIC_TARGETS.issubset(targets), "rig is missing semantic targets")
    for semantic, joint_id in targets.items():
        require(joint_id in by_id, f"semantic target {semantic} references unknown joint {joint_id}")

    framings = rig.get("camera_framings")
    require(isinstance(framings, dict) and REQUIRED_FRAMINGS == set(framings),
            "rig must define exactly the five semantic camera framings")
    for name, framing in framings.items():
        require(isinstance(framing, dict), f"camera framing {name} must be an object")
        zoom = framing.get("zoom")
        require(isinstance(zoom, (int, float)) and 0.5 <= zoom <= 3.0,
                f"camera framing {name} has invalid zoom")
        require(isinstance(framing.get("target"), str) and framing["target"],
                f"camera framing {name} requires a target")
    return rig


def validate_production_rig(rig: dict[str, Any]) -> dict[str, Any]:
    require(rig.get("schema_version") == 2, "production rig schema_version must be 2")
    require(rig.get("rig_id") == "humanoid-production-v2", "unexpected production rig_id")
    convention = rig.get("coordinate_convention")
    require(isinstance(convention, dict)
            and convention.get("left_right") == "character-anatomical"
            and convention.get("front_view_character_right_appears_on") == "screen-left",
            "production rig must use anatomical left/right coordinates")
    joints = rig.get("joints")
    require(isinstance(joints, list) and len(joints) >= 22,
            "production rig requires at least 22 articulated joints")
    by_id: dict[str, dict[str, Any]] = {}
    for joint in joints:
        require(isinstance(joint, dict), "production rig joint must be an object")
        joint_id = joint.get("id")
        require(isinstance(joint_id, str) and joint_id and joint_id not in by_id,
                f"duplicate or empty production rig joint {joint_id!r}")
        require(isinstance(joint.get("pivot"), str) and joint["pivot"],
                f"production joint {joint_id} requires a pivot")
        by_id[joint_id] = joint
    require([joint["id"] for joint in joints if joint.get("parent") is None] == ["root"],
            "production rig requires exactly one root")
    for joint_id, joint in by_id.items():
        parent = joint.get("parent")
        require(parent is None or parent in by_id,
                f"production joint {joint_id} has unknown parent {parent}")
        visited = {joint_id}
        while parent is not None:
            require(parent not in visited, f"production rig parent cycle at {joint_id}")
            visited.add(parent)
            parent = by_id[parent].get("parent")
    targets = rig.get("semantic_targets")
    require(isinstance(targets, dict) and REQUIRED_SEMANTIC_TARGETS.issubset(targets),
            "production rig is missing semantic targets")
    require(all(joint_id in by_id for joint_id in targets.values()),
            "production rig semantic target references an unknown joint")
    framings = rig.get("camera_framings")
    require(isinstance(framings, dict) and set(framings) == REQUIRED_FRAMINGS,
            "production rig must define exactly five camera framings")
    profiles = rig.get("device_profiles")
    required_profiles = {
        "device.none", "prosthesis.lower-leg.right", "wheelchair.manual",
        "hearing-aid.behind-ear.right", "rollator.four-wheel",
    }
    require(isinstance(profiles, dict) and required_profiles.issubset(profiles),
            "production rig is missing canonical device profiles")
    for profile_id, profile in profiles.items():
        require(isinstance(profile, dict), f"device profile {profile_id} must be an object")
        for field in ("required_parts", "required_anchors", "capabilities"):
            values = profile.get(field)
            require(isinstance(values, list) and len(values) == len(set(values)),
                    f"device profile {profile_id} has invalid {field}")
    return rig


def validate_identities(document: dict[str, Any], minimum_count: int = 12) -> list[dict[str, Any]]:
    require(document.get("schema_version") == 1, "pilot identity set schema_version must be 1")
    require(document.get("asset_class") == "technical-fixture",
            "procedural pilot set must be classified as a technical fixture")
    require(document.get("production_use") == "forbidden",
            "procedural pilot set must explicitly forbid production use")
    identities = document.get("identities")
    require(isinstance(identities, list) and len(identities) >= minimum_count,
            f"pilot identity set requires at least {minimum_count} identities")
    ids: set[str] = set()
    names: set[str] = set()
    for identity in identities:
        require(isinstance(identity, dict), "human identity must be an object")
        mascot_id = identity.get("mascot_id")
        name = identity.get("display_name")
        require(identity.get("schema_version") == 1 and identity.get("species") == "human",
                f"{mascot_id} must be a schema-v1 human")
        require(isinstance(mascot_id, str) and re.fullmatch(r"human-[a-z0-9]+-[0-9]{3}", mascot_id),
                f"invalid human mascot_id {mascot_id!r}")
        require(mascot_id not in ids and isinstance(name, str) and name and name not in names,
                f"duplicate human identity {mascot_id!r} / {name!r}")
        ids.add(mascot_id)
        names.add(name)
        rig = identity.get("rig", {})
        require(rig.get("contract_id") == "humanoid-full-body-v1" and rig.get("contract_version") == 1,
                f"{mascot_id} does not use humanoid-full-body-v1")
        appearance = identity.get("appearance", {})
        skin = appearance.get("skin", {})
        require(isinstance(skin.get("tone_scale"), int) and 1 <= skin["tone_scale"] <= 10,
                f"{mascot_id} has invalid skin tone_scale")
        require(skin.get("undertone") in {"cool", "neutral", "olive", "warm"},
                f"{mascot_id} has invalid undertone")
        for field in ("base_color", "highlight_color", "shadow_color"):
            require_color(skin.get(field), f"{mascot_id} skin.{field}")
        face = appearance.get("face", {})
        require(0.82 <= float(face.get("width_ratio", 0)) <= 1.18,
                f"{mascot_id} face width is outside contract")
        require(0.24 <= float(face.get("eye_spacing_ratio", 0)) <= 0.42,
                f"{mascot_id} eye spacing is outside contract")
        hair = appearance.get("hair", {})
        require(hair.get("texture") in {"straight", "wavy", "curly", "coily", "covered"},
                f"{mascot_id} has invalid hair texture")
        require(isinstance(hair.get("style"), str) and hair["style"],
                f"{mascot_id} has no hair style")
        require_color(hair.get("base_color"), f"{mascot_id} hair.base_color")
        require_color(hair.get("highlight_color"), f"{mascot_id} hair.highlight_color")
        body = appearance.get("body", {})
        require(body.get("height_class") in {"short", "medium", "tall"},
                f"{mascot_id} has invalid height class")
        require(body.get("build") in {"broad", "lean", "soft", "stocky", "slender"},
                f"{mascot_id} has invalid body build")
        presentation = identity.get("presentation", {})
        for field in ("primary_color", "secondary_color", "accent_color"):
            require_color(presentation.get(field), f"{mascot_id} presentation.{field}")
        representation = identity.get("representation", {})
        require(representation.get("rendering_source") == "appearance-only",
                f"{mascot_id} heritage metadata must not drive rendering")
        require(isinstance(representation.get("heritage_context"), list)
                and representation["heritage_context"],
                f"{mascot_id} requires representation audit metadata")

    tones = {identity["appearance"]["skin"]["tone_scale"] for identity in identities}
    for label, predicate in (
        ("light", lambda value: value <= 2),
        ("light-medium", lambda value: 3 <= value <= 4),
        ("medium", lambda value: 5 <= value <= 6),
        ("medium-deep", lambda value: 7 <= value <= 8),
        ("deep", lambda value: value >= 9),
    ):
        require(any(predicate(value) for value in tones), f"pilot set has no {label} complexion")
    undertones = {identity["appearance"]["skin"]["undertone"] for identity in identities}
    require(undertones == {"cool", "neutral", "olive", "warm"},
            "pilot set must cover cool, neutral, olive, and warm undertones")
    textures = {identity["appearance"]["hair"]["texture"] for identity in identities}
    require({"straight", "wavy", "curly", "coily", "covered"}.issubset(textures),
            "pilot set does not cover the required hair texture families")
    contexts = " ".join(
        context.casefold()
        for identity in identities
        for context in identity["representation"]["heritage_context"]
    )
    require("black" in contexts and "white" in contexts and "asian" in contexts,
            "pilot set must include Black, White, and Asian representation contexts")
    return identities


def validate_recipes(document: dict[str, Any], rig: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(document.get("schema_version") == 1, "recipe library schema_version must be 1")
    recipes = document.get("recipes")
    require(isinstance(recipes, list) and len(recipes) >= 12, "core recipe library requires 12 recipes")
    available_targets = set(rig["semantic_targets"])
    by_id: dict[str, dict[str, Any]] = {}
    for recipe in recipes:
        require(isinstance(recipe, dict), "motion recipe must be an object")
        recipe_id = recipe.get("recipe_id")
        require(isinstance(recipe_id, str) and SAFE_ID.fullmatch(recipe_id) and recipe_id not in by_id,
                f"invalid or duplicate recipe_id {recipe_id!r}")
        require(recipe.get("camera_framing") in REQUIRED_FRAMINGS,
                f"{recipe_id} has unknown camera framing")
        duration = recipe.get("duration_ms")
        require(isinstance(duration, int) and 100 <= duration <= 10000,
                f"{recipe_id} has invalid duration")
        tracks = recipe.get("tracks")
        require(isinstance(tracks, list) and tracks, f"{recipe_id} requires semantic tracks")
        seen_tracks: set[tuple[str, str]] = set()
        for track in tracks:
            target = track.get("target")
            prop = track.get("property")
            require(target in available_targets, f"{recipe_id} references unknown semantic target {target}")
            require((target, prop) not in seen_tracks, f"{recipe_id} duplicates {target}/{prop}")
            seen_tracks.add((target, prop))
            keyframes = track.get("keyframes")
            require(isinstance(keyframes, list) and len(keyframes) >= 2,
                    f"{recipe_id} track requires keyframes")
            times = [frame.get("at_ms") for frame in keyframes]
            require(times[0] == 0 and times[-1] == duration and times == sorted(set(times)),
                    f"{recipe_id} keyframes must span the duration in strict order")
            if recipe.get("loop") == "loop":
                require(keyframes[0].get("value") == keyframes[-1].get("value"),
                        f"{recipe_id} looping track does not close")
        by_id[recipe_id] = recipe
    return by_id


def validate_lexicon(document: dict[str, Any], recipes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    require(document.get("schema_version") == 1, "phrase lexicon schema_version must be 1")
    phrases = document.get("phrases")
    require(isinstance(phrases, list) and len(phrases) >= 12, "core lexicon requires 12 phrases")
    phrase_ids: set[str] = set()
    for phrase in phrases:
        require(isinstance(phrase, dict), "phrase must be an object")
        phrase_id = phrase.get("phrase_id")
        require(isinstance(phrase_id, str) and SAFE_ID.fullmatch(phrase_id) and phrase_id not in phrase_ids,
                f"invalid or duplicate phrase_id {phrase_id!r}")
        phrase_ids.add(phrase_id)
        require(phrase.get("recipe_id") in recipes, f"{phrase_id} references an unknown recipe")
        require(phrase.get("tier") in {"core", "extended", "long-tail"},
                f"{phrase_id} has invalid tier")
        triggers = phrase.get("triggers")
        require(isinstance(triggers, list) and triggers, f"{phrase_id} requires triggers")
        for trigger in triggers:
            text = trigger.get("text")
            minimum = trigger.get("min_typed_length")
            require(isinstance(text, str) and len(text.strip()) >= 2,
                    f"{phrase_id} contains an unsafe one-character trigger")
            require(isinstance(minimum, int) and 2 <= minimum <= len(text),
                    f"{phrase_id} trigger {text!r} has invalid min_typed_length")
            require(trigger.get("match") in {"exact-token", "full-phrase", "prefix"},
                    f"{phrase_id} trigger {text!r} has invalid match mode")
    return phrases


def validate_production_standard(document: dict[str, Any]) -> dict[str, Any]:
    require(document.get("schema_version") == 1, "human production standard schema_version must be 1")
    require(document.get("standard_id") == "human-pack-production-v1",
            "unexpected human production standard ID")
    require(document.get("asset_class") == "production-art",
            "human production standard must target production art")
    dimensions = document.get("supported_identity_dimensions")
    require(isinstance(dimensions, dict),
            "human production standard requires supported identity dimensions")
    require(set(dimensions.get("life_stages", [])) == {
        "child", "pre-teen", "teen", "young-adult", "adult", "middle-aged", "senior"
    }, "human production standard must support all declared life stages")
    require(set(dimensions.get("complexion_tones", [])) == set(range(1, 11)),
            "human production standard must support complexion positions 1-10")
    require(set(dimensions.get("undertones", [])) == {"cool", "neutral", "olive", "warm"},
            "human production standard must support all undertones")
    require({"wheelchair", "prosthetic-limb", "visual-impairment", "hearing-aid"}.issubset(
        set(dimensions.get("ability_representations", []))),
        "human production standard is missing a supported ability representation")
    editorial = document.get("editorial_policy")
    require(isinstance(editorial, dict)
            and editorial.get("coverage_is_pack_specific") is True
            and editorial.get("every_pack_may_choose_a_subset") is True
            and editorial.get("minor_coded_characters_are_optional") is True
            and editorial.get("minor_coded_characters_require_owner_editorial_approval") is True
            and editorial.get("engine_requires_any_life_stage") is False,
            "human production standard must keep age coverage pack-specific and minors optional")
    require(set(document.get("framings", [])) == REQUIRED_FRAMINGS,
            "human production standard must cover all semantic framings")
    require(set(document.get("readability_sizes_px", [])) == {80, 96, 100},
            "human production standard must gate 80/96/100-pixel readability")
    gates = set(document.get("production_gates", []))
    require({"diverse-human-review", "animation-and-reduced-motion", "cross-backend-parity"}.issubset(gates),
            "human production standard is missing review gates")
    prohibited = set(document.get("prohibited_inference", []))
    require({"race-from-user", "ethnicity-from-user", "ability-from-user", "heritage-to-geometry"}.issubset(prohibited),
            "human production standard is missing inference prohibitions")
    return document


def validate_canonical_family(
    document: dict[str, Any], asset_path: Path | None = None
) -> dict[str, Any]:
    require(document.get("schema_version") == 1,
            "canonical human family schema_version must be 1")
    require(document.get("family_id") == "human-character-library-canonical-family",
            "unexpected canonical human family ID")
    require(document.get("family_version") == 1,
            "canonical human family version must be 1")
    require(document.get("status") == "approved-canonical-foundation",
            "canonical human family has not been approved")
    require(document.get("scope") == "foundation-not-complete-library",
            "canonical family must not claim to be the complete library")
    approval = document.get("approval", {})
    require(approval.get("authority") == "project-owner"
            and approval.get("decision") == "approved"
            and approval.get("date") == "2026-07-15",
            "canonical family approval record is incomplete")
    reference = document.get("reference_asset", {})
    require(reference.get("asset_class") == "approved-concept-reference"
            and reference.get("production_use") == "reference-only",
            "canonical bitmap must remain reference-only")
    members = document.get("canonical_members")
    require(isinstance(members, list) and len(members) == 5,
            "canonical family requires exactly five foundation members")
    require({item.get("id") for item in members} == {"H01", "H04", "H07", "H12", "H13"},
            "canonical family member IDs do not match the approved lineup")
    devices = {
        item["id"]: set(item.get("device_requirements", []))
        for item in members
    }
    require("articulated-below-knee-prosthesis" in devices["H04"],
            "H04 prosthesis contract is missing")
    require("manual-wheelchair" in devices["H07"],
            "H07 wheelchair contract is missing")
    require("behind-the-ear-hearing-aid" in devices["H12"],
            "H12 hearing-aid contract is missing")
    require("rollator" in devices["H13"],
            "H13 rollator contract is missing")
    requirements = set(document.get("production_requirements", []))
    require({"original-layered-svg-source", "device-technical-sheet-when-applicable",
             "diverse-human-review",
             "cross-backend-identity-parity-for-every-claimed-backend",
             "cross-backend-art-direction-parity-for-every-claimed-backend"}.issubset(requirements),
            "canonical family is missing production requirements")
    parity = document.get("cross_backend_parity_policy", {})
    require(
        set(parity.get("public_release_requires", [])) == {"identity_parity", "art_direction_parity"}
        and len(parity.get("identity_parity", [])) >= 4
        and len(parity.get("art_direction_parity", [])) >= 4,
        "canonical family must require both identity and art-direction parity",
    )
    if asset_path is not None:
        require(asset_path.is_file(), f"canonical family asset is missing: {asset_path}")
        require(sha256(asset_path) == reference.get("sha256"),
                "canonical family asset SHA-256 does not match its approved contract")
    return document


def validate_contract_set(
    identities_path: Path,
    rig_path: Path,
    recipes_path: Path,
    lexicon_path: Path,
    minimum_identities: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    rig = validate_rig(read_json(rig_path))
    identities = validate_identities(read_json(identities_path), minimum_identities)
    recipes = validate_recipes(read_json(recipes_path), rig)
    phrases = validate_lexicon(read_json(lexicon_path), recipes)
    return identities, rig, recipes, phrases
