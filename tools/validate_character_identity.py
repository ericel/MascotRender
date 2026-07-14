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


METRIC_NAMES = (
    "headAspectRatio",
    "headToBodyRatio",
    "mouthVerticalRatio",
    "antennaStemWidthRatio",
    "antennaTotalHeightRatio",
    "antennaTipDiameterRatio",
    "eyesWidthToHeadRatio",
    "eyesHeightToHeadRatio",
    "eyesHorizontalSpacingRatio",
    "eyesVerticalCenterRatio",
    "bodyFrameWidthToHeadRatio",
    "bodyInsetWidthToFrameRatio",
    "bodyInsetHeightToFrameRatio",
    "sparkleScreenSizeRatio",
)


def fail(message: str) -> None:
    raise ValueError(message)


def normalized_color(value: str) -> str:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        fail(f"invalid identity color: {value}")
    return value.upper()


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("schema_version") != 2:
        fail("identity contract schema_version must be 2")
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
    for name in ("headAspectRatio", "headToBodyRatio", "mouthVerticalRatio"):
        value = identity.get(name)
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            fail(f"identity contract requires a positive finite {name}")
    antenna = identity.get("antenna")
    eyes = identity.get("eyes")
    body = identity.get("body")
    sparkle = identity.get("sparkle")
    if not all(isinstance(item, dict) for item in (antenna, eyes, body, sparkle)):
        fail("identity contract requires antenna, eyes, body, and sparkle objects")
    for name in ("tipColor", "stemColor"):
        normalized_color(antenna.get(name, ""))
    for name in ("frameColor", "insetColor"):
        normalized_color(body.get(name, ""))
    normalized_color(sparkle.get("color", ""))
    nested_ratios = (
        (antenna, ("stemWidthRatio", "totalHeightRatio", "tipDiameterRatio")),
        (eyes, ("widthToHeadRatio", "heightToHeadRatio", "horizontalSpacingRatio", "verticalCenterRatio")),
        (body, ("frameWidthToHeadRatio", "insetWidthToFrameRatio", "insetHeightToFrameRatio")),
        (sparkle, ("screenSizeRatio",)),
    )
    for owner, names in nested_ratios:
        for name in names:
            value = owner.get(name)
            if (
                not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                fail(f"identity contract requires a positive finite {name}")
    if antenna.get("continuousSilhouette") is not True:
        fail("identity antenna must require a continuous silhouette")
    if body.get("orangeFrame") is not True or body.get("insetPanel") is not True:
        fail("identity body must require an orange frame and inset panel")
    if sparkle.get("anchor") != "head.left":
        fail("identity sparkle anchor must be head.left")
    offset = sparkle.get("screenOffset")
    if (
        not isinstance(offset, list)
        or len(offset) != 2
        or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in offset)
    ):
        fail("identity sparkle screenOffset must contain two finite numbers")
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
    if not isinstance(measurements, dict) or set(measurements) != set(METRIC_NAMES):
        fail("identity contract must define every identity measurement rule")
    if any(not isinstance(rule, str) or not rule for rule in measurements.values()):
        fail("identity contract measurement rules must be non-empty strings")


