# MascotRender Project Status

Updated: 2026-07-21

## Current milestone

E4 — optional Filament/GLB proof is complete. MR-110 through MR-116 are done,
including cross-platform wrapper validation and publication. M0-M6 and E1-E4
are complete. The owner-approved, hash-bound canonical family, Wave 2 Human
Pack, six-identity Micro Reactions pipeline, 23-sticker Calendar Pop pack, and
36-sticker Congratulations Pop pack ship in `v0.6.0`; anonymous consumers
install `mascotrender/0.6.0` from the public JFrog Conan remote. The
content-addressed Micro Reactions bundle remains published as a provider-neutral
GitHub Release asset.
Product/Design approved the generator-v6 50-sticker bundle on 2026-07-14 and
the canonical Human Pack production bundle on 2026-07-15. M7 remains a
separate product-integration pilot.

## Completed locally

- Installable dependency-free C++20 API and relocatable
  `MascotRender::MascotRender` CMake package.
- Conan 2 recipe with pinned dependencies, static/shared, fPIC, and optional CLI
  variants plus a separate installed-package consumer test.
- ThorVG software SVG/text renderer and deterministic libwebp encoder behind
  private implementation types.
- Version-1 pack/sticker schemas, structured source-located diagnostics,
  canonical path containment, expressions, poses, and fixed seeded variation.
- Approved pack-local Changa One static TTF and complete SIL OFL/provenance.
- Largest-valid whole-point text sizing, dynamic-programming balanced wrapping,
  configurable eight-pass outlined glyphs, and outline-aware safe-area fitting.
- Backward-compatible named text slots with explicit or deterministic
  preference-based auto placement, actual fitted-glyph overlap scoring, and
  selected-layer collision bounds expanded by a pack-wide clearance.
- Backward-compatible parented scene nodes with named pivots, inherited affine
  transforms/opacity/depth, deterministic view parallax, transformed collision
  bounds, and byte-stable identity rendering.
- Bounded deterministic timelines for body-bounce and text-pop overlays,
  animated WebP assets, and static poster thumbnails.
- Bounded typed node and camera keyframes with four fixed easing modes,
  subtree transform inheritance, squash/stretch, delayed child follow-through,
  responsive shadow opacity/scale, and animated depth parallax.
- 512 x 512 assets, 256 x 256 thumbnails, alpha/dimension checks, and CLI
  `render`, `render-sample`, and `validate` commands.
- Deterministic procedural generator for cat, bear, bunny, robot, and alien
  identities with ten English/Pidgin phrases per identity.
- Staged batch renderer producing assets, thumbnails, SHA-256 catalogue,
  full-phrase dictionary, and deterministic build report.
- Deterministic review builder producing a complete HTML gallery, side-by-side
  animation playback page, per-sticker CSV checklist, and machine-readable
  summary after independently verifying paths, sizes, hashes, WebP structure,
  animation metadata, and report totals.
- Reviewed lossless cat/text golden with decoded-pixel regression tolerance.
- Approved lossless robot 2.5D animation golden with frame/timestamp metadata
  and decoded RGBA regression tolerance.
- Backend-neutral caption resolution with one collision score/slot/line layout
  shared by 2D, 2.5D, and the post-Filament screen-space compositor.
- Versioned `robot-004` identity contract shared by flat SVG, layered SVG, and
  GLB, with exact palette, required features, six normalized measurements, and
  validation against actual SVG XML and GLB geometry/material data.
- Review-only dimensional 2.5D pose with stronger cast shadow, warm side-plane
  shading, face gradient, rim light, explicit layer depth, and parallax; the
  flat `front` compatibility pose is retained.
- Identity contract v2 locks antenna continuity, normalized eye geometry,
  orange-frame/inset-body structure, and a camera-independent screen-space
  sparkle shared as SVG rather than duplicated in the GLB.
- Public API comments, pack documentation, release notes, benchmark baseline,
  and third-party dependency/font notices.
