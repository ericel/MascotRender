# robot-004 GLB proof

`robot-004.glb` is the deterministic MR-112 true-3D mascot proof. It is built
from code so CI can compare the complete binary without requiring Blender.
Its rounded-square silhouette, curved face, mint antenna/sparkle, warm gold
face plate, orange trim, and navy ink follow the approved 2D/2.5D visual
contract rather than introducing an independent 3D character design.

`identity.json` is the versioned MR-114 identity contract shared with the flat
2D and layered 2.5D packs. It fixes the exact palette, required semantic
features, and normalized proportions for the head, body, eyes, mouth, and
antenna. The generator derives GLB geometry and material colors from this file,
then embeds its ID, version, and SHA-256 in the GLB asset metadata.

Semantic nodes:

- `RobotRoot`, `Body`, `Head`, `Face`, `Antenna`
- `caption_anchor` for the later MR-113 2D caption compositor

Animation clips:

- `idle` — head sway and blink
- `hello` — arm wave and head response
- `hop` — translation, squash/stretch, and independent shadow contraction
- `celebrate` — body/arm motion plus smile and wow morphs

Facial morph targets:

- `blink`, `smile`, `wow`, `squint`, `sad`, `cheek`

Regenerate or verify the asset:

```bash
python tools/generate_robot_glb.py \
  --identity examples/robot-004/identity.json \
  --output examples/robot-004/robot-004.glb
python tools/generate_robot_glb.py \
  --identity examples/robot-004/identity.json \
  --output examples/robot-004/robot-004.glb --check

python tools/validate_character_identity.py \
  --contract examples/robot-004/identity.json \
  --pack examples/robot-2_5d/pack.json \
  --flat-pack examples/robot-2_5d/pack-flat.json \
  --glb examples/robot-004/robot-004.glb
```

The review script requires Pillow and writes five transparent pose WebPs, four
real 13-frame looping animated WebPs, a white-background rest PNG, labelled
pose and motion sheets, a browser playback page, and a JSON manifest. It cleans
legacy review names before rendering and rejects missing brand colors, an
antenna that appears below the character, a static clip, a missing animated
WebP chunk, a wrong frame count, or a loop that does not close:

```bash
python tools/render_robot_glb_review.py \
  --renderer build/filament/cmake/mascotrender-glb-preview \
  --input examples/robot-004/robot-004.glb \
  --output generated/robot-004-review
```

Blender can import the GLB for art iteration, but is not part of the runtime or
deterministic build pipeline.
