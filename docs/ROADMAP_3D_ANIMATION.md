# Scene, Animation, and 3D Expansion Plan

MascotRender will evolve from static 2D composition into a time-sampled scene
compiler. The same semantic sticker recipe should be renderable by a flat 2D,
layered 2.5D, or true 3D backend without exposing backend types in the public
C++ API.

```text
Sticker recipe
  -> scene compiler + text solver + animation timeline
  -> backend-neutral sampled scene
  -> ThorVG 2D | layered 2.5D | Filament 3D
  -> 2D text/effect compositor
  -> static or animated WebP encoder
```

## Contracts to stabilize first

- A scene graph whose nodes have IDs, parents, 3D-compatible position,
  rotation, scale, opacity, pivot, and depth. Existing SVG layers become flat
  nodes with Z rotation and zero depth.
- A generic timeline of typed keyframes and deterministic easing. Rendering at
  `t = 0` must reproduce the static result.
- Named text slots and placement modes. Version 1 currently supports legacy
  style safe areas, explicit named slots, and deterministic `auto` selection.
  Authored avoid-region scoring is implemented; character anchors, rotation,
  paths, and animation-wide
  occupancy masks follow without changing authored wording.
- A frame transport and animation encoder contract based on owned RGBA pixels
  and integer millisecond timestamps.

## Expansion track

### E1 — Layout and scene foundations

Status: layout slice complete. Named text slots, deterministic preference-based
auto placement, actual fitted-glyph scoring, and selected-layer collision bounds
are implemented without breaking existing pack files.

Next: introduce internal scene nodes and parent-child transforms; add
screen-fixed and character-anchor text;
then add rotated/path text after HarfBuzz shaping is available.

Authored per-sticker caption offset/rotation is tracked as `MR-085`. It must
preserve automatic collision-aware placement rather than replacing it.

Exit: one recipe renders unchanged at `t = 0`; top, bottom, left, right, and
speech placements are deterministic at both 512 and 256 pixels.

### E2 — Animated existing 2D packs

Status: first vertical slice complete. Typed scalar tracks, fixed easing, loop
policy, body bounce, text pop, bounded frame sampling, animated WebP, and static
poster thumbnails are implemented. Next add blink/sparkle tracks and solve text
against the union of occupied regions across the animation.

Per-sticker text slide, bounce, and pulse presets plus deterministic goldens are
tracked as `MR-094`. Lottie remains a separate optional exporter decision.

Exit: one existing mascot produces a deterministic animated WebP plus
a stable static poster thumbnail, with bounded duration/frame count and no text
jumping.

### E3 — Layered 2.5D

Status: complete. M6 approved the flat visual baseline and MR-102 approved the
corrected animation on 2026-07-14. The parented robot matches its flat control
byte-for-byte at `t = 0`, demonstrates deterministic depth parallax, and uses
typed node/view tracks for squash/stretch, delayed child follow-through,
responsive shadows, and camera motion. The accepted animation is locked by a
decoded-frame golden.

Split a mascot into parented parts with pivots and depth. Add parallax,
squash-and-stretch, delayed child motion, shadows, and simple camera motion
through the same timeline.

Exit: the robot pack demonstrates head/body/antenna/effect parallax through the
backend-neutral scene contract; the flat 2D backend remains supported.

### E4 — True 3D proof

Add an optional Filament backend behind a separate Conan option. Prove it with
one `robot-004.glb`, semantic bone/anchor mappings, four authored clips, six
facial morph targets, an orthographic camera, and toon lighting. Blender is the
offline authoring/validation tool; it is not a runtime dependency. Captions
remain crisp 2D overlays by default.

Exit: the same recipe renders through 2D, 2.5D, and Filament backends; a normal
consumer that does not enable 3D does not download or link Filament.

Status: MR-110 is complete. `with_filament=False` remains the default Conan
graph, while `with_filament=True` selects the matching CMake feature and pins
`filament/1.74.0`. MR-111 now includes a checksum-pinned wrapper for the
official desktop archives and a real gltfio loader that validates semantic
anchors without exposing Filament types. A headless Metal proof loads mesh
resources and reads transparent RGBA output through a fixed orthographic camera
and hard toon-style key light. Cross-platform wrapper validation and final
remote publication remain.

MR-112 now has a reproducible, Khronos-valid `robot-004.glb`. Its semantic
hierarchy contains `RobotRoot`, body/head/face/antenna nodes, and
`caption_anchor`; its four clips and six face morphs are enumerated and sampled
through Filament tests. The generator does not require Blender, while the GLB
remains editable in Blender for a later art-quality pass.

## Guardrails

- Do not add Filament before the sampled-scene and timeline tests pass.
- Keep 3D optional so the small C++20/Conan package remains useful.
- Use GLB/glTF 2.0 as the exchange format and keep loop/clip-mixing policy in
  MascotRender.
- Pre-render animated WebP for product clients; do not put the 3D renderer in
  the React suggestion tray.
- Pin frame rate, duration, easing formulas, timestamps, backend versions, and
  encoder settings for deterministic builds.