- GitHub Actions definition covering Linux GCC 13 static Release/shared Debug,
  Windows MSVC static/shared Release, macOS arm64 static Release, opt-in
  Filament/GLB builds on all three desktop platforms, plus Linux Clang 18
  ASan/UBSan.
- MIT project license shipped by CMake and Conan.
- Owner-approved Micro Reactions family with Sprig, Cinder, Ripple, Orbit,
  Crumb, and Mallow; 60 animated reactions, 60 reduced-motion equivalents,
  60 thumbnails, and six deterministic styled GLBs.
- Storage-neutral content-addressed bundle staging with 190 immutable objects,
  an atomic stable-channel pointer, and an approval-bound deterministic ZIP
  suitable for GitHub Releases or any object-storage provider.
- Owner-approved Calendar Pop pack with seven weekdays, twelve months, four
  seasons, four OFL font voices, exact spelling, varied placement, animated
  WebP output, and reduced-motion equivalents.
- Owner-approved Congratulations Pop pack with 36 phrases, four OFL font
  voices, six composition systems, varied motifs, exact spelling, animated
  WebP output, and reduced-motion equivalents.

## Verified locally

- AppleClang 21 Release build is warning-clean and all 36 CTest tests pass.
- The opt-in Filament graph passes the complete 46-test local configuration,
  including real Metal engine/gltfio lifecycle, semantic anchor loading,
  missing-anchor failure, bounded output, and non-empty headless RGBA rendering
  through a fixed orthographic camera and toon-style key light.
- The deterministic `robot-004.glb` follows the approved 2D/2.5D robot identity
  and passes the Khronos validator with zero errors and warnings. Filament
  reports four named clips, six named facial morphs, six required semantic
  anchors, exact approved palette pixels, correct antenna-up orientation,
  independent hop-shadow contraction, and distinct pixels for every sampled
  clip. The review tool emits five lossless 512 px WebPs, an upright
  white-background PNG, four real 13-frame looping animated WebPs, pose and
  motion sheets, a browser playback page, and machine-readable validation.
  Product/Design approved both the corrected static gate and animated playback
  proof on 2026-07-14. A later decoded-frame audit reopened only the animation
  export contract; MR-116 corrects it without changing the approved static art.
- MR-116 requires every robot sample and all four 13-frame animated WebPs to be
  512 x 512. The regenerated hop shadow contracts from 276 to 146 pixels wide
  at peak height (52.9%) and from 6,828 to 2,102 interior pixels (30.8%), keeps
  its horizontal center at x=256, and returns exactly to its frame-zero bounds.
  Product/Design approved the corrected playback bundle on 2026-07-14, closing
  MR-116.
- MR-113 renders one collision-aware `NICE ONE!` recipe through flat 2D,
  layered 2.5D, and GLB/Filament. Flat and layered files are byte-identical;
  the repeatable review tool validates caption pixels on every backend and
  emits a three-column contact sheet plus SHA-256 manifest.
- MR-115 independently validates both SVG packs and the generated GLB against
  contract SHA-256
  `3f1d684c5a1b42627641f409ab92e46813937357888d75a77dd5a39df95c2012`.
  All 14 normalized measurements pass. Its three-backend review changes 60,214
  pixels between flat and dimensional 2.5D, preserves 4,558 caption fill pixels,
  and records identical sparkle bounds `(41, 202, 129, 289)` across every
  backend and both tested 3D camera spans.
- The deterministic integration test independently generates and byte-compares
  two 20-sticker/40-asset bundles, including eight animated assets and static
  poster thumbnails.
- Static-with-CLI and shared-without-CLI Conan packages pass the external
  consumer; the consumer proves layered/flat identity and changed parallax from
  installed robot resources, while installed scripts generate and render a real
  bundle.
- The current generated review set contains 5 packs, 50 stickers, 100 WebPs,
  20 animated primary assets, exact authored metadata, and 2,975,724 encoded
  bytes.
