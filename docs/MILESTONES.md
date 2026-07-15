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
- `MR-111` **Done:** The checksum-pinned official Filament binary wrapper,
  bounded GLB v2 loader, and semantic anchor validation are implemented. Native
  CI validates macOS arm64, Linux x86-64, and Windows x86-64 packages. Metal and
  Linux Vulkan execute the headless RGBA proof; hosted Windows validates MSVC
  compile/link, archive integrity, the NOOP runtime, and backend-neutral paths
  without claiming unavailable GPU coverage. Wrapper and Filament-enabled
  MascotRender binaries are published, and logged-out exact-package
  `--build=never` re-downloads passed on all three platforms on 2026-07-14.
- `MR-112` **Done:** Deterministic `robot-004.glb`, semantic anchors,
  `idle`/`hello`/`hop`/`celebrate` clips, six named facial morphs, animation
  sampling, and review generation are implemented. The failed placeholder-art
  review was corrected with the approved rounded-square silhouette and palette,
  curved facial language, pivoted arms, independent hop shadow, deterministic
  white PNG/contact sheet generation, and orientation/palette guards.
  Product/Design approved the corrected static visual gate on 2026-07-14. Four
  real 13-frame looping WebPs, a browser playback page, a five-sample motion
  sheet, decoded-frame hashes, non-static-motion checks, and exact loop-closure
  checks now cover the remaining timing caveat. Hosted Filament validation and
  Product/Design accepted the animated playback proof on 2026-07-14; the later
  MR-116 decoded-frame audit supersedes only its export-size and shadow-evidence
  claims while leaving the approved static design unchanged.
- `MR-113` **Done:** One backend-neutral caption resolver now owns fitting,
  collision scoring, safe-slot selection, and line coordinates. Flat 2D and
  layered 2.5D produce byte-identical captioned posters, while Filament
  composites the same transparent screen-space caption over the real GLB frame.
  Tests and a reproducible three-backend review sheet lock the boundary.
- `MR-114` **Done:** A versioned `robot-004` identity contract now owns the
  exact palette, required features, and six normalized proportions shared by
  flat 2D, layered 2.5D, and GLB. Validation independently measures actual SVG
  and GLB data, the GLB generator derives its geometry from the contract, and
  a reproducible review sheet proves stronger still-frame 2.5D separation
  without changing the flat `front` compatibility pose.
- `MR-115` **Done:** Identity contract v2 locks antenna continuity and three
  antenna ratios, four eye ratios, orange-frame/inset-body structure, and one
  anchored screen-space sparkle rule. The GLB no longer owns sparkle geometry;
  all three backends composite the same SVG bounds, verified unchanged across
  near and far 3D camera spans.
- `MR-116` **Done:** Every robot GLB sample and animated
  WebP now has a mandatory 512 x 512 canvas. The review verifier measures the
  actual translucent contact-shadow ellipse in every decoded hop frame instead
  of inferring shadow response from character motion. Acceptance requires at
  least 30% contraction in both width and pixel area, a stable horizontal
  center, distinct bounds in frames 0/3/6/9/12, and exact loop closure.
  Product/Design approved the corrected playback bundle on 2026-07-14.

## H1: Human identity and full-body technical fixture

**Engineering status: implemented locally. Product status: permanently a
technical fixture; production use forbidden.**

- `MR-120` **Done:** Versioned human identity schema separates complexion
  material, undertone, face, hair, body, presentation, and audit-only heritage
  context. All 12 pilots declare `rendering_source: appearance-only`.
- `MR-121` **Done:** `humanoid-full-body-v1` defines 15 normalized joints,
  semantic gesture/root/head targets, capabilities, and five camera framings.
- `MR-122` **Done:** The C++ scene loader applies bounded semantic camera
  framing around authored anchors while keeping captions screen-fixed and
  transforming collision bounds consistently.
- `MR-123` **Done:** Twelve core semantic motion recipes compile to selected
  concrete layers, close their loops, and preserve phrase/recipe/camera metadata
  in bundle catalogues.
