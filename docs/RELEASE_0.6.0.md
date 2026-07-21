# MascotRender 0.6.0 release notes

Status: published production release. MascotRender is MIT-licensed; the public
Conan remote permits anonymous package downloads.

## Highlights

- Ships the owner-approved Congratulations Pop typography pack with 36 common
  celebration, achievement, milestone, and encouragement phrases.
- Adds four pack-local SIL Open Font License display voices, six composition
  systems, varied celebratory motifs, and pop, pulse, wobble, or float motion.
- Includes deterministic animated WebP recipes and reduced-motion equivalents
  with exact spelling, single-read typography, clean loop closure, and safe
  margins.
- Preserves readable output at 80 pixels as a stress-test floor, recommends
  100 pixels for product trays, and supports 160-pixel showcase rendering.
- Installs the approved Congratulations Pop source pack and generator with the
  Conan package so applications receive both the rendering engine and the
  production content.
- Retains Calendar Pop, the Human Character Library, Micro Reactions, 2D and
  layered 2.5D rendering, and the optional Filament/GLB backend from 0.5.0.

## Production evidence

The project-owner decision is recorded in
`contracts/congratulations-typography-owner-approval-v1.json`. It approves
exact spelling and punctuation, single-read typography, 36-phrase coverage,
family art direction, font/composition/motif variety, animation closure,
reduced motion, deterministic generation, and 80/100/160-pixel readability.

Release CI regenerates and validates the complete pack on Linux, macOS, and
Windows. The sanitizer job renders the review assets while checking the C++
engine for address and undefined-behavior errors. The external Conan consumer
also renders an installed animated Congratulations sticker before publication.

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
conan install --requires=mascotrender/0.6.0 --build=missing
```

Leave Conan Center enabled so public dependencies can resolve. Then call
`find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. The installed Congratulations
Pop pack is under `share/mascotrender/art/congratulations-pop-v1`.

## Compatibility

Version 0.6 is additive relative to 0.5. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, installed
production packs, and application-owned Trie selection remain compatible.
Filament stays opt-in, and all earlier immutable package releases remain
available.
