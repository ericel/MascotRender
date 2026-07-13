# MascotRender 0.1.0 release notes

Status: release candidate; public Conan upload is blocked until the owner
selects a writable remote and supplies the project license text.

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
  outlined glyphs, and safe-area enforcement.
- Transparent deterministic WebP assets and thumbnails.
- Deterministic pack generation and staged batch bundle scripts.
- Decoded-pixel golden regression coverage and external Conan consumer tests.

## Trust and compatibility boundaries

Version 0.1 accepts trusted local pack content. Canonical path containment and
schema checks are defense-in-depth, not a promise that hostile SVG/font inputs
are safe to process. Run third-party content in an application-controlled
sandbox. Only local static `.ttf` fonts and the documented SVG subset are in
scope. Complex shaping, fallback fonts, bidirectional text, animation, and
runtime network fetching are not supported.

Pack schema version 1 is stable for 0.1. The optional text `outline` field is
backward compatible: omitted outlines have width zero. Rendered bytes are
deterministic for identical sources, options, locked dependencies, and target
profile. Cross-platform golden checks compare decoded pixels with a documented
tolerance.

## Install and consume

Once uploaded to an approved Conan remote:

```python
def requirements(self):
    self.requires("mascotrender/0.1.0")
```

```cmake
find_package(MascotRender CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE MascotRender::MascotRender)
target_compile_features(my_application PRIVATE cxx_std_20)
```
