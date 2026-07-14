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


def face_geometry():
    positions: list[list[float]] = []
    indices: list[int] = []

    def quad(left: float, right: float, bottom: float, top: float) -> None:
        start = len(positions)
        positions.extend(
            [
                [left, bottom, 1.02],
                [right, bottom, 1.02],
                [right, top, 1.02],
                [left, top, 1.02],
            ]
        )
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])

    quad(-0.52, -0.18, 0.08, 0.35)
    quad(0.18, 0.52, 0.08, 0.35)
    quad(-0.28, 0.28, -0.34, -0.18)
    normals = [[0.0, 0.0, 1.0] for _ in positions]

    targets: list[list[list[float]]] = []
    for name in MORPH_NAMES:
        delta = [[0.0, 0.0, 0.0] for _ in positions]
        if name == "blink":
            for start in (0, 4):
                for index in (start, start + 1):
                    delta[index][1] += 0.11
                for index in (start + 2, start + 3):
                    delta[index][1] -= 0.11
        elif name == "smile":
            delta[8][1] += 0.02
            delta[9][1] += 0.02
            delta[10][1] += 0.13
            delta[11][1] += 0.13
        elif name == "wow":
            for index in range(8, 12):
                delta[index][0] = -positions[index][0] * 0.48
            delta[8][1] -= 0.09
            delta[9][1] -= 0.09
            delta[10][1] += 0.13
            delta[11][1] += 0.13
        elif name == "squint":
            delta[0][1] += 0.09
            delta[2][1] -= 0.09
            delta[4][1] -= 0.09
            delta[6][1] += 0.09
        elif name == "sad":
            delta[8][1] -= 0.12
            delta[9][1] -= 0.12
            delta[10][1] -= 0.01
            delta[11][1] -= 0.01
        elif name == "cheek":
            for index in range(0, 4):
                delta[index][0] -= 0.07
            for index in range(4, 8):
                delta[index][0] += 0.07
            for index in range(8, 12):
                delta[index][0] = positions[index][0] * 0.18
        targets.append(delta)
    return positions, normals, indices, targets


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

    face_positions, face_normals, face_indices, face_targets = face_geometry()
    face_position = buffer.floats(face_positions, "VEC3", target=34962, bounds=True)
    face_normal = buffer.floats(face_normals, "VEC3", target=34962)
    face_index = buffer.indices(face_indices)
    morph_accessors = [
        buffer.floats(target, "VEC3", target=34962, bounds=True)
        for target in face_targets
    ]

    materials = [
        {
            "name": "robot-yellow",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 0.61, 0.06, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.88,
            },
            "doubleSided": True,
        },
        {
            "name": "robot-teal",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.03, 0.55, 0.66, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.9,
            },
            "doubleSided": True,
        },
        {
            "name": "face-ink",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.025, 0.045, 0.075, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "extensions": {"KHR_materials_unlit": {}},
            "doubleSided": True,
        },
        {
            "name": "antenna-coral",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 0.22, 0.31, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8,
            },
            "doubleSided": True,
        },
    ]

    sphere_primitive = {
        "attributes": {"POSITION": sphere_position, "NORMAL": sphere_normal},
        "indices": sphere_index,
    }
    meshes = []
    for name, material in (
        ("HeadShell", 0),
        ("BodyShell", 1),
        ("DarkPart", 2),
        ("AccentPart", 3),
    ):
        primitive = dict(sphere_primitive)
        primitive["material"] = material
        meshes.append({"name": name, "primitives": [primitive]})
    meshes.append(
        {
            "name": "FaceRig",
            "weights": [0.0] * len(MORPH_NAMES),
            "extras": {"targetNames": MORPH_NAMES},
            "primitives": [
                {
                    "attributes": {"POSITION": face_position, "NORMAL": face_normal},
                    "indices": face_index,
                    "material": 2,
                    "targets": [
                        {"POSITION": accessor} for accessor in morph_accessors
                    ],
                }
            ],
        }
    )

    nodes = [
        {"name": "RobotRoot", "children": [1, 2, 6, 7, 8, 9, 10]},
        {
            "name": "Body",
            "mesh": 1,
            "translation": [0.0, -0.42, 0.0],
            "scale": [0.7, 0.68, 0.46],
        },
        {
            "name": "Head",
            "mesh": 0,
            "translation": [0.0, 0.47, 0.0],
            "scale": [1.0, 0.78, 0.55],
            "children": [3, 4, 5],
        },
        {"name": "Face", "mesh": 4},
        {
            "name": "Antenna",
            "mesh": 3,
            "translation": [0.0, 1.12, 0.0],
            "scale": [0.075, 0.43, 0.075],
        },
        {
            "name": "AntennaTip",
            "mesh": 3,
            "translation": [0.0, 1.55, 0.0],
            "scale": [0.17, 0.17, 0.17],
        },
        {
            "name": "LeftArm",
            "mesh": 1,
            "translation": [-0.82, -0.32, 0.0],
            "scale": [0.19, 0.52, 0.2],
        },
        {
            "name": "RightArm",
            "mesh": 1,
            "translation": [0.82, -0.32, 0.0],
            "scale": [0.19, 0.52, 0.2],
        },
        {
            "name": "LeftFoot",
            "mesh": 2,
            "translation": [-0.34, -1.04, 0.03],
            "scale": [0.3, 0.17, 0.34],
        },
        {
            "name": "RightFoot",
            "mesh": 2,
            "translation": [0.34, -1.04, 0.03],
            "scale": [0.3, 0.17, 0.34],
        },
        {"name": "caption_anchor", "translation": [0.0, 1.95, 0.0]},
    ]

    document: dict[str, object] = {
        "asset": {
            "version": "2.0",
            "generator": "MascotRender deterministic robot generator",
            "extras": {
                "mascot": "robot-004",
                "clips": CLIP_NAMES,
                "facialMorphTargets": MORPH_NAMES,
            },
        },
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"name": "RobotSticker", "nodes": [0]}],
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
            (2, "rotation", [0.0, 0.5, 1.0], [z_rotation(0), z_rotation(-3), z_rotation(0)], "VEC4"),
            (3, "weights", [0.0, 0.46, 0.54, 1.0], [zeros, blink, blink, zeros], "SCALAR"),
        ],
    )
    add_animation(
        document,
        buffer,
        "hello",
        [
            (6, "rotation", [0.0, 0.3, 0.6, 0.9], [z_rotation(0), z_rotation(38), z_rotation(-28), z_rotation(0)], "VEC4"),
            (2, "rotation", [0.0, 0.45, 0.9], [z_rotation(0), z_rotation(-6), z_rotation(0)], "VEC4"),
        ],
    )
    add_animation(
        document,
        buffer,
        "hop",
        [
            (0, "translation", [0.0, 0.3, 0.6, 0.9], [[0, 0, 0], [0, 0.32, 0], [0, 0.08, 0], [0, 0, 0]], "VEC3"),
            (0, "scale", [0.0, 0.15, 0.3, 0.75, 0.9], [[1, 1, 1], [1.08, 0.9, 1], [0.95, 1.08, 1], [1.04, 0.94, 1], [1, 1, 1]], "VEC3"),
        ],
    )
    add_animation(
        document,
        buffer,
        "celebrate",
        [
            (0, "rotation", [0.0, 0.25, 0.5, 0.75, 1.0], [z_rotation(0), z_rotation(-7), z_rotation(7), z_rotation(-4), z_rotation(0)], "VEC4"),
            (3, "weights", [0.0, 0.2, 0.55, 0.8, 1.0], [zeros, smile, smile, wow, zeros], "SCALAR"),
            (6, "rotation", [0.0, 0.5, 1.0], [z_rotation(0), z_rotation(48), z_rotation(0)], "VEC4"),
            (7, "rotation", [0.0, 0.5, 1.0], [z_rotation(0), z_rotation(-48), z_rotation(0)], "VEC4"),
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