- Review round 2 rejected per-character collision patches and the alien's
  separate visual system. Generator v6 now uses the shared silhouette family,
  while the engine applies one selected-layer collision rule to all mascots.
- Animation playback review found and fixed an abrupt loop reset. All repeating
  timelines now end at the starting transform, scale, and opacity.
- The v6 bundle passed round-three Product/Design review and closes M6; its
  catalogue SHA-256 is
  `d16f85b60f707a4559b3a36bca9e8e82dc44b37dbfc8eb24389077799565a57f`.
- Golden `cat-text-sample.webp` is lossless 512 x 512 WebP with SHA-256
  `8591f0dca51b1c8ec39765cb19ed5719c62b12825f9d0aef960452f9a84d23ee`.
- Golden `robot-2_5d-animated-hop.webp` is an approved lossless 512 x 512,
  1200 ms, 15-frame looping WebP with SHA-256
  `c656d66e8d12bea49cebdcd45d2f12d3bba18fc45dbdac6ddce9c99168fe9674`.
- Local render baselines: 1.37 seconds for 10 stickers and 6.21 seconds for 50
  stickers, including animated primary assets and matching poster thumbnails.
- Pack/sticker schemas and generated manifests/catalogues validate as JSON.
- Current-recipe static Release with CLI and shared Debug without CLI both pass
  the macOS external consumer. MSVC Debug is unsupported by the pinned ThorVG
  Conan recipe; Windows CI therefore verifies both linkage forms in Release.

## Known dependency constraint

ThorVG 0.15.16 must compile as C++17 on recent libc++ while MascotRender remains
C++20. Profiles record this package-scoped setting. ADR-003 requires the
workaround to be audited when ThorVG is upgraded.

Filament 1.74.0 does not have a ConanCenter recipe. The repository wrapper uses
Google's checksum-pinned official archives. Its recipe and tested macOS arm64,
Linux x86-64, and Windows x86-64 binaries are published to the MascotRender
remote so external 3D consumers can resolve `with_filament=True`.

## Distribution

Release `v0.6.0` supersedes `v0.5.0` as the current production package. Anonymous
consumers add
`https://ericel.jfrog.io/artifactory/api/conan/conan-local` as a Conan remote;
publication credentials remain confined to repository secrets. Every release
job must pass a logged-out exact-package re-download with `--build=never` on
macOS arm64, Linux x86-64, and Windows x86-64. Fresh caches use
`--build=missing` for public dependencies without matching ConanCenter
binaries. The successful `v0.6.0` publication run is linked from its GitHub
release.

## Product direction baseline

MascotRender is now explicitly defined as an independent open-source procedural
character rendering engine. `MANIFESTO.md`, `VISION.md`, and `ARCHITECTURE.md`
separate the engine from Wahalao and define Character + Recipe + Camera + Output
as the stable conceptual boundary. The repository remains a monorepo while
behavior-backed CMake/Conan module boundaries mature.

The owner-supplied Human Mascot Reference dated 2026-07-15 is the production
visual and capability benchmark. `HUMAN_PACK_VISUAL_STANDARD.md` and
`human-pack-production-v1.json` separate engine-supported identity dimensions
from pack-specific editorial coverage, with reviewable gates spanning body,
complexion, hair, gender presentation, ability, context,
expression, pose, five framings, small-size readability, reduced motion,
provenance, diverse review, and cross-backend parity.

The old procedural human matrix is permanently classified as a technical
fixture with production use forbidden. It continues to prove determinism and
contract behavior; it is not awaiting promotion to approved artwork.

On 2026-07-15 the project owner approved the original H01/H04/H07/H12/H13
concept lineup as the initial canonical family and foundation of the Human
Character Library. The approval covers family visual language, anatomical
rules, assistive-device integration, age diversity, and identity principles.
The pinned contract explicitly states that this is not the complete library and
that the raster reference is not a production rig.

