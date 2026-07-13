# MascotRender 0.1.0 release notes

Status: release candidate; public Conan upload is blocked until the owner
selects and authenticates a writable remote. MascotRender is MIT-licensed.

## Supported package configurations

- C++20 consumers through Conan 2 and CMake's
  `MascotRender::MascotRender` target.
- macOS arm64 with AppleClang 21, Linux x86-64 with GCC 13 or Clang 18, and
  Windows x86-64 with MSVC 19.4x.
- Static and shared libraries. Release is supported on all three platforms;
  Debug is supported on macOS and Linux. The pinned ThorVG 0.15.16 Conan recipe
  explicitly rejects MSVC Debug.
- Optional `mascotrender` CLI through the `with_cli` Conan option.

## Included MVP capabilities

- Deterministic schema-versioned JSON pack and sticker loading.
- Pack-local SVG composition, named expressions and poses, and seeded effects.
- Approved pack-local static TTF loading with no platform font lookup.
- Largest-valid whole-point text fitting, balanced wrapping, configurable
  outlined glyphs, named text slots, deterministic auto placement, and
  avoid-region-aware safe-area enforcement.
- Transparent deterministic static or animated WebP assets and static poster
  thumbnails, with bounded timelines, body bounce, text pop, and a 256 MiB
  retained BGRA frame-buffer safety ceiling.
- Deterministic pack generation and staged batch bundle scripts.
- Decoded-pixel golden regression coverage and external Conan consumer tests.

## Trust and compatibility boundaries

Version 0.1 accepts trusted local pack content. Canonical path containment and
schema checks are defense-in-depth, not a promise that hostile SVG/font inputs
are safe to process. Run third-party content in an application-controlled
sandbox. Only local static `.ttf` fonts and the documented SVG subset are in
scope. Complex shaping, fallback fonts, bidirectional text, authored skeletal
clips, 2.5D/3D, and runtime network fetching are not supported.

Pack schema version 1 is stable for 0.1. The optional text `outline` field is
backward compatible: omitted outlines have width zero. Optional `text_slots`,
`placement`, and `preferred_slots` are also backward compatible; omitting them
retains the style safe area. Optional avoid regions and animation declarations
are likewise additive. Rendered bytes are
deterministic for identical sources, options, locked dependencies, and target
profile. Cross-platform golden checks compare decoded pixels with a documented
tolerance.

## Install and consume

Add the hosted remote and authenticate with JFrog read credentials:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan remote login mascotrender <jfrog-username>
```

Then require the package from the consuming recipe:

```python
def requirements(self):
    self.requires("mascotrender/0.1.0")
```

```cmake
find_package(MascotRender CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE MascotRender::MascotRender)
target_compile_features(my_application PRIVATE cxx_std_20)
```
