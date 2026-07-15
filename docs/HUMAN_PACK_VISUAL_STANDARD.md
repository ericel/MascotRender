# Human Pack Visual and Representation Standard

Status: normative production gate for `mascot-pack-human`. The procedural
human pilots in `examples/human-pilots` are technical fixtures and are not
production artwork.

The visual benchmark is the owner-supplied **Human Mascot Reference** dated
2026-07-15. It defines the expected level of anatomy, character specificity,
styling, diversity, expression, and small-size readability. Production assets
must be original and appropriately licensed; the benchmark is not itself a
source-art pack.

The project owner approved `art/concepts/human-pack-v1/family-gate-v1.png` on
2026-07-15 as the initial canonical family. H01, H04, H07, H12, and H13 now
establish the Human Character Library's family language, anatomical rules,
assistive-device integration, age diversity, and identity principles. The
versioned `human-canonical-family-v1` contract pins that decision. This family
is the foundation for future characters, not the complete library. H01's
inclusion is an approved Human Pack v1 editorial decision; it does not make
minor-coded characters an engine requirement or a requirement for other packs.

## Visual family

- friendly full-body characters with clear head, torso, articulated limbs,
  hands, and footwear;
- consistent stylized proportions, outline language, shading, palette behavior,
  facial construction, and material treatment across the pack;
- distinctive individuals rather than one body with palette and hair swaps;
- readable silhouettes and primary expression at 80, 96, and 100 pixels;
- controlled highlights and shadows that remain legible across complexions;
- neutral/rest artwork plus authored expressive poses that respect the rig;
- no accidental clipping, disconnected anatomy, layer dropout, or caption and
  accessory collisions.

The target family is approximately three-and-a-half to five stylized heads tall
depending on life stage and body design. This is a review range, not a formula
that forces every person into identical proportions.

## Supported identity dimensions and pack-specific coverage

MascotRender supports authored characters across the following dimensions.
This is a capability list, not a requirement that every Human Pack contain
every value:

- life stage: child, pre-teen, teen, young adult, adult, middle-aged, senior;
- body presentation: slim, average, curvy, plus-size, athletic, and at least one
  additional authored build that does not collapse into those labels;
- complexion: the complete approved 10-position tone scale and cool, neutral,
  olive, and warm undertones;
- hair: straight, wavy, curly, coily, protective styles, hair covering, short,
  long, and no-hair/bald presentations where appropriate;
- gender presentation: multiple feminine, masculine, and androgynous designs;
- ability: wheelchair user, prosthetic limb, visual-impairment representation,
  hearing aid, and a review-approved additional representation;
- clothing and context: casual, formal, generational, cultural, and occupation
  designs without treating clothing as proof of identity;
- expression and pose: happy, laughing, surprised, thinking, confident, sorry,
  excited, greeting, farewell, agreement, disagreement, gratitude, and concern.

Each pack declares its own editorial coverage goals and may validly target only
adults, only seniors, or another reviewed subset. Minor-coded characters are
optional. A pack that includes a child, pre-teen, or teen must record an
explicit owner/editorial approval and intended use; schema success cannot make
that decision. Coverage metadata exists for audit and selection. It must never
be inferred from an end user or converted into stereotyped geometry rules.

## Assistive technology and cultural details

Assistive devices are functional parts of the authored character and rig, not
decorative accessories that may disappear during animation. Wheelchair poses,
prosthetic articulation, cane contact, hearing-device visibility, and caption
clearance require device-specific review.

Cultural clothing, religious garments, hairstyles, names, occupations, and
gestures require review by people familiar with the represented context.
Generic labels such as `Asian`, `African`, or `Middle Eastern` are coverage
summaries, not sufficient art direction.

## Camera and text

Every production master must pass:

- face close-up;
- bust;
- three-quarter;
- full body;
- dynamic full body.

Caption placement supports top, bottom, left, right, speech-bubble, and
character-attached/hand-sign compositions when declared by the recipe. Shared
screen-space text remains independent of vector, layered, or GLB geometry.

## Required outputs and accessibility

Each pack declares supported output capabilities rather than implying support:

- PNG static;
- WebP static or animated;
- optional APNG, AVIF, Lottie, and GLB when implemented and validated.

Each phrase presentation requires exact text, locale, alternate text, motion
intent, and a reduced-motion behavior. Contrast, caption safe areas, alpha
bounds, animation loop closure, and flash/motion limits are automated gates.

## Production approval gates

An identity cannot be marked production-ready until it passes:

1. contract and provenance validation;
2. neutral-turnaround and required-framing review;
3. expression and pose review;
4. 80/96/100-pixel readability review;
5. complexion and contrast validation;
6. assistive-device/cultural-detail review where applicable;
7. animation playback and reduced-motion review;
8. diverse human review with named review roles and recorded disposition;
9. cross-backend identity parity for every backend claimed by the pack.

Schema success alone never grants visual approval.
