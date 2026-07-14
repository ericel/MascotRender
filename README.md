# MascotRender

Licensed under the [MIT License](LICENSE).

MascotRender is a local-first C++20 library and CLI for compiling structured
mascot packs into deterministic static and animated sticker assets.

The project has completed the C++20 static-rendering MVP and is extending its
backend-neutral scene model toward positioned text, animation, 2.5D, and 3D.
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
- [M6 sticker review record](docs/M6_REVIEW.md)
- [0.1.0 release notes](docs/RELEASE_0.1.0.md)
- [Conan publication runbook](docs/PUBLISHING.md)
- [Third-party notices](docs/THIRD_PARTY_NOTICES.md)
- [Pipeline benchmarks](docs/BENCHMARKS.md)
- [Current status](docs/STATUS.md)
- [Scene, animation, and 3D expansion plan](docs/ROADMAP_3D_ANIMATION.md)

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
hosted compiler/sanitizer matrix is green. The protected Conan publication
workflow uploads and then proves a clean anonymous remote consumer; release
`v0.1.0` and its tested binaries are public.

Pack v1 also supports backward-compatible named text slots. Stickers can select
an explicit slot such as `top` or request deterministic `auto` placement with
an ordered preference list; authored avoid regions keep captions off important
art. Optional bounded timelines now drive body-bounce and text-pop overlays into
deterministic animated WebP, while batch thumbnails remain static posters. These
are the first stable contracts in the planned scene/2.5D/optional-Filament
expansion.

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

python3 tools/build_sticker_review.py \
  --input generated/bundle \
  --expected-count 50 \
  --force
```

The result includes 512 px assets, 256 px thumbnails, a SHA-256 catalogue,
phrase dictionary, deterministic build report, and a verified review gallery
at `generated/bundle/review/index.html`. The review directory also contains a
side-by-side animated playback page at `animation-review.html`, a 50-row CSV
sign-off checklist, and a machine-readable verification summary. All three
scripts are installed under `share/mascotrender/tools` by CMake and Conan.
Pull-request CI uploads the complete bundle and gallery as a downloadable
14-day artifact.

## Layered 2.5D acceptance example

The `examples/robot-2_5d` pack splits a robot into parented shadow, body, side
panel, head, antenna, face, and effect nodes. Render the approved flat view and
a deterministic parallax view with the same C++ engine:

```bash
mascotrender render \
  --pack examples/robot-2_5d/pack.json \
  --sticker examples/robot-2_5d/stickers/flat.json \
  --output robot-flat.webp

mascotrender render \
  --pack examples/robot-2_5d/pack.json \
  --sticker examples/robot-2_5d/stickers/parallax-right.json \
  --output robot-parallax-right.webp

mascotrender render \
  --pack examples/robot-2_5d/pack.json \
  --sticker examples/robot-2_5d/stickers/animated-hop.json \
  --output robot-animated-hop.webp

mascotrender render \
  --pack examples/robot-2_5d/pack.json \
  --sticker examples/robot-2_5d/stickers/dimensional-caption-proof.json \
  --output robot-dimensional.webp
```

At zero view the layered pack is byte-identical to `pack-flat.json`. The shifted
view applies inherited depth parallax while captions remain screen-fixed. The
animated example uses typed node and camera tracks for squash/stretch, delayed
head and antenna follow-through, a responsive shadow, and moving parallax. The
review-only `dimensional` pose makes depth visible in a still with a stronger
cast shadow, warm side planes, face gradient, rim light, and a shifted view;
the existing `front` pose remains the flat compatibility control.

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

Checked-in Release profiles and hosted package-consumer jobs cover macOS
arm64/AppleClang 21, Linux x86-64/GCC 13, and Windows x86-64/MSVC 19.4x. The
root `conan.lock` is the macOS graph; Linux and Windows use the lockfiles under
`locks/`.

## Optional Filament boundary

The default package has no 3D dependency. The first E4 slice reserves an
explicit opt-in package identity and CMake switch:

```bash
conan install . -o "&:with_filament=True" --build=missing
```

That option requires the pinned `filament/1.74.0` package and sets
`MASCOTRENDER_WITH_FILAMENT=ON`. Filament is not currently available from
ConanCenter, so `recipes/filament` wraps the checksum-pinned official desktop
archives and exposes `filament::filament` plus `filament::gltfio`. The wrapper
is validated on macOS arm64, Linux x86-64, and Windows x86-64. The internal
proof loads GLB resources, validates
semantic anchors, and reads transparent RGBA pixels from a fixed orthographic
camera. The default `with_filament=False` graph remains fully installable from
public dependencies and does not download or link Filament.

Hosted macOS and Linux jobs execute the pixel-rendering tests through Metal and
Mesa/Vulkan respectively. The hosted Windows image has no Vulkan ICD, so its
job validates archive integrity, MSVC compile/link, Filament's NOOP runtime,
and the installed preview executable; real Windows rendering requires a
Vulkan-capable driver on the consumer machine.

MR-112 includes the deterministic `examples/robot-004/robot-004.glb` proof with
four clips (`idle`, `hello`, `hop`, `celebrate`), six named facial morphs, and a
caption anchor. The authored rounded-square model uses the approved 2D/2.5D
gold, orange, mint, cream, and navy visual contract. Filament development
builds can generate five lossless review frames, an upright white-background
PNG, four 13-frame looping animated WebPs, pose/motion sheets, a browser
playback page, and machine-checked review metadata with:

```bash
python tools/render_robot_glb_review.py \
  --renderer build/filament/cmake/mascotrender-glb-preview \
  --input examples/robot-004/robot-004.glb \
  --output generated/robot-004-review
```

MR-113 keeps captions as a shared, screen-space 2D composition pass. The same
pack/sticker recipe and collision-aware resolved layout are used by flat 2D,
layered 2.5D, and Filament 3D. Generate the three-backend acceptance sheet with:

```bash
python tools/render_caption_backend_review.py \
  --renderer-2d build/Release/mascotrender \
  --renderer-3d build/filament/cmake/mascotrender-glb-preview \
  --output generated/mr113-caption-review
```

The review fails if flat and layered `t = 0` pixels differ or if any backend
does not render the caption inside the selected safe area.

MR-114 adds a versioned `robot-004` character identity contract shared by the
SVG and GLB packs. Exact palette values, required features, and six normalized
proportion measurements are checked against the actual SVG XML and GLB mesh
data rather than trusting authored metadata. Validate it and generate the
identity review sheet with:

```bash
python tools/validate_character_identity.py \
  --contract examples/robot-004/identity.json \
  --pack examples/robot-2_5d/pack.json \
  --flat-pack examples/robot-2_5d/pack-flat.json \
  --glb examples/robot-004/robot-004.glb

python tools/render_character_identity_review.py \
  --renderer-2d build/Release/mascotrender \
  --renderer-3d build/filament/cmake/mascotrender-glb-preview \
  --output generated/mr115-parity-review
```

Captions remain one separate screen-space layer in all three outputs.
MR-115 evolves the contract to version 2 with explicit antenna, eye, body-frame,
and sparkle subcontracts. The sparkle is no longer GLB geometry: packs mark it
`screen_space`, and the Filament preview composites the same SVG after the 3D
pass, keeping identical bounds as camera span changes.

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