def expected_metrics(identity: dict[str, object]) -> dict[str, float]:
    antenna = identity["antenna"]
    eyes = identity["eyes"]
    body = identity["body"]
    sparkle = identity["sparkle"]
    return {
        "headAspectRatio": float(identity["headAspectRatio"]),
        "headToBodyRatio": float(identity["headToBodyRatio"]),
        "mouthVerticalRatio": float(identity["mouthVerticalRatio"]),
        "antennaStemWidthRatio": float(antenna["stemWidthRatio"]),
        "antennaTotalHeightRatio": float(antenna["totalHeightRatio"]),
        "antennaTipDiameterRatio": float(antenna["tipDiameterRatio"]),
        "eyesWidthToHeadRatio": float(eyes["widthToHeadRatio"]),
        "eyesHeightToHeadRatio": float(eyes["heightToHeadRatio"]),
        "eyesHorizontalSpacingRatio": float(eyes["horizontalSpacingRatio"]),
        "eyesVerticalCenterRatio": float(eyes["verticalCenterRatio"]),
        "bodyFrameWidthToHeadRatio": float(body["frameWidthToHeadRatio"]),
        "bodyInsetWidthToFrameRatio": float(body["insetWidthToFrameRatio"]),
        "bodyInsetHeightToFrameRatio": float(body["insetHeightToFrameRatio"]),
        "sparkleScreenSizeRatio": float(sparkle["screenSizeRatio"]),
    }


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
    antenna_identity = identity["antenna"]
    eye_identity = identity["eyes"]
    body_identity = identity["body"]
    sparkle_identity = identity["sparkle"]

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
    sparkle_paths = svg_elements(
        layer_source(pack, pack_path, "spark"), "path"
    )

    if len(head_rects) < 2 or len(body_rects) < 2 or len(eyes) != 2:
        fail("2D identity geometry is incomplete")
    head = head_rects[0]
    body_frame = body_rects[0]
    body_inset = body_rects[1]
    head_y = number(head, "y")
    head_width = number(head, "width")
    head_height = number(head, "height")
    eye_centers = [number(eye, "cx") for eye in eyes]
    eye_y = sum(number(eye, "cy") for eye in eyes) / len(eyes)
    eye_width = sum(number(eye, "rx") * 2.0 for eye in eyes) / len(eyes)
    eye_height = sum(number(eye, "ry") * 2.0 for eye in eyes) / len(eyes)

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
    tip_bottom = number(tip, "cy") + number(tip, "r")
    stem_numbers = [
        float(value)
        for value in re.findall(r"-?\d+(?:\.\d+)?", antenna_lines[0].attrib["d"])
    ]
    if len(stem_numbers) < 4:
        fail("2D antenna stem does not expose both endpoints")
    stem_y_values = [stem_numbers[1], stem_numbers[3]]
    stem_top = min(stem_y_values)
    stem_bottom = max(stem_y_values)
    stem_width = number(antenna_lines[0], "stroke-width")
    if len(side_ears) != 2:
        fail("2D identity requires two orange side ears")
    if len(sparkle_paths) != 1:
        fail("2D identity requires exactly one screen-space sparkle path")
    sparkle = sparkle_paths[0]
    sparkle_numbers = [
        float(value)
        for value in re.findall(r"-?\d+(?:\.\d+)?", sparkle.attrib["d"])
    ]
    sparkle_x = sparkle_numbers[0::2]
    sparkle_y = sparkle_numbers[1::2]
    sparkle_width = max(sparkle_x) - min(sparkle_x)
    sparkle_height = max(sparkle_y) - min(sparkle_y)
    sparkle_center_x = (max(sparkle_x) + min(sparkle_x)) * 0.5
    sparkle_center_y = (max(sparkle_y) + min(sparkle_y)) * 0.5

    color_checks = {
        "head primary": (head_rects[1].attrib.get("fill"), primary),
        "body inset": (body_inset.attrib.get("fill"), body_identity["insetColor"]),
        "head secondary": (head.attrib.get("fill"), secondary),
        "body frame": (body_frame.attrib.get("fill"), body_identity["frameColor"]),
        "antenna tip": (tip.attrib.get("fill"), antenna_identity["tipColor"]),
        "antenna stem": (antenna_lines[0].attrib.get("stroke"), antenna_identity["stemColor"]),
        "sparkle": (sparkle.attrib.get("fill"), sparkle_identity["color"]),
    }
    for label, (actual, expected) in color_checks.items():
        if actual is None or normalized_color(actual) != expected:
            fail(f"2D {label} color does not match the identity contract")
    if any(
        normalized_color(ear.attrib.get("fill", "#000000")) != secondary
        for ear in side_ears
    ):
        fail("2D side-ear color does not match the identity contract")

    if antenna_identity["continuousSilhouette"] and (
        stem_bottom < head_y or stem_top > tip_bottom
    ):
        fail("2D antenna silhouette is not continuous from head through tip")
    spark_layer = next(layer for layer in pack["layers"] if layer["id"] == "spark")
    if float(spark_layer.get("depth", 0.0)) != 0.0 or spark_layer.get("screen_space") is not True:
        fail("2D sparkle must be an explicit screen-space layer at depth zero")
    expected_sparkle_x = (
        number(head, "x")
        + float(sparkle_identity["screenOffset"][0]) * head_width
    )
    expected_sparkle_y = (
        head_y
        + head_height * 0.5
        + float(sparkle_identity["screenOffset"][1]) * head_height
    )
    position_tolerance = float(contract["validation"]["ratioTolerance"])
    if not math.isclose(
        sparkle_center_x, expected_sparkle_x, abs_tol=head_width * position_tolerance
    ) or not math.isclose(
        sparkle_center_y, expected_sparkle_y, abs_tol=head_height * position_tolerance
    ):
        fail("2D sparkle does not match its head.left screen-space anchor")

    metrics = {
        "headAspectRatio": head_width / head_height,
        "headToBodyRatio": head_height / number(body_inset, "height"),
        "mouthVerticalRatio": (mouth_y - head_y) / head_height,
        "antennaStemWidthRatio": stem_width / head_width,
        "antennaTotalHeightRatio": (head_y - tip_top) / head_height,
        "antennaTipDiameterRatio": number(tip, "r") * 2.0 / head_width,
        "eyesWidthToHeadRatio": eye_width / head_width,
        "eyesHeightToHeadRatio": eye_height / head_height,
        "eyesHorizontalSpacingRatio": abs(eye_centers[1] - eye_centers[0]) / head_width,
        "eyesVerticalCenterRatio": (eye_y - head_y) / head_height,
        "bodyFrameWidthToHeadRatio": number(body_frame, "width") / head_width,
        "bodyInsetWidthToFrameRatio": number(body_inset, "width") / number(body_frame, "width"),
        "bodyInsetHeightToFrameRatio": number(body_inset, "height") / number(body_frame, "height"),
        "sparkleScreenSizeRatio": max(sparkle_width, sparkle_height) / min(float(pack["canvas"]["width"]), float(pack["canvas"]["height"])),
    }
    tolerance = float(contract["validation"]["ratioTolerance"])
    expected = expected_metrics(identity)
    for name, actual in metrics.items():
        close_ratio(name, actual, expected[name], tolerance)
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


