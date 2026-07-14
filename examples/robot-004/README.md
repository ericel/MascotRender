# robot-004 GLB proof

`robot-004.glb` is the deterministic MR-112 true-3D mascot proof. It is built
from code so CI can compare the complete binary without requiring Blender.
Its rounded-square silhouette, curved face, mint antenna/sparkle, warm gold
face plate, orange trim, and navy ink follow the approved 2D/2.5D visual
contract rather than introducing an independent 3D character design.

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
python tools/generate_robot_glb.py --output examples/robot-004/robot-004.glb
python tools/generate_robot_glb.py \
  --output examples/robot-004/robot-004.glb --check
```

The review script requires Pillow and writes five transparent pose WebPs, four
real 13-frame looping animated WebPs, a white-background rest PNG, labelled
pose and motion sheets, a browser playback page, and a JSON manifest. It cleans
legacy review names before rendering and rejects missing brand colors, an
antenna that appears below the character, a static clip, a missing animated
WebP chunk, a wrong frame count, or a loop that does not close:

```bash
python tools/render_robot_glb_review.py \
  --renderer build/Release/mascotrender-glb-preview \
  --input examples/robot-004/robot-004.glb \
  --output generated/robot-004-review
```

Blender can import the GLB for art iteration, but is not part of the runtime or
deterministic build pipeline.
