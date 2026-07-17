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

The sticker display set expands this rule to Bangers Regular, Lilita One
Regular, and Kalam Bold. They are static TTF files pinned to a `google/fonts`
revision with local OFL terms and SHA-256 entries in
`content/fonts/sticker-display-v1/manifest.json`. Third-party catalogue sites
may be used for discovery, but never as the redistribution authority.

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

## ADR-021: Shared screen-space caption composition across render backends

- Status: Accepted
- Date: 2026-07-14

Caption fitting, collision scoring, selected-area choice, and per-line
coordinates resolve once through a backend-neutral contract. ThorVG consumes
that result for existing 2D/2.5D scenes and can render the caption alone into a
transparent straight-alpha BGRA frame. The optional Filament boundary converts
that same overlay onto its straight-alpha RGBA frame after the 3D render.

Captions remain screen-fixed and are not GLB meshes, textures, or Filament
entities. This keeps typography deterministic, crisp, pack-font licensed, and
independent of camera depth while leaving the default Conan graph free of
Filament. Existing 2D text goldens must remain pixel-stable; flat and layered
captioned `t = 0` output must be byte-identical.

## ADR-022: Versioned character identity contract across backends

- Status: Accepted
- Date: 2026-07-14

Character identity is an authored, backend-independent contract. Each contract
owns a stable character ID and version, exact palette, required semantic
features, normalized proportion measurements, and explicit measurement
definitions. Participating packs pin the canonical JSON bytes by SHA-256; GLB
generation derives its geometry and materials from the same file and embeds the
contract reference in asset metadata.

Acceptance must inspect actual SVG XML and GLB material, node, and mesh data;
matching metadata alone is insufficient. The first contract is `robot-004` and
covers head aspect, head-to-body ratio, eye spacing and height, mouth height,
antenna height, palette, and five required features.

Captions remain outside this contract as the shared screen-space layer from
ADR-021. Layered 2.5D may add review-only shading, rim light, shadow, depth, and
view offsets, but must preserve the original flat pose as a compatibility
control. Identity-driven art revisions may update a golden only with recorded
review evidence and unchanged motion acceptance checks.

## ADR-023: Screen-space semantic effects and identity contract v2

- Status: Accepted
- Date: 2026-07-14

Character effects whose apparent size is part of identity are screen-space
composition, not GLB geometry. Pack layers may opt into `screen_space`; these
unparented layers draw after character nodes and ignore mascot transforms and
view parallax. The optional Filament preview renders the same selected SVG into
a transparent overlay and composites it after the GLB pass. Caption composition
remains separate but shares the generic straight-alpha overlay boundary.

The `robot-004` identity contract advances to version 2. It adds explicit
antenna, eye, body-frame/inset, and sparkle subcontracts. Validation measures
the actual SVG and GLB meshes/material assignments, rejects any GLB sparkle
mesh, and requires its embedded screen-space effect declaration to match the
contract. Review acceptance compares sparkle pixel bounds across 2D, 2.5D,
Filament, and multiple orthographic camera spans.

## ADR-024: MascotRender is independent character-rendering infrastructure

- Status: Accepted
- Date: 2026-07-15

MascotRender is an open-source procedural character rendering engine rather
than a Wahalao-specific sticker subsystem. Its stable conceptual input is a
Character, Semantic Recipe, Camera, and Output Configuration. Wahalao consumes
the engine through an adapter and does not own phrase, identity, pack, or
renderer contracts.

Module boundaries begin as tested CMake targets and later Conan components in
one repository. They are not split into separate repositories until public API
stability and independent release cadence justify the cost.

## ADR-025: Production human art is distinct from technical fixtures

- Status: Accepted
- Date: 2026-07-15

The procedural 12-human matrix proves deterministic identity, rig, camera,
recipe, rendering, review, and packaging behavior. It is permanently marked a
technical fixture with production use forbidden. Automated schema or coverage
success cannot promote it to production artwork.

