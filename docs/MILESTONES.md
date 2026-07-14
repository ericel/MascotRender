# MascotRender Milestones and Initial Backlog

## Delivery objective

Release an installable C++20 engine before scaling content production. The
first engineering release is successful when an unrelated Conan/CMake consumer
can load a small mascot pack and generate deterministic transparent WebP
assets. Product runtime integration and the 200-sticker pilot follow that
engine release.

Estimates are engineering days for one senior C++ engineer. Art work proceeds
in parallel and is called out where it becomes an exit dependency.

## Milestone summary

| ID | Milestone | Estimate | Release result |
|---|---|---:|---|
| M0 | Build and package bootstrap | 1-2 days | Consumer can install and link an empty library |
| M1 | First transparent sticker | 2-3 days | One hard-coded scene renders to WebP |
| M2 | Data-driven mascot pack | 3-4 days | JSON pack and sticker spec drive composition |
| M3 | Text, thumbnails, and validation | 3-4 days | Ten representative stickers render correctly |
| M4 | Batch compiler and manifests | 2-3 days | A versioned static pack is generated |
| M5 | Engine 0.1 hardening and release | 2-3 days | `mascotrender/0.1.0` is publishable |
| M6 | 50-sticker coherence gate | 1-2 weeks | Product and Design approve the art system |
| M7 | 200-sticker product pilot | 2-4 weeks | End-to-end chat pilot is releasable |

M0-M5 form the engine MVP. M6-M7 form the product pilot.

## M0: Build and package bootstrap

Goal: prove the distribution contract before implementing rendering.

### Backlog

- `MR-001` Create the C++20 CMake project and
  `MascotRender::MascotRender` build-tree alias.
- `MR-002` Add visibility/export macros and a generated version header.
- `MR-003` Add the Conan 2 recipe with `shared` and `fPIC` options.
- `MR-004` Add pinned dependencies and host/build lockfile workflow.
- `MR-005` Add CMake install/export/config/version rules.
- `MR-006` Add `test_package` as a separate consumer project.
- `MR-007` Add Catch2 unit-test target and CTest integration.
- `MR-008` Add CLI target with only `--help` and `--version` initially.
- `MR-009` Add Linux, macOS, and Windows Conan package smoke jobs.

### Exit criteria

- `conan create . --build=missing` succeeds from a clean cache/profile.
- `test_package` uses only installed/package artifacts.
- The consumer calls `mascotrender::version()` and links successfully.
- Static Release packages pass on Linux and macOS; Windows may be allowed as a
  documented M5 blocker if the initial CI environment is unavailable.

## M1: First transparent sticker

Goal: complete the smallest end-to-end graphics path.

### Backlog

- `MR-010` Define owned RGBA pixel-buffer and encoded-image types.
- `MR-011` Add internal `IRenderBackend` and ThorVG software implementation.
- `MR-012` Render a hard-coded layer stack into a 512 x 512 transparent buffer.
- `MR-013` Encode the buffer with libwebp using explicit settings.
- `MR-014` Add the in-memory `Engine::render` vertical-slice API.
- `MR-015` Add alpha, dimensions, and WebP decode smoke assertions.
- `MR-016` Store and verify one reviewed golden result.

### Exit criteria

- The external `test_package` produces a valid transparent WebP.
- No ThorVG, libwebp, or JSON header appears in the public include tree.
- Two consecutive renders in one pinned profile produce identical bytes.

## M2: Data-driven mascot pack

Goal: replace the hard-coded scene with the smallest useful content model.

### Backlog

- `MR-020` Define schema-versioned `pack.json` and sticker JSON formats.
- `MR-021` Implement structured diagnostics and the custom C++20 `Result<T>`.
- `MR-022` Load pack metadata and canonicalize all referenced paths.
- `MR-023` Load a restricted local SVG subset through ThorVG.
- `MR-024` Implement deterministic z-order and transform semantics.
- `MR-025` Implement named expression and pose layer overrides.
- `MR-026` Implement deterministic seed derivation and fixed PRNG.
- `MR-027` Reject missing references, duplicate IDs, traversal, and external URLs.
- `MR-028` Document the pack and sticker schemas with working examples.

### Exit criteria

- One JSON sticker spec and one example pack produce the M1 golden image.
- Changing a pose or expression changes only declared layers.
- Invalid references report file and JSON-path context.
- Variation tests do not depend on unordered iteration, time, or platform hash.

### Art dependency

The example pack must contain one original mascot, three expressions, two
poses, two effects, declared pivots/anchors, and provenance metadata.

## M3: Text, thumbnails, and validation

