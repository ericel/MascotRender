#!/usr/bin/env python3
"""Author the canonical human production GLBs in Blender.

Run normally to spawn Blender for every master, or run inside Blender with
``-- --master H01``. The authored .blend file is retained beside the exported
GLB so production geometry is reviewable rather than hidden in a generator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MASTER_IDS = ("H01", "H04", "H07", "H12", "H13")
POSES = ("rest", "greeting", "farewell", "agreement", "disagreement", "gratitude", "concern", "surprise", "celebration")
EXPRESSIONS = ("happy", "laughing", "surprised", "thinking", "confident", "sorry", "excited")
TURNAROUND_CLIPS = ("turnaround-three-quarter", "turnaround-side", "turnaround-back")


def patch_unlit_glb(path: Path, master_id: str) -> None:
    """Mark Blender's flat-color materials as KHR_materials_unlit."""
    payload = path.read_bytes()
    json_length, json_type = struct.unpack_from("<I4s", payload, 12)
    if payload[:4] != b"glTF" or json_type != b"JSON":
        raise ValueError(f"unexpected GLB container: {path}")
    document = json.loads(payload[20:20 + json_length].decode("utf-8"))
    document.setdefault("asset", {}).setdefault("extras", {})["characterIdentity"] = {
        "characterId": master_id,
        "familyId": "human-character-library-canonical-family",
        "assetClass": "authored-production-review-candidate",
        "productionUse": "forbidden-until-owner-design-review",
    }
    used = document.setdefault("extensionsUsed", [])
    if "KHR_materials_unlit" not in used:
        used.append("KHR_materials_unlit")
    for spec in document.get("materials", []):
        spec.setdefault("extensions", {})["KHR_materials_unlit"] = {}
    encoded = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    json_chunk = struct.pack("<I4s", len(encoded), b"JSON") + encoded
    binary_offset = 20 + json_length
    binary_chunk = payload[binary_offset:]
    rebuilt = b"glTF" + struct.pack("<II", 2, 12 + len(json_chunk) + len(binary_chunk)) + json_chunk + binary_chunk
    path.write_bytes(rebuilt)


def host_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "art/human-pack-v1/masters")
    parser.add_argument("--master", choices=MASTER_IDS)
    args = parser.parse_args()
    blender = shutil.which("blender")
    if blender is None:
        raise SystemExit("Blender is required to author production human GLBs")
    masters = (args.master,) if args.master else MASTER_IDS
    for master_id in masters:
        subprocess.run([
            blender, "--background", "--python", str(Path(__file__).resolve()), "--",
            "--input", str(args.input.resolve()), "--master", master_id,
        ], check=True)
    return 0


