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

Status: in progress. Named text slots, deterministic preference-based auto
placement, and authored avoid-region scoring are implemented without breaking
existing pack files.

Next: introduce internal scene nodes and parent-child transforms; add
screen-fixed and character-anchor text;
then add rotated/path text after HarfBuzz shaping is available.

Exit: one recipe renders unchanged at `t = 0`; top, bottom, left, right, and
speech placements are deterministic at both 512 and 256 pixels.

### E2 — Animated existing 2D packs

Status: first vertical slice complete. Typed scalar tracks, fixed easing, loop
policy, body bounce, text pop, bounded frame sampling, animated WebP, and static
poster thumbnails are implemented. Next add blink/sparkle tracks and solve text
against the union of occupied regions across the animation.

Exit: one existing mascot produces a deterministic animated WebP plus
a stable static poster thumbnail, with bounded duration/frame count and no text
jumping.

### E3 — Layered 2.5D

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

## Guardrails

- Do not add Filament before the sampled-scene and timeline tests pass.
- Keep 3D optional so the small C++20/Conan package remains useful.
- Use GLB/glTF 2.0 as the exchange format and keep loop/clip-mixing policy in
  MascotRender.
- Pre-render animated WebP for product clients; do not put the 3D renderer in
  the React suggestion tray.
- Pin frame rate, duration, easing formulas, timestamps, backend versions, and
  encoder settings for deterministic builds.