Goal: render a small representative content set with exact authored text.

### Backlog

- `MR-030` **Done:** load only pack-declared local static TTF files.
- `MR-031` **Done:** deterministic dynamic-programming balanced wrapping.
- `MR-032` **Done:** implement largest-valid whole-point font-size search with configured minimum.
- `MR-033` **Done:** configurable deterministic glyph outline with safe-area fitting.
- `MR-034` **Done:** render 512 x 512 main assets and 256 x 256 thumbnails.
- `MR-035` Validate dimensions, alpha, visible bounds, and encoded file size.
- `MR-036` Add `mascotrender validate`.
- `MR-037` **Done (engineering gate):** ten generated cases cover punctuation
  and long text; a decoded-pixel golden locks the reviewed example. Full
  Product/Design approval remains the M6 gate.

### Exit criteria

- Text is byte-for-byte equal to the authored Unicode string in metadata.
- All ten fixtures fit their declared frame or fail with a useful diagnostic.
- Fonts are loaded from the pack; platform font discovery is not used.
- Main and thumbnail assets retain transparency and expected dimensions.

### Art and legal dependency

One distributable font, minimum font sizes, maximum line counts, safe areas,
and text styles must be approved before this milestone can close.

## M4: Batch compiler and manifests

Goal: turn single-sticker rendering into a deployable versioned pack.

### Backlog

- `MR-040` **Done (MVP script):** build every sticker spec below a generated-pack directory.
- `MR-041` **Done:** generate `catalogue.json` with text, alt text, dimensions, byte sizes, paths, and hashes.
- `MR-042` **Done:** generate a case-folded full-phrase `dictionary.json`.
- `MR-043` **Partial:** enforce minimum trigger length, stop words, safe IDs, and declared word boundaries; product matcher tests remain.
- `MR-044` **Done:** generate deterministic structured `build-report.json`.
- `MR-045` **Done:** publish through staging with previous-bundle restoration on failure.
- `MR-046` **Done:** end-to-end test generates and byte-compares two 20-sticker/40-asset builds.

### Exit criteria

- A clean build produces the documented immutable directory layout.
- A failed render cannot leave a partially publishable pack.
- Trigger tests prove that `he` does not match inside `the` or `weather`.
- Output metadata contains stable IDs, exact text, alt text, locale, hashes,
  dimensions, and pack/schema versions.

## M5: Engine 0.1 hardening and release

Goal: publish a package other C++ applications can safely adopt.

### Backlog

- `MR-050` **Done:** public API documentation, release notes, and consumer example.
- `MR-051` **Done:** warning-clean GCC, Clang, AppleClang, and MSVC builds.
- `MR-052` **Done:** Linux Clang 18 ASan/UBSan suite passes in hosted CI.
- `MR-053` **Done:** MIT project license, dependency/font inventory, and notices
  are packaged.
- `MR-054` Pin Conan profiles, lockfiles, recipe revision, and dependency options.
- `MR-055` **Done for supported matrix:** static Release/shared Debug pass on
  macOS and hosted Linux; Windows static/shared Release pass. ThorVG's pinned
  recipe explicitly rejects MSVC Debug.
- `MR-056` **Done:** ten- and fifty-sticker local baselines are recorded.
- `MR-057` Tag and publish `mascotrender/0.1.0` to the approved Conan remote.

### Exit criteria

- All M0-M4 criteria pass in clean CI.
- Public headers are warning-clean and dependency-free.
- No unresolved blocker-level sanitizer, license, packaging, or golden failure.
- Release notes document supported profiles and the trusted-pack limitation.
- A second sample application can adopt the package using only its Conan
  requirement and `MascotRender::MascotRender`.

## M6: 50-sticker coherence gate

Goal: validate the procedural art system before scaling content production.

**Status: complete — Product/Design approval recorded 2026-07-14.**

Add CSV import, contact-sheet review, incremental caching, additional poses and
effects, and performance reporting as needed for the content workflow. Exit
requires Design and Product approval of a 50-sticker contact sheet and no
unresolved rendering or licensing failures.

The engine must not scale to 200 stickers until this gate passes.

Engineering result: the deterministic five-pack/50-sticker generator, renderer,
and full-bundle verifier are complete. The review tool produces an HTML contact
sheet, a 50-row per-sticker CSV checklist, and a machine-readable verification
summary; pull-request CI publishes the verified bundle as a review artifact.
The approved round-three bundle has no unresolved failures, and the project
owner approved the contact sheet and animation play-through.

