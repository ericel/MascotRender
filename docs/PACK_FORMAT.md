# MascotRender Pack Format v1

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
  "canvas": { "width": 512, "height": 512 },
  "layers": [
    { "id": "body", "source": "layers/body.svg", "z": 10 },
    { "id": "eyes-happy", "source": "layers/eyes-happy.svg", "z": 20 },
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

## Sticker

```json
{
  "schema_version": 1,
  "sticker_id": "happy-example",
  "pack_id": "example-pack",
  "alt_text": "The example mascot smiling",
  "expression": "happy",
  "pose": "front",
  "seed": 42,
  "layers": [],
  "text": {
    "content": "YOU GOT THIS!",
    "style": "caption",
    "placement": "auto",
    "preferred_slots": ["bottom", "top"]
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

## Text behavior in 0.1

The engine loads only the exact pack-declared static TTF. Platform font lookup
and fallback are never used. ASCII whitespace is normalized at wrap boundaries.
The renderer searches downward from `max_font_size` for the largest whole-point
size that fits, chooses the fewest valid lines, and balances them by minimizing
squared unused line width. An outline is rendered as eight deterministic glyph
passes around the fill and participates in safe-area fitting. For auto
placement, the renderer chooses the candidate yielding the largest font, then
the fewest lines, then the earliest authored preference. Text is centered above
the selected SVG layers. Explicit newline preservation, collision masks,
rotation, paths, fallback fonts, shaping, and bidirectional text remain later
work.

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
