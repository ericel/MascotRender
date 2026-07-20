#!/usr/bin/env python3
"""Generate deterministic identity-specific styled GLBs for Micro Reactions."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from generate_robot_glb import (
    GlbBuffer,
    add_animation,
    combine_geometry,
    curve_geometry,
    ellipse_geometry,
    encode_glb,
    quadratic_curve,
    rounded_rect_prism,
    star_geometry,
    unlit_material,
    uv_sphere,
    z_rotation,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "content/micro-styled-glb-identities-v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "art/micro-reactions-v1/styled-glb-proofs"


def read_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or not isinstance(value.get("identities"), list):
        raise ValueError(f"invalid styled GLB identity contract: {path}")
    return value


def medal_star_geometry():
    positions, normals, indices = star_geometry()
    return (
        [[x * 0.42, y * 0.42, z] for x, y, z in positions],
        normals,
        indices,
    )


def build_document(spec: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    palette = spec["palette"]
    identity_id = spec["identity_id"]
    signature_clip = spec["signature_clip"]
    clip_names = ["idle", signature_clip, "proud"]
    buffer = GlbBuffer()

    def accessors(geometry):
        positions, normals, indices = geometry
        return (
            buffer.floats(positions, "VEC3", target=34962, bounds=True),
            buffer.floats(normals, "VEC3", target=34962),
            buffer.indices(indices),
        )

    body_kind = spec["body_kind"]
    if body_kind == "sprig":
        body_geometry = rounded_rect_prism(2.05, 2.02, 0.78, 0.94)
        body_scale = [1.06, 1.02, 1.0]
    elif body_kind == "rounded":
        body_geometry = rounded_rect_prism(2.05, 2.10, 0.78, 0.58)
        body_scale = [1.04, 1.04, 1.0]
    elif body_kind == "ember":
        body_geometry = uv_sphere(16, 24)
        body_scale = [1.24, 1.34, 0.58]
    elif body_kind == "round":
        body_geometry = uv_sphere(16, 24)
        body_scale = [1.30, 1.26, 0.58]
    elif body_kind == "cloud":
        body_geometry = uv_sphere(16, 24)
        body_scale = [1.10, 1.04, 0.52]
    else:
        raise ValueError(f"unsupported body kind for {identity_id}: {body_kind}")

    body_accessors = accessors(body_geometry)
    sphere_accessors = accessors(uv_sphere(14, 20))
    lower_shade = accessors(ellipse_geometry(0.0, -0.78, 1.0, 0.28))
    highlight = accessors(
        curve_geometry(
            quadratic_curve((-0.88, 0.12), (-1.00, 0.52), (-0.72, 0.82)),
            0.080,
        )
    )
    eye_shapes = accessors(
        combine_geometry(
            [
                ellipse_geometry(-0.39, 0.23, 0.285, 0.115),
                ellipse_geometry(0.39, 0.23, 0.285, 0.115),
            ]
        )
    )
    eye_whites = accessors(
        combine_geometry(
            [
                ellipse_geometry(-0.39, 0.23, 0.185, 0.066),
                ellipse_geometry(0.39, 0.23, 0.185, 0.066),
            ]
        )
    )
    pupils = accessors(
        combine_geometry(
            [
                ellipse_geometry(-0.37, 0.23, 0.052, 0.064),
                ellipse_geometry(0.41, 0.23, 0.052, 0.064),
            ]
        )
    )
    brows = accessors(
        combine_geometry(
            [
                curve_geometry(
                    quadratic_curve((-0.68, 0.52), (-0.40, 0.71), (-0.12, 0.55)),
                    0.052,
                ),
                curve_geometry(
                    quadratic_curve((0.12, 0.55), (0.40, 0.71), (0.68, 0.52)),
                    0.052,
                ),
            ]
        )
    )
    mouth = accessors(
        curve_geometry(
            quadratic_curve((-0.34, -0.19), (0.01, -0.47), (0.39, -0.13)),
            0.070,
        )
    )
    cheeks = accessors(
        combine_geometry(
            [
                curve_geometry(
                    quadratic_curve((-0.64, -0.02), (-0.48, 0.07), (-0.32, -0.01)),
                    0.040,
                ),
                curve_geometry(
                    quadratic_curve((0.32, -0.01), (0.48, 0.07), (0.64, -0.02)),
                    0.040,
                ),
            ]
        )
    )
    medal = accessors(ellipse_geometry(0.0, -0.76, 0.25, 0.25))
    medal_star = accessors(medal_star_geometry())
    sparkle = accessors(star_geometry())

    materials = [
        unlit_material("micro-outline", palette["outline"]),
        unlit_material("micro-primary", palette["primary"]),
        unlit_material("micro-secondary", palette["secondary"]),
        unlit_material("micro-light", palette["light"]),
        unlit_material("micro-accent", palette["accent"]),
        unlit_material("micro-white", palette["white"]),
        unlit_material("micro-blush", palette["blush"]),
        unlit_material("contact-shadow", palette["outline"], 0.20),
    ]

    def primitive(mesh_accessors, material):
        position, normal, indices = mesh_accessors
        return {
            "attributes": {"POSITION": position, "NORMAL": normal},
            "indices": indices,
            "material": material,
        }

    meshes = [
        {"name": "Body", "primitives": [primitive(body_accessors, 1)]},
        {"name": "BodyOutline", "primitives": [primitive(body_accessors, 0)]},
        {"name": "LowerShade", "primitives": [primitive(lower_shade, 2)]},
        {"name": "BodyHighlight", "primitives": [primitive(highlight, 3)]},
        {"name": "ProudEyeShapes", "primitives": [primitive(eye_shapes, 0)]},
        {"name": "EyeWhites", "primitives": [primitive(eye_whites, 5)]},
        {"name": "Pupils", "primitives": [primitive(pupils, 0)]},
        {"name": "SmoothArchedBrows", "primitives": [primitive(brows, 0)]},
        {"name": "CompactProudSmile", "primitives": [primitive(mouth, 0)]},
        {"name": "RestrainedBlush", "primitives": [primitive(cheeks, 6)]},
        {"name": "AchievementMedal", "primitives": [primitive(medal, 4)]},
        {"name": "AchievementStar", "primitives": [primitive(medal_star, 5)]},
        {"name": "SecondaryAnatomy", "primitives": [primitive(sphere_accessors, 2)]},
        {"name": "AnatomyOutline", "primitives": [primitive(sphere_accessors, 0)]},
        {"name": "LightAnatomy", "primitives": [primitive(sphere_accessors, 3)]},
        {"name": "AccentAnatomy", "primitives": [primitive(sphere_accessors, 4)]},
        {"name": "AccentSparkle", "primitives": [primitive(sparkle, 4)]},
        {"name": "ContactShadow", "primitives": [primitive(sphere_accessors, 7)]},
    ]

    nodes: list[dict[str, Any]] = []

    def node(name: str, **properties: Any) -> int:
        nodes.append({"name": name, **properties})
        return len(nodes) - 1

    root = node(
        "MascotRoot",
        extras={
            "identityId": identity_id,
            "displayName": spec["display_name"],
            "archetype": spec["archetype"],
            "semantic": "proud",
            "signatureAnatomy": spec["signature_node"],
            "referenceGate": "micro-orbit-final-glb-face-parity-v1",
        },
    )
    body_outline = node(
        "BodyOutline",
        mesh=1,
        scale=[body_scale[0] * 1.055, body_scale[1] * 1.055, body_scale[2] * 1.08],
    )
    body = node("Body", mesh=0, translation=[0, 0, 0.10], scale=body_scale)
    lower = node(
        "LowerShade",
        mesh=2,
        translation=[0.0, -0.08, 0.70],
        scale=[1.08, 1.0, 1.0],
    )
    highlight_node = node("BodyHighlight", mesh=3, translation=[0.0, 0.05, 0.73])
    face = node(
        "Face",
        translation=[0, 0.0, 0.76],
        extras={
            "semantic": "proud",
            "expressionContract": {
                "eyeShape": "narrow-composed",
                "browShape": "smooth-arched",
                "smileShape": "compact-curved",
                "blush": "restrained",
            },
        },
    )
    eye_shape_node = node("ProudEyeShapes", mesh=4, translation=[0, 0, 0.01])
    eye_white_node = node("EyeWhites", mesh=5, translation=[0, 0, 0.025])
    pupil_node = node("Pupils", mesh=6, translation=[0, 0, 0.04])
    brow_node = node("SmoothArchedBrows", mesh=7, translation=[0, 0, 0.05])
    mouth_node = node("CompactProudSmile", mesh=8, translation=[0, 0, 0.05])
    cheek_node = node("RestrainedBlush", mesh=9, translation=[0, 0, 0.05])
    medal_node = node("AchievementMedal", mesh=10, translation=[0, 0, 0.02])
    medal_star_node = node("AchievementStar", mesh=11, translation=[0, -0.76, 0.018])
    signature = node(
        spec["signature_node"],
        extras={
            "semantic": spec["signature_kind"],
            "identitySpecific": True,
            "secondaryMotionClip": signature_clip,
        },
    )
    shadow = node(
        "GroundShadow",
        mesh=17,
        translation=[0.0, -1.48, -0.24],
        scale=[1.12, 0.08, 0.38],
    )

    nodes[root]["children"] = [
        body_outline,
        body,
        lower,
        highlight_node,
        face,
        signature,
    ]
    nodes[face]["children"] = [
        eye_shape_node,
        eye_white_node,
        pupil_node,
        brow_node,
        mouth_node,
        cheek_node,
        medal_node,
        medal_star_node,
    ]

    signature_children: list[int] = []

    def anatomy_pair(
        name: str,
        translation: list[float],
        scale: list[float],
        *,
        fill_mesh: int = 12,
        rotation: list[float] | None = None,
    ) -> None:
        properties: dict[str, Any] = {
            "translation": translation,
            "scale": [component * 1.10 for component in scale],
        }
        if rotation is not None:
            properties["rotation"] = rotation
        outline = node(f"{name}Outline", mesh=13, **properties)
        fill_properties = {
            "translation": [translation[0], translation[1], translation[2] + 0.08],
            "scale": scale,
        }
        if rotation is not None:
            fill_properties["rotation"] = rotation
        fill = node(name, mesh=fill_mesh, **fill_properties)
        signature_children.extend([outline, fill])

    def anatomy_fill(
        name: str,
        translation: list[float],
        scale: list[float],
        *,
        fill_mesh: int,
    ) -> None:
        signature_children.append(
            node(
                name,
                mesh=fill_mesh,
                translation=translation,
                scale=scale,
            )
        )

    signature_kind = spec["signature_kind"]
    if signature_kind == "leaf":
        anatomy_pair(
            "LeftLeafEar",
            [-1.03, 0.74, 0.05],
            [0.48, 0.78, 0.18],
            rotation=z_rotation(43),
        )
        anatomy_pair(
            "RightLeafEar",
            [1.03, 0.74, 0.05],
            [0.48, 0.78, 0.18],
            rotation=z_rotation(-43),
        )
        anatomy_pair(
            "TopSprout",
            [0.05, 1.33, 0.05],
            [0.26, 0.53, 0.16],
            fill_mesh=15,
            rotation=z_rotation(-16),
        )
    elif signature_kind == "flame":
        anatomy_pair(
            "LeftFlame",
            [-0.52, 1.08, 0.02],
            [0.34, 0.68, 0.20],
            rotation=z_rotation(-24),
        )
        anatomy_pair(
            "CrownFlame",
            [0.00, 1.35, 0.04],
            [0.38, 0.80, 0.22],
            rotation=z_rotation(4),
        )
        anatomy_pair(
            "RightFlame",
            [0.50, 1.08, 0.02],
            [0.32, 0.64, 0.20],
            rotation=z_rotation(25),
        )
        anatomy_pair(
            "InnerEmber",
            [0.04, 1.30, 0.22],
            [0.17, 0.40, 0.10],
            fill_mesh=15,
            rotation=z_rotation(5),
        )
    elif signature_kind == "gill":
        for side, x in (("Left", -1.16), ("Right", 1.16)):
            direction = -1 if x < 0 else 1
            for index, y in enumerate((0.58, 0.02, -0.54), start=1):
                anatomy_pair(
                    f"{side}Gill{index}",
                    [x, y, 0.03],
                    [0.27, 0.42, 0.17],
                    rotation=z_rotation(direction * (18 + (index - 2) * 8)),
                )
        anatomy_pair(
            "LeftGillAccent",
            [-1.06, 0.58, 0.24],
            [0.10, 0.14, 0.07],
            fill_mesh=15,
        )
        anatomy_pair(
            "RightGillAccent",
            [1.06, 0.58, 0.24],
            [0.10, 0.14, 0.07],
            fill_mesh=15,
        )
    elif signature_kind == "ear":
        anatomy_pair("LeftRoundEar", [-0.88, 0.98, 0.0], [0.62, 0.62, 0.25])
        anatomy_pair("RightRoundEar", [0.88, 0.98, 0.0], [0.62, 0.62, 0.25])
        anatomy_fill(
            "LeftInnerEar",
            [-0.88, 0.98, 0.23],
            [0.32, 0.32, 0.09],
            fill_mesh=14,
        )
        anatomy_fill(
            "RightInnerEar",
            [0.88, 0.98, 0.23],
            [0.32, 0.32, 0.09],
            fill_mesh=14,
        )
        anatomy_fill(
            "LeftCheekPatch",
            [-0.62, -0.40, 0.74],
            [0.40, 0.31, 0.07],
            fill_mesh=14,
        )
        anatomy_fill(
            "RightCheekPatch",
            [0.62, -0.40, 0.74],
            [0.40, 0.31, 0.07],
            fill_mesh=14,
        )
    elif signature_kind == "puff":
        puff_positions = [
            (-0.86, 0.76, 0.62),
            (0.00, 1.03, 0.72),
            (0.86, 0.76, 0.62),
            (-1.04, 0.02, 0.58),
            (1.04, 0.02, 0.58),
            (-0.78, -0.70, 0.56),
            (0.00, -0.94, 0.62),
            (0.78, -0.70, 0.56),
        ]
        for index, (x, y, size) in enumerate(puff_positions, start=1):
            anatomy_pair(
                f"CloudPuff{index}",
                [x, y, 0.0],
                [size, size, 0.24],
                fill_mesh=0,
            )
    else:
        raise ValueError(f"unsupported signature kind for {identity_id}: {signature_kind}")

    nodes[signature]["children"] = signature_children

    left_effect = node(
        "LeftSignatureEffect",
        mesh=16,
        translation=[-1.52, 0.36, 0.34],
        scale=[0.28, 0.28, 0.28],
    )
    right_effect = node(
        "RightSignatureEffect",
        mesh=15 if signature_kind in {"gill", "puff"} else 16,
        translation=[1.53, -0.36, 0.30],
        scale=[0.16, 0.16, 0.16],
    )
    nodes[root]["children"].extend([left_effect, right_effect])

    document: dict[str, Any] = {
        "asset": {
            "version": "2.0",
            "generator": "MascotRender deterministic Micro Reactions styled GLB generator",
            "extras": {
                "mascot": identity_id,
                "clips": clip_names,
                "productionUse": "forbidden-until-family-styled-glb-review",
                "referenceIdentity": "micro-orbit-004",
                "referenceApprovalGate": "micro-orbit-final-glb-face-parity-v1",
                "palette": palette,
            },
        },
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"name": f"{spec['display_name']}Sticker", "nodes": [root, shadow]}],
        "nodes": nodes,
        "materials": materials,
        "meshes": meshes,
    }

    add_animation(
        document,
        buffer,
        "idle",
        [
            (
                root,
                "scale",
                [0.0, 0.6, 1.2],
                [[1, 1, 1], [1.014, 0.986, 1], [1, 1, 1]],
                "VEC3",
            ),
            (
                signature,
                "rotation",
                [0.0, 0.6, 1.2],
                [z_rotation(0), z_rotation(2), z_rotation(0)],
                "VEC4",
            ),
        ],
    )

    signature_tracks: list[tuple[Any, ...]]
    if signature_kind == "leaf":
        signature_tracks = [
            (
                signature,
                "rotation",
                [0.0, 0.3, 0.6, 0.9, 1.2],
                [z_rotation(0), z_rotation(-8), z_rotation(7), z_rotation(-4), z_rotation(0)],
                "VEC4",
            )
        ]
    elif signature_kind == "flame":
        signature_tracks = [
            (
                signature,
                "scale",
                [0.0, 0.3, 0.6, 0.9, 1.2],
                [[1, 1, 1], [0.93, 1.14, 1], [1.08, 0.91, 1], [0.96, 1.10, 1], [1, 1, 1]],
                "VEC3",
            )
        ]
    elif signature_kind == "gill":
        signature_tracks = [
            (
                signature,
                "scale",
                [0.0, 0.4, 0.8, 1.2],
                [[1, 1, 1], [1.12, 0.92, 1], [0.94, 1.08, 1], [1, 1, 1]],
                "VEC3",
            )
        ]
    elif signature_kind == "ear":
        signature_tracks = [
            (
                root,
                "translation",
                [0.0, 0.3, 0.6, 0.9, 1.2],
                [[0, 0, 0], [0, 0.12, 0], [0, -0.035, 0], [0, 0.07, 0], [0, 0, 0]],
                "VEC3",
            ),
            (
                signature,
                "rotation",
                [0.0, 0.6, 1.2],
                [z_rotation(0), z_rotation(-5), z_rotation(0)],
                "VEC4",
            ),
        ]
    else:
        signature_tracks = [
            (
                signature,
                "scale",
                [0.0, 0.4, 0.8, 1.2],
                [[1, 1, 1], [1.08, 1.12, 1], [0.96, 0.94, 1], [1, 1, 1]],
                "VEC3",
            ),
            (
                root,
                "translation",
                [0.0, 0.6, 1.2],
                [[0, 0, 0], [0, 0.09, 0], [0, 0, 0]],
                "VEC3",
            ),
        ]
    add_animation(document, buffer, signature_clip, signature_tracks)

    add_animation(
        document,
        buffer,
        "proud",
        [
            (
                root,
                "translation",
                [0.0, 0.5, 1.0],
                [[0, 0, 0], [0, 0.10, 0], [0, 0, 0]],
                "VEC3",
            ),
            (
                root,
                "scale",
                [0.0, 0.5, 1.0],
                [[1, 1, 1], [1.025, 1.025, 1], [1, 1, 1]],
                "VEC3",
            ),
            (
                shadow,
                "scale",
                [0.0, 0.5, 1.0],
                [[1.12, 0.08, 0.38], [0.88, 0.07, 0.38], [1.12, 0.08, 0.38]],
                "VEC3",
            ),
        ],
    )

    while len(buffer.data) % 4:
        buffer.data.append(0)
    document["buffers"] = [{"byteLength": len(buffer.data)}]
    document["bufferViews"] = buffer.views
    document["accessors"] = buffer.accessors
    return document, bytes(buffer.data)


def selected_specs(
    contract: dict[str, Any],
    identities: list[str],
) -> list[dict[str, Any]]:
    specs = contract["identities"]
    if not identities:
        return specs
    requested = set(identities)
    selected = [spec for spec in specs if spec["identity_id"] in requested]
    missing = requested - {spec["identity_id"] for spec in selected}
    if missing:
        raise ValueError(f"unknown identity IDs: {sorted(missing)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--identity", action="append", default=[])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    contract = read_contract(args.contract.resolve())
    specs = selected_specs(contract, args.identity)
    output_root = args.output_root.resolve()
    for spec in specs:
        document, binary = build_document(spec)
        payload = encode_glb(document, binary)
        output = output_root / f"{spec['identity_id']}.glb"
        if args.check:
            if not output.is_file() or output.read_bytes() != payload:
                raise SystemExit(f"generated GLB differs from {output}")
            print(f"verified deterministic GLB: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
            print(
                f"wrote {output} ({len(payload)} bytes, "
                f"{len(document['animations'])} clips)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
