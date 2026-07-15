# MascotRender Product Roadmap

This roadmap translates the product vision into gated releases. Detailed work
items and historical engine milestones remain in `MILESTONES.md`.

## Foundation already proven

- installable C++20 library and CLI through Conan/CMake;
- deterministic vector rendering and WebP encoding;
- data-driven packs, fonts, captions, collision handling, and batch catalogues;
- typed animation timelines and animated WebP;
- parented layered 2.5D scenes, pivots, depth, parallax, and responsive shadows;
- optional Filament/GLB backend with one cross-backend robot identity contract;
- semantic phrase, motion, rig, and camera technical fixtures.

## Phase A — Open-source product baseline

Deliver the manifesto, vision, architecture boundaries, contribution/security
policies, public terminology, and behavior-backed API roadmap. Keep a monorepo
and preserve the installable 0.1 API while extracting internal targets.

Exit: a new contributor can explain what belongs to the engine, a pack, an
application adapter, and a rendering backend without Wahalao-specific rules.

## Phase B — Authored Human Pack v1

Create original licensed master artwork meeting the Human Pack visual and
representation standard. Declare pack-specific editorial goals across the
engine-supported identity dimensions; no individual age group is mandatory and
minor-coded characters require an explicit owner decision. Cover the chosen
bodies, complexions, hair, gender presentations, abilities, contexts,
expressions, poses, camera framings, small-size output, and reduced motion.
Record diverse review.

Exit not yet achieved. The front-facing five-identity vector foundation is
approved, but turnaround construction, complete semantic pose evidence, and
dimensional 2.5D proof remain production blockers.

## Phase C — Portable packages and public APIs

Implement bounded `.mascot` loading, package/capability inspection, Character
and Recipe Catalogues, compile/render configuration APIs, immutable asset keys,
and clear ABI/version rules. Extract CMake targets and introduce Conan
components only after consumer tests cover their dependency graph.

Exit: an unrelated application loads a verified package, selects a recipe,
checks capabilities, renders an asset, and handles a declared fallback without
using repository paths or internal JSON types.

## Phase D — Cross-backend human parity

Retarget every claimed canonical human to GLB, preserve assistive devices and
authored features, and validate measurable identity parity across vector,
layered, and 3D output. Expansion follows animation playback and accessibility
review.

Current result: all five technical GLB prototypes carry 16 clips and render
through Filament, but the owner rejected their artistic identity and
assistive-device parity. Exit requires production models that preserve each
authored face, body, hair, clothing, proportion, and device topology, followed
by a fresh artifact-bound visual approval.

## Phase E — Authoring and ecosystem

Build authoring APIs, inspection reports, editor workflows, localization,
plugin SDK boundaries, contribution templates, pack signing policy, and
community review. Keep engine and pack release cycles independent.

Exit: a third party can build, license, validate, review, and publish a pack
without changing MascotRender source.

## Phase F — Production consumers and scale

Integrate Wahalao through a thin adapter and phrase Trie. Add tiered core,
extended, and on-demand asset generation, sharded catalogues, cache/rollback,
telemetry under privacy policy, and additional Education, Medical, Sports,
Fantasy, and seasonal packs.

Exit: Wahalao and at least one unrelated application ship MascotRender-backed
characters; catalogue size does not multiply Trie complexity by mascot count.

## Content scale target

Prefer a compact reviewed library of approximately 50–100 semantic motion
recipes combined with 1,000+ localized phrase presentations. Do not create
1,000 nearly duplicated animations merely to satisfy a numerical goal.
