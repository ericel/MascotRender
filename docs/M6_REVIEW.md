# M6 sticker review record

## Review round 1 — 2026-07-14

Decision: changes requested. The shared visual language was accepted, but the
bundle was not approved because character differentiation, framing, and caption
placement needed correction.

| Finding | Disposition in generator v5 |
| --- | --- |
| Alien read as a purple bunny with antennae | Alien now has a teal/pink palette, narrower oval silhouette, three-eye expression rig, forehead markings, cheeks, and no muzzle. |
| Character headroom was inconsistent | Cat, bear, bunny, robot, and alien top accessories now occupy a normalized 64–78 px top band on the 512 px canvas. |
| Alien and robot antennae crossed top captions | Both packs declare antenna avoid regions and generated stickers offer only the bottom caption slot. |
| Bottom captions were too close to platform masks | The bottom slot is inset to `y=376, height=88`, ending 48 px above the 512 px canvas edge. |
| Per-phrase angled or off-center captions | Deferred to `MR-085`; this is an authored placement feature, not part of the collision fix. |
| More expressive chat-style text motion | Deferred to `MR-094`; animated WebP text presets and goldens are separate from static layout correction. |

## Review round 2 — 2026-07-14

Decision: changes requested. Alien/bunny differentiation and the original
alien/robot caption collisions improved, but the correction exposed two root
problems: cat, bear, and bunny retained the same accessory collision, and the
redesigned alien no longer belonged to the shared visual family. Animation
files were genuine animated WebPs, but their playback quality had not yet been
reviewed.

| Finding | Disposition in generator v6 and engine layout |
| --- | --- |
| Caption collision was patched per character | Every selectable body/pose layer now declares collision bounds. The engine expands selected bounds by a pack-wide clearance, scores the actual fitted glyph rectangle including outline, and applies the same rule to all species. Generator v6 contains no species-specific caption preference. |
| Cat, bear, and bunny ears still crossed captions | The general selected-layer rule covers ears, antennae, and body silhouettes. A direct C++ regression proves automatic placement matches the collision-free slot, while the 5 × 3 review matrix covers `hello`, `lets-go`, and `well-done` for every species. |
| Alien broke pack coherence | Alien returns to the shared rounded-square body and muzzle/face construction. Teal, antennae, and a three-eye rig retain its identity without a separate oval/blush/freckle visual system. |
| Animation quality was not reviewed | The reviewer now produces `animation-review.html`, playing all four animated phrases side by side per mascot. Frame inspection found and fixed an abrupt caption reset; repeating timelines now finish at their starting state with an explicit fade-out. |

## Round 3 resubmission evidence

The canonical seed remains `20260713`. The resubmitted bundle contains five
packs, 50 stickers, 20 animated primary assets, and 100 WebPs. The review
builder verifies all asset hashes and report totals before either gallery is
opened. All 24 local CTest cases pass, including the engine-level collision and
loop-seam regressions. Product/Design approval remains pending until review
round 3; this record does not self-approve M6.
