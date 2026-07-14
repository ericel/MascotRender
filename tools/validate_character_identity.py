#!/usr/bin/env python3
"""Validate a 2D pack and deterministic GLB against one identity contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ElementTree


RATIO_NAMES = (
    "headAspectRatio",
    "headToBodyRatio",
    "eyeSpacingRatio",
    "eyeVerticalRatio",
    "mouthVerticalRatio",
    "antennaHeightRatio",
)


def fail(message: str) -> None:
    raise ValueError(message)


def normalized_color(value: str) -> str:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        fail(f"invalid identity color: {value}")
    return value.upper()


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("schema_version") != 1:
        fail("identity contract schema_version must be 1")
    if (
        not isinstance(contract.get("characterId"), str)
        or not contract["characterId"]
    ):
        fail("identity contract requires a non-empty characterId")
    identity = contract.get("identity")
    validation = contract.get("validation")
    if not isinstance(identity, dict) or not isinstance(validation, dict):
        fail("identity contract requires identity and validation objects")
    for name in ("primaryColor", "secondaryColor", "accentColor", "outlineColor"):
        normalized_color(identity.get(name, ""))
    for name in RATIO_NAMES:
        value = identity.get(name)
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            fail(f"identity contract requires a positive finite {name}")
    features = identity.get("requiredFeatures")
    if (
        not isinstance(features, list)
        or not features
        or any(not isinstance(feature, str) or not feature for feature in features)
        or len(features) != len(set(features))
    ):
        fail("identity contract requires unique non-empty requiredFeatures")
    tolerance = validation.get("ratioTolerance")
    if (
        not isinstance(tolerance, (int, float))
        or not math.isfinite(tolerance)
        or not 0 <= tolerance <= 0.25
    ):
        fail("identity contract ratioTolerance must be between 0 and 0.25")
    measurements = validation.get("measurements")
    if not isinstance(measurements, dict) or set(measurements) != set(RATIO_NAMES):
        fail("identity contract must define all six measurement rules")
    if any(not isinstance(rule, str) or not rule for rule in measurements.values()):
        fail("identity contract measurement rules must be non-empty strings")


def close_ratio(name: str, actual: float, expected: float, tolerance: float) -> None:
    if not math.isclose(actual, expected, abs_tol=tolerance):
        fail(
            f"{name} is {actual:.4f}; expected {expected:.4f} "
            f"within {tolerance:.4f}"
        )


def layer_source(pack: dict[str, object], pack_path: Path, layer_id: str) -> Path:
    for layer in pack["layers"]:
        if layer["id"] == layer_id:
            return pack_path.parent / layer["source"]
    fail(f"pack is missing identity layer: {layer_id}")


def svg_elements(path: Path, name: str) -> list[ElementTree.Element]:
    root = ElementTree.parse(path).getroot()
    return [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == name
    ]


def number(element: ElementTree.Element, attribute: str) -> float:
    try:
        return float(element.attrib[attribute])
    except (KeyError, ValueError) as error:
        fail(f"{attribute} is missing or invalid in SVG element: {error}")


def validate_pack(
    contract: dict[str, object], contract_sha256: str, pack_path: Path
) -> dict[str, float]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    identity = contract["identity"]
    declaration = pack.get("character_identity")
    expected_declaration = {
        "character_id": contract["characterId"],
        "contract_version": contract["schema_version"],
        "contract_sha256": contract_sha256,
        "required_features": identity["requiredFeatures"],
    }
    if declaration != expected_declaration:
        fail(f"{pack_path} character_identity does not match the contract")

    primary = normalized_color(identity["primaryColor"])
    secondary = normalized_color(identity["secondaryColor"])
    accent = normalized_color(identity["accentColor"])
    outline = normalized_color(identity["outlineColor"])

    head_rects = svg_elements(layer_source(pack, pack_path, "head"), "rect")
    body_rects = svg_elements(layer_source(pack, pack_path, "body"), "rect")
    face_path = layer_source(pack, pack_path, "face")
    eyes = svg_elements(face_path, "ellipse")
    face_paths = svg_elements(face_path, "path")
    antenna_path = layer_source(pack, pack_path, "antenna")
    antenna_lines = svg_elements(antenna_path, "path")
    antenna_tips = svg_elements(antenna_path, "circle")
    side_ears = svg_elements(
        layer_source(pack, pack_path, "side-panels"), "rect"
    )

    if len(head_rects) < 2 or len(body_rects) < 2 or len(eyes) != 2:
        fail("2D identity geometry is incomplete")
    head = head_rects[0]
    body_core = body_rects[1]
    head_y = number(head, "y")
    head_width = number(head, "width")
    head_height = number(head, "height")
    eye_centers = [number(eye, "cx") for eye in eyes]
    eye_y = sum(number(eye, "cy") for eye in eyes) / len(eyes)

    mouth = next(
        (
            path
            for path in face_paths
            if normalized_color(path.attrib.get("stroke", "#000000")) == outline
        ),
        None,
    )
    nose = next(
        (
            path
            for path in face_paths
            if normalized_color(path.attrib.get("fill", "#000000")) == accent
        ),
        None,
    )
    if mouth is None or nose is None:
        fail("2D face is missing the contract mouth or teal triangular nose")
    mouth_numbers = [
        float(value)
        for value in re.findall(r"-?\d+(?:\.\d+)?", mouth.attrib["d"])
    ]
    if len(mouth_numbers) < 2:
        fail("2D mouth path does not expose an identity anchor")
    mouth_y = mouth_numbers[1]

    if len(antenna_lines) != 1 or len(antenna_tips) != 1:
        fail("2D identity requires exactly one antenna and one tip")
    tip = antenna_tips[0]
    tip_top = number(tip, "cy") - number(tip, "r")
    if len(side_ears) != 2:
        fail("2D identity requires two orange side ears")

    color_checks = {
        "head primary": (head_rects[1].attrib.get("fill"), primary),
        "body primary": (body_core.attrib.get("fill"), primary),
        "head secondary": (head.attrib.get("fill"), secondary),
        "body secondary": (body_rects[0].attrib.get("fill"), secondary),
        "antenna tip": (tip.attrib.get("fill"), accent),
        "antenna stem": (antenna_lines[0].attrib.get("stroke"), outline),
    }
    for label, (actual, expected) in color_checks.items():
        if actual is None or normalized_color(actual) != expected:
            fail(f"2D {label} color does not match the identity contract")
    if any(
        normalized_color(ear.attrib.get("fill", "#000000")) != secondary
        for ear in side_ears
    ):
        fail("2D side-ear color does not match the identity contract")

    metrics = {
        "headAspectRatio": head_width / head_height,
        "headToBodyRatio": head_height / number(body_core, "height"),
        "eyeSpacingRatio": abs(eye_centers[1] - eye_centers[0]) / head_width,
        "eyeVerticalRatio": (eye_y - head_y) / head_height,
        "mouthVerticalRatio": (mouth_y - head_y) / head_height,
        "antennaHeightRatio": (head_y - tip_top) / head_height,
    }
    tolerance = float(contract["validation"]["ratioTolerance"])
    for name, actual in metrics.items():
        close_ratio(name, actual, float(identity[name]), tolerance)
    return metrics


def read_glb(path: Path) -> tuple[dict[str, object], bytes]:
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"glTF":
        fail(f"{path} is not a GLB document")
    version, total = struct.unpack_from("<II", payload, 4)
    if version != 2 or total != len(payload):
        fail(f"{path} has an invalid GLB header")
    offset = 12
    document = None
    binary = b""
    while offset < len(payload):
        length, chunk_type = struct.unpack_from("<I4s", payload, offset)
        chunk = payload[offset + 8 : offset + 8 + length]
        if chunk_type == b"JSON":
            document = json.loads(chunk)
        elif chunk_type == b"BIN\0":
            binary = chunk
        offset += 8 + length
    if document is None:
        fail(f"{path} has no JSON chunk")
    return document, binary


def accessor_rows(
    document: dict[str, object], binary: bytes, accessor_index: int
) -> list[tuple[float, ...]]:
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][accessor["bufferView"]]
    component_count = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
    }[accessor["type"]]
    if accessor["componentType"] != 5126:
        fail("identity geometry accessor is not float32")
    start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    stride = int(view.get("byteStride", component_count * 4))
    return [
        struct.unpack_from(
            "<" + "f" * component_count, binary, start + index * stride
        )
        for index in range(accessor["count"])
    ]


def position_rows(
    document: dict[str, object], binary: bytes, mesh_name: str
) -> list[tuple[float, ...]]:
    mesh = next(
        (item for item in document["meshes"] if item["name"] == mesh_name), None
    )
    if mesh is None:
        fail(f"GLB is missing identity mesh: {mesh_name}")
    accessor = mesh["primitives"][0]["attributes"]["POSITION"]
    return accessor_rows(document, binary, accessor)


def material_hex(document: dict[str, object], name: str) -> str:
    material = next(
        (item for item in document["materials"] if item["name"] == name), None
    )
    if material is None:
        fail(f"GLB is missing identity material: {name}")
    channels = material["pbrMetallicRoughness"]["baseColorFactor"][:3]
    return "#" + "".join(
        f"{round(float(channel) * 255):02X}" for channel in channels
    )


def bounds(rows: list[tuple[float, ...]], component: int) -> tuple[float, float]:
    values = [row[component] for row in rows]
    return min(values), max(values)


def validate_glb(
    contract: dict[str, object], contract_sha256: str, glb_path: Path
) -> dict[str, float]:
    document, binary = read_glb(glb_path)
    identity = contract["identity"]
    extras = document["asset"].get("extras", {})
    declaration = extras.get("characterIdentity")
    if declaration is None:
        fail("GLB does not declare asset.extras.characterIdentity")
    if declaration.get("characterId") != contract["characterId"]:
        fail("GLB characterId does not match the identity contract")
    if declaration.get("contractVersion") != contract["schema_version"]:
        fail("GLB contract version does not match")
    if declaration.get("contractSha256") != contract_sha256:
        fail("GLB identity contract hash is stale")
    if declaration.get("requiredFeatures") != identity["requiredFeatures"]:
        fail("GLB required features do not match the identity contract")

    palette = extras.get("palette", {})
    expected_palette = {
        "gold": identity["primaryColor"],
        "orange": identity["secondaryColor"],
        "mint": identity["accentColor"],
        "ink": identity["outlineColor"],
    }
    if any(
        normalized_color(palette.get(name, "")) != normalized_color(color)
        for name, color in expected_palette.items()
    ):
        fail("GLB declared palette does not match the identity contract")
    for material_name, color in (
        ("robot-gold", identity["primaryColor"]),
        ("robot-orange-trim", identity["secondaryColor"]),
        ("robot-mint", identity["accentColor"]),
        ("face-ink", identity["outlineColor"]),
    ):
        if material_hex(document, material_name) != normalized_color(color):
            fail(f"GLB material {material_name} does not match the contract")

    nodes = {node["name"]: node for node in document["nodes"]}
    features = {
        node.get("extras", {}).get("identityFeature")
        for node in document["nodes"]
        if node.get("extras", {}).get("identityFeature")
    }
    missing = set(identity["requiredFeatures"]) - features
    if missing:
        fail(f"GLB is missing identity features: {sorted(missing)}")
    antenna_count = sum(
        node.get("extras", {}).get("identityFeature") == "single_antenna"
        for node in document["nodes"]
    )
    if antenna_count != 1:
        fail("GLB identity requires exactly one antenna")
    if "LeftFoot" in nodes or "RightFoot" in nodes:
        fail("GLB identity must not introduce separate feet")
    if "Mouth" not in nodes or "FacialCurves" in nodes:
        fail("GLB must use the shared mascot mouth language without eyebrows")

    head_rows = position_rows(document, binary, "HeadShell")
    body_rows = position_rows(document, binary, "BodyShell")
    eye_rows = position_rows(document, binary, "EyeWhites")
    pupil_rows = position_rows(document, binary, "FaceRig")
    mouth_rows = position_rows(document, binary, "MouthCurve")
    head_x = bounds(head_rows, 0)
    head_y = bounds(head_rows, 1)
    body_y = bounds(body_rows, 1)
    head_width = head_x[1] - head_x[0]
    head_height = head_y[1] - head_y[0]
    negative_eye_x = bounds([row for row in eye_rows if row[0] < 0], 0)
    positive_eye_x = bounds([row for row in eye_rows if row[0] > 0], 0)
    left_eye_center = sum(negative_eye_x) * 0.5
    right_eye_center = sum(positive_eye_x) * 0.5
    eye_y = bounds(eye_rows, 1)
    eye_center_y = sum(eye_y) * 0.5
    pupil_x = bounds(pupil_rows, 0)
    pupil_y = bounds(pupil_rows, 1)
    pupil_combined_width = pupil_x[1] - pupil_x[0]
    expected_combined_width = (
        2 * float(identity["eyeSpacingRatio"]) + (pupil_y[1] - pupil_y[0])
    )
    if not math.isclose(pupil_combined_width, expected_combined_width, abs_tol=0.02):
        fail("GLB pupils are not the contract round-eye style")
    if len(mouth_rows) < 2:
        fail("GLB mouth mesh does not expose its curve anchor")
    mouth_y = (mouth_rows[0][1] + mouth_rows[1][1]) * 0.5

    tip = nodes["AntennaTip"]
    tip_top = float(tip["translation"][1]) + float(tip["scale"][1])
    metrics = {
        "headAspectRatio": head_width / head_height,
        "headToBodyRatio": head_height / (body_y[1] - body_y[0]),
        "eyeSpacingRatio": (right_eye_center - left_eye_center) / head_width,
        "eyeVerticalRatio": (head_y[1] - eye_center_y) / head_height,
        "mouthVerticalRatio": (head_y[1] - mouth_y) / head_height,
        "antennaHeightRatio": (tip_top - head_y[1]) / head_height,
    }
    tolerance = float(contract["validation"]["ratioTolerance"])
    for name, actual in metrics.items():
        close_ratio(name, actual, float(identity[name]), tolerance)
        close_ratio(
            f"declared {name}",
            float(declaration["metrics"][name]),
            float(identity[name]),
            0.0,
        )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--flat-pack", type=Path)
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    contract_bytes = args.contract.read_bytes()
    contract = json.loads(contract_bytes)
    validate_contract(contract)
    contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
    pack_metrics = validate_pack(contract, contract_sha256, args.pack)
    if args.flat_pack is not None:
        flat_metrics = validate_pack(contract, contract_sha256, args.flat_pack)
        if flat_metrics != pack_metrics:
            fail("flat and layered packs resolve different identity metrics")
    glb_metrics = validate_glb(contract, contract_sha256, args.glb)

    report = {
        "characterId": contract["characterId"],
        "contractSha256": contract_sha256,
        "requiredFeatures": contract["identity"]["requiredFeatures"],
        "packMetrics": {
            name: round(value, 6) for name, value in pack_metrics.items()
        },
        "glbMetrics": {
            name: round(value, 6) for name, value in glb_metrics.items()
        },
        "status": "pass",
    }
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