The five approved front-facing identities have deterministic layered SVG
candidates: 176 semantic layers, five 512-pixel framings per identity, a
production-v2 22-joint rig, and separately bound prosthesis, wheelchair,
hearing-aid, and rollator parts. Anatomical right is formalized as screen-left
in an unmirrored front view. The renderer validates all 25 combinations and the
review builder emits nine sheets: framing and sticker-fit lineups, a common
world-scale lineup, true 80/96/100-pixel renders, 19 isolated device parts,
anchors, pivots, contacts, and four genuine animated device checks. Twelve
authored low-LOD layers are selected by the C++ renderer for the four device
users. H13's three-quarter framing has the preferred 16-pixel top margin. On
2026-07-15 the project owner approved vector identity parity for all five
members, explicitly including H07's seated geometry and footrest relationship.
The technical run emits 20 turnaround images, 35 expression/pose renders, 35
reduced-motion equivalents, five GLBs, and 80 Filament clip renders. The project
owner rejected the resulting production sheets on 2026-07-15. Side-view hair is
detached, three-quarter rotations do not rotate the whole hierarchy, device
topology collapses outside the front view, required pose evidence is incomplete,
and the primitive GLBs do not preserve identity or assistive-device geometry.
Technical validation succeeds, but the reviewed result is `release-blocked`
with production use `forbidden`.

A corrected candidate replaced synthetic production evidence with retained
Blender sources and authored GLBs. Complete-character hierarchy rotations drive
front/three-quarter/side/back views; hair remains attached; wheelchair and
rollator topology survives rotation; seven expressions and all nine poses are
shown on separate sheets; and a dedicated depth sheet shows flat, layered,
left/right parallax, and animated midpoint states. At that recovery stage, the
six review-sheet hashes were intentionally unapproved, so the generated status was
`awaiting-owner-production-design-review` with production use `forbidden`.
The owner then partially approved the isolated expressions, isolated vector
poses, flat/layered identity, and front-view GLB identity, while rejecting rear
shell construction, rigid device parallax, side/back device topology, readable
GLB semantic poses, and full parity. That decision is bound to the reviewed six
sheet hashes. The next seven-sheet candidate fixes those rejected areas, adds a
dedicated GLB semantic-pose sheet, and again awaits an owner decision bound to
its new hashes.
That bundle received near-final partial approval. The final targeted authoring
pass restores H01's skirt and visible legs, gives H04 a single short-coily hair
silhouette with long teal sleeves, and replaces H12's erroneous rear skin oval
with complete bob coverage and a rear grey streak. Cross-backend gates are now
split into identity parity and stricter family art-direction parity. Five real
nine-frame animated WebPs, five static semantic reduced-motion equivalents, a
playback storyboard, and a browser review page provided the previously missing
timing/loop evidence and became the final owner-review candidate.
The project owner approved those exact eight artifact hashes on 2026-07-15.
Native WebP container validation plus Pillow and ImageMagick decoding confirmed
all five nine-frame loops and five one-frame reduced-motion equivalents with
perfect loop closure. The authoritative result is now
`public-release-approved` with production use `public-release` and no blocking
findings.

Age values are engine capabilities rather than mandatory pack coverage. H01 is
an explicit approved Human Pack v1 editorial choice. On 2026-07-16 the owner
also explicitly approved the authored pre-teen H02 and teen H03 identities as
optional Human Pack members; the engine still does not require minor-coded
characters or infer a user's age.

The draft `.mascot` v1 container specification and deterministic authoring tool
establish a portable package boundary. Engine loading remains future work; the
0.1 trusted-directory API is unchanged.

## Next execution track

The 15-identity × 41-phrase production matrix now has an owner-approved
small-display system. Its 1,845 derived animated assets use animation-aware
80/96/100 profiles while the canonical 512×512 assets remain unchanged. The
owner approved the exact contract and three review-sheet hashes on 2026-07-17:
100 pixels is the default tray, 96 is compact, and 80 is a stress/compatibility
floor. The new gate-status record removes small-display occupancy from the
remaining list.

