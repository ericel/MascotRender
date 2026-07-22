# MascotRender 0.8.0 release notes

Status: production release candidate. MascotRender is MIT-licensed; the public
Conan remote permits anonymous package downloads.

## Highlights

- Ships the owner-approved Christmas & New Year Glow pack with 30 exact phrases:
  18 Christmas reactions and 12 New Year reactions.
- Adds nine seasonal pattern families and 30 distinct hero-motif families,
  including trees, holly, wreaths, ornaments, gifts, cocoa, snow, fireworks,
  clocks, countdowns, calendars, disco elements, and fresh-start symbols.
- Combines four SIL OFL display-font voices, six composition systems, and pop,
  pulse, wobble, and float motion while retaining a single readable phrase.
- Includes deterministic animated WebP recipes and explicit reduced-motion
  equivalents for all 30 stickers.
- Validates exact spelling and punctuation, Christmas/New Year category
  separation, 19-pixel-or-greater animation clearance, visible midpoint motion,
  exact loop closure, and 80/100/160-pixel readability.
- Installs the canonical pack, generator, contract, phrase matrix, fonts, and
  hash-bound owner approval through both CMake and Conan.
- Retains Workday Reactions, Congratulations Pop, Calendar Pop, the Human
  Character Library, Micro Reactions, 2D and layered 2.5D rendering, and
  optional Filament/GLB.

## Production evidence

The project-owner decision is recorded in
`contracts/christmas-new-year-glow-owner-approval-v1.json`. It binds the exact
complete-family sheet, small-display sheet, motion sheet, and browser playback
review hashes approved on 2026-07-22.

The pack regression performs two independent complete generations, compares
the canonical source tree, validates every recipe through the C++ CLI, and
checks every animated WebP for real animation chunks, visible mid-cycle change,
exact loop closure, and safe frame margins.

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
conan install --requires=mascotrender/0.8.0 \
  --remote=mascotrender \
  --remote=conancenter \
  --build=missing \
  -s:h compiler.cppstd=20 \
  -s:h "thorvg/*:compiler.cppstd=17"
```

Then call `find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. The installed seasonal pack
is under `share/mascotrender/art/christmas-new-year-glow-v1`.

## Compatibility

Version 0.8 is additive relative to 0.7. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, installed
production packs, and application-owned Trie selection remain compatible.
Filament stays opt-in, and all earlier immutable package releases remain
available.
