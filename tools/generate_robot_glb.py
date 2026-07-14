#!/usr/bin/env python3
"""Generate the deterministic MR-112 robot-004 GLB asset."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct


MORPH_NAMES = ["blink", "smile", "wow", "squint", "sad", "cheek"]
CLIP_NAMES = ["idle", "hello", "hop", "celebrate"]


class GlbBuffer:
    def __init__(self) -> None:
        self.data = bytearray()
        self.views: list[dict[str, int]] = []
        self.accessors: list[dict[str, object]] = []

    def _view(self, payload: bytes, target: int | None = None) -> int:
        while len(self.data) % 4:
            self.data.append(0)
        offset = len(self.data)
        self.data.extend(payload)
        view: dict[str, int] = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(payload),
        }
        if target is not None:
            view["target"] = target
        self.views.append(view)
        return len(self.views) - 1

    def floats(
        self,
        rows: list[list[float]],
        kind: str,
        *,
        target: int | None = None,
        bounds: bool = False,
    ) -> int:
        payload = b"".join(
            struct.pack("<" + "f" * len(row), *row) for row in rows
        )
        accessor: dict[str, object] = {
            "bufferView": self._view(payload, target),
            "componentType": 5126,
            "count": len(rows),
            "type": kind,
        }
        if bounds and rows:
            accessor["min"] = [min(row[i] for row in rows) for i in range(len(rows[0]))]
            accessor["max"] = [max(row[i] for row in rows) for i in range(len(rows[0]))]
        self.accessors.append(accessor)
        return len(self.accessors) - 1

    def scalars(self, values: list[float], *, bounds: bool = False) -> int:
        return self.floats([[value] for value in values], "SCALAR", bounds=bounds)

    def indices(self, values: list[int]) -> int:
        payload = struct.pack("<" + "H" * len(values), *values)
        self.accessors.append(
            {
                "bufferView": self._view(payload, 34963),
                "componentType": 5123,
                "count": len(values),
                "type": "SCALAR",
                "min": [min(values)],
                "max": [max(values)],
            }
        )
        return len(self.accessors) - 1


def uv_sphere(latitudes: int = 12, longitudes: int = 16):
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    for latitude in range(latitudes + 1):
        phi = math.pi * latitude / latitudes
        y = math.cos(phi)
        radius = math.sin(phi)
        for longitude in range(longitudes + 1):
            theta = 2.0 * math.pi * longitude / longitudes
            x = radius * math.cos(theta)
            z = radius * math.sin(theta)
            positions.append([x, y, z])
            normals.append([x, y, z])
    stride = longitudes + 1
    for latitude in range(latitudes):
        for longitude in range(longitudes):
            a = latitude * stride + longitude
            b = a + stride
            indices.extend([a, b, a + 1, a + 1, b, b + 1])
    return positions, normals, indices


def rounded_rect_prism(
    width: float,
    height: float,
    depth: float,
    radius: float,
    corner_segments: int = 6,
):
    """Return a compact rounded-square prism with a flat sticker-friendly face."""
    half_width = width * 0.5
    half_height = height * 0.5
    border: list[list[float]] = []
    corners = [
        (half_width - radius, -half_height + radius, -90.0),
        (half_width - radius, half_height - radius, 0.0),
        (-half_width + radius, half_height - radius, 90.0),
        (-half_width + radius, -half_height + radius, 180.0),
    ]
    for center_x, center_y, start_angle in corners:
        for step in range(corner_segments):
            angle = math.radians(start_angle + 90.0 * step / corner_segments)
            border.append(
                [
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                ]
            )

    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    front = depth * 0.5
    back = -front

    front_center = len(positions)
    positions.append([0.0, 0.0, front])
    normals.append([0.0, 0.0, 1.0])
    front_border = len(positions)
    for x, y in border:
        positions.append([x, y, front])
        normals.append([0.0, 0.0, 1.0])
    for index in range(len(border)):
        next_index = (index + 1) % len(border)
        indices.extend(
            [front_center, front_border + index, front_border + next_index]
        )

    back_center = len(positions)
    positions.append([0.0, 0.0, back])
    normals.append([0.0, 0.0, -1.0])
    back_border = len(positions)
    for x, y in border:
        positions.append([x, y, back])
        normals.append([0.0, 0.0, -1.0])
    for index in range(len(border)):
        next_index = (index + 1) % len(border)
        indices.extend(
            [back_center, back_border + next_index, back_border + index]
        )

    for index, (x, y) in enumerate(border):
        next_index = (index + 1) % len(border)
        next_x, next_y = border[next_index]
        midpoint_x = (x + next_x) * 0.5
        midpoint_y = (y + next_y) * 0.5
        length = math.hypot(midpoint_x / half_width, midpoint_y / half_height)
        normal = [
            midpoint_x / half_width / length,
            midpoint_y / half_height / length,
            0.0,
        ]
        start = len(positions)
        positions.extend(
            [[x, y, front], [x, y, back], [next_x, next_y, back], [next_x, next_y, front]]
        )
        normals.extend([normal] * 4)
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])
    return positions, normals, indices


def ellipse_geometry(
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    *,
    segments: int = 20,
):
    positions = [[center_x, center_y, 0.0]]
    positions.extend(
        [
            [
                center_x + radius_x * math.cos(2.0 * math.pi * step / segments),
                center_y + radius_y * math.sin(2.0 * math.pi * step / segments),
                0.0,
            ]
            for step in range(segments)
        ]
    )
    indices: list[int] = []
    for step in range(segments):
        indices.extend([0, 1 + step, 1 + ((step + 1) % segments)])
    return positions, [[0.0, 0.0, 1.0] for _ in positions], indices


def curve_geometry(points: list[list[float]], width: float):
    positions: list[list[float]] = []
    indices: list[int] = []
    half_width = width * 0.5
    for start_point, end_point in zip(points, points[1:]):
        delta_x = end_point[0] - start_point[0]
        delta_y = end_point[1] - start_point[1]
        length = math.hypot(delta_x, delta_y)
        normal_x = -delta_y / length * half_width
        normal_y = delta_x / length * half_width
        start = len(positions)
        positions.extend(
            [
                [start_point[0] + normal_x, start_point[1] + normal_y, 0.0],
                [start_point[0] - normal_x, start_point[1] - normal_y, 0.0],
                [end_point[0] - normal_x, end_point[1] - normal_y, 0.0],
                [end_point[0] + normal_x, end_point[1] + normal_y, 0.0],
            ]
        )
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])
    return positions, [[0.0, 0.0, 1.0] for _ in positions], indices


def quadratic_curve(start, control, end, steps: int = 18):
    return [
        [
            (1.0 - time) ** 2 * start[0]
            + 2.0 * (1.0 - time) * time * control[0]
            + time**2 * end[0],
            (1.0 - time) ** 2 * start[1]
            + 2.0 * (1.0 - time) * time * control[1]
            + time**2 * end[1],
        ]
        for time in (step / steps for step in range(steps + 1))
    ]


def combine_geometry(parts):
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    for part_positions, part_normals, part_indices in parts:
        offset = len(positions)
        positions.extend(part_positions)
        normals.extend(part_normals)
        indices.extend(offset + index for index in part_indices)
    return positions, normals, indices


def eye_geometry(radius_x: float, radius_y: float):
    return combine_geometry(
        [
            ellipse_geometry(-0.34, 0.18, radius_x, radius_y),
            ellipse_geometry(0.34, 0.18, radius_x, radius_y),
        ]
    )


def face_ink_geometry():
    pupil_positions, pupil_normals, pupil_indices = eye_geometry(0.07, 0.105)
    targets: list[list[list[float]]] = []
    for name in MORPH_NAMES:
        delta: list[list[float]] = []
        for x, y, _ in pupil_positions:
            eye_center_y = 0.18
            if name == "blink":
                delta.append([0.0, (eye_center_y - y) * 0.88, 0.0])
            elif name == "wow":
                eye_center_x = -0.34 if x < 0.0 else 0.34
                delta.append([(x - eye_center_x) * 0.35, (y - eye_center_y) * 0.35, 0.0])
            elif name == "squint":
                delta.append([0.0, (eye_center_y - y) * 0.58, 0.0])
            elif name == "sad":
                delta.append([0.0, -0.035, 0.0])
            elif name == "cheek":
                delta.append([-0.025 if x < 0.0 else 0.025, 0.0, 0.0])
            else:
                delta.append([0.0, 0.025, 0.0])
        targets.append(delta)
    return pupil_positions, pupil_normals, pupil_indices, targets


def facial_curve_geometry():
    return combine_geometry(
        [
            curve_geometry(
                quadratic_curve((-0.52, 0.37), (-0.34, 0.57), (-0.16, 0.37)),
                0.075,
            ),
            curve_geometry(
                quadratic_curve((0.16, 0.37), (0.34, 0.57), (0.52, 0.37)),
                0.075,
            ),
            curve_geometry(
                quadratic_curve((-0.38, -0.22), (0.0, -0.62), (0.38, -0.22)),
                0.075,
            ),
        ]
    )


def triangle_geometry():
    positions = [[-0.1, -0.03, 0.0], [0.1, -0.03, 0.0], [0.0, -0.16, 0.0]]
    return positions, [[0.0, 0.0, 1.0]] * 3, [0, 1, 2]


def star_geometry():
    positions = [[0.0, 0.0, 0.0]]
    for point in range(8):
        angle = math.pi * 0.5 - point * math.pi * 0.25
        radius = 0.31 if point % 2 == 0 else 0.095
        positions.append([radius * math.cos(angle), radius * math.sin(angle), 0.0])
    indices: list[int] = []
    for point in range(8):
        indices.extend([0, 1 + point, 1 + ((point + 1) % 8)])
    return positions, [[0.0, 0.0, 1.0] for _ in positions], indices


def unlit_material(name: str, color: str, alpha: float = 1.0):
    # Post-processing is deliberately disabled by the headless sticker renderer,
    # so store display-space channels to preserve the approved SVG palette in
    # the byte output instead of applying a second transfer curve.
    channels = [int(color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
    material: dict[str, object] = {
        "name": name,
        "pbrMetallicRoughness": {
            "baseColorFactor": [*channels, alpha],
            "metallicFactor": 0.0,
            "roughnessFactor": 1.0,
        },
        "extensions": {"KHR_materials_unlit": {}},
        "doubleSided": True,
    }
    if alpha < 1.0:
        material["alphaMode"] = "BLEND"
    return material


def z_rotation(degrees: float) -> list[float]:
    radians = math.radians(degrees) * 0.5
    return [0.0, 0.0, math.sin(radians), math.cos(radians)]


def add_animation(
    document: dict[str, object],
    buffer: GlbBuffer,
    name: str,
    tracks: list[tuple[int, str, list[float], list[list[float]], str]],
) -> None:
    samplers: list[dict[str, object]] = []
    channels: list[dict[str, object]] = []
    for node, path, times, values, kind in tracks:
        input_accessor = buffer.scalars(times, bounds=True)
        if kind == "SCALAR":
            output_accessor = buffer.scalars(
                [component for row in values for component in row]
            )
        else:
            output_accessor = buffer.floats(values, kind)
        samplers.append(
            {
                "input": input_accessor,
                "output": output_accessor,
                "interpolation": "LINEAR",
            }
        )
        channels.append(
            {
                "sampler": len(samplers) - 1,
                "target": {"node": node, "path": path},
            }
        )
    document.setdefault("animations", []).append(
        {"name": name, "samplers": samplers, "channels": channels}
    )


def build_document() -> tuple[dict[str, object], bytes]:
    buffer = GlbBuffer()
    sphere_positions, sphere_normals, sphere_indices = uv_sphere()
    sphere_position = buffer.floats(
        sphere_positions, "VEC3", target=34962, bounds=True
    )
    sphere_normal = buffer.floats(sphere_normals, "VEC3", target=34962)
    sphere_index = buffer.indices(sphere_indices)

    def mesh_accessors(geometry):
        positions, normals, indices = geometry
        return (
            buffer.floats(positions, "VEC3", target=34962, bounds=True),
            buffer.floats(normals, "VEC3", target=34962),
            buffer.indices(indices),
        )

    head_accessors = mesh_accessors(rounded_rect_prism(2.0, 1.85, 0.68, 0.37))
    panel_accessors = mesh_accessors(rounded_rect_prism(1.7, 1.52, 0.08, 0.28))
    body_accessors = mesh_accessors(rounded_rect_prism(1.18, 0.62, 0.58, 0.22))
    white_eye_accessors = mesh_accessors(eye_geometry(0.15, 0.23))
    face_positions, face_normals, face_indices, face_targets = face_ink_geometry()
    face_accessors = (
        buffer.floats(face_positions, "VEC3", target=34962, bounds=True),
        buffer.floats(face_normals, "VEC3", target=34962),
        buffer.indices(face_indices),
    )
    morph_accessors = [
        buffer.floats(target, "VEC3", target=34962, bounds=True)
        for target in face_targets
    ]
    curve_accessors = mesh_accessors(facial_curve_geometry())
    nose_accessors = mesh_accessors(triangle_geometry())
    star_accessors = mesh_accessors(star_geometry())

    materials = [
        unlit_material("robot-gold", "#FFD166"),
        unlit_material("robot-orange-trim", "#E49B36"),
        unlit_material("robot-mint", "#7AE1D2"),
        unlit_material("face-ink", "#3C3042"),
        unlit_material("eye-cream", "#FFF7DA"),
        unlit_material("contact-shadow", "#3C3042", 0.24),
    ]

    def primitive(accessors, material, targets=None):
        position, normal, index = accessors
        result: dict[str, object] = {
            "attributes": {"POSITION": position, "NORMAL": normal},
            "indices": index,
            "material": material,
        }
        if targets is not None:
            result["targets"] = [{"POSITION": accessor} for accessor in targets]
        return result

    sphere_accessors = (sphere_position, sphere_normal, sphere_index)
    meshes = [
        {"name": "HeadShell", "primitives": [primitive(head_accessors, 1)]},
        {"name": "FacePlate", "primitives": [primitive(panel_accessors, 0)]},
        {"name": "BodyShell", "primitives": [primitive(body_accessors, 0)]},
        {"name": "OrangePart", "primitives": [primitive(sphere_accessors, 1)]},
        {"name": "MintPart", "primitives": [primitive(sphere_accessors, 2)]},
        {"name": "DarkPart", "primitives": [primitive(sphere_accessors, 3)]},
        {"name": "EyeWhites", "primitives": [primitive(white_eye_accessors, 4)]},
        {
            "name": "FaceRig",
            "weights": [0.0] * len(MORPH_NAMES),
            "extras": {"targetNames": MORPH_NAMES},
            "primitives": [primitive(face_accessors, 3, morph_accessors)],
        },
        {"name": "FacialCurves", "primitives": [primitive(curve_accessors, 3)]},
        {"name": "MintNose", "primitives": [primitive(nose_accessors, 2)]},
        {"name": "Sparkle", "primitives": [primitive(star_accessors, 2)]},
        {"name": "ContactShadow", "primitives": [primitive(sphere_accessors, 5)]},
    ]

    nodes: list[dict[str, object]] = []

    def node(name: str, **properties) -> int:
        nodes.append({"name": name, **properties})
        return len(nodes) - 1

    robot_root = node("RobotRoot")
    body = node("Body", mesh=2, translation=[0.0, -0.78, -0.04])
    head = node("Head", mesh=0, translation=[0.0, 0.2, 0.0])
    face_panel = node("FacePlate", mesh=1, translation=[0.0, 0.0, 0.37])
    face = node("Face", translation=[0.0, 0.0, 0.425])
    eye_group = node("EyeGroup")
    eye_whites = node("EyeWhites", mesh=6)
    face_rig = node("FaceRig", mesh=7)
    facial_curves = node("FacialCurves", mesh=8, translation=[0.0, 0.0, 0.012])
    nose = node("Nose", mesh=9, translation=[0.0, 0.0, 0.018])
    antenna = node(
        "Antenna",
        mesh=5,
        translation=[0.0, 1.08, 0.0],
        scale=[0.065, 0.3, 0.065],
    )
    antenna_tip = node(
        "AntennaTip",
        mesh=4,
        translation=[0.0, 1.38, 0.0],
        scale=[0.16, 0.16, 0.16],
    )
    left_arm_pivot = node("LeftArmPivot", translation=[-1.0, 0.12, 0.0])
    left_arm = node(
        "LeftArm",
        mesh=3,
        translation=[-0.02, -0.34, 0.0],
        scale=[0.17, 0.4, 0.18],
    )
    right_arm_pivot = node("RightArmPivot", translation=[1.0, 0.12, 0.0])
    right_arm = node(
        "RightArm",
        mesh=3,
        translation=[0.02, -0.34, 0.0],
        scale=[0.17, 0.4, 0.18],
    )
    left_foot = node(
        "LeftFoot",
        mesh=5,
        translation=[-0.37, -1.09, 0.05],
        scale=[0.32, 0.14, 0.28],
    )
    right_foot = node(
        "RightFoot",
        mesh=5,
        translation=[0.37, -1.09, 0.05],
        scale=[0.32, 0.14, 0.28],
    )
    shadow = node(
        "GroundShadow",
        mesh=11,
        translation=[0.0, -1.19, -0.24],
        scale=[1.04, 0.12, 0.3],
    )
    sparkle = node(
        "Sparkle",
        mesh=10,
        translation=[-1.34, 0.2, 0.1],
        scale=[0.85, 0.85, 0.85],
    )
    caption_anchor = node("caption_anchor", translation=[0.0, 1.88, 0.0])

    nodes[robot_root]["children"] = [
        body,
        head,
        left_arm_pivot,
        right_arm_pivot,
        left_foot,
        right_foot,
    ]
    nodes[head]["children"] = [face_panel, face, antenna, antenna_tip]
    nodes[face]["children"] = [eye_group, facial_curves, nose]
    nodes[eye_group]["children"] = [eye_whites, face_rig]
    nodes[left_arm_pivot]["children"] = [left_arm]
    nodes[right_arm_pivot]["children"] = [right_arm]

    document: dict[str, object] = {
        "asset": {
            "version": "2.0",
            "generator": "MascotRender deterministic robot generator",
            "extras": {
                "mascot": "robot-004",
                "clips": CLIP_NAMES,
                "facialMorphTargets": MORPH_NAMES,
                "visualContract": "approved-2d-2.5d-robot-v3",
                "palette": {
                    "gold": "#FFD166",
                    "orange": "#E49B36",
                    "mint": "#7AE1D2",
                    "ink": "#3C3042",
                    "cream": "#FFF7DA",
                },
            },
        },
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [
            {
                "name": "RobotSticker",
                "nodes": [robot_root, shadow, sparkle, caption_anchor],
            }
        ],
        "nodes": nodes,
        "materials": materials,
        "meshes": meshes,
    }

    zeros = [0.0] * len(MORPH_NAMES)
    blink = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    smile = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    wow = [0.0, 0.0, 1.0, 0.0, 0.0, 0.0]

    add_animation(
        document,
        buffer,
        "idle",
        [
            (head, "rotation", [0.0, 0.5, 1.0], [z_rotation(0), z_rotation(-3), z_rotation(0)], "VEC4"),
            (eye_group, "scale", [0.0, 0.44, 0.5, 0.56, 1.0], [[1, 1, 1], [1, 1, 1], [1, 0.08, 1], [1, 1, 1], [1, 1, 1]], "VEC3"),
            (face_rig, "weights", [0.0, 0.46, 0.54, 1.0], [zeros, blink, blink, zeros], "SCALAR"),
        ],
    )
    add_animation(
        document,
        buffer,
        "hello",
        [
            (left_arm_pivot, "rotation", [0.0, 0.22, 0.46, 0.7, 0.9], [z_rotation(0), z_rotation(-118), z_rotation(-78), z_rotation(-124), z_rotation(0)], "VEC4"),
            (head, "rotation", [0.0, 0.45, 0.9], [z_rotation(0), z_rotation(7), z_rotation(0)], "VEC4"),
            (face_rig, "weights", [0.0, 0.45, 0.9], [zeros, smile, zeros], "SCALAR"),
        ],
    )
    add_animation(
        document,
        buffer,
        "hop",
        [
            (robot_root, "translation", [0.0, 0.3, 0.6, 0.9], [[0, 0, 0], [0, 0.58, 0], [0, 0.16, 0], [0, 0, 0]], "VEC3"),
            (robot_root, "scale", [0.0, 0.15, 0.3, 0.72, 0.9], [[1, 1, 1], [1.1, 0.9, 1], [0.92, 1.12, 1], [1.08, 0.92, 1], [1, 1, 1]], "VEC3"),
            (shadow, "scale", [0.0, 0.3, 0.6, 0.9], [[1.04, 0.12, 0.3], [0.55, 0.07, 0.3], [0.86, 0.1, 0.3], [1.04, 0.12, 0.3]], "VEC3"),
            (left_arm_pivot, "rotation", [0.0, 0.3, 0.9], [z_rotation(0), z_rotation(-28), z_rotation(0)], "VEC4"),
            (right_arm_pivot, "rotation", [0.0, 0.3, 0.9], [z_rotation(0), z_rotation(28), z_rotation(0)], "VEC4"),
        ],
    )
    add_animation(
        document,
        buffer,
        "celebrate",
        [
            (robot_root, "translation", [0.0, 0.22, 0.5, 0.78, 1.0], [[0, 0, 0], [0, 0.2, 0], [0, 0.05, 0], [0, 0.16, 0], [0, 0, 0]], "VEC3"),
            (head, "rotation", [0.0, 0.25, 0.5, 0.75, 1.0], [z_rotation(0), z_rotation(-9), z_rotation(9), z_rotation(-5), z_rotation(0)], "VEC4"),
            (face_rig, "weights", [0.0, 0.2, 0.55, 0.8, 1.0], [zeros, smile, smile, wow, zeros], "SCALAR"),
            (eye_group, "scale", [0.0, 0.5, 1.0], [[1, 1, 1], [1, 0.62, 1], [1, 1, 1]], "VEC3"),
            (left_arm_pivot, "rotation", [0.0, 0.25, 0.5, 0.75, 1.0], [z_rotation(0), z_rotation(-118), z_rotation(-132), z_rotation(-124), z_rotation(0)], "VEC4"),
            (right_arm_pivot, "rotation", [0.0, 0.25, 0.5, 0.75, 1.0], [z_rotation(0), z_rotation(118), z_rotation(132), z_rotation(124), z_rotation(0)], "VEC4"),
            (sparkle, "scale", [0.0, 0.25, 0.5, 0.75, 1.0], [[0.85, 0.85, 0.85], [1.25, 1.25, 1.25], [0.7, 0.7, 0.7], [1.15, 1.15, 1.15], [0.85, 0.85, 0.85]], "VEC3"),
        ],
    )

    while len(buffer.data) % 4:
        buffer.data.append(0)
    document["buffers"] = [{"byteLength": len(buffer.data)}]
    document["bufferViews"] = buffer.views
    document["accessors"] = buffer.accessors
    return document, bytes(buffer.data)


def encode_glb(document: dict[str, object], binary: bytes) -> bytes:
    json_bytes = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    binary += b"\0" * ((-len(binary)) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    return b"".join(
        [
            b"glTF",
            struct.pack("<II", 2, total),
            struct.pack("<I4s", len(json_bytes), b"JSON"),
            json_bytes,
            struct.pack("<I4s", len(binary), b"BIN\0"),
            binary,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--check", action="store_true", help="verify output instead of writing it"
    )
    args = parser.parse_args()
    document, binary = build_document()
    output = encode_glb(document, binary)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != output:
            raise SystemExit(f"generated GLB differs from {args.output}")
        print(f"verified deterministic GLB: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(
        f"wrote {args.output} ({len(output)} bytes, "
        f"{len(CLIP_NAMES)} clips, {len(MORPH_NAMES)} morph targets)"
    )


if __name__ == "__main__":
    main()