def blender_main() -> int:
    import bpy
    from mathutils import Vector

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--master", choices=MASTER_IDS, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    master_id = args.master
    root = args.input / master_id
    identity = json.loads((root / "identity.json").read_text(encoding="utf-8"))
    palette = identity["palette"]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("MascotRenderWorld")
    scene.world.color = (0.94, 0.96, 0.98)

    def rgba(value: str, alpha: float = 1.0):
        return tuple(int(value[index:index+2], 16) / 255 for index in (1, 3, 5)) + (alpha,)

    def darken(value: str, factor: float = .78) -> str:
        channels = [max(0, min(255, round(int(value[index:index+2], 16) * factor))) for index in (1, 3, 5)]
        return "#" + "".join(f"{channel:02X}" for channel in channels)

    materials: dict[str, object] = {}

    def material(name: str, color: str, alpha: float = 1.0):
        key = f"{name}-{color}-{alpha}"
        if key in materials:
            return materials[key]
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = rgba(color, alpha)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = rgba(color)
        bsdf.inputs["Roughness"].default_value = 0.82
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Alpha"].default_value = alpha
        if alpha < 1:
            mat.surface_render_method = "DITHERED"
        materials[key] = mat
        return mat

    ink = material("Outline", palette["outline"])
    skin = material("Skin", palette["skin"])
    skin_light = material("SkinHighlight", palette["skin_light"])
    hair = material("Hair", palette["hair"])
    primary = material("Primary", palette["primary"])
    secondary = material("Secondary", palette["secondary"])
    accent = material("Accent", palette["accent"])
    white = material("EyeWhite", "#FFF8EE")
    pants = material("Pants", {"H01":"#2879A8","H04":"#252A34","H07":"#315D82","H12":"#203B5D","H13":"#187B83"}[master_id])
    shoe = material("Shoes", {"H01":"#E94E64","H04":"#E9EEE8","H07":"#E8D8B9","H12":"#1C2633","H13":"#724277"}[master_id])
    device_dark = material("DeviceDark", "#3E4D5C")
    device_light = material("DeviceLight", "#A9BCC4")
    shadow_mat = material("ContactShadow", palette["outline"], .22)
    primary_shadow = material("PrimaryCelShadow", darken(palette["primary"], .80))

    def finish(obj, name: str, mat, semantic: str | None = None, parent=None):
        obj.name = name
        obj.data.materials.append(mat)
        if semantic:
            obj["semantic"] = semantic
        if parent is not None:
            world = obj.matrix_world.copy()
            obj.parent = parent
            if parent.name == "HeadPivot" or parent.name.startswith("Eye") or parent.name in {"HairRoot", "MouthPivot"}:
                obj.matrix_world = world
        return obj

    def uv(name, location, scale, mat, semantic=None, parent=None, segments=32):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=16, location=location)
        obj = bpy.context.object
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.shade_smooth()
        return finish(obj, name, mat, semantic, parent)

    def rounded(name, location, dimensions, radius, mat, semantic=None, parent=None):
        bpy.ops.mesh.primitive_cube_add(location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("Soft authored bevel", "BEVEL")
        bevel.width = radius
        bevel.segments = 5
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        bpy.ops.object.shade_smooth()
        return finish(obj, name, mat, semantic, parent)

    def skirt_frustum(name, location, mat, semantic=None, parent=None):
        bpy.ops.mesh.primitive_cone_add(
            vertices=4, radius1=.68, radius2=.49, depth=.50,
            location=location, rotation=(0, 0, math.pi/4),
        )
        obj = bpy.context.object
        obj.scale.y = .48
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("Skirt edge softness", "BEVEL")
        bevel.width = .06
        bevel.segments = 3
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        bpy.ops.object.shade_smooth()
        return finish(obj, name, mat, semantic, parent)

    def cylinder(name, start, end, radius, mat, semantic=None, parent=None):
        start_v, end_v = Vector(start), Vector(end)
        delta = end_v - start_v
        midpoint = (start_v + end_v) * .5
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=delta.length, location=midpoint)
        obj = bpy.context.object
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.object.shade_smooth()
        return finish(obj, name, mat, semantic, parent)

    def torus(name, location, major, minor, mat, semantic=None, parent=None, rotation=(math.pi/2, 0, 0)):
        bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=40, minor_segments=10, location=location, rotation=rotation)
        obj = bpy.context.object
        return finish(obj, name, mat, semantic, parent)

    def curve(name, points, bevel, mat, semantic=None, parent=None, cyclic=False):
        data = bpy.data.curves.new(name, "CURVE")
        data.dimensions = "3D"
        data.bevel_depth = bevel
        data.bevel_resolution = 3
        spline = data.splines.new("BEZIER")
        spline.bezier_points.add(len(points)-1)
        for point, co in zip(spline.bezier_points, points):
            point.co = co
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
        spline.use_cyclic_u = cyclic
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        return finish(obj, name, mat, semantic, parent)

    character = bpy.data.objects.new(f"{master_id}CharacterRoot", None)
    bpy.context.collection.objects.link(character)
    character["semantic"] = "root"
    character["characterId"] = master_id
    character["familyId"] = identity["family_id"]
    character["license"] = "MIT"

    dimensions = {
        "H01": (.62, .68, .47, .86), "H04": (.57, .62, .72, 1.18),
        "H07": (.59, .64, .70, .90), "H12": (.58, .64, .69, 1.04),
        "H13": (.60, .65, .78, 1.02),
    }[master_id]
    head_w, head_h, torso_w, torso_h = dimensions
    seated = master_id == "H07"
    head_z = .72 if not seated else .63
    torso_z = -.43 if not seated else -.35

    head_pivot = bpy.data.objects.new("HeadPivot", None)
    bpy.context.collection.objects.link(head_pivot)
    head_pivot.location = (0, 0, head_z)
    head_pivot.parent = character
    head_pivot["semantic"] = "head"
    left_arm_pivot = bpy.data.objects.new("ArmLeftPivot", None)
    right_arm_pivot = bpy.data.objects.new("ArmRightPivot", None)
    for obj, x, semantic in ((left_arm_pivot, torso_w*.84, "arm.left"), (right_arm_pivot, -torso_w*.84, "arm.right")):
        bpy.context.collection.objects.link(obj)
        obj.location = (x, -.01, torso_z+torso_h*.34)
        obj.parent = character
        obj["semantic"] = semantic

    # Contact shadow and cel-style outlined body masses.
    uv("GroundShadow", (0, .18, -1.72 if not seated else -1.57), (1.03 if not seated else 1.48, .12, .07), shadow_mat, "ground.contact", None)
    # Front-only outline plates preserve the approved navy rim without turning
    # into the generic solid navy shell that obscured every rear view.
    rounded("TorsoOutline", (0, -.15, torso_z), (torso_w*2.045, .018, torso_h*1.045), .18, ink, None, character)
    rounded("Torso", (0, -.04, torso_z+.01), (torso_w*2, .72, torso_h), .20, primary, "torso", character)
    rounded("TorsoCelShade", (torso_w*.66, -.414, torso_z), (torso_w*.31, .016, torso_h*.72), .09, primary_shadow, "cel-shade.torso", character)
    uv("HeadOutline", (0, -.30, head_z), (head_w*1.045, .012, head_h*1.045), ink, None, head_pivot)
    uv("Head", (0, -.055, head_z), (head_w, .45, head_h), skin, "face", head_pivot)
    cylinder("NeckBack", (0,.10,torso_z+torso_h*.47), (0,.10,head_z-head_h*.72), .16, skin, "neck.back", character)

    # Clothing landmarks.
    if master_id == "H01":
        skirt_frustum("Skirt", (0, -.05, -.98), pants, "clothing.skirt", character)
        uv("HeartBadge", (0, -.43, torso_z+.10), (.13, .025, .15), secondary, "clothing.heart", character)
        rounded("GarmentBack", (0,.335,torso_z), (.72,.035,.54), .10, primary, "garment.back", character)
    elif master_id == "H04":
        rounded("JacketCenter", (0, -.425, torso_z), (.055, .018, torso_h*.82), .02, white, "clothing.jacket-center", character)
        curve("JacketYoke", [(-.55,-.425,torso_z+.34),(0,-.435,torso_z+.18),(.55,-.425,torso_z+.34)], .035, secondary, parent=character)
        curve("JacketBackYoke", [(-.55,.33,torso_z+.34),(0,.36,torso_z+.18),(.55,.33,torso_z+.34)], .035, secondary, "garment.back", character)
    elif master_id == "H07":
        rounded("OvershirtCenter", (0, -.425, torso_z), (.07, .018, torso_h*.84), .02, accent, "clothing.overshirt", character)
        curve("OvershirtYoke", [(-.47,-.425,torso_z+.27),(0,-.435,torso_z+.13),(.47,-.425,torso_z+.27)], .04, secondary, parent=character)
        rounded("OvershirtBack", (0,.335,torso_z), (.70,.035,.62), .10, primary, "garment.back", character)
    elif master_id == "H12":
        for x in (-.31, .31):
            rounded(f"CardiganPanel{'Left' if x>0 else 'Right'}", (x,-.425,torso_z), (.055,.018,torso_h*.82), .02, white, "clothing.cardigan", character)
        curve("CardiganCollar", [(-.38,-.425,torso_z+.30),(0,-.435,torso_z+.05),(.38,-.425,torso_z+.30)], .035, white, parent=character)
        curve("CardiganBackSeam", [(0,.34,torso_z+.36),(0,.37,torso_z),(0,.34,torso_z-.36)], .025, white, "garment.back", character)
    else:
        curve("PatternedScarf", [(-.53,-.425,torso_z+.32),(0,-.445,torso_z+.10),(.53,-.425,torso_z+.32)], .085, secondary, "clothing.patterned-scarf", character)
        curve("ScarfAccent", [(-.35,-.438,torso_z+.27),(0,-.452,torso_z+.14),(.35,-.438,torso_z+.27)], .026, accent, parent=character)
        curve("ScarfBack", [(-.50,.35,torso_z+.31),(0,.38,torso_z+.12),(.50,.35,torso_z+.31)], .07, secondary, "garment.back", character)

    # Face: smaller, identity-preserving landmarks instead of shared giant eyes.
    eye_spacing = {"H01":.25,"H04":.23,"H07":.25,"H12":.23,"H13":.24}[master_id]
    eye_scale = {"H01":(.105,.045,.14),"H04":(.085,.04,.115),"H07":(.10,.04,.095),"H12":(.085,.04,.11),"H13":(.09,.04,.11)}[master_id]
    eye_pivots = []
    for side, x in (("Left", eye_spacing), ("Right", -eye_spacing)):
        pivot = bpy.data.objects.new(f"Eye{side}Pivot", None)
        bpy.context.collection.objects.link(pivot)
        pivot.location = (x, -.49, head_z+.08)
        pivot_world = pivot.matrix_world.copy()
        pivot.parent = head_pivot
        pivot.matrix_world = pivot_world
        eye_pivots.append(pivot)
        uv(f"EyeWhite{side}", (x,-.50,head_z+.08), eye_scale, white, f"eye.{side.lower()}", pivot)
        uv(f"Pupil{side}", (x,-.545,head_z+.075), (.038,.022,.055), ink, f"pupil.{side.lower()}", pivot)
        curve(f"Brow{side}", [(x-.11,-.535,head_z+.27),(x,-.56,head_z+.31),(x+.11,-.535,head_z+.27)], .025, hair, parent=pivot)
    uv("Nose", (0,-.555,head_z-.06), (.045,.024,.055), skin_light, "nose", head_pivot)
    mouth_pivot = bpy.data.objects.new("MouthPivot", None)
    bpy.context.collection.objects.link(mouth_pivot)
    mouth_pivot.location = (0, -.545, head_z-.26)
    mouth_world = mouth_pivot.matrix_world.copy()
    mouth_pivot.parent = head_pivot
    mouth_pivot.matrix_world = mouth_world
    curve("Mouth", [(-.23,-.545,head_z-.22),(0,-.57,head_z-.35),(.23,-.545,head_z-.22)], .035, ink, "mouth", mouth_pivot)
    if master_id == "H04":
        curve("Beard", [(-.38,-.49,head_z-.18),(0,-.52,head_z-.48),(.38,-.49,head_z-.18)], .055, hair, "facial-hair.beard", head_pivot)
    if master_id == "H13":
        for side, x in (("Left", eye_spacing), ("Right", -eye_spacing)):
            torus(f"Glasses{side}", (x,-.57,head_z+.08), .15, .026, ink, f"glasses.{side.lower()}", head_pivot, rotation=(math.pi/2,0,0))
        cylinder("GlassesBridge", (-.09,-.58,head_z+.08),(.09,-.58,head_z+.08),.025,ink,parent=head_pivot)

    # Hair is modeled around the skull and therefore remains attached in every view.
    hair_root = bpy.data.objects.new("HairRoot", None)
    bpy.context.collection.objects.link(hair_root)
    hair_root.location = (0, 0, head_z)
    hair_world = hair_root.matrix_world.copy()
    hair_root.parent = head_pivot
    hair_root.matrix_world = hair_world
    hair_root["semantic"] = "hair"
    if master_id == "H01":
        for index, (x,z,s) in enumerate(((-.37,.43,.25),(-.17,.51,.18),(0,.54,.19),(.17,.51,.18),(.37,.43,.25),(-.68,.42,.34),(.68,.42,.34))):
            uv(f"HairCurl{index}",(x,-.02,head_z+z),(s,.28,s),hair,None,hair_root,24)
    elif master_id == "H04":
        rounded("CoilyHairCap",(0,-.06,head_z+.44),(.92,.48,.30),.14,hair,"hair.short-coily",hair_root)
        for index, x in enumerate((-.36,-.24,-.12,0,.12,.24,.36)):
            uv(f"HairCurl{index}",(x,-.39,head_z+.47+(index%2)*.035),(.135,.075,.13),hair,None,hair_root,20)
    elif master_id == "H07":
        rounded("StraightHairCap",(0,.0,head_z+.43),(1.02,.55,.34),.16,hair,"hair.short-straight",hair_root)
        curve("SidePart",[(-.18,-.31,head_z+.55),(.05,-.36,head_z+.52),(.34,-.31,head_z+.42)],.025,secondary,parent=hair_root)
    elif master_id == "H12":
        hair_grey = material("HairGrey", "#7D7B80")
        rounded("BobBack",(0,.05,head_z),(1.20,.52,1.32),.28,hair,"hair.greying-bob",hair_root)
        uv("BobFaceOpening",(0,-.49,head_z-.03),(.51,.012,.56),skin,None,hair_root,32)
        rounded("BobRearCoverage",(0,.48,head_z-.02),(1.08,.025,1.18),.25,hair,"hair.back",hair_root)
        curve("GreyStreakRear",[(-.30,.505,head_z+.52),(-.18,.515,head_z+.20),(-.29,.505,head_z-.18)],.04,hair_grey,"hair.grey-streak.back",hair_root)
        curve("GreyStreak",[(-.30,-.34,head_z+.55),(-.18,-.39,head_z+.25),(-.31,-.37,head_z-.18)],.045,hair_grey,"hair.grey-streak",hair_root)
    else:
        grey_light = material("HairHighlight", "#E4DFD7")
        positions = [(-.48,.34),(-.28,.52),(0,.58),(.28,.52),(.48,.34),(-.55,.05),(.55,.05)]
        for index,(x,z) in enumerate(positions):
            uv(f"GreyCurl{index}",(x,-.01,head_z+z),(.24,.29,.24),hair,None,hair_root,24)
            curve(f"CurlHighlight{index}",[(x-.08,-.30,head_z+z),(x,-.34,head_z+z+.08),(x+.08,-.30,head_z+z)],.018,grey_light,parent=hair_root)

    # Arms are two-segment authored hierarchies, enabling meaningful gestures.
    arm_objects = []
    for pivot, sign, side in ((left_arm_pivot,1,"Left"),(right_arm_pivot,-1,"Right")):
        cylinder(f"UpperArmOutline{side}",(0,.015,0),(sign*.10,-.005,-.42),.155,ink,None,pivot)
        upper = cylinder(f"UpperArm{side}",(0,-.015,0),(sign*.10,-.035,-.42),.13,primary,f"upper-arm.{side.lower()}",pivot)
        fore_material = primary if master_id == "H04" else skin
        cylinder(f"ForearmOutline{side}",(sign*.10,.0,-.42),(sign*.08,-.04,-.82),.118,ink,None,pivot)
        fore = cylinder(f"Forearm{side}",(sign*.10,-.035,-.42),(sign*.08,-.075,-.82),.095,fore_material,f"forearm.{side.lower()}",pivot)
        uv(f"HandOutline{side}",(sign*.08,-.055,-.91),(.145,.115,.175),ink,None,pivot)
        uv(f"Hand{side}",(sign*.08,-.09,-.91),(.12,.09,.15),skin_light,f"hand.{side.lower()}",pivot)
        arm_objects.append(pivot)

    # Legs and assistive devices.
    if not seated:
        for side, x in (("Left",.28),("Right",-.28)):
            if master_id == "H04" and side == "Right":
                rounded("ProstheticSocketRight",(x,0,-1.00),(.29,.34,.43),.10,device_dark,"prosthesis.socket.right",character)
                cylinder("ProstheticPylonRight",(x,0,-1.18),(x,0,-1.52),.07,device_light,"prosthesis.pylon.right",character)
                rounded("ProstheticFootRight",(x-.06,-.08,-1.63),(.48,.52,.20),.09,device_light,"prosthesis.foot.right",character)
            else:
                leg_material = skin if master_id == "H01" else pants
                cylinder(f"LegOutline{side}",(x,.02,-.84),(x,.02,-1.48),.17,ink,None,character)
                cylinder(f"Leg{side}",(x,-.02,-.84),(x,-.02,-1.48),.14,leg_material,f"leg.{side.lower()}",character)
                rounded(f"FootOutline{side}",(x + (.06 if side=='Left' else -.06),-.04,-1.61),(.52,.56,.23),.10,ink,None,character)
                rounded(f"Foot{side}",(x + (.06 if side=='Left' else -.06),-.10,-1.61),(.46,.50,.18),.08,shoe,f"foot.{side.lower()}",character)
    else:
        for side,x in (("Left",.25),("Right",-.25)):
            cylinder(f"Thigh{side}",(x,0,-.70),(x*.95,-.18,-1.05),.16,pants,f"leg.{side.lower()}",character)
            cylinder(f"Shin{side}",(x*.95,-.18,-1.05),(x*.90,-.25,-1.34),.14,pants,parent=character)
            rounded(f"Foot{side}",(x*.90,-.34,-1.42),(.42,.48,.18),.08,shoe,f"foot.{side.lower()}",character)
        # Manual wheelchair: wheels, pushrims, seat, backrest, frame, footrest, casters.
        for side,x in (("Left",.83),("Right",-.83)):
            torus(f"Wheel{side}",(x,.06,-1.05),.66,.075,ink,f"wheel.{side.lower()}",character)
            torus(f"Pushrim{side}",(x,-.055,-1.05),.54,.027,device_light,f"pushrim.{side.lower()}",character)
            torus(f"WheelSideProfile{side}",(x,.06,-1.05),.66,.055,ink,f"wheel.side-profile.{side.lower()}",character,rotation=(0,math.pi/2,0))
            torus(f"PushrimSideProfile{side}",(x,-.055,-1.05),.54,.021,device_light,f"pushrim.side-profile.{side.lower()}",character,rotation=(0,math.pi/2,0))
            for spoke in range(8):
                angle = spoke*math.pi/4
                cylinder(f"Spoke{side}{spoke}",(x,-.02,-1.05),(x+math.cos(angle)*.53,-.02,-1.05+math.sin(angle)*.53),.012,device_light,parent=character)
        rounded("WheelchairSeat",(0,.02,-.72),(1.18,.66,.15),.05,device_dark,"wheelchair.seat",character)
        rounded("WheelchairBackrest",(0,.22,-.43),(1.05,.18,.78),.08,device_dark,"wheelchair.backrest",character)
        cylinder("WheelchairFrame",(-.52,0,-.70),(.52,0,-.70),.055,device_light,"wheelchair.frame",character)
        cylinder("WheelchairFootrestPost",(0,-.08,-.78),(0,-.28,-1.38),.05,device_light,parent=character)
        rounded("WheelchairFootrest",(0,-.33,-1.45),(.72,.45,.10),.04,device_light,"wheelchair.footrest",character)
        for side,x in (("Left",.48),("Right",-.48)):
            torus(f"WheelchairCaster{side}",(x,-.28,-1.49),.14,.04,ink,f"wheelchair.caster.{side.lower()}",character)

    if master_id == "H12":
        ear_anchor = bpy.data.objects.new("EarRightAnchor", None)
        hearing_root = bpy.data.objects.new("HearingAidRoot", None)
        for obj, semantic in ((ear_anchor,"ear.right.anchor"),(hearing_root,"hearing-aid.root")):
            bpy.context.collection.objects.link(obj)
            obj["semantic"] = semantic
        ear_anchor.location = (-.56,-.38,head_z-.08)
        ear_world = ear_anchor.matrix_world.copy(); ear_anchor.parent = head_pivot; ear_anchor.matrix_world = ear_world
        hearing_root.location = ear_anchor.location
        hearing_world = hearing_root.matrix_world.copy(); hearing_root.parent = ear_anchor; hearing_root.matrix_world = hearing_world
        rounded("HearingAidCaseRight",(-.61,-.12,head_z+.03),(.14,.18,.27),.06,accent,"hearing-aid.case.right",hearing_root)
        curve("HearingAidTubeRight",[(-.61,-.28,head_z+.13),(-.68,-.34,head_z-.02),(-.58,-.38,head_z-.12)],.025,device_light,"hearing-aid.tube.right",hearing_root)
        uv("HearingAidEarpieceRight",(-.56,-.39,head_z-.13),(.055,.025,.07),accent,"hearing-aid.earpiece.right",hearing_root)
    if master_id == "H13":
        # Four-wheel rollator with handles, seat, cross brace, and distinct wheel pairs.
        rollator = bpy.data.objects.new("RollatorFrame",None)
        bpy.context.collection.objects.link(rollator)
        rollator.parent = character
        rollator["semantic"] = "rollator.frame"
        for side,x in (("Left",.78),("Right",-.78)):
            cylinder(f"RollatorPost{side}",(x,-.18,-.55),(x,-.30,-1.47),.055,device_light,parent=rollator)
            cylinder(f"RollatorHandle{side}",(x,-.18,-.55),(x+(.25 if side=='Left' else -.25),-.28,-.55),.065,ink,f"rollator.handle.{side.lower()}",rollator)
        cylinder("RollatorCrossBraceA",(-.76,-.27,-1.26),(.76,-.27,-.76),.045,accent,parent=rollator)
        cylinder("RollatorCrossBraceB",(.76,-.27,-1.26),(-.76,-.27,-.76),.045,accent,parent=rollator)
        rounded("RollatorSeat",(0,-.22,-.90),(1.12,.42,.13),.04,device_dark,"rollator.seat",rollator)
        wheel_specs = (("FrontLeft",.82,-.43,-1.53),("FrontRight",-.82,-.43,-1.53),("RearLeft",.68,.03,-1.50),("RearRight",-.68,.03,-1.50))
        for name,x,y,z in wheel_specs:
            torus(f"RollatorWheel{name}",(x,y,z),.16,.045,ink,f"rollator.wheel.{name.lower()}",rollator)
            torus(f"RollatorWheelSideProfile{name}",(x,y,z),.16,.035,ink,f"rollator.wheel.side-profile.{name.lower()}",rollator,rotation=(0,math.pi/2,0))

    # Animation authoring: object actions are merged by semantic NLA track name.
    def animate(obj, clip: str, data_path: str, values):
        obj.animation_data_create()
        obj.animation_data.action = None
        for frame, value in ((1, values[0]), (12, values[1]), (24, values[2])):
            if data_path == "rotation_euler":
                obj.rotation_mode = "XYZ"
                obj.rotation_euler = value
            elif data_path == "scale":
                obj.scale = value
            elif data_path == "location":
                obj.location = value
            obj.keyframe_insert(data_path=data_path, frame=frame, group=clip)
        action = obj.animation_data.action
        action.name = f"{clip}.{obj.name}"
        track = obj.animation_data.nla_tracks.new()
        track.name = clip
        track.strips.new(clip, 1, action)
        obj.animation_data.action = None

    pose_angles = {
        "rest": (0,0), "greeting": (0,2.15), "farewell": (-2.15,0),
        "agreement": (-.72,.72), "disagreement": (.95,-.95), "gratitude": (-1.18,1.18),
        "concern": (-1.05,1.05), "surprise": (-1.35,1.35), "celebration": (-2.22,2.22),
    }
    for clip,(left,right) in pose_angles.items():
        animate(left_arm_pivot,clip,"rotation_euler",((0,0,0),(0,left,0),(0,0,0)))
        animate(right_arm_pivot,clip,"rotation_euler",((0,0,0),(0,right,0),(0,0,0)))
        if clip == "rest":
            animate(character,clip,"location",((0,0,0),(0,0,.018),(0,0,0)))
        elif clip == "gratitude":
            animate(head_pivot,clip,"rotation_euler",((0,0,0),(.08,0,.14),(0,0,0)))
    expression_scales = {
        "happy": (1,1,1), "laughing": (1,.16,1), "surprised": (1,1.35,1),
        "thinking": (1,.82,1), "confident": (1,.62,1), "sorry": (1,.82,1), "excited": (1,1.22,1),
    }
    for clip,scale_mid in expression_scales.items():
        name = f"expression-{clip}"
        for pivot in eye_pivots:
            animate(pivot,name,"scale",((1,1,1),scale_mid,(1,1,1)))
        mouth_mid = {"happy":(1.03,1,1.06),"laughing":(1,1,1.55),"surprised":(.35,1,1.55),"thinking":(.75,1,.7),"confident":(1.05,1,.8),"sorry":(1,1,-.75),"excited":(1.2,1,1.25)}.get(clip,(1,1,1))
        animate(mouth_pivot,name,"scale",((1,1,1),mouth_mid,(1,1,1)))
        tilt = {"thinking":-.10,"confident":.08,"sorry":-.07,"excited":.10}.get(clip,0)
        animate(head_pivot,name,"rotation_euler",((0,0,0),(0,tilt*.25,tilt),(0,0,0)))

    # A production semantic presentation combines readable posture and face;
    # pixel-different isolated tracks alone are not meaningful evidence.
    animate(left_arm_pivot,"semantic-excited","rotation_euler",((0,0,0),(0,-2.22,0),(0,0,0)))
    animate(right_arm_pivot,"semantic-excited","rotation_euler",((0,0,0),(0,2.22,0),(0,0,0)))
    for pivot in eye_pivots:
        animate(pivot,"semantic-excited","scale",((1,1,1),(1,1.35,1),(1,1,1)))
    animate(mouth_pivot,"semantic-excited","scale",((1,1,1),(1.25,1,1.45),(1,1,1)))
    animate(character,"semantic-excited","location",((0,0,0),(0,0,.16),(0,0,0)))

    # True hierarchy rotations provide reviewable neutral turnarounds.  Hair,
    # limbs, prostheses, wheelchair and rollator remain parented to the same
    # character root; no front-view geometry is compressed or detached.
    for clip, angle in (("turnaround-three-quarter", -math.pi/4),
                        ("turnaround-side", -math.pi/2),
                        ("turnaround-back", math.pi)):
        animate(character, clip, "rotation_euler", ((0,0,0), (0,0,angle), (0,0,0)))

    scene.frame_start = 1
    scene.frame_end = 24
    blend_path = root / f"{master_id}.blend"
    glb_path = root / f"{master_id}-production.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path), export_format="GLB", export_yup=True,
        export_animations=True, export_animation_mode="NLA_TRACKS",
        export_nla_strips=True, export_merge_animation="NLA_TRACK",
        export_extras=True, export_apply=False,
    )
    patch_unlit_glb(glb_path, master_id)
    manifest_path = root / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["glb"] = glb_path.name
    manifest["glb_sha256"] = hashlib.sha256(glb_path.read_bytes()).hexdigest()
    manifest["dcc_source"] = blend_path.name
    manifest["dcc_source_sha256"] = hashlib.sha256(blend_path.read_bytes()).hexdigest()
    manifest["glb_asset_class"] = "authored-production-review-candidate"
    manifest["glb_production_use"] = "forbidden-until-owner-design-review"
    manifest["glb_required_semantic_clip_count"] = len(POSES) + len(EXPRESSIONS)
    manifest["glb_turnaround_clip_count"] = len(TURNAROUND_CLIPS)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"authored {master_id}: {blend_path.name} -> {glb_path.name}")
    return 0


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        raise SystemExit(host_main())
    raise SystemExit(blender_main())
