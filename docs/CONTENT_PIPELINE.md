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
- a species-specific primary palette and silhouette; alien additionally uses a
  narrow oval body and a three-eye expression rig;
- normalized accessory headroom, antenna-aware bottom-only captions for alien
  and robot, and a 48 px bottom safe-area inset;
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
animated WebP. Complete `checklist.csv` with `pass`, `fail`, or `n/a` for every
criterion and an `approve` or `revise` decision for every sticker.

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
