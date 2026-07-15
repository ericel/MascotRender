# MascotRender 0.2.0 release notes

Status: published production release. MascotRender is MIT-licensed and the
published Conan remote permits anonymous reads.

## Highlights

- Production-approved canonical Human Pack family H01, H04, H07, H12, and H13
  with exact artifact-hash binding and explicit public-release authorization.
- Deterministic flat 2D, layered 2.5D, and optional Filament/GLB 3D outputs with
  cross-backend identity and art-direction parity.
- Five semantic framings, neutral turnarounds, isolated expressions, nine
  semantic poses, depth/parallax motion, and reduced-motion equivalents.
- Semantically decomposed prosthesis, wheelchair, hearing-aid, and rollator
  geometry that remains part of each character's identity and motion rig.
- Shared screen-space caption composition across 2D, 2.5D, and 3D.
- Portable `.mascot` package specification and deterministic package authoring
  validation.

## Production evidence

The release gate is recorded in
`generated/canonical-human-production-review/release-review.json`. Every
technical and production gate passes, all backends are
`public-release-approved`, and the owner's decision is bound to the exact eight
review-artifact SHA-256 hashes. A changed render cannot inherit this approval.

Pull-request CI validates C++ compilation, unit and external-consumer tests,
sanitizers, deterministic sticker generation, Human Pack contracts, and the
optional Filament backend across macOS, Linux, and Windows. Publication CI then
creates the supported Conan binaries, uploads them, logs out, removes the local
package, and repeats the consumer test with `--build=never`.

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
conan install --requires=mascotrender/0.2.0 --build=missing
```

Then use `find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. Enable the optional 3D package
with `-o "mascotrender/*:with_filament=True"`.

## Compatibility

Version 0.2 is additive relative to 0.1. Existing C++ rendering APIs and pack
schema version 1 remain compatible. Filament stays opt-in, so default consumers
do not acquire the 3D dependency graph. The trusted-local-content security
boundary documented for 0.1 remains unchanged.
