# MascotRender 0.9.0 release notes

Status: production release candidate. MascotRender is MIT-licensed; the public
Conan remote permits anonymous package downloads.

## Highlights

- Ships the owner-approved Wise Owl Academy illustrated pack with 100 exact
  education phrases across ten semantic categories.
- Preserves Sage as one stable mascot identity while using scene-specific
  props, multi-character compositions, category palettes, and six caption
  composition systems instead of repeated text swaps.
- Includes deterministic animated WebP recipes, visible midpoint motion, exact
  loop closure, semantic Trie triggers, and reduced-motion equivalents for all
  100 stickers.
- Locks the ten approved golden compositions byte-for-byte and validates all
  100 scenes at the 100-pixel production default, 160-pixel showcase size, and
  80-pixel stress floor.
- Enforces an immutable minimum frame margin of 16 pixels. Automatic cropping
  may not tighten below that bound, and platform effects may not extend beyond
  the validated union bounds.
- Installs the canonical art pack, three generation stages, content matrix,
  contracts, and hash-bound owner decision through both CMake and Conan.
- Retains the Human Character Library, Micro Reactions, Calendar Pop,
  Congratulations Pop, Workday Reactions, Christmas & New Year Glow, 2D and
  layered 2.5D rendering, and optional Filament/GLB.

## Production evidence

The project-owner decision is recorded in
`contracts/education-wise-owl-production-owner-approval-v2.json`. It binds the
complete 100-sticker contact sheet, the all-100 100-pixel sheet, long-copy
80/100/160 review, full motion sheet, playback catalogue, and ten category
sheets by SHA-256.

The generator verifies the decision hashes against a fresh candidate, checks
all 100 animations for real midpoint changes and exact loop closure, preserves
all ten golden reduced-motion hashes, and rejects any frame with less than the
16-pixel safety margin. Two independent complete generations produced
byte-identical source and review trees.

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
conan install --requires=mascotrender/0.9.0 \
  --remote=mascotrender \
  --remote=conancenter \
  --build=missing \
  -s:h compiler.cppstd=20 \
  -s:h "thorvg/*:compiler.cppstd=17"
```

Then call `find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. The installed production pack
is under `share/mascotrender/art/education-wise-owl-illustrated-v2`.

## Compatibility

Version 0.9 is additive relative to 0.8. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, installed
production packs, and application-owned Trie selection remain compatible.
Filament stays opt-in, and all earlier immutable package releases remain
available.