The H1 human representation fixture foundation is implemented locally: 12 versioned
appearance contracts, one normalized 15-joint full-body rig, 12 semantic core
phrases and reusable motion recipes, real engine-level semantic camera framing,
and deterministic generation/review tooling for 144 pilot stickers. Contract
validation covers all ten complexion positions, four undertones, five hair
texture families, three height classes, and five builds. The technical review
builder verifies every identity/phrase poster and intentionally reports
`technical-fixture`; these synthetic pilots can never become approved Human
Pack art merely by passing automated checks.

The complete Wave 2 technical production candidate is now available at
`generated/human-wave2-final-production-review`. It contains all ten
flat/layered/GLB comparisons, true vector/GLB four-view turnarounds, 90 GLB pose
renders, 70 GLB expression renders, ten native semantic-excited loops and their
reduced-motion equivalents, and focused H05/H08 specialist packages. Two full
regenerations produced byte-identical trees. The technical manifest SHA-256 is
`3052c22f69485f92e5a4f405c5b01bcaa9c51d3a4ef0dce5854f38905b1b0893`.

The project owner approved Wave 2 turnarounds, identity recognition, semantic
pose/expression parity, and animation/reduced-motion quality on 2026-07-17.
The first cross-backend art-direction submission failed, and its four approved
gates remained bound while the GLB silhouette, facial language, outline
hierarchy, clothing, and device styling were corrected. The phrase Trie
continues to map triggers to semantic phrase IDs rather than duplicating
terminals per mascot.

The focused correction is in
`generated/human-wave2-art-direction-review-v2`. It compares matched rest,
greeting, and excited semantics; all ten GLBs include depth-safe ink shells,
age-aware proportions, longer legs, outlined eyes/body/limbs, additional
clothing detail, and corrected cane ground contact. Two builds produced
byte-identical trees and all 46 tests pass. The owner approved its four exact
review-image hashes on 2026-07-17, closing the only reopened visual gate. Its
review manifest SHA-256 is
`661bcf566c6b63bb9f7324fb2faa95e6910c127abee7bbd39b7d3fab2db6aa88`.

The project owner then activated H02, H03, H05, H06, H08, H09, H10, H11, H14,
and H15 for public release. All fifteen canonical human identities are now
production-eligible with uniform rotation and no demographic inference. The
authoritative records are
`human-wave2-cross-backend-art-direction-owner-approval-v1.json`,
`human-wave2-production-activation-v1.json`, and
`human-development-matrix-gate-status-v6.json`.

H05 orientation-white-cane and H08 head-covering specialist reviews remain
visible as non-blocking post-release advisories. No specialist approval is
claimed. A later qualified review may result in a corrective release.
The phrase Trie must map triggers to
semantic phrase IDs rather than multiplying terminals by every mascot.

The approved generator-v6 contact sheet is the M6 visual regression baseline,
the identity-aligned robot hop is the MR-102 layered-animation baseline, the
MR-113 sheet is the shared-caption backend baseline, and the MR-115 sheet is
the cross-backend identity/parity baseline. The approved MR-116 bundle is the
uniform 512 px 3D animation and directly measured hop-shadow baseline. MR-111
closed after native macOS, Linux, and Windows CI plus anonymous remote package
verification. Matcher boundary and collision behavior remains part of M7
unless a reusable matcher is deliberately added to the engine.

The approved expansion direction is documented in `ROADMAP_3D_ANIMATION.md`.
The deterministic 2D, layered 2.5D, and optional Filament/GLB slices are
complete. The default Conan graph explicitly keeps Filament disabled. Hosted CI
covers macOS arm64, Linux x86-64, and Windows x86-64; Metal and Linux Vulkan
jobs exercise pixel rendering, while hosted Windows proves archive integrity,
MSVC compile/link, the Filament NOOP runtime, and backend-neutral engine paths
because the runner has no Vulkan ICD. The next product track is M7 integration.
