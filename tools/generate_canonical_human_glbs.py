#!/usr/bin/env python3
"""Generate deterministic semantic GLB counterparts for all canonical humans."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from generate_canonical_human_masters import EXPRESSIONS, MASTERS, POSES
from generate_robot_glb import (
    GlbBuffer,
    add_animation,
    combine_geometry,
    curve_geometry,
    ellipse_geometry,
    encode_glb,
    quadratic_curve,
    rounded_rect_prism,
    triangle_geometry,
    unlit_material,
    uv_sphere,
    z_rotation,
)


ROOT = Path(__file__).resolve().parent.parent


def ring_geometry(radius: float, width: float, segments: int = 32):
    points = [
        [radius * math.cos(2 * math.pi * step / segments), radius * math.sin(2 * math.pi * step / segments)]
        for step in range(segments + 1)
    ]
    return curve_geometry(points, width)


def build_glb(master_id: str, identity: dict[str, Any], source_sha: str) -> bytes:
    d = MASTERS[master_id]
    mode = d["mode"]
    buffer = GlbBuffer()

    def accessors(geometry):
        positions, normals, indices = geometry
        return (
            buffer.floats(positions, "VEC3", target=34962, bounds=True),
            buffer.floats(normals, "VEC3", target=34962),
            buffer.indices(indices),
        )

    def primitive(geometry, material: int):
        position, normal, index = accessors(geometry)
        return {"attributes": {"POSITION": position, "NORMAL": normal}, "indices": index, "material": material}

    palette = identity["palette"]
    material_specs = [
        ("skin", palette["skin"], 1.0), ("skin-highlight", palette["skin_light"], 1.0),
        ("hair", palette["hair"], 1.0), ("primary", palette["primary"], 1.0),
        ("secondary", palette["secondary"], 1.0), ("accent", palette["accent"], 1.0),
        ("outline", palette["outline"], 1.0), ("eye-white", "#FFF8EE", 1.0),
        ("pants", d["pants"], 1.0), ("shoe", d["shoe"], 1.0),
        ("device", "#66717E", 1.0), ("shadow", palette["outline"], .22),
    ]
    materials = [unlit_material(name, color, alpha) for name, color, alpha in material_specs]
    material = {name: index for index, (name, _, _) in enumerate(material_specs)}

    head_dimensions = {
        "child": (1.34, 1.28), "prosthesis": (1.18, 1.16), "wheelchair": (1.22, 1.20),
        "hearing-aid": (1.20, 1.24), "rollator": (1.22, 1.22),
    }
    torso_dimensions = {
        "child": (1.0, .92), "prosthesis": (1.48, 1.22), "wheelchair": (1.36, 1.10),
        "hearing-aid": (1.24, 1.16), "rollator": (1.42, 1.22),
    }
    head_width, head_height = head_dimensions[mode]
    torso_width, torso_height = torso_dimensions[mode]
    geometries = {
        "sphere": uv_sphere(10, 14),
        "head": rounded_rect_prism(head_width, head_height, .42, .34),
        "torso": rounded_rect_prism(torso_width, torso_height, .34, .24),
        "limb": rounded_rect_prism(.23, .82, .22, .11),
        "short-limb": rounded_rect_prism(.24, .56, .22, .11),
        "foot": rounded_rect_prism(.48, .2, .38, .09),
        "eye-whites": combine_geometry([ellipse_geometry(-.27, .08, .13, .18), ellipse_geometry(.27, .08, .13, .18)]),
        "pupils": combine_geometry([ellipse_geometry(-.27, .07, .05, .07), ellipse_geometry(.27, .07, .05, .07)]),
        "mouth": curve_geometry(quadratic_curve((-.28, -.28), (0, -.52), (.28, -.28)), .055),
        "brows": combine_geometry([
            curve_geometry(quadratic_curve((-.42, .31), (-.27, .39), (-.12, .31)), .045),
            curve_geometry(quadratic_curve((.12, .31), (.27, .39), (.42, .31)), .045),
        ]),
        "nose": triangle_geometry(),
        "beard": curve_geometry(quadratic_curve((-.4, -.24), (0, -.73), (.4, -.24)), .08),
        "glasses": combine_geometry([ring_geometry(.18, .035, 20), ring_geometry(.18, .035, 20)]),
        "wheel-large": ring_geometry(.72, .085),
        "wheel-small": ring_geometry(.18, .075),
        "frame-horizontal": rounded_rect_prism(1.25, .10, .14, .04),
        "frame-vertical": rounded_rect_prism(.10, 1.05, .14, .04),
        "hearing-case": rounded_rect_prism(.14, .25, .12, .06),
        "clothing-horizontal": rounded_rect_prism(1.0, .075, .08, .03),
        "clothing-vertical": rounded_rect_prism(.075, .9, .08, .03),
        "skirt": rounded_rect_prism(1.22, .38, .28, .12),
        "badge": uv_sphere(8, 10),
        "hand": uv_sphere(8, 10),
    }
    mesh_material = {
        "sphere": "hair", "head": "skin", "torso": "primary", "limb": "primary",
        "short-limb": "skin", "foot": "shoe", "eye-whites": "eye-white", "pupils": "outline",
        "mouth": "outline", "wheel-large": "outline", "wheel-small": "outline",
        "brows": "outline", "nose": "accent", "beard": "hair", "glasses": "outline",
        "frame-horizontal": "device", "frame-vertical": "device", "hearing-case": "accent",
        "clothing-horizontal": "secondary", "clothing-vertical": "accent", "skirt": "pants", "badge": "secondary",
        "hand": "skin-highlight",
    }
    meshes = [
        {"name": name, "primitives": [primitive(geometry, material[mesh_material[name]])]}
        for name, geometry in geometries.items()
    ]
    mesh = {name: index for index, name in enumerate(geometries)}
    nodes: list[dict[str, Any]] = []

    def node(name: str, **properties: Any) -> int:
        nodes.append({"name": name, **properties})
        return len(nodes) - 1

    height_scale = {"H01": .78, "H04": 1.08, "H07": .92, "H12": .96, "H13": .94}[master_id]
    root = node("CharacterRoot", scale=[height_scale, height_scale, height_scale], extras={"semantic": "root"})
    shadow = node("GroundShadow", mesh=mesh["sphere"], translation=[0, -1.72, -.28], scale=[1.05, .08, .34])
    torso_y = -.43 if mode != "wheelchair" else -.25
    torso = node("Torso", mesh=mesh["torso"], translation=[0, torso_y, 0], extras={"semantic": "torso"})
    head = node("Head", mesh=mesh["head"], translation=[0, .72, 0], extras={"semantic": "head"})
    face = node("Face", translation=[0, .72, .235], extras={"semantic": "face"})
    eyes = node("EyeGroup", mesh=mesh["eye-whites"])
    pupils = node("Pupils", mesh=mesh["pupils"], translation=[0, 0, .012])
    mouth = node("Mouth", mesh=mesh["mouth"], translation=[0, 0, .018])
    brows = node("Brows", mesh=mesh["brows"], translation=[0, 0, .016])
    nose = node("Nose", mesh=mesh["nose"], translation=[0, -.02, .02], scale=[.7, .7, .7])
    face_children = [eyes, pupils, mouth, brows, nose]
    if mode == "prosthesis":
        face_children.append(node("Beard", mesh=mesh["beard"], translation=[0, -.02, .025]))
    if mode == "rollator":
        left_glass = node("GlassLeft", mesh=mesh["glasses"], translation=[-.27, .08, .03], scale=[.55, .62, 1])
        right_glass = node("GlassRight", mesh=mesh["glasses"], translation=[.27, .08, .03], scale=[.55, .62, 1])
        bridge = node("GlassesBridge", mesh=mesh["frame-horizontal"], translation=[0, .08, .03], scale=[.18, .5, .5])
        face_children.extend([left_glass, right_glass, bridge])
    nodes[face]["children"] = face_children
    nodes[head]["children"] = [face]
    hair_root = node("Hair", translation=[0, 1.43, -.48], extras={"semantic": "hair"})
    hair_nodes: list[int] = []
    hair_layout = [(-.34, -.02, .31, .27), (0, .08, .36, .3), (.34, -.02, .31, .27)]
    if mode == "child":
        hair_layout += [(-.68, -.02, .38, .4), (.68, -.02, .38, .4)]
    elif mode == "hearing-aid":
        hair_layout += [(-.52, -.42, .24, .56), (.52, -.42, .24, .56)]
    elif mode == "rollator":
        hair_layout += [(-.56, -.23, .27, .3), (.56, -.23, .27, .3), (-.18, .3, .26, .25), (.18, .3, .26, .25)]
    for index, (px, py, scale_x, scale_y) in enumerate(hair_layout):
        hair_nodes.append(node(f"HairPart{index}", mesh=mesh["sphere"], translation=[px, py, 0], scale=[scale_x, scale_y, scale_x*.65]))
    nodes[hair_root]["children"] = hair_nodes

    left_arm_pivot = node("ArmLeftPivot", translation=[.67, -.03, 0], extras={"semantic": "arm.left"})
    right_arm_pivot = node("ArmRightPivot", translation=[-.67, -.03, 0], extras={"semantic": "arm.right"})
    left_arm = node("ArmLeft", mesh=mesh["limb"], translation=[0, -.4, .14])
    right_arm = node("ArmRight", mesh=mesh["limb"], translation=[0, -.4, .14])
    left_hand = node("HandLeft", mesh=mesh["hand"], translation=[0, -.83, .16], scale=[.13, .16, .12], extras={"semantic": "hand.left"})
    right_hand = node("HandRight", mesh=mesh["hand"], translation=[0, -.83, .16], scale=[.13, .16, .12], extras={"semantic": "hand.right"})
    nodes[left_arm_pivot]["children"] = [left_arm, left_hand]
    nodes[right_arm_pivot]["children"] = [right_arm, right_hand]
    children = [torso, head, hair_root, left_arm_pivot, right_arm_pivot]

    clothing_nodes: list[int] = []
    if mode == "child":
        clothing_nodes += [
            node("Skirt", mesh=mesh["skirt"], translation=[0, -.93, .02]),
            node("HeartBadge", mesh=mesh["badge"], translation=[0, -.35, .22], scale=[.13, .16, .05], extras={"semantic": "clothing.heart"}),
        ]
    elif mode == "prosthesis":
        clothing_nodes += [
            node("JacketCenter", mesh=mesh["clothing-vertical"], translation=[0, torso_y, .2], scale=[1, 1.06, 1]),
            node("JacketYoke", mesh=mesh["clothing-horizontal"], translation=[0, .02, .2], scale=[1.22, 1, 1]),
        ]
    elif mode == "wheelchair":
        clothing_nodes += [
            node("OvershirtCenter", mesh=mesh["clothing-vertical"], translation=[0, torso_y, .2], scale=[1, .9, 1]),
            node("OvershirtYoke", mesh=mesh["clothing-horizontal"], translation=[0, .02, .2], scale=[1.08, 1, 1]),
        ]
    elif mode == "hearing-aid":
        clothing_nodes += [
            node("CardiganLeft", mesh=mesh["clothing-vertical"], translation=[-.28, torso_y, .2], scale=[.8, 1.08, 1]),
            node("CardiganRight", mesh=mesh["clothing-vertical"], translation=[.28, torso_y, .2], scale=[.8, 1.08, 1]),
            node("CardiganCollar", mesh=mesh["clothing-horizontal"], translation=[0, .02, .2], scale=[.9, 1, 1]),
        ]
    elif mode == "rollator":
        clothing_nodes += [
            node("ScarfUpper", mesh=mesh["clothing-horizontal"], translation=[0, -.05, .2], scale=[1.2, 1.4, 1], extras={"semantic": "clothing.patterned-scarf"}),
            node("ScarfLower", mesh=mesh["clothing-horizontal"], translation=[0, -.24, .2], scale=[.92, .8, 1]),
        ]
    children += clothing_nodes

    if mode == "wheelchair":
        leg_left = node("LegLeft", mesh=mesh["short-limb"], translation=[.25, -.96, .03], rotation=z_rotation(-18), extras={"semantic": "leg.left"})
        leg_right = node("LegRight", mesh=mesh["short-limb"], translation=[-.25, -.96, .03], rotation=z_rotation(18), extras={"semantic": "leg.right"})
        foot_left = node("FootLeft", mesh=mesh["foot"], translation=[.32, -1.35, .08], extras={"semantic": "foot.left"})
        foot_right = node("FootRight", mesh=mesh["foot"], translation=[-.32, -1.35, .08], extras={"semantic": "foot.right"})
        wheel_left = node("WheelLeft", mesh=mesh["wheel-large"], translation=[.78, -1.18, -.05], extras={"semantic": "wheel.left"})
        wheel_right = node("WheelRight", mesh=mesh["wheel-large"], translation=[-.78, -1.18, -.05], extras={"semantic": "wheel.right"})
        frame = node("WheelchairFrame", mesh=mesh["frame-horizontal"], translation=[0, -.88, -.02], extras={"semantic": "wheelchair.frame"})
        footrest = node("WheelchairFootrest", mesh=mesh["frame-horizontal"], translation=[0, -1.43, .05], scale=[.65, 1, 1], extras={"semantic": "wheelchair.footrest"})
        children += [leg_left, leg_right, foot_left, foot_right, wheel_left, wheel_right, frame, footrest]
    else:
        left_leg = node("LegLeft", mesh=mesh["limb"], translation=[.28, -1.12, 0], extras={"semantic": "leg.left"})
        left_foot = node("FootLeft", mesh=mesh["foot"], translation=[.34, -1.58, .05], extras={"semantic": "foot.left"})
        children += [left_leg, left_foot]
        if mode == "prosthesis":
            socket = node("ProstheticSocketRight", mesh=mesh["short-limb"], translation=[-.28, -.96, 0], scale=[1.05, .72, 1], extras={"semantic": "prosthesis.socket.right"})
            pylon = node("ProstheticPylonRight", mesh=mesh["frame-vertical"], translation=[-.28, -1.38, 0], scale=[.72, .5, .72], extras={"semantic": "prosthesis.pylon.right"})
            foot = node("ProstheticFootRight", mesh=mesh["foot"], translation=[-.36, -1.66, .05], extras={"semantic": "prosthesis.foot.right"})
            children += [socket, pylon, foot]
        else:
            children.append(node("LegRight", mesh=mesh["limb"], translation=[-.28, -1.12, 0], extras={"semantic": "leg.right"}))
            children.append(node("FootRight", mesh=mesh["foot"], translation=[-.34, -1.58, .05], extras={"semantic": "foot.right"}))
    if mode == "hearing-aid":
        case = node("HearingAidCaseRight", mesh=mesh["hearing-case"], translation=[-.64, .78, .12], extras={"semantic": "hearing-aid.case.right"})
        tube = node("HearingAidTubeRight", mesh=mesh["frame-vertical"], translation=[-.59, .71, .18], scale=[.35, .22, .35], rotation=z_rotation(-28), extras={"semantic": "hearing-aid.tube.right"})
        earpiece = node("HearingAidEarpieceRight", mesh=mesh["sphere"], translation=[-.55, .67, .2], scale=[.07, .07, .05], extras={"semantic": "hearing-aid.earpiece.right"})
        nodes[head].setdefault("children", []).extend([case, tube, earpiece])
    if mode == "rollator":
        frame_root = node("RollatorFrame", extras={"semantic": "rollator.frame"})
        frame_children = [
            node("RollatorCrossbar", mesh=mesh["frame-horizontal"], translation=[0, -1.0, .26]),
            node("RollatorPostLeft", mesh=mesh["frame-vertical"], translation=[.72, -1.08, .26]),
            node("RollatorPostRight", mesh=mesh["frame-vertical"], translation=[-.72, -1.08, .26]),
            node("RollatorHandleLeft", mesh=mesh["frame-horizontal"], translation=[.68, -.57, .26], scale=[.3, 1, 1], extras={"semantic": "rollator.handle.left"}),
            node("RollatorHandleRight", mesh=mesh["frame-horizontal"], translation=[-.68, -.57, .26], scale=[.3, 1, 1], extras={"semantic": "rollator.handle.right"}),
        ]
        for name, px, py, scale in (("FrontLeft", .76, -1.62, 1.0), ("FrontRight", -.76, -1.62, 1.0), ("RearLeft", .58, -1.5, .72), ("RearRight", -.58, -1.5, .72)):
            frame_children.append(node(f"RollatorWheel{name}", mesh=mesh["wheel-small"], translation=[px, py, .25], scale=[scale, scale, scale], extras={"semantic": f"rollator.wheel.{name.lower()}"}))
        nodes[frame_root]["children"] = frame_children
        children.append(frame_root)
    nodes[root]["children"] = children

    clips = [*POSES, *[f"expression-{name}" for name in EXPRESSIONS]]
    document: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "MascotRender deterministic canonical human GLB generator", "extras": {
            "characterIdentity": {"characterId": master_id, "familyId": identity["family_id"], "sourceIdentitySha256": source_sha, "direction": identity["identity_direction"]},
            "semanticRig": "humanoid-production-v2", "deviceProfile": identity["device_profile"],
            "palette": palette, "clips": clips, "license": "MIT",
            "metrics": {"heightScale": height_scale, "headWidth": head_width, "headHeight": head_height, "torsoWidth": torso_width, "torsoHeight": torso_height},
        }},
        "extensionsUsed": ["KHR_materials_unlit"], "scene": 0,
        "scenes": [{"name": f"{master_id}CanonicalHuman", "nodes": [root, shadow]}],
        "nodes": nodes, "materials": materials, "meshes": meshes,
    }
    pose_angles = {
        "rest": (0, 0), "greeting": (0, -118), "farewell": (118, 0),
        "agreement": (-42, 42), "disagreement": (58, -58), "gratitude": (72, -72),
        "concern": (-68, 68), "surprise": (82, -82), "celebration": (128, -128),
    }
    for pose, (left_angle, right_angle) in pose_angles.items():
        add_animation(document, buffer, pose, [
            (left_arm_pivot, "rotation", [0, .5, 1], [z_rotation(0), z_rotation(left_angle), z_rotation(0)], "VEC4"),
            (right_arm_pivot, "rotation", [0, .5, 1], [z_rotation(0), z_rotation(right_angle), z_rotation(0)], "VEC4"),
        ])
    expression_scales = {
        "happy": (1, 1, 1), "laughing": (.14, 1.25, 1.4), "surprised": (1.3, .35, 1.8),
        "thinking": (.8, .7, .35), "confident": (.55, 1.1, .7), "sorry": (.8, 1, 1), "excited": (1.15, 1.3, 1.2),
    }
    expression_tilts = {"happy": 2, "laughing": -4, "surprised": 0, "thinking": -6, "confident": 4, "sorry": -3, "excited": 7}
    for expression, (eye_y, mouth_x, mouth_y) in expression_scales.items():
        tracks = [
            (eyes, "scale", [0, .5, 1], [[1, 1, 1], [1, eye_y, 1], [1, 1, 1]], "VEC3"),
            (pupils, "scale", [0, .5, 1], [[1, 1, 1], [1, eye_y, 1], [1, 1, 1]], "VEC3"),
            (mouth, "scale", [0, .5, 1], [[1, 1, 1], [mouth_x, mouth_y, 1], [1, 1, 1]], "VEC3"),
            (head, "rotation", [0, .5, 1], [z_rotation(0), z_rotation(expression_tilts[expression]), z_rotation(0)], "VEC4"),
            (hair_root, "rotation", [0, .5, 1], [z_rotation(0), z_rotation(expression_tilts[expression]), z_rotation(0)], "VEC4"),
        ]
        if expression == "sorry":
            tracks.append((mouth, "rotation", [0, .5, 1], [z_rotation(0), z_rotation(180), z_rotation(0)], "VEC4"))
        add_animation(document, buffer, f"expression-{expression}", tracks)
    while len(buffer.data) % 4:
        buffer.data.append(0)
    document["buffers"] = [{"byteLength": len(buffer.data)}]
    document["bufferViews"] = buffer.views
    document["accessors"] = buffer.accessors
    return encode_glb(document, bytes(buffer.data))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "art/human-pack-v1/masters")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="build every GLB twice in memory and verify deterministic bytes without writing legacy fixtures",
    )
    args = parser.parse_args()
    if args.check and args.self_test:
        parser.error("--check and --self-test are mutually exclusive")
    records = []
    for master_id in sorted(MASTERS):
        root = args.input / master_id
        identity_path = root / "identity.json"
        identity_bytes = identity_path.read_bytes()
        identity = json.loads(identity_bytes)
        payload = build_glb(master_id, identity, hashlib.sha256(identity_bytes).hexdigest())
        output = root / f"{master_id}.glb"
        if args.self_test:
            repeated = build_glb(master_id, identity, hashlib.sha256(identity_bytes).hexdigest())
            if repeated != payload:
                raise SystemExit(f"in-memory GLB generation is nondeterministic for {master_id}")
        elif args.check:
            if not output.is_file() or output.read_bytes() != payload:
                raise SystemExit(f"generated GLB differs from {output}")
        else:
            output.write_bytes(payload)
        records.append({"master_id": master_id, "path": output.name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "clip_count": len(POSES)+len(EXPRESSIONS), "reduced_motion": "freeze-semantic-clip-at-0.5-seconds-with-playback-disabled"})
    manifest = args.input / "glb-manifest.json"
    document = {"schema_version": 1, "generator": "generate_canonical_human_glbs.py", "license": "MIT", "master_count": len(records), "records": records}
    encoded = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.self_test:
        print(f"verified {len(records)} deterministic canonical human GLBs in memory")
    elif args.check:
        if not manifest.is_file() or manifest.read_text(encoding="utf-8") != encoded:
            raise SystemExit(f"generated manifest differs from {manifest}")
        print(f"verified {len(records)} deterministic canonical human GLBs")
    else:
        manifest.write_text(encoded, encoding="utf-8", newline="\n")
        print(f"generated {len(records)} canonical human GLBs with {len(POSES)+len(EXPRESSIONS)} clips each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
