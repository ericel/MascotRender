# MascotRender Pack Format v1

This document defines the trusted local directory model consumed by the 0.1
engine. The draft portable `.mascot` authoring container is specified separately
in `MASCOT_PACKAGE_SPEC.md`; it is not yet an accepted engine input. A future
bounded loader will verify that container before translating it into this
compiled pack model.

A pack declares local SVG layers, invariant base layers, named expressions and
poses, optional seeded variation groups, and optional local TTF fonts and text
styles. A sticker chooses an expression and pose and may provide authored text;
MascotRender resolves the composition and returns an encoded image in memory.

The normative machine-readable files are
[`pack.schema.json`](../schemas/pack.schema.json) and
[`sticker.schema.json`](../schemas/sticker.schema.json). A runnable pack is in
[`examples/cat`](../examples/cat).

## Pack

```json
{
  "schema_version": 1,
  "pack_id": "example-pack",
  "character_identity": {
    "character_id": "robot-004",
    "contract_version": 1,
    "contract_sha256": "<64 lowercase hexadecimal characters>",
    "required_features": ["rounded_square_head", "single_antenna"]
  },
  "canvas": { "width": 512, "height": 512 },
  "layers": [
    {
      "id": "body",
      "source": "layers/body.svg",
      "z": 10,
      "pivot": "head",
      "depth": 0,
      "screen_space": false,
      "collision_bounds": { "x": 123, "y": 58, "width": 266, "height": 359 }
    },
    { "id": "eyes-happy", "source": "layers/eyes-happy.svg", "z": 20, "parent": "body", "pivot": "head", "depth": 0.2 },
    { "id": "spark-left", "source": "layers/spark-left.svg", "z": 30 },
    { "id": "spark-right", "source": "layers/spark-right.svg", "z": 31 }
  ],
  "base_layers": ["body"],
  "expressions": { "happy": ["eyes-happy"] },
  "poses": { "front": [] },
  "provenance": {
    "creator": "Example Studio",
    "license": "Internal approved asset",
    "source": "Original vector artwork"
  },
  "anchors": { "face_center": { "x": 256, "y": 280 } },
  "pivots": { "head": { "x": 256, "y": 280 } },
  "text_slots": {
    "top": { "x": 40, "y": 12, "width": 432, "height": 96 },
    "bottom": { "x": 72, "y": 382, "width": 368, "height": 104 }
  },
  "avoid_regions": [
    { "name": "face", "x": 123, "y": 145, "width": 266, "height": 272 }
  ],
  "text_clearance": 12,
  "fonts": [
    {
      "id": "display",
      "source": "fonts/changa-one/ChangaOne-Regular.ttf",
      "license": "fonts/changa-one/OFL.txt"
    }
  ],
  "text_styles": {
    "caption": {
      "font": "display",
      "safe_area": { "x": 72, "y": 382, "width": 368, "height": 104 },
      "min_font_size": 24,
      "max_font_size": 54,
      "max_lines": 2,
      "fill": { "r": 255, "g": 255, "b": 255 },
      "outline": {
        "width": 4,
        "color": { "r": 30, "g": 37, "b": 58 }
      }
    }
  },
  "variation_groups": [
    {
      "id": "spark-position",
      "choices": [["spark-left"], ["spark-right"], []]
    }
  ]
}
```

- `schema_version` must be `1`.
- `pack_id`, layer IDs, z values, and variation-group IDs must be unique.
- `character_identity` is optional. When present, it pins the pack to a
  versioned external identity contract by character ID, contract version,
  SHA-256, and required feature list. MascotRender preserves this declaration;
  project validation may additionally inspect SVG or GLB geometry against it.
- `rig` is optional backward-compatible metadata that identifies a normalized
  rig contract and maps each authored pose's semantic targets (for example
  `gesture.primary`) to concrete selected layer IDs. Offline recipe compilers
  resolve those semantic names before the C++ loader validates animation
  tracks, so the runtime remains deterministic and backend-neutral.
- Canvas dimensions must be between 1 and 4096 pixels.
- A source must be a relative `.svg` path resolving inside the pack directory.
- Absolute paths, URLs, missing files, symlink escapes, and non-SVG sources are
  rejected.
- z values, not JSON array or sticker selection order, define composition.
- Base, expression, pose, explicit, and variation layers are unioned by ID.
- Variation groups are evaluated in their JSON array order.
- Provenance strings are required. Named anchors and pivots must contain finite
  coordinates inside the declared canvas.
