#!/usr/bin/env python3
"""Generate the deterministic styled GLB proof for Micro Reactions Orbit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from generate_robot_glb import (
    GlbBuffer,
    add_animation,
    combine_geometry,
    curve_geometry,
    ellipse_geometry,
    encode_glb,
    quadratic_curve,
    star_geometry,
    unlit_material,
    uv_sphere,
    z_rotation,
)


CLIP_NAMES = ["idle", "orbital-tilt", "proud"]
PALETTE = {
    "outline": "#203654",
    "primary": "#9B7CF6",
    "secondary": "#6D55D8",
    "light": "#D7C9FF",
    "accent": "#FFD166",
    "white": "#FFFDF8",
    "blush": "#FF6F91",
}


def x_rotation(degrees: float) -> list[float]:
    radians = math.radians(degrees) * 0.5
    return [math.sin(radians), 0.0, 0.0, math.cos(radians)]


def torus_geometry(
    major_radius: float,
    minor_radius: float,
    major_segments: int = 40,
    minor_segments: int = 8,
):
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    for major in range(major_segments):
        u = math.tau * major / major_segments
        for minor in range(minor_segments):
            v = math.tau * minor / minor_segments
            radial = major_radius + minor_radius * math.cos(v)
            positions.append(
                [radial * math.cos(u), minor_radius * math.sin(v), radial * math.sin(u)]
            )
            normals.append(
                [math.cos(v) * math.cos(u), math.sin(v), math.cos(v) * math.sin(u)]
            )
    for major in range(major_segments):
        next_major = (major + 1) % major_segments
        for minor in range(minor_segments):
            next_minor = (minor + 1) % minor_segments
            a = major * minor_segments + minor
            b = next_major * minor_segments + minor
            c = next_major * minor_segments + next_minor
            d = major * minor_segments + next_minor
            indices.extend([a, b, c, a, c, d])
    return positions, normals, indices


def medal_star_geometry():
    star_positions, star_normals, star_indices = star_geometry()
    return (
        [[x * 0.42, y * 0.42, z] for x, y, z in star_positions],
        star_normals,
        star_indices,
    )


def build_document() -> tuple[dict[str, object], bytes]:
    buffer = GlbBuffer()

    def accessors(geometry):
        positions, normals, indices = geometry
        return (
            buffer.floats(positions, "VEC3", target=34962, bounds=True),
            buffer.floats(normals, "VEC3", target=34962),
            buffer.indices(indices),
        )

    sphere = accessors(uv_sphere(16, 24))
    body_highlight = accessors(ellipse_geometry(-0.34, 0.54, 0.42, 0.25))
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
    antenna_stem = accessors(
        curve_geometry(
            quadratic_curve((0.00, -0.04), (-0.13, 0.26), (0.00, 0.58)),
            0.115,
        )
    )
    torus_outline = accessors(torus_geometry(1.48, 0.095))
    torus_gold = accessors(torus_geometry(1.48, 0.068))
    medal = accessors(ellipse_geometry(0.0, -0.76, 0.25, 0.25))
    medal_star = accessors(medal_star_geometry())
    sparkle = accessors(star_geometry())

    materials = [
        unlit_material("orbit-outline", PALETTE["outline"]),
        unlit_material("orbit-primary", PALETTE["primary"]),
        unlit_material("orbit-secondary", PALETTE["secondary"]),
        unlit_material("orbit-light", PALETTE["light"]),
        unlit_material("orbit-accent", PALETTE["accent"]),
        unlit_material("orbit-white", PALETTE["white"]),
        unlit_material("orbit-blush", PALETTE["blush"]),
        unlit_material("contact-shadow", PALETTE["outline"], 0.20),
    ]

    def primitive(mesh_accessors, material):
        position, normal, indices = mesh_accessors
        return {
            "attributes": {"POSITION": position, "NORMAL": normal},
            "indices": indices,
            "material": material,
        }

    meshes = [
        {"name": "BodySphere", "primitives": [primitive(sphere, 1)]},
        {"name": "BodyOutline", "primitives": [primitive(sphere, 0)]},
        {"name": "LowerShade", "primitives": [primitive(sphere, 2)]},
        {"name": "BodyHighlight", "primitives": [primitive(body_highlight, 3)]},
        {"name": "ProudEyeShapes", "primitives": [primitive(eye_shapes, 0)]},
        {"name": "Pupils", "primitives": [primitive(pupils, 0)]},
        {"name": "Brows", "primitives": [primitive(brows, 0)]},
        {"name": "Mouth", "primitives": [primitive(mouth, 0)]},
        {"name": "Cheeks", "primitives": [primitive(cheeks, 6)]},
        {"name": "AntennaStem", "primitives": [primitive(antenna_stem, 0)]},
        {"name": "AntennaTip", "primitives": [primitive(sphere, 4)]},
        {"name": "OrbitRingOutline", "primitives": [primitive(torus_outline, 0)]},
        {"name": "OrbitRing", "primitives": [primitive(torus_gold, 4)]},
        {"name": "AchievementMedal", "primitives": [primitive(medal, 4)]},
        {"name": "AchievementStar", "primitives": [primitive(medal_star, 5)]},
        {"name": "SideSparkle", "primitives": [primitive(sparkle, 4)]},
        {"name": "ContactShadow", "primitives": [primitive(sphere, 7)]},
        {"name": "EyeWhites", "primitives": [primitive(eye_whites, 5)]},
    ]

    nodes: list[dict[str, object]] = []

    def node(name: str, **properties) -> int:
        nodes.append({"name": name, **properties})
        return len(nodes) - 1

    root = node(
        "OrbitRoot",
        extras={
            "identityId": "micro-orbit-004",
            "semantic": "proud",
            "identityFeatures": [
                "ringed-sphere-body",
                "single-antenna",
                "gold-orbit-ring",
                "side-star-effects",
                "achievement-medal",
            ],
        },
    )
    body_outline = node("BodyOutline", mesh=1, scale=[1.30, 1.30, 0.48])
    body = node("Body", mesh=0, translation=[0, 0, 0.10], scale=[1.22, 1.22, 0.55])
    lower_shade = node(
        "LowerShade",
        mesh=2,
        translation=[0.0, -0.78, 0.69],
        scale=[1.09, 0.25, 0.08],
    )
    highlight = node(
        "BodyHighlight",
        mesh=3,
        translation=[-0.10, 0.20, 0.73],
        scale=[0.85, 0.85, 1.0],
    )
    face = node(
        "Face",
        translation=[0, 0, 0.76],
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
    eye_white_node = node("EyeWhites", mesh=17, translation=[0, 0, 0.025])
    pupil_node = node("Pupils", mesh=5, translation=[0, 0, 0.04])
    brow_node = node("UpwardBrows", mesh=6, translation=[0, 0, 0.05])
    mouth_node = node("AsymmetricConfidentSmile", mesh=7, translation=[0, 0, 0.05])
    cheek_node = node("LiftedCheeks", mesh=8, translation=[0, 0, 0.05])
    medal_node = node("AchievementMedal", mesh=13, translation=[0, 0, 0.02])
    medal_star_node = node("AchievementStar", mesh=14, translation=[0, -0.76, 0.018])
    antenna_pivot = node(
        "AntennaPivot",
        translation=[0.04, 1.29, 0],
        extras={
            "attachment": "continuous-curved",
            "baseOverlapsHead": True,
        },
    )
    antenna_stem_node = node("AntennaStem", mesh=9)
    antenna_tip_outline = node(
        "AntennaTipOutline",
        mesh=1,
        translation=[0.0, 0.58, 0.0],
        scale=[0.25, 0.25, 0.13],
    )
    antenna_tip = node(
        "AntennaTip",
        mesh=10,
        translation=[0.0, 0.58, 0.15],
        scale=[0.19, 0.19, 0.15],
    )
    ring_pivot = node(
        "OrbitRingPivot",
        rotation=x_rotation(22),
        extras={"secondaryMotion": "counter-tilt"},
    )
    ring_outline_node = node("OrbitRingOutline", mesh=11)
    ring_node = node("OrbitRing", mesh=12, translation=[0.0, 0.0, 0.08])
    left_star = node(
        "LeftStar",
        mesh=15,
        translation=[-1.53, 0.43, 0.35],
        scale=[0.42, 0.42, 0.42],
    )
    right_star = node(
        "RightStar",
        mesh=15,
        translation=[1.53, -0.35, 0.30],
        scale=[0.22, 0.22, 0.22],
    )
    shadow = node(
        "GroundShadow",
        mesh=16,
        translation=[0.0, -1.48, -0.24],
        scale=[1.12, 0.08, 0.38],
    )

    nodes[root]["children"] = [
        body_outline,
        body,
        lower_shade,
        highlight,
        face,
        antenna_pivot,
        ring_pivot,
        left_star,
        right_star,
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
    nodes[antenna_pivot]["children"] = [
        antenna_stem_node,
        antenna_tip_outline,
        antenna_tip,
    ]
    nodes[ring_pivot]["children"] = [ring_outline_node, ring_node]

    document: dict[str, object] = {
        "asset": {
            "version": "2.0",
            "generator": "MascotRender deterministic Micro Orbit generator",
            "extras": {
                "mascot": "micro-orbit-004",
                "clips": CLIP_NAMES,
                "productionUse": "approved-as-selected-styled-glb-proof",
                "approvalGate": "micro-orbit-final-glb-face-parity-v1",
                "palette": PALETTE,
                "faceParityContract": {
                    "eyeConstruction": "narrow-horizontal-almond",
                    "proudEyelids": "composed",
                    "eyebrows": "smooth-arched",
                    "smile": "compact-curved",
                    "blush": "restrained",
                    "antennaAttachment": "continuous-curved",
                },
            },
        },
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"name": "MicroOrbitSticker", "nodes": [root, shadow]}],
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
                [[1, 1, 1], [1.018, 0.982, 1], [1, 1, 1]],
                "VEC3",
            ),
            (
                antenna_pivot,
                "rotation",
                [0.0, 0.6, 1.2],
                [z_rotation(0), z_rotation(3), z_rotation(0)],
                "VEC4",
            ),
        ],
    )
    add_animation(
        document,
        buffer,
        "orbital-tilt",
        [
            (
                root,
                "rotation",
                [0.0, 0.3, 0.6, 0.9, 1.2],
                [z_rotation(0), z_rotation(-3), z_rotation(2), z_rotation(-1), z_rotation(0)],
                "VEC4",
            ),
            (
                ring_pivot,
                "rotation",
                [0.0, 0.6, 1.2],
                [x_rotation(22), x_rotation(28), x_rotation(22)],
                "VEC4",
            ),
            (
                antenna_pivot,
                "rotation",
                [0.0, 0.3, 0.6, 1.2],
                [z_rotation(0), z_rotation(5), z_rotation(-3), z_rotation(0)],
                "VEC4",
            ),
        ],
    )
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document, binary = build_document()
    payload = encode_glb(document, binary)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            raise SystemExit(f"generated GLB differs from {args.output}")
        print(f"verified deterministic GLB: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(
        f"wrote {args.output} ({len(payload)} bytes, {len(CLIP_NAMES)} clips, "
        "styled Orbit identity proof)"
    )


if __name__ == "__main__":
    main()
