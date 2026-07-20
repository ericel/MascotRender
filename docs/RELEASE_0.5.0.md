# MascotRender 0.5.0 release notes

Status: published production release. MascotRender is MIT-licensed; the public
Conan remote permits anonymous package downloads.

## Highlights

- Ships the owner-approved Calendar Pop typography pack with seven weekdays,
  twelve months, and four seasons.
- Adds four pack-local SIL Open Font License display voices with varied
  rotation, placement, color, and pulse, wobble, or float motion.
- Adds renderer-native depth and highlight shells that share one fitted glyph
  layout, preventing decorative extrusion from reading as duplicated letters.
- Adds ordered text blocks and authored text transforms while preserving
  compatibility with existing single-caption sticker definitions.
- Includes 23 deterministic animated WebP recipes, reduced-motion equivalents,
  256-pixel thumbnails, semantic IDs, and Trie-ready aliases including
  `autumn` and `fall`.
- Installs the approved Calendar Pop source pack and generator with the Conan
  package so consumers receive the production content rather than only the
  underlying rendering API.
- Retains the Human Character Library, Micro Reactions family, 2D and layered
  2.5D rendering, and optional Filament/GLB backend from 0.4.0.

## Production evidence

The project-owner decision is recorded in
`contracts/calendar-typography-owner-approval-v1.json`. It approves exact
spelling, single-read depth treatment, family coherence, font and color
variety, animation closure, reduced motion, deterministic generation, and
80/100/160-pixel readability.

Release CI regenerates and compares the complete Calendar Pop source and review
trees on Linux and macOS. Sanitizer CI renders and validates the complete pack
once while checking the C++ engine for address and undefined behavior errors.

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
conan install --requires=mascotrender/0.5.0 --build=missing
```

Leave Conan Center enabled so public dependencies can resolve. Then call
`find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. The installed Calendar Pop
pack is under `share/mascotrender/art/calendar-pop-v1`.

## Compatibility

Version 0.5 is additive relative to 0.4. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, Human Pack,
Micro Reactions, and application-owned Trie selection remain compatible.
Filament stays opt-in, and all earlier immutable package releases remain
available.
