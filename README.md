# MascotRender

MascotRender is a local-first C++20 library and CLI for compiling structured
mascot packs into deterministic static sticker assets.

The project has completed the local M1/M2 vertical slices and started M3 text.
The current pre-release package is `mascotrender/0.1.0`, consumable from Conan 2
and CMake as `MascotRender::MascotRender`. It composes versioned JSON-selected
SVG layers and optional pack-declared static TTF text through ThorVG, then
returns a WebP encoded by libwebp. The example pack ships Changa One under the
SIL Open Font License 1.1; platform font discovery is not used.

## Project documents

- [Software Design Document v0.2](MascotRender_SDD_v0.2.docx)
- [Milestones and initial backlog](docs/MILESTONES.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Pack format v1](docs/PACK_FORMAT.md)
- [Mascot generation and batch pipeline](docs/CONTENT_PIPELINE.md)
- [0.1.0 release notes](docs/RELEASE_0.1.0.md)
- [Third-party notices](docs/THIRD_PARTY_NOTICES.md)
- [Pipeline benchmarks](docs/BENCHMARKS.md)
- [Current status](docs/STATUS.md)

The original v0.1 SDD is retained unchanged as the review baseline.

## Verified vertical slice

The current implementation proves the distribution and graphics path:

1. `conan create` produces static or shared `mascotrender/0.1.0` packages.
2. The external `test_package` installs, links, renders, and writes a WebP.
3. Unit tests decode the WebP and verify dimensions, alpha, and repeatability.
4. Public headers expose no ThorVG, libwebp, JSON, or CLI types.
5. Pack-local font loading, text fitting, and 512/256 pixel text rendering are
   covered by the unit suite.

Balanced wrapping, outlined text, and a decoded-pixel golden are complete. The
remaining release path is hosted compiler/sanitizer verification, owner license
text, and selection of a writable Conan remote.

## Generate a demo sticker bundle

After building the CLI, generate five mascot identities and render 50 stickers:

```bash
python3 tools/generate_mascot_packs.py \
  --output generated/mascots --count 5 --seed 20260713 --force

python3 tools/render_mascot_packs.py \
  --input generated/mascots \
  --output generated/bundle \
  --mascotrender build/Release/mascotrender \
  --force
```

The result includes 512 px assets, 256 px thumbnails, a SHA-256 catalogue,
phrase dictionary, and deterministic build report. Both scripts are installed
under `share/mascotrender/tools` by CMake and Conan.

## Bootstrap build

The checked-in macOS profile keeps MascotRender at C++20 while compiling the
pinned ThorVG 0.15.16 dependency as C++17 to avoid its collision with the C++20
`std::identity` symbol on recent libc++ releases.

```bash
conan create . \
  -pr:h profiles/macos-armv8-release \
  -pr:b default \
  --lockfile=conan.lock \
  --build=missing
```

Checked-in Release profiles cover macOS arm64/AppleClang 21, Linux
x86-64/GCC 13, and Windows x86-64/MSVC 19.4x. The GitHub Actions smoke workflow
uses the Linux and Windows profiles and their platform-specific lockfiles; the
root `conan.lock` is the locally verified macOS graph.

## Use from another Conan project

Add the package requirement to the consuming recipe:

```python
def requirements(self):
    self.requires("mascotrender/0.1.0")
```

Link the canonical imported target:

```cmake
find_package(MascotRender CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE MascotRender::MascotRender)
target_compile_features(my_application PRIVATE cxx_std_20)
```

The in-memory pack-rendering API is intentionally small:

```cpp
#include <fstream>
#include <mascotrender/mascotrender.hpp>

mascotrender::Engine engine;
mascotrender::RenderRequest request{
    "path/to/pack.json",
    "path/to/sticker.json",
    {}
};
auto rendered = engine.render(request);
if (!rendered) {
    // rendered.error().code and rendered.error().message are dependency-free.
    return 1;
}

const auto& image = rendered.value();
std::ofstream out{"sample.webp", std::ios::binary};
out.write(reinterpret_cast<const char*>(image.bytes.data()),
          static_cast<std::streamsize>(image.bytes.size()));
```

`render_sample` remains available as an M1 smoke entry point. New applications
should use the versioned pack/spec API above. The schemas and a working layered
SVG/text example are installed under `share/mascotrender` in the Conan package.

## Developer build and test

```bash
conan install . \
  -pr:h profiles/macos-armv8-release \
  -pr:b default \
  --lockfile=conan.lock \
  --build=missing

cmake --preset conan-release -DMASCOTRENDER_BUILD_TESTS=ON
cmake --build --preset conan-release
ctest --preset conan-release --output-on-failure
```

Render the sample from the CLI:

```bash
build/Release/mascotrender render-sample --output sample.webp
build/Release/mascotrender render \
  --pack examples/cat/pack.json \
  --sticker examples/cat/stickers/text-sample.json \
  --output sample-from-pack.webp
build/Release/mascotrender validate \
  --pack examples/cat/pack.json \
  --sticker examples/cat/stickers/text-sample.json
```
