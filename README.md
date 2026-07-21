# MascotRender

Licensed under the [MIT License](LICENSE).

See [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), and the
[Community Code of Conduct](CODE_OF_CONDUCT.md).

MascotRender is an open-source, local-first C++20 procedural character
rendering library and CLI. It compiles structured character packs and semantic
recipes into deterministic static and animated assets. It has no application,
cloud, CDN, or storage-provider dependency; consuming products remain separate
integrations.

The project ships a production-ready C++20 engine spanning deterministic 2D,
layered 2.5D, animation, reduced-motion output, and optional Filament/GLB 3D.
The current public package is `mascotrender/0.7.0`, consumable from Conan 2
and CMake as `MascotRender::MascotRender`. It composes versioned JSON-selected
SVG layers and optional pack-declared static TTF text through ThorVG, then
returns a WebP encoded by libwebp. The example pack ships Changa One under the
SIL Open Font License 1.1; platform font discovery is not used.

## Project documents

- [Manifesto](docs/MANIFESTO.md)
- [Product vision](docs/VISION.md)
- [Product roadmap](docs/ROADMAP.md)
- [Architecture direction](docs/ARCHITECTURE.md)
- [Human Pack visual and representation standard](docs/HUMAN_PACK_VISUAL_STANDARD.md)
- [Human Pack v1 art brief](docs/HUMAN_PACK_V1_ART_BRIEF.md)
- [Human Pack production recovery plan](docs/HUMAN_PACK_PRODUCTION_RECOVERY.md)
- [Approved canonical human family concept](art/concepts/human-pack-v1/family-gate-v1.png)
- [Canonical human semantic SVG masters](art/human-pack-v1/masters/generation-manifest.json)
- [Portable `.mascot` package specification](docs/MASCOT_PACKAGE_SPEC.md)
- [Software Design Document v0.2](MascotRender_SDD_v0.2.docx)
- [Milestones and initial backlog](docs/MILESTONES.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Pack format v1](docs/PACK_FORMAT.md)
- [Storage-neutral bundle protocol v1](docs/BUNDLE_PROTOCOL.md)
- [Micro Reactions product pack](docs/MICRO_REACTIONS.md)
- [Workday Reactions 96-sticker development pack](docs/WORKDAY_REACTIONS.md)
- [Mascot generation and batch pipeline](docs/CONTENT_PIPELINE.md)
- [M6 sticker review record](docs/M6_REVIEW.md)
- [0.1.0 release notes](docs/RELEASE_0.1.0.md)
- [0.2.0 release notes](docs/RELEASE_0.2.0.md)
- [0.3.0 release notes](docs/RELEASE_0.3.0.md)
- [0.4.0 release notes](docs/RELEASE_0.4.0.md)
- [0.5.0 release notes](docs/RELEASE_0.5.0.md)
- [0.6.0 release notes](docs/RELEASE_0.6.0.md)
- [0.7.0 release notes](docs/RELEASE_0.7.0.md)
- [Conan publication runbook](docs/PUBLISHING.md)
- [Third-party notices](docs/THIRD_PARTY_NOTICES.md)
- [Pipeline benchmarks](docs/BENCHMARKS.md)
- [Current status](docs/STATUS.md)
- [Scene, animation, and 3D expansion plan](docs/ROADMAP_3D_ANIMATION.md)
- [Human mascot identity and representation system](docs/HUMAN_MASCOT_SYSTEM.md)

The original v0.1 SDD is retained unchanged as the review baseline.

## Install with Conan 2

The MascotRender remote permits anonymous reads. Keep Conan Center enabled for
the public dependency graph and compile ThorVG 0.15.16 as C++17; MascotRender
and consuming applications remain C++20:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan install --requires=mascotrender/0.7.0 \
  --remote=mascotrender \
  --remote=conancenter \
  --build=missing \
  -s:h compiler.cppstd=20 \
  -s:h "thorvg/*:compiler.cppstd=17"
