# MascotRender 0.3.0 release notes

Status: published production release. MascotRender is MIT-licensed and the
published Conan remote permits anonymous reads.

## Highlights

- Expands the production Human Character Library from five to fifteen authored
  identities: H01-H15.
- Adds the owner-approved Wave 2 cohort H02, H03, H05, H06, H08, H09, H10,
  H11, H14, and H15 with hash-bound production activation.
- Ships deterministic flat 2D, layered 2.5D, and optional Filament/GLB output
  for Wave 2, including four-view turnarounds, semantic poses and expressions,
  native animation, and reduced-motion equivalents.
- Adds uniform deterministic identity rotation after Unicode Trie phrase
  matching. The selector performs no demographic inference and permits an
  explicit character choice to override rotation.
- Adds the 15-identity by 41-phrase production matrix and animation-aware
  80/96/100-pixel display profiles without changing canonical 512-pixel assets.
- Adds varied caption placement, phrase semantics, accessibility metadata,
  typography review tooling, and Wahalao development-bundle generation.
- Installs both approved human-art cohorts, their contracts and content, and
  the Wave 2 generation/review tools in CMake and Conan packages.

## Production evidence

The project-owner approvals are bound to exact reviewed artifact hashes in:

- `contracts/human-wave2-owner-production-decision-v1.json`;
- `contracts/human-wave2-cross-backend-art-direction-owner-approval-v1.json`;
- `contracts/human-wave2-production-activation-v1.json`;
- `contracts/human-development-matrix-gate-status-v6.json`.

All ten Wave 2 identities pass neutral-turnaround, cross-backend identity,
cross-backend art-direction, GLB semantic pose/expression, animation, and
reduced-motion gates. All fifteen canonical identities are production-eligible
with uniform selection weight.

H05 orientation-and-mobility white-cane review and H08 cultural-detail
head-covering review remain documented post-release advisories. This release
does not claim specialist approval. A later qualified review may result in a
corrective release.

## Supported Conan configurations

- macOS arm64, AppleClang 21, Release, static library with CLI.
- Linux x86-64, GCC 13, Release, static library with CLI or shared library.
- Windows x86-64, MSVC 19.4x, Release, static library with CLI or shared library.
- Optional Filament/GLB static packages with CLI on macOS arm64, Linux x86-64,
  and Windows x86-64.

## Install

No consumer credentials are required:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan install --requires=mascotrender/0.3.0 --build=missing
```

When a fresh cache lacks matching public dependency binaries, leave Conan
Center enabled and use `--build=missing` instead. Then call
`find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. Enable the optional 3D package
with `-o "mascotrender/*:with_filament=True"`.

## Compatibility

Version 0.3 is additive relative to 0.2. Existing C++ rendering APIs, the
`MascotRender::MascotRender` CMake target, and pack schema version 1 remain
compatible. Filament stays opt-in, so default consumers do not acquire the 3D
dependency graph. Existing `mascotrender/0.2.0` package revisions remain
immutable and available.
