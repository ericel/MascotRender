# MascotRender 0.1.0 release notes

Status: published. Release `v0.1.0`, the default desktop package matrix, and
optional Filament/GLB packages are available from the public MascotRender Conan
remote without consumer credentials. MascotRender is MIT-licensed.

## Supported package configurations

- C++20 consumers through Conan 2 and CMake's
  `MascotRender::MascotRender` target.
- macOS arm64 with AppleClang 21, Linux x86-64 with GCC 13 or Clang 18, and
  Windows x86-64 with MSVC 19.4x.
- Static and shared libraries. Release is supported on all three platforms;
  Debug is supported on macOS and Linux. The pinned ThorVG 0.15.16 Conan recipe
  explicitly rejects MSVC Debug.
- Optional `mascotrender` CLI through the `with_cli` Conan option.
- Optional Filament/GLB rendering through the `with_filament` Conan option on
  macOS arm64, Linux x86-64, and Windows x86-64.

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
scope. Complex shaping, fallback fonts, bidirectional text, and runtime network
fetching are not supported. Layered 2.5D timelines and the optional bounded GLB
pipeline are supported through the documented schemas; arbitrary untrusted 3D
content and general-purpose scene authoring are not.

Pack schema version 1 is stable for 0.1. The optional text `outline` field is
backward compatible: omitted outlines have width zero. Optional `text_slots`,
`placement`, and `preferred_slots` are also backward compatible; omitting them
retains the style safe area. Optional avoid regions and animation declarations
are likewise additive. Rendered bytes are
deterministic for identical sources, options, locked dependencies, and target
profile. Cross-platform golden checks compare decoded pixels with a documented
tolerance.

## Install and consume

Add the public hosted remote; consumer credentials are not required:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan install --requires=mascotrender/0.1.0 --build=missing
```

MascotRender's matching binary downloads from the public remote without
credentials. `--build=missing` lets Conan build any public third-party
dependency for which ConanCenter has no binary matching the consumer's compiler
profile. Consumers with those dependencies already cached may use
`--build=never` to require an entirely binary-only resolution.

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
