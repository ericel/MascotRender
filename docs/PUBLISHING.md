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

- Linux x86-64 GCC 13 Release, static library with CLI.
- Linux x86-64 GCC 13 Release, shared library without CLI.
- Windows x86-64 MSVC 19.4x Release, static library with CLI.
- Windows x86-64 MSVC 19.4x Release, shared library without CLI.

Every matrix job creates and runs the package consumer, uploads the recipe and
its binary, removes `mascotrender` from the runner cache, and runs the external
consumer again with `--build=never` against the configured remote. A job is not
successful merely because upload completed.

## Release sequence

1. Merge a green release-candidate pull request into protected `main`.
2. Manually dispatch `Publish Conan package` for the exact recipe version.
3. Record recipe and package revisions from the successful run.
4. Verify a separate authenticated consumer can resolve the hosted remote.
5. Create the matching `vX.Y.Z` tag and GitHub release.

Pushing a `v*` tag runs the same publication workflow. The tag version must
match `conanfile.py`; a mismatch fails before authentication or upload.

Consumers configure the remote and install normally:

```bash
conan remote add mascotrender https://ericel.jfrog.io/artifactory/api/conan/conan-local
conan remote login mascotrender <jfrog-username>
conan install --requires=mascotrender/0.1.0 --remote=mascotrender --build=never
```

The JFrog repository currently requires read credentials. Do not commit a
password or access token; obtain consumer credentials from the repository
owner. Public unauthenticated installation requires anonymous read access in
JFrog or acceptance into Conan Center.
