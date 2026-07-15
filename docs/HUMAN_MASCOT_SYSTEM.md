# Human Mascot Identity and Representation System

Status: technical fixture pipeline implemented; production Human Pack artwork
not yet authored.

The owner-supplied Human Mascot Reference dated 2026-07-15 supersedes the
procedural pilot contact sheets as the visual target. The source matrix and its
generated art remain test fixtures for determinism, schema, rig, phrase,
camera, and packaging coverage. They are not candidates for production
approval. The normative production gate is `HUMAN_PACK_VISUAL_STANDARD.md`.

## Product boundary

MascotRender does not model race as a rendering enum. Race and ethnicity are
social identities and cannot be reduced to a skin swatch or one facial
template. The human contract therefore separates:

- complexion tone, undertone, reference base, highlight, and shadow colors;
- normalized facial proportions and independent feature profiles;
- hair texture, silhouette/style, and material colors;
- height class, build, shoulder ratio, and hip ratio;
- clothing colors, presentation, and accessories;
- editorial heritage context used only for representation audits.

Every identity declares `representation.rendering_source` as
`appearance-only`. The generator never branches on heritage labels. This makes
palette swaps insufficient by design while also preventing stereotypes from
becoming renderer logic.

## Normalized full-body rig

`humanoid-full-body-v1` defines one parented root/hips/torso/head/limb topology,
named pivots, semantic targets, and capability declarations. Motion recipes use
targets such as `root`, `head`, `gesture.primary`, and `gesture.secondary`.
Each pose binds those semantics to selected layer IDs before a normal sticker
document reaches the C++ engine.

The same architecture can retarget future 2.5D or GLB humans. A missing
capability must fail compilation or select an explicitly declared fallback; it
must never silently drop a gesture.

## Semantic camera framing

Sticker-size readability requires more than a full-body camera. Recipes choose
one of five engine-supported framings:

- `face-closeup` for firm, confused, or suspicious reactions;
- `bust` for greetings, laughter, surprise, and affection;
- `three-quarter` for agreement, gratitude, apology, and pleading;
- `full-body` for readable whole-body gestures;
- `dynamic-full-body` for energetic movement.

The engine scales character-space layers around a named pack anchor. Captions
remain screen-fixed and collision bounds receive the same transform.

## Pilot coverage

The source matrix contains 12 synthetic identities and deliberately spans all
ten complexion scale positions, cool/neutral/olive/warm undertones, straight,
wavy, curly, coily, and covered hair, multiple face profiles, all supported
height classes, and five body builds. It includes editorial Black, White, East
Asian, South Asian, Southeast Asian, Middle Eastern/North African, Latina, and
mixed-heritage contexts without using those labels as geometry inputs.

This matrix is a coverage instrument, not proof of respectful representation.
It is deliberately marked `technical-fixture` with production use forbidden.
New original production artwork requires reviewers from represented contexts.
Review must check:

- recognizable but non-stereotyped facial and hair silhouettes;
- complexion lighting that is neither washed out nor muddy across backends;
- equal phrase, pose, and animation quality across every identity;
- hair, clothing, limb, caption, and canvas collision safety;
- readability at 80–100 px and in each semantic camera framing;
- respectful names, metadata, clothing, and cultural presentation.

The contact-sheet builder uses Pillow, matching the existing 3D/identity review
tools. Contract generation and C++ rendering remain standard-library/C++ only;
CI environments without Pillow skip only contact-sheet composition, not the
identity, rig, recipe, deterministic generation, or rendered-bundle gates.

## Scale strategy

The phrase Trie remains independent of appearance:

```text
typed words → phrase ID → recipe ID → selected mascot → immutable asset
```

Terminal Trie nodes contain phrase IDs, not every mascot rendition. Generate a
small universal pack when a mascot is created, generate extended phrases for
approved/popular mascots, and render the long tail on demand into immutable,
content-addressed bundles. This prevents thousands of mascots from multiplying
the matching index or forcing clients to download a global asset catalogue.