The owner-supplied Human Mascot Reference dated 2026-07-15 is the visual and
coverage benchmark for original Human Pack v1 artwork. Production approval
uses the versioned human-pack standard, provenance, small-size readability,
assistive-device/cultural review, reduced-motion review, diverse human review,
and claimed-backend identity parity. Representation metadata supports audit;
it never infers user identity or drives geometry from heritage labels.

## ADR-026: Draft `.mascot` v1 is a deterministic ZIP-compatible container

- Status: Accepted
- Date: 2026-07-15

Portable character packages use a ZIP-compatible `.mascot` authoring container
with a root `manifest.json`, sorted entries, fixed metadata, declared SHA-256
hashes, safe relative paths, explicit capabilities, provenance, and licenses.
Version 1 uses stored entries to avoid compressor-version nondeterminism.

The authoring packager and verifier do not make the container a trusted engine
input. The 0.1 directory API remains unchanged until a bounded loader rejects
duplicates, traversal, symlinks/devices, unknown requirements, excessive sizes,
hash mismatches, and undeclared content before compilation.

## ADR-027: Five approved masters define the initial canonical human family

- Status: Accepted
- Date: 2026-07-15

The project owner approved the original H01, H04, H07, H12, and H13 concept
lineup as the initial canonical family. It establishes the visual language,
anatomical rules, assistive-device integration, age diversity, and identity
principles that future Human Character Library members must follow.

The versioned family contract pins the reference SHA-256, approval, five member
IDs, device requirements, production requirements, and scope. The scope is a
foundation rather than a complete library. The raster is an approved concept
reference, not a layered production source or permission to skip the pack's
declared editorial goals, licensing, small-size, device-motion, diverse-review,
or backend parity gates.

## ADR-028: Human identity dimensions are capabilities, not mandatory pack coverage

- Status: Accepted
- Date: 2026-07-15

MascotRender supports authored human characters across life stage, body,
complexion, hair, presentation, ability, and context dimensions. The engine
does not require any pack to contain every value. Each pack owns an explicit
editorial coverage decision and may choose a reviewed subset.

Minor-coded characters are optional. H01 remains part of the owner-approved
Human Pack v1 foundation, while proposed pre-teen H02 and teen H03 are deferred
until a separate owner/editorial approval records their intended use. Automated
coverage validation cannot make or imply that decision.

## ADR-029: Human selection rotates authored identities without demographic inference

- Status: Accepted
- Date: 2026-07-16

Human Expansion Wave 2 adds ten independently authored identity candidates to
the five-character canonical foundation. Heritage context is review metadata;
it never derives geometry and is never visible to runtime selection. After the
Unicode trie resolves a phrase, production-eligible human identities rotate
with uniform weight using a stable conversation offset and round robin. An
explicit character choice may override rotation, but the selector must not
infer or target a user's race, ethnicity, complexion, or appearance.

Wave 2 candidates remain excluded from production selection until hash-bound
owner identity approval, cultural or assistive-device review where applicable,
authored cross-backend parity, and final production activation. Phrase
multiplication follows identity approval so a weak identity cannot be amplified
into hundreds of derivative stickers.

## ADR-030: Production captions use strict animation-aware semantic exclusion

- Status: Accepted
- Date: 2026-07-16

Caption placement for animated stickers is solved against the union of each
selected semantic layer's transformed collision bounds across the complete
sampled loop. Character, hair, limbs, and assistive-device layers contribute
independent raster-derived bounds. A production pack may forbid overlap; an
intersecting slot is then rejected instead of merely receiving a worse score.
If no slot remains, validation fails and the asset is not rendered.

Production review checks every frame against a 16-source-pixel canvas margin
and publishes complete-sticker sheets at 80, 96, and 100 pixels. Phrase intent,
physical pose implementation, audience class, and accessible description are
separate authored fields. Reusing a pose never permits apology or affection to
be mislabeled as gratitude.

## ADR-031: Canonical delivery and small-display composition are separate profiles

- Status: Accepted
- Date: 2026-07-17