```

Then call `find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender`. Conan downloads a matching published
MascotRender binary when one exists; `--build=missing` covers public
third-party dependencies or compiler profiles for which Conan Center has no
matching binary.

## Verified vertical slice

The current implementation proves the distribution and graphics path:

1. `conan create` produces static or shared `mascotrender/0.7.0` packages.
2. The external `test_package` installs, links, renders, and writes a WebP.
3. Unit tests decode the WebP and verify dimensions, alpha, and repeatability.
4. Public headers expose no ThorVG, libwebp, JSON, or CLI types.
5. Pack-local font loading, text fitting, and 512/256 pixel text rendering are
   covered by the unit suite.

Balanced wrapping, outlined text, and a decoded-pixel golden are complete. The
hosted compiler/sanitizer matrix is green. The protected Conan publication
workflow uploads and then proves a logged-out exact-package re-download;
release `v0.7.0` and its tested binaries are public. A fresh Conan cache may
build public third-party dependencies that ConanCenter does not provide as
matching binaries.

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

python3 tools/mascot_bundle.py validate \
  --bundle generated/bundle

python3 tools/mascot_bundle.py stage \
  --bundle generated/bundle \
  --output generated/distribution \
  --channel stable \
  --force
```

The result includes 512 px assets, 256 px thumbnails, explicit static
reduced-motion equivalents, a SHA-256 catalogue, a semantic phrase dictionary,
deterministic build report, and a verified review gallery
at `generated/bundle/review/index.html`. The review directory also contains a
side-by-side animated playback page at `animation-review.html`, a 50-row CSV
sign-off checklist, and a machine-readable verification summary. All three
generation/review scripts plus the bundle validator/stager are installed under
`share/mascotrender/tools` by CMake and Conan.
Pull-request CI uploads the complete bundle and gallery as a downloadable
14-day artifact.

## Use the production Calendar Pop pack

Release `v0.5.0` installs the approved Calendar Pop source pack under
`share/mascotrender/art/calendar-pop-v1`. It contains seven weekdays, twelve
months, four seasons, four OFL display fonts, semantic trigger aliases, and
animated plus reduced-motion recipes. The pack remains structured input for
MascotRender rather than an application-specific opaque asset bundle.

Maintainers can regenerate its source and review evidence with:

```bash
python3 tools/generate_calendar_typography_pack.py \
  --mascotrender build/Release/mascotrender \
  --force
```

The production contract enforces exact spelling, one fitted glyph layout per
word, animation closure, safe margins, small-display readability, and
project-owner approval.

## Use the production Congratulations Pop pack

Release `v0.6.0` installs the approved 36-sticker Congratulations Pop source
pack under `share/mascotrender/art/congratulations-pop-v1`. It combines four
OFL display-font voices, six composition systems, semantic trigger aliases,
motif variety, animated WebP recipes, and reduced-motion equivalents.

Maintainers can regenerate its source and review evidence with:

```bash
python3 tools/generate_congratulations_pack.py \
  --mascotrender build/Release/mascotrender \
  --force
```

The production contract enforces exact spelling and punctuation, single-read
typography, clean loop closure, safe margins, deterministic generation, and
80/100/160-pixel readability across all 36 phrases.

## Use the production Workday Reactions pack

Release `v0.7.0` installs the approved 96-sticker Workday Reactions source pack
under `share/mascotrender/art/workday-reactions-v1`. Pace, an original
red-panda office mascot, performs common workflow, meeting, decision, teamwork,
results, time, energy, and office-humor reactions. The pack includes explicit
Trie triggers, animated WebP recipes, reduced-motion equivalents, eight
caption compositions, four OFL display-font voices, and 25 visual prop
archetypes.

Maintainers can regenerate the source and review evidence with:

```bash
python3 tools/generate_workday_reactions_pack.py \
  --mascotrender build/Release/mascotrender \
  --force
```

The production contract binds the exact owner-reviewed artifacts and enforces
96-way semantic completeness, Pace identity, caption/character balance,
80/100/160-pixel readability, loop closure, reduced motion, deterministic
generation, and exact-phrase Trie coverage.

