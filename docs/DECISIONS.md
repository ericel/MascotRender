# MascotRender Architecture Decisions

Status values are `Accepted`, `Proposed`, `Superseded`, or `Deferred`.

## ADR-001: Build-time content compiler

- Status: Accepted
- Date: 2026-07-13

MascotRender 0.1 is a build-time library and CLI. It generates immutable assets
and manifests. It does not render a new sticker for every chat message or
keystroke. Runtime suggestion lookup and message attachment are product-pilot
consumers of generated data, not responsibilities of the engine MVP.

## ADR-002: Conan 2 is the package manager

- Status: Accepted
- Date: 2026-07-13

Dependencies and MascotRender binaries are distributed through Conan 2. The
source project remains ordinary CMake and also installs a relocatable CMake
config package. The canonical consumer target is
`MascotRender::MascotRender`.

The package recipe must contain a real `test_package`; successful compilation
of MascotRender's own tests is not sufficient proof that consumers can use the
package.

## ADR-003: ThorVG software renderer for 0.1

- Status: Accepted
- Date: 2026-07-13

The first renderer uses the ThorVG software backend pinned to the Conan Center
version verified by the lockfile. libwebp performs final WebP encoding. Skia is
deferred because its GN-based build and distribution workflow would add work
before the scene and pack contracts are validated.

ThorVG 0.15.16 is compiled as C++17 inside the pinned Conan dependency profile
while MascotRender and its public consumers remain C++20. This avoids an
upstream `identity`/`std::identity` name collision on recent libc++ toolchains.
The exception is isolated to the dependency package ID and must be removed or
re-evaluated when the ThorVG recipe is upgraded.

ThorVG and libwebp types remain private implementation details. An internal
renderer interface preserves a later migration path without exposing backend
types in the public ABI.

## ADR-004: JSON-only engine MVP

- Status: Accepted
- Date: 2026-07-13

Version 0.1 reads JSON sticker specifications and JSON mascot-pack metadata.
CSV authoring is deferred to the pilot toolchain. A CSV importer can later
convert content-operator files into the same canonical `StickerSpec` model.

## ADR-005: Trusted curated SVG packs in 0.1

- Status: Accepted
- Date: 2026-07-13

The first release accepts only repository-controlled mascot packs produced by
the approved art workflow. It validates that paths remain inside the pack root
and rejects external URLs and disallowed references. It is not an isolation
boundary for hostile third-party SVG files. Full untrusted-input sanitization
requires a separate security milestone.

## ADR-006: Determinism is profile-scoped

- Status: Accepted
- Date: 2026-07-13

Byte-identical output is required for the same source, lockfile, font files,
renderer settings, and pinned Conan host/build profiles. Different operating
systems or rasterizer versions must remain visually equivalent, but are not
promised to produce identical bytes.

The engine uses an explicitly named fixed hash and PRNG algorithm. It must not
use `std::hash`, `std::random_device`, platform font discovery, current time, or
unordered iteration to determine rendered output.

## ADR-007: Public headers do not expose dependencies

- Status: Accepted
- Date: 2026-07-13

The public C++ API uses standard-library and MascotRender-owned types only.
ThorVG, libwebp, JSON, and CLI types remain private. `Engine` and pack handles
use Pimpl or exported destructors so shared-library ownership is unambiguous.

A custom `Result<T>` is used because the project is C++20 and
`std::expected` is C++23.

## ADR-008: First text boundary

- Status: Accepted
- Date: 2026-07-13

The first vertical slice supports exact English and Pidgin text using packaged
TTF/OTF files, deterministic wrapping, and font-size fitting. HarfBuzz and
FreeType integration, fallback chains, bidirectional text, Korean shaping, and
full Unicode normalization are deferred until the base render pipeline is
proven.

## ADR-009: Owned in-memory render result

- Status: Accepted
- Date: 2026-07-13

The library returns encoded image bytes in an owned `EncodedImage` through a
custom C++20 `Result<T>`. It does not write files or throw backend exceptions as
part of the core render operation. Applications and the CLI decide where and
how to persist the result.

