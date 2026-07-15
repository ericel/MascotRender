# Human Pack v1 Art Brief

Status: front-facing five-master vector foundation approved; current turnaround,
dimensional 2.5D proof, and GLB production conversion rejected on 2026-07-15.

## Goal

Create an original full-body character family at the quality and breadth of the
owner-supplied Human Mascot Reference while preserving MascotRender's authored,
deterministic, backend-independent contracts.

The pack should feel warm, contemporary, expressive, and readable in messaging
at 80–100 pixels, while retaining enough structure for education, healthcare,
games, assistants, and enterprise applications.

## Asset model

Do not create one combinatorial person generator that freely mixes every body,
face, hair, garment, culture, and device. Human Pack v1 uses curated master
identities:

- each master owns recognizable facial construction, complexion materials,
  hair, body proportions, neutral wardrobe, rig constraints, and review record;
- reviewed wardrobe or occupation presentations are variants of that identity;
- assistive devices are identity/rig features with functional motion rules, not
  removable costumes;
- expressions, gestures, camera framing, captions, and effects come from shared
  semantic recipes;
- cultural presentation is authored and reviewed in context rather than derived
  from a broad heritage label.

## Candidate expansion cohort

The approved foundation contains H01, H04, H07, H12, and H13. The following
slots are an editorial planning pool, not an engine requirement, a minimum pack
size, or a promise to produce every row. Names and cultural details are
finalized with appropriate reviewers.

| Slot | Life stage | Body direction | Presentation/technical emphasis |
|---|---|---|---|
| H01 | child | average | Black girl; coily protective hairstyle; energetic greeting |
| H02 | pre-teen | slim | Deferred: requires separate owner/editorial approval before concept production |
| H03 | teen | athletic | Deferred: requires separate owner/editorial approval before concept production |
| H04 | young adult | athletic | Black man; prosthetic lower limb with articulated hop rules |
| H05 | young adult | average | Middle Eastern woman; reviewed modest clothing and head covering |
| H06 | adult | curvy | Latina woman; curly hair; confident and professional variants |
| H07 | adult | average | Southeast Asian man; wheelchair and seated gesture rig |
| H08 | adult | plus-size | mixed-heritage androgynous person; contemporary streetwear |
| H09 | adult | slim | South Asian man; formal and casual variants |
| H10 | adult | athletic | Black woman; sport and casual variants |
| H11 | middle-aged | broad | White man; visual-impairment presentation and cane contact rules |
| H12 | middle-aged | average | East Asian woman; visible hearing aid and conversation poses |
| H13 | senior | soft | Black woman; natural grey hair and mobility-support review |
| H14 | senior | average | White man; glasses, facial hair, and distinct generation styling |

The eventual v1 editorial selection should state its chosen tone and undertone
coverage, but it is not required to exhaust every engine-supported dimension.
No identity exists only to fill a checkbox: each needs a name, personality
note, neutral design, and equal expression/animation quality.

## Visual construction target

- approximately 3.5–5 stylized heads tall depending on age/body design;
- large readable head and eyes without collapsing everyone to one face rig;
- clear neck, torso, upper/lower limbs, hands, and footwear;
- expressive eyebrows, eye shapes, nose construction, mouth and cheek language;
- consistent outline hierarchy and soft two- or three-tone shading;
- separated hair front/back, face, hands, garment panels, limbs, footwear,
  devices, and effects for rigging;
- hands designed for open wave, point, clasp, thumbs-up, fist, and relaxed poses;
- neutral silhouettes remain identifiable without captions or color.

At a 512-pixel authoring canvas, the concept target begins with 4–7-pixel
primary outlines and 2–4-pixel interior detail. These values are tuned after
80/96/100-pixel reduction tests rather than treated as universal constants.

## Required source delivery per master

1. front neutral character and palette/material sheet;
2. front, three-quarter, side, and back turnaround;
3. normalized joint/pivot overlay and ground-contact definition;
4. face sheet for the required expressions;
5. hand/gesture sheet;
6. rest, greeting, farewell, agreement, disagreement, gratitude, concern,
   surprise, and celebration poses;
7. all five camera-framing previews;
8. 80/96/100-pixel readability strip;
9. assistive-device behavior sheet where applicable;
10. provenance, license, accessibility alt text, and review metadata.

Production source is layered SVG for vector/layered output plus a semantic GLB
for every claimed 3D identity. Raster concept art is acceptable for review but
is not the final rig source.

## Concept approval rule

The project owner approved the front-facing family language represented by H01,
H04, H07, H12, and H13 on 2026-07-15. Their canonical contract governs future
human designs. The first generated turnaround and GLB conversion failed the
production design gate and remains useful only as a technical prototype. A
replacement must rotate the complete character/device hierarchy, preserve
identity and device topology in every view and backend, demonstrate real 2.5D
depth behavior, and receive a new artifact-bound owner approval. New cohort
members must meet that bar without copying the canonical identities.
