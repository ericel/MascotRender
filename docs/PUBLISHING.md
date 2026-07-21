# Conan publication

MascotRender publishes immutable Conan recipe and binary revisions through the
`Publish Conan package` GitHub Actions workflow. Publication is intentionally
separate from pull-request validation.

## Repository configuration

The workflow requires these GitHub Actions repository secrets:

- `CONAN_URL`: writable Conan 2 remote URL.
- `CONAN_PASSWORD`: API token or password for the remote.
- `CONAN_USER`: username for the remote account.

## Published configurations

- macOS arm64 AppleClang 21 Release, static library with CLI.
- Linux x86-64 GCC 13 Release, static library with CLI.
- Linux x86-64 GCC 13 Release, shared library without CLI.
- Windows x86-64 MSVC 19.4x Release, static library with CLI.
- Windows x86-64 MSVC 19.4x Release, shared library without CLI.
- macOS arm64, Linux x86-64, and Windows x86-64 static packages with the
  optional Filament GLB renderer and CLI enabled.

The Filament publication jobs first publish the checksum-pinned
`filament/1.74.0` wrapper for their platform, then publish the matching
Filament-enabled MascotRender binary. Every matrix job logs out, removes the
published packages from its runner cache, and runs the external consumer again
with `--build=never`. This verifies that anonymous users can download the exact
published binary rather than rebuilding it locally. A job is not successful
merely because upload completed.

Windows publication validates the installed preview executable and Filament
NOOP runtime because the hosted runner has no Vulkan ICD. Metal on macOS and
Mesa/Vulkan on Linux provide the full pixel-rendering gates. Windows consumers
need a Vulkan-capable driver to use the renderer.

## Release sequence

1. Merge a green release-candidate pull request into protected `main`.
2. Create and push the matching `vX.Y.Z` tag. The tag starts the protected
   `Publish Conan package` workflow and must match the recipe version.
3. Record recipe and package revisions from the successful run.
4. Verify a separate anonymous consumer can resolve the hosted remote.
5. Build the approval-bound content ZIP with
   `tools/package_bundle_release.py`.
6. Create the GitHub release from the already-published tag and attach the ZIP
   plus its SHA-256 file.

Pushing a `v*` tag runs the same publication workflow. The tag version must
match `conanfile.py`; a mismatch fails before authentication or upload.

Consumers configure the remote and install normally:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan install --requires=mascotrender/0.7.0 --build=missing
```

The JFrog repository permits anonymous reads but requires authenticated writes.
The install command leaves all configured remotes enabled so locked public
dependencies can resolve from Conan Center while MascotRender resolves from
the hosted JFrog remote. `--build=missing` is required for a genuinely fresh
cache when ConanCenter lacks third-party binaries matching the selected
compiler profile. Publication CI uses `--build=never` only after building the
dependency graph, then evicts the just-published MascotRender/Filament packages
and logs out; that specifically proves the hosted package binaries can be
downloaded anonymously without silently rebuilding them.
