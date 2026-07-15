# Human Pack Production Recovery Plan

Status: recovery complete. Original production candidate rejected by the project owner on
2026-07-15. The first corrected candidate received partial approval for
expressions, vector poses, layered identity, and front-view GLB identity. The
next candidate corrected every remaining gate and received an owner decision
bound to its exact hashes. Human Pack v1 is approved for public release.

## Failure diagnosis

The rejected pipeline confused technical execution with visual design quality.
File validity, distinct hashes, palette pixels, semantic-node counts, animation
counts, and broad silhouette aspect ratios prove that an asset loads and moves.
They cannot prove that it preserves an authored face, age, body, hairstyle,
garment, pose meaning, or assistive-device topology.

The current candidate must not be patched by loosening proportions or adding
more primitive shapes. Its turnaround and GLB authoring approach is the wrong
production method.

## Production approach

All five canonical identities remain in scope. Work proceeds identity by
identity only to keep review defects local; this sequencing does not reduce the
release scope.

1. Freeze the approved front-facing 2D master and identity landmarks.
2. Author front, three-quarter, side, and back vector views as complete views.
   Do not synthesize them by translating the head, face, or hair independently.
3. Bind hair, clothing, limbs, and assistive devices to one character-space
   hierarchy and prove attachment continuity in every view.
4. Author all nine required pose families explicitly: rest, greeting, farewell,
   agreement, disagreement, gratitude, concern, surprise, and celebration.
5. Refine expression semantics independently of pose. Thinking, confident, and
   sorry require their own gaze, brow, mouth, head, and posture rules.
6. Build a genuine layered 2.5D rig with visible Z separation, parallax,
   overlap changes, shading, responsive contact shadow, and accessory or hair
   follow-through during motion.
7. Retarget the approved identity to an authored 3D model using Blender or an
   equivalent production DCC. The deterministic Python GLB primitive generator
   remains a loader/animation fixture only.
8. Preserve device construction as functional topology, not named placeholder
   nodes: prosthetic socket/pylon/foot, wheelchair wheel/pushrim/frame/seat/
   backrest/footrest/casters, hearing-aid case/tube/earpiece, and rollator
   frame/handles/four wheels/hand and ground contacts.
9. Render the complete review matrix and bind the sheet SHA-256 values to a new
   project-owner production-design decision.
10. Repeat for all five identities before declaring cross-backend release.

## Required visual evidence

The next review bundle must contain separate sheets for:

- four-view turnarounds at a common scale;
- nine named pose families, without expression labels standing in for poses;
- seven named expressions on a common neutral pose;
- 80/96/100-pixel readability;
- 2.5D rest, parallax-left/right, and motion midpoint with responsive shadows;
- flat/vector, layered 2.5D, and GLB identity parity;
- per-device front, three-quarter, side, and back topology;
- animated playback and reduced-motion alternatives.

## Production gate rules

- Automated validation may report `technical-validation-success`.
- Automated validation must never issue owner visual approval.
- A candidate without a design decision bound to its exact review-sheet hashes
  is `awaiting-owner-production-design-review` and `production_use: forbidden`.
- A rejected or partially approved bound decision is `release-blocked` and
  remains forbidden.
- Public release requires both technical gates and an explicit approved bound
  owner decision with no unresolved visual or representation blocker.

Cross-backend review has two non-substitutable levels. Identity parity requires
the same character, defining hair/garment/device features, palette, age, and
body direction. Art-direction parity additionally requires the shared navy
silhouette language, two-to-three-tone cel treatment, facial line language, and
comparable garment detail. Public production parity requires both levels.

## Final backend disposition

| Backend | Current status |
|---|---|
| Flat 2D front-facing identity | Public-release approved |
| Layered 2.5D identity | Public-release approved, including depth and motion |
| Turnarounds | Public-release approved across four views |
| GLB loading and clip execution | Technically validated and public-release approved |
| GLB identity parity | Public-release approved for all five identities |
| GLB art-direction parity | Public-release approved for Human Pack v1 |
| Animation/reduced motion | Public-release approved; all five pairs locally decoded and loop-checked |
| Public production use | Approved and activated |
