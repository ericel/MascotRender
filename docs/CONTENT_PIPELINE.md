# Mascot content pipeline

MascotRender ships three standard-library Python scripts around the C++20 engine.
They are deterministic build tools; applications still consume the C++ library
through Conan and `MascotRender::MascotRender`.

## 1. Generate mascot packs

From a source checkout:

```bash
python3 tools/generate_mascot_packs.py \
  --output generated/mascots \
  --count 5 \
  --seed 20260713 \
  --force
```

This produces five identities—cat, bear, bunny, robot, and alien—with ten
stickers each. Every pack contains:

- deterministic SVG layers;
- front and round poses;
- happy, sleepy, and surprised expressions;
- seeded left/right effects;
- ten English/Pidgin phrases with punctuation and longer text;
- named top/bottom slots, avoid regions, and four animated phrases per mascot;
- a shared rounded-square body/muzzle family with species-specific accessories
  and palettes; alien remains distinct through teal, antennae, and three eyes;
- selected-layer collision bounds, one pack-wide clearance buffer, automatic
  caption placement with no per-species overrides, normalized accessory
  headroom, and a 48 px bottom safe-area inset;
- the approved pack-local Changa One static TTF and complete OFL license;
- a schema-v1 `pack.json` and ten sticker JSON specifications.

`generation-manifest.json` records the generation version, seed, identities,
palette values, font hash, and counts. The same inputs produce byte-identical
pack directories.

## 2. Build the sticker bundle

```bash
python3 tools/render_mascot_packs.py \
  --input generated/mascots \
  --output generated/bundle \
  --mascotrender build/Release/mascotrender \
  --force
```

The batch builder validates every pack/sticker pair through the CLI, renders a
512 x 512 static or animated WebP and a 256 x 256 static poster thumbnail, and
publishes through a staging directory. A failed command removes staging and
cannot replace the last successful bundle.

The bundle contains:

```text
bundle/
  assets/<pack-id>/<sticker-id>.webp
  thumbnails/<pack-id>/<sticker-id>.webp
  catalogue.json
  dictionary.json
  build-report.json
```

`catalogue.json` contains exact authored text, alt text, expression, pose, seed,
animation metadata, dimensions, byte size, relative paths, and SHA-256 hashes. `dictionary.json`
contains case-folded full-phrase triggers and declares Unicode word-boundary
matching so a trigger cannot match inside a larger word. Repeated phrases across
mascot identities intentionally map to a stable ordered list. `build-report.json`
records deterministic counts, settings, and total encoded bytes; it contains no
wall-clock timestamps.

## 3. Verify and review all stickers

```bash
python3 tools/build_sticker_review.py \
  --input generated/bundle \
  --expected-count 50 \
  --force
```

Open `generated/bundle/review/index.html`. It shows every thumbnail grouped by
pack, labels animated assets, and links each card to its full-size static or
animated WebP. Open `animation-review.html` to play the four animated phrases
side by side for every mascot. Complete `checklist.csv` with `pass`, `fail`, or
`n/a` for every criterion and an `approve` or `revise` decision for every
sticker.

The review builder does not trust the catalogue blindly. Before writing the
gallery it verifies every relative path, byte count, SHA-256 hash, WebP header,
animation flag, static poster thumbnail, and build-report total. Its
`review-summary.json` records the verified bundle hashes and leaves the formal
status at `awaiting_design_product_approval`.

The pull-request workflow regenerates the canonical 50-sticker bundle and
publishes it as the `mascotrender-50-sticker-review-<commit>` artifact for 14
days. Download it from the workflow run and open `review/index.html` locally.

## Custom runs

- `--count` accepts 1 through 50 identities.
- `--seed` accepts an unsigned 64-bit integer.
- `--width`, `--height`, `--thumbnail-size`, `--quality`, and `--lossless`
  control bundle rendering. Animated main assets always receive static poster
  thumbnails through the engine's first-frame-only option.
- The review builder accepts `--expected-count` to turn a missing or extra
  sticker into a hard failure.
- Omit `--force` in automation when overwriting an existing result should be an
  error.

The generator currently owns five geometric species templates. Add a new
species by extending `SPECIES` and `body_layer()` while keeping layer IDs and
the pack schema stable. Content intended for release still requires design and
product review; procedural output does not by itself close the M6 art gate.

## Human full-body pilot pipeline

Human mascots use four independent, versioned inputs:

- `examples/human-pilots/identities.json` — 12 curated appearance contracts;
- `contracts/humanoid-full-body-v1.json` — normalized joints, semantic targets,
  capabilities, and camera framings;
- `content/motion-recipes-core-v1.json` — 12 reusable motions that target the
  semantic rig rather than mascot-specific layers;
- `content/phrase-lexicon-core-v1.json` — captions, categories, emotions,
  locale-aware triggers, match policies, minimum typed lengths, and recipes.

The current procedural human generator is a deterministic engineering fixture,
not the production Human Pack art pipeline. Its output is forbidden from
production use. Production human sources must conform to
`HUMAN_PACK_VISUAL_STANDARD.md`, carry explicit provenance and licenses, and
pass the recorded human review gates before packaging.

`generate_human_pilots.py` compiles semantic targets to the selected concrete
arm/head/root layers for every pose. The normal C++ loader then validates and
renders those tracks. Heritage context is copied only to the identity/audit
record; generated geometry reads complexion, face, hair, body, and presentation
attributes and never branches on race or heritage labels.

The default pilot produces 12 identities × 12 core phrases = 144 sticker
specifications. Use `build_human_pilot_review.py` to create one 12-character
contact sheet per phrase. The verifier checks source counts, non-empty alpha
bounds, visible reference complexion pixels, deterministic hashes, and complete
identity/phrase coverage. Success proves the fixture pipeline only; it cannot
approve or promote the generated visuals.

## Canonical human technical-art review

The owner-approved H01/H04/H07/H12/H13 concept is translated into deterministic
semantic SVG production-review candidates with:

```sh
python3 tools/generate_canonical_human_masters.py --force
python3 tools/build_canonical_human_review.py --force
```

The generator writes a layered master, pack, identity, source manifest, and
five framing specifications per character under `art/human-pack-v1/masters`.
The production-v2 humanoid rig binds the prosthetic socket/pylon/foot,
wheelchair wheels/pushrims/frame/footrest, hearing-aid case/tube/earpiece, and
rollator frame/handles/four wheels as separately addressable semantic parts.
The reviewer renders 25 canonical 512-pixel posters and nine review sheets. In
addition to the sticker-fit framing matrix it emits a same-world-scale lineup,
true 80/96/100-pixel outputs, 19 isolated semantic device parts, labeled
anchors/pivots/contact points, and four animated device-motion checks. The C++
renderer selects 12 authored 100-pixel LOD layers for prosthesis, wheelchair,
hearing-aid, and rollator readability instead of merely downsampling the base
SVGs. The rig and regression fixtures define left/right anatomically; character
right projects to screen-left in an unmirrored front view.

The project owner approved vector identity parity for all five masters on
2026-07-15, explicitly including H07's seated pose and footrest relationship.
The front-facing vector family remains an approved foundation. The current
turnaround and GLB candidate is owner-rejected and `production_use: forbidden`.
Automated checks prove valid files, rendering, palettes, clip execution, and
semantic nodes; they do not prove authored identity or device parity. The
artifact-bound decision and blocking findings are recorded in
`generated/canonical-human-production-review/release-review.json`.
