# robot-004 GLB proof

`robot-004.glb` is the deterministic MR-112 true-3D mascot proof. It is built
from code so CI can compare the complete binary without requiring Blender.

Semantic nodes:

- `RobotRoot`, `Body`, `Head`, `Face`, `Antenna`
- `caption_anchor` for the later MR-113 2D caption compositor

Animation clips:

- `idle` — head sway and blink
- `hello` — arm wave and head response
- `hop` — translation plus squash/stretch
- `celebrate` — body/arm motion plus smile and wow morphs

Facial morph targets:

- `blink`, `smile`, `wow`, `squint`, `sad`, `cheek`

Regenerate or verify the asset:

```bash
python tools/generate_robot_glb.py --output examples/robot-004/robot-004.glb
python tools/generate_robot_glb.py \
  --output examples/robot-004/robot-004.glb --check
```

Blender can import the GLB for art iteration, but is not part of the runtime or
deterministic build pipeline.