- Font sources must be local `.ttf` files, and each font declaration must point
  to a local `.txt` license. Both paths must resolve inside the pack directory.
- Text styles reference declared font IDs and define a canvas-relative safe
  area, minimum and maximum size, one to three lines, an RGB fill, and an
  optional 0-to-32 canvas-unit outline with its own RGB color.
- `text_slots` optionally declares reusable named canvas rectangles. Slot IDs
  are pack-local and each rectangle must be finite, positive, and contained by
  the canvas.
- `avoid_regions` declares named rectangles that automatic text should not
  cover. Names must be unique and rectangles must remain inside the canvas.
- A layer may declare `collision_bounds`, a canvas-relative rectangle covering
  the visual occupancy that text must avoid when that layer is selected.
  MascotRender adds only the selected layers' bounds to automatic placement.
- `text_clearance` optionally expands selected-layer collision bounds by 0 to
  128 canvas units before placement scoring. Expansion is clipped to the
  canvas.
- A layer may set `screen_space: true` to draw after character-space nodes and
  opt out of mascot transforms and depth parallax. Screen-space layers cannot
  declare a parent. Use this for effects whose pixel size must not change with
  a 2.5D or 3D camera; captions remain the separate text compositor.

## Layered 2.5D nodes

Every SVG layer is also a backend-neutral scene node. Existing declarations
remain flat identity nodes. A layer may additionally declare:

- `parent`: another layer ID whose affine transform, opacity, and depth it
  inherits; the parent need not be selected for its transform to resolve;
- `pivot`: an ID from the pack's `pivots` map, used as the center for local
  rotation and scale;
- `depth`: a finite value from -4 through 4, added to parent depth;
- `screen_space`: optional boolean for unparented post-character effects that
  remain fixed under view and mascot animation;
- `transform`: optional `x`, `y`, `rotation_degrees`, `scale_x`, `scale_y`, and
  `opacity` values. Defaults are identity translation/rotation/scale and full
  opacity.

The compiler rejects parent cycles, missing parents, unknown pivots, and invalid
transform values. Nodes draw by resolved world depth and then by the existing
unique integer `z`. At an identity view, identity nodes use the original flat
render path byte-for-byte. The runnable
[`robot-2_5d`](../examples/robot-2_5d) example includes a flat control and a
layered pack with shadow, body, head, face, antenna, and effect depths.

## Sticker

```json
{
  "schema_version": 1,
  "sticker_id": "happy-example",
  "pack_id": "example-pack",
  "alt_text": "The example mascot smiling",
  "phrase_id": "encouragement.you-got-this",
  "recipe_id": "motion.celebrate-jump",
  "expression": "happy",
  "pose": "front",
  "seed": 42,
  "view": { "x": 0, "y": 0 },
  "camera": {
    "framing": "three-quarter",
    "target": "face_center",
    "zoom": 1.05,
    "offset_x": 0,
    "offset_y": 24
  },
  "layers": [],
  "text": {
    "content": "YOU GOT THIS!",
    "style": "caption",
    "placement": "auto",
    "preferred_slots": ["bottom", "top"]
  },
  "animation": {
    "duration_ms": 800,
    "fps": 10,
    "loop": "loop",
    "overlays": ["text_pop"],
    "tracks": [{
      "target": "body",
      "property": "scale_y",
      "keyframes": [
        { "at_ms": 0, "value": 1, "easing": "ease_out" },
        { "at_ms": 300, "value": 1.08, "easing": "ease_in_out" },
        { "at_ms": 800, "value": 1 }
      ]
    }]
  }
}
```

`expression` and `pose` must name entries declared by the pack. `layers` is an
optional list for sticker-specific effects. `text` is optional; its style must
name a pack text style, and content is limited to 280 UTF-8 bytes. Omitted
`placement` preserves the style's legacy `safe_area`. A named placement selects
that pack slot. `auto` considers `preferred_slots` in order, or all slots in
lexicographic ID order when no preference is supplied. Unknown and duplicate
slot references are rejected with JSON-path diagnostics. The C++ caller
supplies output dimensions and WebP settings with `RenderOptions`; these are
build settings rather than authored pack content.

An optional sticker `view` supplies bounded canvas-space x/y offsets from -128
through 128. Each node moves by the negative view offset multiplied by its
resolved depth, producing deterministic parallax while text stays screen-fixed.
Collision bounds receive the same world transform and parallax before automatic
text placement.