- `MR-124` **Done:** Twelve curated pilot identities generate 144 full-body
  sticker specifications deterministically. Coverage spans all ten complexion
  scale values, four undertones, five hair texture families, three height
  classes, five builds, and multiple representation contexts.
- `MR-125` **Done:** The review builder emits 12 phrase contact sheets and a
  machine-readable 144-poster validation report. The output is explicitly a
  technical fixture and cannot be promoted to production artwork.
- `MR-126` **Superseded:** Product review correctly established a materially
  higher authored-human standard instead of approving the procedural fixture.
- `MR-127` **Moved to H2:** GLB parity begins only after an original Human Pack
  v1 identity passes the production visual and representation gate.
- `MR-128` **Pending:** Add tiered/on-demand pack generation and sharded
  catalogues before scaling beyond curated pilots.

## H2: Authored Human Pack v1

**Engineering prototype status: complete locally. Front-facing vector
foundation: approved. Production turnaround and cross-backend design: rejected.**

- `MR-130` **Done locally:** Establish the Human Mascot Reference dated
  2026-07-15 as the visual/coverage benchmark and record the normative Human
  Pack visual and representation standard.
- `MR-131` **Done locally:** Add the machine-readable production capability and
  editorial-policy contract, keep coverage pack-specific, make minor-coded
  characters optional, and enforce fixture-versus-production classification.
- `MR-132` **Done locally:** The project owner approved H01, H04, H07, H12, and H13
  on 2026-07-15 as the initial canonical family and foundation of the Human
  Character Library. Their exact concept SHA, visual language, anatomical
  principles, and device rules are versioned in
  `human-canonical-family-v1`. Deterministic layered SVG production-review
  candidates now provide 176 semantic layers and independently bound
  assistive-device parts.
  The corrective parity pass formalizes anatomical left/right and restores
  character-specific face, age, body, hair, clothing, glasses, and scarf cues.
  On 2026-07-15 the owner approved vector parity for all five members, including
  H07's seated geometry and footrest relationship. MIT production licensing and
  public redistribution authority are now recorded in the release evidence.
- `MR-133` **Reopened:** Five 512-pixel framing samples, a common-world-scale
  lineup, 15 true-size 80/96/100-pixel renders, 12 authored low-LOD layers, 19
  semantic-device part proofs, labeled anchor/pivot/contact sheets, four
  animated device checks, 20 authored turnaround views, 35 expression/pose
  renders, and 35 reduced-motion equivalents are technically validated. The
  owner rejected the turnaround construction: hair detaches in side views,
  three-quarter views do not rotate the complete hierarchy, and device topology
  is incomplete outside the front view.
- `MR-134` **Technical prototype only:** All five GLBs load and expose nine pose
  and seven expression clips plus named device nodes. Their primitive geometry
  does not preserve authored faces, bodies, clothing, hair, or assistive-device
  construction, so they are not production art.
- `MR-135` **Failed design gate:** The reviewer renders 80 GLB clips, but its
  former numeric checks proved execution rather than artistic parity. The exact
  rejected sheets are now bound to the owner decision; the report correctly
  emits `release-blocked` and `production_use: forbidden`.

## P1: Independent open-source platform foundation

- `MR-140` **Done locally:** Add the project manifesto, product vision, module
  boundaries, and the explicit Wahalao-as-consumer boundary.
- `MR-141` **Done locally:** Specify the draft portable `.mascot` v1 container,
  licensing/provenance requirements, deterministic ordering, and path safety.
- `MR-142` **Done locally:** Add a deterministic `.mascot` build/verify tool and
  regression tests for byte stability and traversal rejection.
- `MR-143` **Pending:** Introduce behavior-backed package loader and capability
  inspection APIs while preserving the 0.1 file-based render call.
- `MR-144` **Pending:** Split the monolithic target into internal core, vector,
  layered, animation, and text targets, then expose Conan components only after
  dependency and ABI tests pass.
- `MR-145` **Pending:** Add Character Catalogue, Recipe Catalogue, compile, and
  capability APIs; implement the Wahalao adapter outside the engine.

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