The canonical animated human sticker remains a 512×512 delivery asset. Tray
and stress-test outputs at 100, 96, and 80 pixels are derived display profiles,
not naive resizes and not replacements for the canonical asset.

The backend-neutral profile solver isolates the animated character/device and
screen-space caption, computes each component's union bounds over the complete
loop, and applies one stable transform per component for every frame. It picks
the largest safe composition within the profile's occupancy range. Wide
assistive-device geometry may satisfy the character-size gate by width and is
never cropped. Long side captions fall back to a vertical slot when their
actual rendered glyph height would be less than ten percent of the tile.

Minimum combined occupancy is evaluated over the animation union because a
caption may intentionally fade out at a loop endpoint. Canvas margin, maximum
occupancy, character/device size, and zero caption collision remain per-frame
requirements. This distinction prevents both animation pumping and false
failures on intentional transparent caption frames.

The project owner approved the exact `human-small-display-occupancy-v1`
contract and 80/96/100 contact-sheet hashes on 2026-07-17. `tray-100` is the
recommended default, `tray-96` is the compact profile, and `stress-80` is only
the compatibility/readability floor. The binding approval is
`contracts/human-small-display-occupancy-owner-approval-v1.json`; it closes the
occupancy gate without waiving any specialist, turnaround, GLB, playback, or
final production gate.

## ADR-032: Wave 2 production activation requires deterministic complete evidence

- Status: Accepted
- Date: 2026-07-17

Wave 2 production review is one hash-bound package spanning flat 2D, layered
2.5D, GLB front identity, true four-view GLB turnarounds, nine semantic poses,
seven expressions, native animation playback, reduced motion, and the H05/H08
specialist evidence. A front-only GLB or a still sheet cannot stand in for the
missing views or playback.

The review builder verifies semantic hierarchy, clip presence, palette and
silhouette thresholds, visible motion, exact loop closure, reduced-motion
equivalence, and full-tree byte determinism. H08's crown is a true rear shell;
the front skin shell, side panels, and shoulder drape form its opening without
intersecting coplanar surfaces, preventing nondeterministic GPU depth ties.
H05's vector cane sweep remains outside the leg silhouette and preserves a
visible red tip in every sampled frame.

Automation may report technical success but cannot approve assistive-device
behavior, cultural construction, art direction, or production activation.
Those decisions remain separately attributable to qualified reviewers and the
project owner. Until both specialist reviews and the hash-bound owner decision
pass, Wave 2 remains excluded from public production selection.

On 2026-07-17 the project owner reviewed the complete Wave 2 package and
approved neutral turnarounds, cross-backend identity recognition, GLB semantic
poses and expressions, and animation/reduced-motion quality. Cross-backend
art-direction parity failed. The exact partial decision is bound in
`human-wave2-owner-production-decision-v1.json`; corrective work must preserve
the four approved gates and return only the GLB art-direction comparison for
owner re-review.

The corrective candidate uses semantically matched rest, greeting, and excited
states across flat 2D, layered 2.5D, and GLB. Wave 2 GLBs now use real
depth-safe ink shells instead of detached front-view outline cards, smaller
age-aware head proportions, longer authored legs, outlined facial/body
hierarchy, richer hoodie construction, and a ground-correct H05 cane. The
focused deterministic package is
`generated/human-wave2-art-direction-review-v2`; it does not reopen the four
approved owner gates.

On 2026-07-17 the project owner approved the corrected cross-backend
art-direction gate against the exact four review-image hashes in
`human-wave2-cross-backend-art-direction-owner-approval-v1.json`. The owner
then explicitly activated all ten Wave 2 members for public production use.
The binding activation is
`human-wave2-production-activation-v1.json`; the production selector now
rotates all fifteen approved human identities uniformly without demographic
inference.

The H05 orientation-white-cane and H08 head-covering specialist reviews remain
open as named, non-blocking post-release advisories. The activation does not
claim that a qualified specialist supplied either decision. Findings from
those reviews can require a corrective release, but they do not silently
revoke or weaken the project owner's explicit production activation.
