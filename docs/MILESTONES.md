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
- `MR-051` Run warning-clean GCC, Clang, AppleClang, and MSVC builds.
- `MR-052` **CI configured:** run ASan/UBSan on Linux; hosted result pending.
- `MR-053` **Partial:** dependency/font inventory and notices are packaged;
  owner project-license text remains required for public distribution.
- `MR-054` Pin Conan profiles, lockfiles, recipe revision, and dependency options.
- `MR-055` **Local partial:** static Release and shared Debug pass on macOS;
  hosted Linux variants and Windows static/shared Release remain. ThorVG's
  pinned recipe explicitly rejects MSVC Debug.
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

Add CSV import, contact-sheet review, incremental caching, additional poses and
effects, and performance reporting as needed for the content workflow. Exit
requires Design and Product approval of a 50-sticker contact sheet and no
unresolved rendering or licensing failures.

The engine must not scale to 200 stickers until this gate passes.

## M7: 200-sticker product pilot

Goal: integrate the generated pack into Drogon delivery and React local
suggestion matching.

This milestone includes immutable CDN paths, ETags, rollback, local trailing
phrase extraction, deterministic ranking, MLS attachment metadata, receiving
client fallback, content QA, and pilot telemetry under an approved privacy
policy.

## First execution batch

Start these items immediately:

1. `MR-001` through `MR-006` as the critical engineering path.
2. `MR-009` CI profiles in parallel with the package recipe.
3. The M2 example-pack art dependency in parallel with M0.
4. Font licensing and text-limit decisions before M3 begins.

Do not start incremental caching, CSV, animation, OpenCV, runtime integration,
or 200-sticker production until their preceding exit gates pass.

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