Optional `phrase_id` and `recipe_id` preserve semantic provenance in generated
catalogues. An optional `camera` selects one of `face-closeup`, `bust`,
`three-quarter`, `full-body`, or `dynamic-full-body`; it scales character-space
layers around a declared pack anchor and moves that anchor by bounded screen
offsets. Captions and screen-space effects do not scale. Selected-layer
collision bounds receive the same camera transform before automatic text
placement, so close-ups cannot silently invalidate caption safety.

## Text behavior in 0.1

The engine loads only the exact pack-declared static TTF. Platform font lookup
and fallback are never used. ASCII whitespace is normalized at wrap boundaries.
The renderer searches downward from `max_font_size` for the largest whole-point
size that fits, chooses the fewest valid lines, and balances them by minimizing
squared unused line width. An outline is rendered as eight deterministic glyph
passes around the fill and participates in safe-area fitting. For auto
placement, the renderer computes the fitted glyph rectangle including its
outline, then scores that actual rectangle against authored avoid regions and
the selected layers' expanded collision bounds. It chooses the candidate with
the least overlap, then the largest font, fewest lines, and earliest authored
preference. This makes caption placement follow the selected rig rather than a
species-specific slot override. Text is centered above the selected SVG layers.
Explicit newline preservation, pixel occupancy masks, rotation, paths,
fallback fonts, shaping, and bidirectional text remain later work.

## Animation behavior in 0.1

An optional sticker `animation` renders a time-sampled scene and encodes it with
libwebp's animated WebP encoder. `duration_ms` is 100 through 10000, `fps` is 1
through 30, and the combination is limited to 2 through 300 logical frames.
Supported loop policies are `once`, `loop`, `ping_pong`, and
`hold_last_frame`. The first procedural overlays are `body_bounce` and
`text_pop`; unknown or duplicate overlays fail with a JSON-path diagnostic.

An animation may instead, or additionally, contain typed `tracks`. Node targets
name a selected layer and support `translate_x`, `translate_y`, `scale_x`,
`scale_y`, `rotation_degrees`, and multiplicative `opacity`. The reserved
`$view` target supports `view_x` and `view_y`, which animate depth parallax while
screen-fixed text remains stable. A node track affects that node's full subtree,
so a body scale moves its parented head while a later head or antenna track adds
deterministic follow-through. Easing is `linear`, `ease_out`, `ease_in_out`, or
`back_out`.

Tracks require at least two strictly increasing keyframes, beginning at zero and
ending at `duration_ms`. Values are finite and property-bounded. A `loop` track
must end at its starting value; duplicate target/property pairs, unknown nodes,
and invalid camera targets fail with an exact JSON location.

Frame timestamps, easing functions, transforms, encoder settings, and overlay
order are fixed. Repeating timelines normalize their final logical sample to
the loop endpoint; looping text-pop tracks also fade back to their initial
scale and opacity so the last-to-first transition is continuous. A render is
rejected before frame allocation if its retained BGRA frame buffers would
exceed the 256 MiB safety ceiling.
`RenderOptions::animation_first_frame_only` and the CLI
`--first-frame-only` flag produce a stable static poster; the batch pipeline
uses that path for thumbnails. libwebp may merge identical resting frames, so
the encoded frame count can be lower than the logical sample count without
changing duration or playback.

## Deterministic variation

An explicit unsigned 64-bit `seed` is used directly. When it is omitted, the
engine derives one with 64-bit FNV-1a over `pack_id`, a zero separator,
`sticker_id`, and a final zero separator. It advances SplitMix64 once per
variation group and selects `random_value % choice_count`.

This algorithm is part of format v1. It does not use `std::hash`, wall-clock
time, `std::random_device`, filesystem order, or unordered iteration.

## Diagnostics

Failures return an owned `Error` containing a stable `ErrorCode`, readable
message, source file, and JSON-style location such as `$.expression` or
`$.layers[2].source` when available.

## Trust boundary

Version 0.1 accepts curated repository-controlled SVGs. It constrains the
top-level source paths but does not claim to sanitize hostile SVG internals.
Do not expose pack loading directly to untrusted uploads.

## CLI

```bash
mascotrender render \
  --pack examples/cat/pack.json \
  --sticker examples/cat/stickers/text-sample.json \
  --output sample.webp
```
