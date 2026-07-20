# MascotRender 0.4.0 release notes

Status: published production release. MascotRender is MIT-licensed; the public
Conan remote and GitHub Release assets permit anonymous downloads.

## Highlights

- Ships the owner-approved Micro Reactions family: Sprig, Cinder, Ripple,
  Orbit, Crumb, and Mallow.
- Adds 60 production animated WebP reactions, 60 authored static
  reduced-motion equivalents, 60 thumbnails, and six deterministic styled GLB
  models.
- Preserves identity-specific dimensional motion: leaf sway, ember flicker,
  gill ripple, orbital tilt, snack bounce, and puff float.
- Extends the storage-neutral bundle protocol with optional content-addressed
  GLB models while retaining compatibility with WebP-only consumers.
- Adds deterministic, approval-bound release archives that verify the complete
  190-object publish plan before writing a byte-stable ZIP and SHA-256 file.
- Publishes the immutable bundle `mascotrender-b1-dc088762e1b7` as a GitHub
  Release asset, independent of any consuming application or cloud provider.
- Retains the complete owner-approved canonical and Wave 2 Human Character
  Library and the existing flat 2D, layered 2.5D, animation, reduced-motion,
  and optional Filament rendering paths.

## Production evidence

The final Micro Reactions activation is bound to the exact reviewed source and
distribution hashes in:

- `contracts/micro-reactions-final-pack-owner-approval-v1.json`;
- `contracts/micro-orbit-final-glb-face-parity-owner-approval-v1.json`;
- `contracts/micro-reactions-styled-glb-family-owner-approval-v1.json`.

The release candidate contains six identities, 60 animated stickers, 60
reduced-motion equivalents, 60 thumbnails, six GLBs, and 190 staged
distribution objects. The final archive tool rejects unapproved candidates,
missing or extra objects, unsafe paths, byte-size mismatches, and SHA-256
mismatches.

The approved display guidance is 100 pixels by default, 80 pixels as the
minimum stress-test floor, and 160 pixels for comfortable showcase
presentation.

## Public content bundle

The GitHub Release provides:

- `mascotrender-micro-reactions-mascotrender-b1-dc088762e1b7.zip`;
- `mascotrender-micro-reactions-mascotrender-b1-dc088762e1b7.zip.sha256`.

The archive contains the immutable bundle metadata, stable channel pointer,
content-addressed WebP and GLB objects, publish plan, and permanent owner
approval. Consumers may host these files on GitHub, Firebase Storage, GCS, S3,
another CDN, or a local development server without changing the protocol.

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
conan install --requires=mascotrender/0.4.0 --build=missing
```

Leave Conan Center enabled so public dependencies can resolve. Then call
`find_package(MascotRender CONFIG REQUIRED)` and link
`MascotRender::MascotRender` from a C++20 target. Enable the optional 3D
package with `-o "mascotrender/*:with_filament=True"`.

## Compatibility

Version 0.4 is additive relative to 0.3. Existing C++ APIs, the
`MascotRender::MascotRender` CMake target, pack schema version 1, sticker-only
bundle consumers, and application-owned Trie selection remain compatible.
Filament stays opt-in. Existing package and content-bundle releases remain
immutable and available.
