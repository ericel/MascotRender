# Contributing to MascotRender

MascotRender welcomes engine, tooling, documentation, test, and independently
licensed character-pack contributions.

Read `docs/MANIFESTO.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` before
changing public contracts. Wahalao-specific behavior belongs in an application
adapter rather than the engine.

## Engineering changes

- preserve C++20 compatibility and dependency-free public headers;
- add behavior and tests before exposing a public API;
- keep vector, layered, GLB, animation, text, authoring, and application
  concerns within their documented boundaries;
- preserve deterministic ordering, fixed sampling, explicit seeds, local
  resources, and immutable output metadata;
- return structured diagnostics for invalid content;
- update schemas, format documentation, decisions, and consumer tests when a
  contract changes;
- do not broaden the trusted-pack boundary without a security review.

Run at minimum:

```bash
cmake -S . -B build/Release
cmake --build build/Release
ctest --test-dir build/Release --output-on-failure
conan create . -pr:h profiles/macos-armv8-release -pr:b default \
  --lockfile=conan.lock --build=missing
```

Use the corresponding pinned Linux or Windows host profile when changing
platform-sensitive behavior.

## Character-pack and art changes

Every redistributed asset needs explicit provenance and a compatible license.
Do not submit copied reference artwork, undeclared fonts, generated assets with
unclear rights, or remote-resource dependencies.

Human artwork must follow `docs/HUMAN_PACK_VISUAL_STANDARD.md`. Coverage labels
support audit and review; they must not drive stereotyped geometry or infer
anything about a user. Production claims require the recorded human,
accessibility, animation, small-size, and backend-parity gates.

Technical fixtures must be visibly classified and cannot be promoted to
production merely because automated checks pass.

## Review expectations

Keep changes scoped, explain compatibility impact, identify generated files,
and include the commands used for validation. Golden updates require an
intentional renderer or art revision plus review evidence.