The M1 `Engine::render_sample` function is explicitly a vertical-slice API. The
owned image, options, error, and result contracts are intended to survive M2;
the hard-coded sample entry point is not the final pack-rendering abstraction.

WebP encoding uses method 4, exact transparent-color preservation, and no
encoder worker threads. Method 6 was rejected after a local measurement took
several seconds per simple 512 x 512 render; method 4 reduced the entire
two-render/decode test suite to under one tenth of a second in the pinned
Release profile.

## ADR-010: Platform-specific Conan lockfiles

- Status: Accepted
- Date: 2026-07-13

Each supported host profile has its own Conan lockfile. Dependency versions and
recipe revisions remain aligned, but build requirements differ by platform:
Linux requires NASM and Windows additionally requires Strawberry Perl in the
current graph. Reusing the macOS lockfile caused graph resolution to fail before
the package could build.

## ADR-011: Named composition and fixed variation algorithm

- Status: Accepted
- Date: 2026-07-13

Pack format v1 composes the union of invariant base layers, one named
expression, one named pose, optional sticker-specific layers, and one selected
choice per variation group. Pack-defined unique integer z values order flat
layers; ADR-019 extends ordering for optional depth-enabled scene nodes.

An explicit unsigned 64-bit sticker seed is used directly. If absent, the seed
is derived with 64-bit FNV-1a over the pack and sticker IDs with zero-byte
separators. SplitMix64 advances once for each variation group in declared array
order. These exact algorithms are part of schema version 1 and may not change
without a schema-version or renderer-version decision.

## ADR-012: Pack-local static TTF provenance

- Status: Accepted
- Date: 2026-07-13

M3 embeds only static TTF files acquired from an authoritative upstream release.
Each pack font declaration includes a local source and complete local license;
both canonical paths must remain inside the pack root. The package records the
upstream repository revision and font SHA-256. Platform font discovery, remote
font URLs, WOFF/WOFF2, unverified third-party mirrors, and variable-font axes are
outside the 0.1 trust and compatibility boundary.

The first approved font is Changa One Regular from `google/fonts`, licensed
under SIL OFL 1.1. The complete font license is also copied into the Conan
package license directory.

## ADR-013: Scripted procedural content compiler

- Status: Accepted
- Date: 2026-07-13

The 0.1 content pipeline uses standard-library Python scripts for procedural SVG
pack generation and batch orchestration around the installable C++20 engine.
This keeps artistic iteration and manifest I/O out of the public library ABI
while preserving the C++ renderer as the single validation and image-generation
implementation. The scripts are installed as package resources and tested
against the installed CLI.

Generation uses a fixed SplitMix64 implementation, sorted filesystem traversal,
stable JSON formatting, no network access, and no current-time fields. Batch
publication uses staging and emits SHA-256-addressed metadata. Moving the batch
orchestration into a future C++ CLI subcommand is allowed without changing pack
schema v1 or the public library API.

## ADR-014: Balanced text layout and deterministic outline

- Status: Accepted
- Date: 2026-07-13

Text layout searches downward for the largest valid whole-point font size. At
each size it chooses the fewest possible lines and uses dynamic programming to
minimize squared unused line width. Equal-cost layouts choose the earliest cut.
This replaces greedy wrapping without changing schema version 1.

ThorVG 0.15 text objects do not expose glyph stroke controls. An optional pack
outline therefore renders eight glyph copies at fixed cardinal and diagonal
offsets before the fill pass. Outline width is expressed in canvas units, scales
with output dimensions, is limited to 0 through 32, and is included in safe-area
fitting. A future native glyph-stroke implementation may replace the multi-pass
method only with a renderer-version decision and updated golden review.

## ADR-015: Named text slots and deterministic auto placement

- Status: Accepted
- Date: 2026-07-13