Review round 1 requested alien/bunny differentiation, normalized headroom,
caption/accessory clearance, and bottom mask safety. Round 2 confirmed those
improvements but rejected per-species collision patches and the alien's separate
visual system. Generator v6 and the engine layout now use selected-layer
collision bounds, actual fitted-glyph overlap, one general clearance rule, and
a shared silhouette family. The animation reviewer also exposes all four motion
presets side by side and a loop-seam regression protects playback. Round 3
Product/Design review approved the corrected bundle, closing the gate.

## M7: 200-sticker product pilot

Goal: integrate the generated pack into Drogon delivery and React local
suggestion matching.

This milestone includes immutable CDN paths, ETags, rollback, local trailing
phrase extraction, deterministic ranking, MLS attachment metadata, receiving
client fallback, content QA, and pilot telemetry under an approved privacy
policy.

## Engine expansion track: animation, 2.5D, and 3D

This track may proceed after the 0.1 static contract is stable. It must preserve
the small default package and is detailed in `ROADMAP_3D_ANIMATION.md`.

### E1: Layout and scene foundations — 4-7 days

- `MR-080` **Done:** backward-compatible named text slots and explicit placement.
- `MR-081` **Done:** deterministic preference-based auto slot selection.
- `MR-082` **Done for rectangle regions:** authored avoid regions and
  deterministic overlap scoring. Alpha/path occupancy remains future work.
- `MR-083` Add internal parented scene nodes with position, rotation, scale,
  opacity, pivot, and depth; static output is the `t = 0` compatibility test.
- `MR-084` Add screen-fixed and character-anchor text placement.
- `MR-085` Add optional per-sticker caption offset, rotation, and authored
  placement without changing automatic collision handling.

### E2: Animated current 2D packs — 7-10 days

- `MR-090` **Done for scalar overlays:** typed internal keyframes, fixed easing
  formulas, and once/loop/ping-pong/hold-last loop policies.
- `MR-091` **Done:** deterministic frame sampling with bounded FPS, duration,
  and frames.
- `MR-092` **Partial:** body-bounce and text-pop overlays are complete; blink
  and sparkle remain future additions.
- `MR-093` **Done:** deterministic animated WebP encoder plus static poster
  thumbnail mode.
- `MR-094` Add per-sticker text slide, bounce, and pulse presets with animation
  goldens. Treat Lottie as a separate optional export decision.

### E3: Layered 2.5D — 10-15 days

**Status: E3 complete; MR-100 through MR-102 are done.**

- `MR-100` **Done:** parented mascot parts, named pivots, inherited affine
  transforms/opacity/depth, deterministic parallax, transformed collision
  bounds, and identity fast-path compatibility.
- `MR-101` **Done:** bounded typed node/view keyframes provide squash/stretch,
  delayed child follow-through, responsive shadows, and camera parallax while
  preserving the flat `t = 0` poster.
- `MR-102` **Done:** Product/Design approved the corrected robot hop on
  2026-07-14. The accepted lossless animated WebP, metadata, timestamps, and
  decoded RGBA frames are locked by the animation golden test.

### E4: Optional Filament/GLB proof — 15-25 days plus art

- `MR-110` **Done:** Optional Conan/CMake Filament feature with no default
  dependency. Hosted macOS arm64 package-consumer coverage is also restored.
- `MR-111` **In progress:** The checksum-pinned official Filament binary
  wrapper, macOS Metal lifecycle test, bounded GLB v2 loader, and semantic
  anchor validation are implemented. A headless RGBA proof now exercises a
  fixed orthographic camera and hard toon-style key light. Linux/Windows
  wrapper validation and final remote publication remain.
- `MR-112` One robot with four clips and six facial morph targets.
- `MR-113` Same-recipe 2D/2.5D/3D proof with 2D caption compositing.

## First execution batch

Start these items immediately:

1. `MR-001` through `MR-006` as the critical engineering path.
2. `MR-009` CI profiles in parallel with the package recipe.
3. The M2 example-pack art dependency in parallel with M0.
4. Font licensing and text-limit decisions before M3 begins.

Do not add Filament until the sampled-scene/timeline contracts and animated 2D
tests pass. The M6 coherence gate has passed; any scale-up to 200 stickers now
belongs to the separately controlled M7 pilot.

## Project controls

- Every backlog item must have an owner, acceptance test, and linked milestone
  before work begins.
- A milestone closes only when its exit criteria pass in CI; percentage complete
  is not an exit criterion.
- Changes to public API, pack schema, renderer, package target, or determinism
  rules require a recorded decision in `docs/DECISIONS.md`.
- Golden files may change only with an intentional art/renderer version change
  and review evidence.
- Estimates are re-baselined after M1 and after the M6 coherence review.