## Download the production Micro Reactions pack

Release `v0.4.0` publishes the approved six-identity Micro Reactions family as
a provider-neutral GitHub Release ZIP. It contains 60 animated reactions, 60
reduced-motion equivalents, 60 thumbnails, six styled GLBs, immutable release
metadata, the semantic dictionary, and a stable channel pointer. Verify the
companion SHA-256 file, extract the archive, and serve the directory from any
static file host or object-storage provider.

Maintainers can reproduce the archive from the approved candidate:

```bash
python3 tools/package_bundle_release.py \
  --distribution generated/micro-reactions-production-distribution \
  --source-bundle generated/micro-reactions-production-bundle \
  --approval contracts/micro-reactions-final-pack-owner-approval-v1.json \
  --output \
    mascotrender-micro-reactions-mascotrender-b1-dc088762e1b7.zip
```

The command fails unless the source metadata, all 190 staged objects, and the
exact distribution file set match the project-owner approval.

## Generate the full-body human pilot matrix

Human mascots use a separate appearance contract rather than a `race` geometry
switch. Complexion material, undertone, facial proportions, hair texture/style,
body proportions, clothing, and editorial representation metadata remain
independent. Validate and generate the 12-identity × 12-phrase pilot with:

```bash
python3 tools/validate_human_pilots.py

python3 tools/generate_human_pilots.py \
  --output generated/human-pilots \
  --count 12 \
  --force

python3 tools/build_human_pilot_review.py \
  --input generated/human-pilots \
  --mascotrender build/Release/mascotrender \
  --force
```

The output contains 144 animated sticker specifications and 12 deterministic
contact sheets at `generated/human-pilots/review/index.html`. These simplified
procedural humans are permanently classified as technical fixtures and are not
production art. Production Human Pack assets must meet
`docs/HUMAN_PACK_VISUAL_STANDARD.md`, use original licensed artwork, and pass
diverse human review; fixture validation cannot promote them.

## Build and review the canonical Human Pack candidate

The front-facing H01/H04/H07/H12/H13 vector family is an owner-approved
foundation. The current turnaround and GLB conversion is explicitly blocked
from production. Generate its vector, layered, and GLB candidates and run the
technical plus owner-decision gate with:

```bash
python3 tools/generate_canonical_human_masters.py --force
python3 tools/author_canonical_human_blender.py
python3 tools/build_canonical_human_review.py --force
python3 tools/build_canonical_human_production_review.py --force
```

The authored `.blend` sources remain beside their production-review GLBs. The
reviewer exercises all five GLBs through the optional Filament backend and
writes technical evidence plus the artifact-bound owner decision to
`generated/canonical-human-production-review/release-review.json`. File counts,
distinct hashes, palette presence, semantic nodes, and successful renders prove
technical execution only; visual approval remains an explicit owner decision.
Earlier rejected and partially approved bundles remain recorded in the review
history, while the current eight-sheet bundle is owner-approved and hash-bound.

The production reviewer also writes `animation-review.html`, real animated WebP
loops, static reduced-motion semantic equivalents, and an animation storyboard.
Cross-backend identity parity and family art-direction parity are separate gates;
public release requires both.

Human Pack v1 is owner-approved for public release. The approval is bound to the
exact eight current review-sheet hashes. CI requires fresh cross-platform review
runs to reach `technical-validation-success`; it separately validates the bound
approval contract as `public-release-approved` / `public-release`. A rerender
with different pixel hashes is deliberately not allowed to inherit owner approval.

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

The optional 3D configuration uses the platform-specific Filament lockfile:

```bash
conan create . \
  -pr:h profiles/macos-armv8-release \
  -pr:b default \
  --lockfile=locks/macos-armv8-filament-release.lock \
  --build=missing \
  -o '&:with_filament=True'
```

Equivalent pinned Filament lockfiles are checked in for Linux x86-64 and
Windows x86-64. macOS is therefore an explicit native validation target, not an
unvalidated default.

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
    self.requires("mascotrender/0.7.0")
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