def mesh_material_name(document: dict[str, object], mesh_name: str) -> str:
    mesh = next(
        (item for item in document["meshes"] if item["name"] == mesh_name), None
    )
    if mesh is None:
        fail(f"GLB is missing identity mesh: {mesh_name}")
    material_index = mesh["primitives"][0]["material"]
    return document["materials"][material_index]["name"]


def bounds(rows: list[tuple[float, ...]], component: int) -> tuple[float, float]:
    values = [row[component] for row in rows]
    return min(values), max(values)


def validate_glb(
    contract: dict[str, object], contract_sha256: str, glb_path: Path
) -> dict[str, float]:
    document, binary = read_glb(glb_path)
    identity = contract["identity"]
    antenna_identity = identity["antenna"]
    eye_identity = identity["eyes"]
    body_identity = identity["body"]
    sparkle_identity = identity["sparkle"]
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
        "antennaTip": antenna_identity["tipColor"],
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
        ("antenna-tip", antenna_identity["tipColor"]),
    ):
        if material_hex(document, material_name) != normalized_color(color):
            fail(f"GLB material {material_name} does not match the contract")
    expected_mesh_materials = {
        "BodyFrame": "robot-orange-trim",
        "BodyInset": "robot-gold",
        "AntennaStem": "face-ink",
        "AntennaTip": "antenna-tip",
    }
    for mesh_name, material_name in expected_mesh_materials.items():
        if mesh_material_name(document, mesh_name) != material_name:
            fail(f"GLB {mesh_name} does not use {material_name}")

    nodes = {node["name"]: node for node in document["nodes"]}
    features = {
        node.get("extras", {}).get("identityFeature")
        for node in document["nodes"]
        if node.get("extras", {}).get("identityFeature")
    }
    screen_effects = extras.get("screenSpaceEffects", {})
    sparkle_effect = screen_effects.get("sparkle")
    if not isinstance(sparkle_effect, dict):
        fail("GLB is missing the screen-space sparkle declaration")
    if sparkle_effect.get("identityFeature"):
        features.add(sparkle_effect["identityFeature"])
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
    if "Sparkle" in nodes or any(
        mesh.get("name") == "Sparkle" for mesh in document["meshes"]
    ):
        fail("GLB sparkle must be a screen-space effect, not model geometry")
    expected_effect = {
        **sparkle_identity,
        "identityFeature": "screen_space_sparkle",
    }
    if sparkle_effect != expected_effect:
        fail("GLB screen-space sparkle rule does not match the contract")

    head_rows = position_rows(document, binary, "HeadShell")
    body_frame_rows = position_rows(document, binary, "BodyFrame")
    body_inset_rows = position_rows(document, binary, "BodyInset")
    antenna_stem_rows = position_rows(document, binary, "AntennaStem")
    eye_rows = position_rows(document, binary, "EyeWhites")
    pupil_rows = position_rows(document, binary, "FaceRig")
    mouth_rows = position_rows(document, binary, "MouthCurve")
    head_x = bounds(head_rows, 0)
    head_y = bounds(head_rows, 1)
    body_frame_x = bounds(body_frame_rows, 0)
    body_frame_y = bounds(body_frame_rows, 1)
    body_inset_x = bounds(body_inset_rows, 0)
    body_inset_y = bounds(body_inset_rows, 1)
    head_width = head_x[1] - head_x[0]
    head_height = head_y[1] - head_y[0]
    negative_eye_x = bounds([row for row in eye_rows if row[0] < 0], 0)
    positive_eye_x = bounds([row for row in eye_rows if row[0] > 0], 0)
    left_eye_center = sum(negative_eye_x) * 0.5
    right_eye_center = sum(positive_eye_x) * 0.5
    eye_y = bounds(eye_rows, 1)
    eye_width = negative_eye_x[1] - negative_eye_x[0]
    eye_height = eye_y[1] - eye_y[0]
    eye_center_y = sum(eye_y) * 0.5
    pupil_x = bounds(pupil_rows, 0)
    pupil_y = bounds(pupil_rows, 1)
    pupil_combined_width = pupil_x[1] - pupil_x[0]
    expected_combined_width = (
        head_width * float(eye_identity["horizontalSpacingRatio"])
        + (pupil_y[1] - pupil_y[0])
    )
    if not math.isclose(pupil_combined_width, expected_combined_width, abs_tol=0.02):
        fail("GLB pupils are not the contract round-eye style")
    if len(mouth_rows) < 2:
        fail("GLB mouth mesh does not expose its curve anchor")
    mouth_y = (mouth_rows[0][1] + mouth_rows[1][1]) * 0.5

    tip = nodes["AntennaTip"]
    tip_top = float(tip["translation"][1]) + float(tip["scale"][1])
    tip_bottom = float(tip["translation"][1]) - float(tip["scale"][1])
    stem_y = bounds(antenna_stem_rows, 1)
    stem_x = bounds(antenna_stem_rows, 0)
    stem_translation_y = float(nodes["Antenna"]["translation"][1])
    stem_top = stem_y[1] + stem_translation_y
    stem_bottom = stem_y[0] + stem_translation_y
    if antenna_identity["continuousSilhouette"] and (
        stem_bottom > head_y[1] or stem_top < tip_bottom
    ):
        fail("GLB antenna silhouette is not continuous from head through tip")
    metrics = {
        "headAspectRatio": head_width / head_height,
        "headToBodyRatio": head_height / (body_inset_y[1] - body_inset_y[0]),
        "mouthVerticalRatio": (head_y[1] - mouth_y) / head_height,
        "antennaStemWidthRatio": (stem_x[1] - stem_x[0]) / head_width,
        "antennaTotalHeightRatio": (tip_top - head_y[1]) / head_height,
        "antennaTipDiameterRatio": float(tip["scale"][0]) * 2.0 / head_width,
        "eyesWidthToHeadRatio": eye_width / head_width,
        "eyesHeightToHeadRatio": eye_height / head_height,
        "eyesHorizontalSpacingRatio": (right_eye_center - left_eye_center) / head_width,
        "eyesVerticalCenterRatio": (head_y[1] - eye_center_y) / head_height,
        "bodyFrameWidthToHeadRatio": (body_frame_x[1] - body_frame_x[0]) / head_width,
        "bodyInsetWidthToFrameRatio": (body_inset_x[1] - body_inset_x[0]) / (body_frame_x[1] - body_frame_x[0]),
        "bodyInsetHeightToFrameRatio": (body_inset_y[1] - body_inset_y[0]) / (body_frame_y[1] - body_frame_y[0]),
        "sparkleScreenSizeRatio": float(sparkle_effect["screenSizeRatio"]),
    }
    tolerance = float(contract["validation"]["ratioTolerance"])
    expected = expected_metrics(identity)
    for name, actual in metrics.items():
        close_ratio(name, actual, expected[name], tolerance)
        close_ratio(
            f"declared {name}",
            float(declaration["metrics"][name]),
            expected[name],
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
