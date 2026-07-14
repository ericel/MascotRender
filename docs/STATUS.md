# MascotRender Project Status

Updated: 2026-07-14

## Current milestone

E4 — optional Filament/GLB proof. MR-110 and MR-112 through MR-115 are complete;
MR-116 animation-export correction is in review, then MR-111 cross-platform
wrapper publication resumes. M0-M6
and E1-E3 are complete, release `v0.1.0` is published, and
anonymous consumers can install `mascotrender/0.1.0` from the public JFrog Conan
remote. Product/Design approved the generator-v6 50-sticker bundle on
2026-07-14. M7 remains a separate product-integration pilot.

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
  Windows MSVC static/shared Release, macOS arm64 static Release, an opt-in
  macOS Filament/GLB build, plus Linux Clang 18 ASan/UBSan.
- MIT project license shipped by CMake and Conan.

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
  Final playback signoff remains pending review of this corrected bundle.
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
Google's checksum-pinned official archives; its recipe and binaries must be
published to the MascotRender remote before external 3D consumers can resolve
`with_filament=True`.

## Distribution

Release `v0.1.0` and its tested Conan binaries are published. Anonymous
consumers add
`https://ericel.jfrog.io/artifactory/api/conan/conan-local` as a Conan remote;
publication credentials remain confined to repository secrets.

## Next execution track

The approved generator-v6 contact sheet is the M6 visual regression baseline,
the identity-aligned robot hop is the MR-102 layered-animation baseline, the
MR-113 sheet is the shared-caption backend baseline, and the MR-115 sheet is
the cross-backend identity/parity baseline. MR-116 is the active correction
gate for uniform 512 px 3D animation exports and directly measured hop-shadow
response. After its playback review, the next E4 work is the
remaining MR-111 Linux/Windows Filament-wrapper validation and remote optional
package publication. Matcher boundary and collision behavior remains part of
M7 unless a reusable matcher is deliberately added to the engine.

The approved expansion direction is documented in `ROADMAP_3D_ANIMATION.md`.
The deterministic 2D and layered 2.5D slices are complete. The next major
engine step is the optional Filament/GLB backend proof. The default Conan graph
now explicitly keeps Filament disabled, and hosted CI covers macOS arm64 in
addition to Linux and Windows. MR-111 now packages the official Filament 1.74.0
desktop archives because ConanCenter does not provide Filament. Its macOS
Metal/gltfio lifecycle, semantic GLB loader, orthographic camera, hard key
lighting, and headless RGBA readback are implemented. Linux/Windows wrapper
validation and remote publication remain before MR-111 can close.
