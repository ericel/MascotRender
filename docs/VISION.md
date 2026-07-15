# MascotRender Vision

## Product definition

MascotRender is an open-source procedural character rendering engine. It
compiles versioned character packs and semantic recipes into deterministic
static or animated assets.

It is not a prompt wrapper, avatar identity inference service, or Wahalao-only
sticker subsystem.

```text
Character + Recipe + Camera + Output Configuration
                         |
                         v
                MascotRender compiler
                         |
                         v
             Scene graph + sampled timeline
                         |
            +------------+-------------+
            |            |             |
          Vector       Layered         GLB
            |            |             |
            +------------+-------------+
                         |
                         v
              Static or animated asset
```

## Product lines

The engine and character packs have independent identities and release cycles.

- `mascotrender-core`: contracts, compilation, diagnostics, determinism;
- `mascotrender-vector`: software vector rendering;
- `mascotrender-layered`: parented 2.5D animation and parallax;
- `mascotrender-glb`: optional 3D/GLB rendering;
- `mascotrender-animation`: semantic timelines and sampling;
- `mascotrender-text`: captions, layout, localization, accessibility;
- `mascotrender-cli`: validation, rendering, inspection, and packaging;
- `mascotrender-author`: future authoring APIs and editor support;
- `mascot-pack-*`: independently licensed Human, Robot, Cat, Education,
  Medical, Sports, Fantasy, and seasonal content.

These begin as CMake targets and Conan components in one repository. Separate
repositories are justified only after their public contracts and release
cadences stabilize.

## Stable conceptual API

Every backend receives the same four concepts:

1. a character identity and capability set;
2. a semantic recipe;
3. a camera/framing configuration;
4. an output configuration.

The compiler resolves semantic targets into concrete layers, joints, materials,
effects, and timeline tracks. Backends consume the compiled representation;
applications do not contain renderer-specific character rules.

## Initial applications

- Wahalao uses phrase matching and mascot selection for chat assets.
- Education packs can provide teachers, learners, subjects, and feedback.
- Healthcare packs can provide respectful professionals, patients, guidance,
  and accessible communication.
- Games can use fantasy or sports packs for lightweight expressive UI.
- Customer-support and assistant products can use branded mascot identities.

## Success measures

- unrelated C++20 consumers install through Conan and CMake;
- reviewed inputs produce deterministic immutable outputs;
- identity remains recognizable across supported backends;
- 2D poster rendering targets less than 100 ms on the reference profile;
- a compact reviewed motion library supports at least 1,000 localized phrase
  presentations without duplicating animation logic;
- third parties can author and validate packs without modifying engine code;
- Wahalao ships as the first production proof without owning engine contracts.

## Research direction

The project may support work on backend-independent character contracts,
semantic animation retargeting, representation-aware authoring, deterministic
asset pipelines, and measurable cross-backend identity parity.
