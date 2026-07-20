# Micro Reactions

Micro Reactions is MascotRender's first text-free, face-dominant product pack.
It is deliberately separate from the human phrase matrix: the shared reaction
semantics provide search and selection consistency, while every identity owns
its silhouette, secondary anatomy, temperament, effects, and motion
performance.

The product cohort contains six engine packs and ten reactions per identity:
60 animated stickers plus 60 static reduced-motion equivalents. The canonical
delivery canvas is 512 by 512 pixels, with explicit reviews at 80, 100, and 160
pixels.

The screenshots used during product planning are market references only. No
third-party character, silhouette, pose, prop arrangement, lettering, or
composition may be reproduced. Source artwork generated for this pack is
original SVG and distributed under the project MIT license after owner
activation.

## Milestone gates

1. Owner review of the six vector identities and ten-reaction matrix.
2. Animation playback and reduced-motion parity.
3. Layered 2.5D depth, parallax, and responsive-shadow review.
4. Styled GLB parity for the selected identity proof.
5. Owner production activation and immutable bundle publication.

The owner approved the six vector identities, all ten reaction semantics, the
controlled 6 × 10 × 3 small-display evidence, animated reaction structure, and
Orbit layered-depth proof on 2026-07-20.

The correction pass keeps `proud` and strengthens it with upward brows, lifted
cheeks, an asymmetric confident smile, and an achievement medallion. Controlled
review sheets now show every identity and every reaction independently at 80,
100, and 160 pixels. Orbit is the first volumetric proof and carries nine
independent 2.5D depth layers plus a deterministic styled GLB with `idle`,
`orbital-tilt`, and `proud` clips.

The owner conditionally approved Orbit's dimensional GLB architecture,
semantic structure, palette and outline transport, deterministic generation,
and all three animation loops on 2026-07-20. A focused source-geometry
correction now narrows the eyes, restores the composed proud gaze, smooths the
brows, compacts the smile, restrains the blush, and joins the curved antenna
continuously to the head. That correction remained blocked from production
until the owner reviewed the regenerated final face-parity evidence.

The owner approved `micro-orbit-004-final-glb-face-parity-review-v1` on
2026-07-20. Orbit is now the production-approved selected styled-GLB reference
for cross-backend identity, semantic expression, outline and palette
transport, animation, reduced motion, small-display readability, and
deterministic generation. This approval activates Orbit as a reference proof;
the five remaining identities and the complete Micro Reactions pack still
require their own styled-GLB and final-pack gates.

The family expansion now has deterministic styled GLB candidates for Sprig,
Cinder, Ripple, Crumb, and Mallow. Each candidate retains the approved proud
facial language while preserving identity-specific anatomy and motion:
`leaf-sway`, `ember-flicker`, `gill-ripple`, `snack-bounce`, and `puff-float`.
The six-identity evidence includes approved Orbit as the reference row,
cross-backend proud comparisons, three real clips per new GLB, reduced-motion
equivalents, and 80/100/160-pixel profiles. These five new GLBs remained
forbidden for production while
`micro-reactions-styled-glb-family-expansion-v1` awaited owner review.

The owner approved that family expansion gate on 2026-07-20. The exact five
GLB hashes, six-character review sheets, signature-motion evidence, loop
closure, reduced-motion equivalents, and small-display profiles are bound in
`micro-reactions-styled-glb-family-owner-approval-v1.json`. The approved
display guidance is 100 pixels by default, 80 pixels as the minimum stress
floor, and 160 pixels for comfortable showcase presentation. The remaining
gate is final activation of the complete Micro Reactions product bundle.

## Production bundle candidate

Build the complete storage-neutral source bundle:

```bash
python3 tools/build_micro_reactions_bundle.py --force
```

Validate and content-address it:

```bash
python3 tools/mascot_bundle.py validate \
  --bundle generated/micro-reactions-production-bundle
python3 tools/mascot_bundle.py stage \
  --bundle generated/micro-reactions-production-bundle \
  --output generated/micro-reactions-production-distribution \
  --channel micro-reactions-stable \
  --force
```

The candidate contains 60 animated WebPs, 60 static reduced-motion
equivalents, 60 static thumbnails, and the six approved styled GLBs. The
semantic dictionary remains independent of identity selection, so consumers
can compile its reaction intents into a Trie and choose a character after the
match. `micro-reactions-final-pack-owner-decision-template-v1.json` binds the
immutable candidate hashes; publishing the channel remains blocked until that
last owner-activation decision is approved.
