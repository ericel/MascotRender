# MascotRender Project Status

Updated: 2026-07-13

## Current milestone

M5 — Engine 0.1 release candidate. M0-M4 are implemented, the hosted compiler
and sanitizer matrix is green, and the project is MIT-licensed. A writable
Conan remote remains the publication gate. Product/Design approval of the full
50-sticker art set is the separate M6 gate.

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
  preference-based auto placement.
- 512 x 512 assets, 256 x 256 thumbnails, alpha/dimension checks, and CLI
  `render`, `render-sample`, and `validate` commands.
- Deterministic procedural generator for cat, bear, bunny, robot, and alien
  identities with ten English/Pidgin phrases per identity.
- Staged batch renderer producing assets, thumbnails, SHA-256 catalogue,
  full-phrase dictionary, and deterministic build report.
- Reviewed lossless cat/text golden with decoded-pixel regression tolerance.
- Public API comments, pack documentation, release notes, benchmark baseline,
  and third-party dependency/font notices.
- GitHub Actions definition covering Linux GCC 13 static Release/shared Debug,
  Windows MSVC static/shared Release, plus Linux Clang 18 ASan/UBSan.
- MIT project license shipped by CMake and Conan.

## Verified locally

- AppleClang 21 Release build is warning-clean and all 20 CTest tests pass.
- The deterministic integration test independently generates and byte-compares
  two 20-sticker/40-asset bundles.
- Static-with-CLI and shared-without-CLI Conan packages pass the external
  consumer; installed scripts generate and render a real bundle.
- The current generated review set contains 5 packs, 50 stickers, 100 WebPs,
  exact authored metadata, and 1,305,940 encoded bytes.
- Representative cat, bear, bunny, robot, and alien outputs were visually
  inspected after balanced layout/outline changes; transparency, punctuation,
  margins, and outline weight are coherent.
- Golden `cat-text-sample.webp` is lossless 512 x 512 WebP with SHA-256
  `8591f0dca51b1c8ec39765cb19ed5719c62b12825f9d0aef960452f9a84d23ee`.
- Local render baselines: 1.03 seconds for 10 stickers and 4.84 seconds for 50
  stickers, including matching thumbnails.
- Pack/sticker schemas and generated manifests/catalogues validate as JSON.
- Current-recipe static Release with CLI and shared Debug without CLI both pass
  the macOS external consumer. MSVC Debug is unsupported by the pinned ThorVG
  Conan recipe; Windows CI therefore verifies both linkage forms in Release.

## Known dependency constraint

ThorVG 0.15.16 must compile as C++17 on recent libc++ while MascotRender remains
C++20. Profiles record this package-scoped setting. ADR-003 requires the
workaround to be audited when ThorVG is upgraded.

## Remaining release gates

1. Select and authenticate a writable Conan remote. Only Conan Center is
   configured locally and it is not the project binary publishing destination.
2. After the remote is selected, upload the tested recipe/binaries, verify a
   clean remote consumer, tag `v0.1.0`, and record immutable recipe/package
   revisions.

## Product follow-up

The engineering golden is approved as a regression baseline, not as final
Product/Design approval of all generated art. M6 still requires full 50-sticker
coherence review. Matcher boundary/collision behavior belongs to the product
integration unless a reusable matcher is deliberately added to the engine.

The approved expansion direction is documented in `ROADMAP_3D_ANIMATION.md`:
stabilize scene/text contracts, add deterministic animation to current 2D packs,
advance to layered 2.5D, and only then add an optional Filament/GLB backend.