Pack format v1 gains optional named `text_slots`. Sticker text may retain the
style `safe_area`, select one slot, or request `auto` with an ordered preference
list. Auto placement chooses the candidate with the largest fitted font, then
the fewest lines, then the earliest preference. When no preference is supplied,
slot IDs are considered in lexicographic order. These optional fields are
backward compatible and do not alter output for existing stickers.

Alpha/path collision masks, rotated/path text, character anchors, and
animation-wide occupancy scoring require additional renderer work and are not
claimed by this first slice. Rectangle avoid regions were added by the later
animation vertical slice recorded in ADR-018.

## ADR-016: Time-sampled backend-neutral scene expansion

- Status: Accepted
- Date: 2026-07-13

Animation, 2.5D, and 3D will share a scene graph, typed keyframe timeline, text
layout contract, owned RGBA frame transport, and animation encoder interface.
Static rendering is the sample at `t = 0`. Existing SVG layers become flat
scene nodes; a future Filament backend consumes GLB/glTF 2.0 behind an optional
Conan feature and cannot leak Filament types into the public API.

Expansion order is fixed: layout/scene foundations, animated current 2D packs,
layered 2.5D, then one true-3D robot proof. Product clients consume pre-rendered
animated WebP and static thumbnails rather than embedding a 3D runtime.

## ADR-017: MIT project license

- Status: Accepted
- Date: 2026-07-13

MascotRender source and bundled project-owned sample content are distributed
under the MIT License with copyright held by `ericel`. The Conan recipe declares
`MIT`; CMake and Conan packages ship the complete root license. Dependency,
font, and separately generated-content licenses remain independently binding.

## ADR-018: Bounded deterministic 2D animation vertical slice

- Status: Accepted
- Date: 2026-07-13

Sticker format v1 gains optional bounded animation declarations: duration,
frame rate, loop policy, and a fixed set of procedural overlays. The first
overlay set is body bounce plus text pop. An internal timeline samples owned
frame state with fixed easing formulas; no animation implementation type enters
the public API.

Animated stickers encode through libwebp's animation API with explicit encoder
settings and loop count. Batch output keeps the full animation as the primary
asset and renders a stable static poster for its thumbnail. Encoders may merge
identical consecutive resting frames, so acceptance is based on deterministic
bytes, timing, canvas, loop metadata, and decoded frame changes rather than an
exact encoded-frame count.

## ADR-019: Backward-compatible layered 2.5D scene nodes

- Status: Accepted
- Date: 2026-07-14

Pack format v1 gains optional layer parent, named pivot, local affine transform,
opacity, and depth fields. Sticker format v1 gains an optional bounded `view`
offset. Missing fields compile to identity nodes, and the renderer retains its
existing identity fast path; therefore every pre-existing pack and the approved
M6 `t = 0` pixels remain unchanged.

Parent transforms, depth, and opacity resolve deterministically before
rendering. Parent cycles, missing parents, unknown pivots, non-finite values,
and out-of-range transforms fail with pack/sticker JSON locations. World depth
orders nodes before the existing unique z tie-breaker and controls parallax
against the sticker view. Text remains screen-fixed, while transformed
collision bounds follow the visible node.

This contract deliberately stops before procedural squash/stretch, delayed
child motion, shadow response, or camera timelines; those are MR-101 timeline
features built on the resolved nodes rather than additional ad hoc render paths.

## ADR-020: Typed node and camera tracks for layered 2.5D motion

- Status: Accepted
- Date: 2026-07-14

Sticker animation gains bounded typed scalar tracks. A track targets a selected
scene node or the reserved `$view` camera and owns strictly ordered integer-time
keyframes with one of four fixed easing formulas. Node transforms compose around
their resolved named pivots and affect the full descendant chain; child tracks
compose afterward, enabling delayed follow-through without character-specific
renderer branches. Animated opacity multiplies inherited pack opacity.

Camera tracks add to the sticker's static view and reuse resolved node depth for
parallax. Looping tracks must return to their initial value. The existing
procedural overlays remain supported, omitted tracks remain identity, and static
poster mode renders the same byte-stable `t = 0` scene as MR-100.
