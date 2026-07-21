# MascotRender 0.7.0 release notes

Status: production release candidate. MascotRender is MIT-licensed; the public
Conan remote permits anonymous package downloads.

## Highlights

- Ships the owner-approved Workday Reactions pack with 96 common workplace
  phrases across workflow, meetings, decisions, teamwork, results, time,
  energy, and office humor.
- Introduces Pace, an original red-panda office mascot with a stable
  terracotta, cream, navy, and teal identity system.
- Adds 19 poses, 32 moods, 26 motion semantics, eight caption compositions,
  four SIL OFL display-font voices, 25 visual prop archetypes, and 93 semantic
  prop/effect concepts.
- Includes 96 deterministic animated WebP recipes, 96 reduced-motion
  equivalents, 96 tray thumbnails, and explicit normalized Trie triggers.
- Validates exact text, 18-pixel-or-greater frame margins, clean loop closure,
  and 80/100/160-pixel readability; 100 pixels remains the recommended product
  default.
- Installs the canonical pack, generator, contract, matrix, fonts, and owner
  approval with CMake and Conan.
- Retains Congratulations Pop, Calendar Pop, the Human Character Library,
  Micro Reactions, 2D and layered 2.5D rendering, and optional Filament/GLB.

## Production evidence

The project-owner decision is recorded in
`contracts/workday-reactions-owner-approval-v1.json`. It binds the exact
complete-family sheet, eight category sheets, small-display sheet, motion
sheet, and browser playback review hashes approved on 2026-07-21.

The Workday regression performs two independent complete generations and
byte-compares both source and review trees within each render runtime and
compares the generated source tree with the canonical production source. The
owner-approved review hashes remain bound as runtime-specific evidence rather
than a cross-platform encoder invariant. The regression also validates all sticker
documents through the C++ CLI and checks every animated asset for real WebP
animation chunks, visible mid-cycle change, exact loop closure, and safe frame
margins. The external Conan consumer renders an installed Workday sticker and
confirms it is genuinely animated.

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
conan install --requires=mascotrender/0.7.0 \
  --remote=mascotrender \
  --remote=conancenter \
  --build=missing \
  -s:h compiler.cppstd=20 \
  -s:h "thorvg/*:compiler.cppstd=17"
```

ThorVG 0.15.16 is intentionally compiled as C++17 to avoid its `identity`
symbol colliding with C++20 `std::identity` on recent libc++ releases;
MascotRender and its consumers remain C++20. Leave Conan Center enabled so
public dependencies can resolve. Then call
`find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. The installed Workday pack is
under `share/mascotrender/art/workday-reactions-v1`.

## Compatibility

Version 0.7 is additive relative to 0.6. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, installed
production packs, and application-owned Trie selection remain compatible.
Filament stays opt-in, and all earlier immutable package releases remain
available.
