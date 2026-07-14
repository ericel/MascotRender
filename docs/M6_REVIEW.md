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

## Resubmission evidence

The canonical seed remains `20260713`. The resubmitted bundle contains five
packs, 50 stickers, 20 animated primary assets, and 100 WebPs. The review
builder must verify all asset hashes and report totals before the contact sheet
is inspected. Product/Design approval remains pending until review round 2.
