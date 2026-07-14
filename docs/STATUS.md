# MascotRender Project Status

Updated: 2026-07-14

## Current milestone

E4 — optional Filament/GLB proof. M0-M6 and E1-E3 are complete, release `v0.1.0` is published, and
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
- Public API comments, pack documentation, release notes, benchmark baseline,
  and third-party dependency/font notices.
- GitHub Actions definition covering Linux GCC 13 static Release/shared Debug,
  Windows MSVC static/shared Release, plus Linux Clang 18 ASan/UBSan.
- MIT project license shipped by CMake and Conan.

## Verified locally

- AppleClang 21 Release build is warning-clean and all 32 CTest tests pass.
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
  `61e255a91dbdb2dc8005d646d28cef6b4de2f64bcaa1781775b0152578465873`.
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

## Distribution

Release `v0.1.0` and its tested Conan binaries are published. Anonymous
consumers add
`https://ericel.jfrog.io/artifactory/api/conan/conan-local` as a Conan remote;
publication credentials remain confined to repository secrets.

## Next execution track

The approved generator-v6 contact sheet is the M6 visual regression baseline,
and the corrected robot hop is the MR-102 layered-animation baseline. E3 is
closed. The next engine track is E4: an optional Filament/GLB proof that leaves
the default C++20/Conan package free of 3D dependencies. Matcher boundary and
collision behavior remains part of M7 unless a reusable matcher is deliberately
added to the engine.

The approved expansion direction is documented in `ROADMAP_3D_ANIMATION.md`.
The deterministic 2D and layered 2.5D slices are complete. The next major
engine step is the optional Filament/GLB backend proof.
