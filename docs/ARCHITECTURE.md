# MascotRender Architecture Direction

Status: normative direction for post-0.1 work. Existing 0.1 file-based APIs
remain supported while the behavioral contracts below are implemented.

## Compiler boundary

Applications provide identifiers and policy. Packs provide authored identity
and capabilities. Recipes provide intent. The compiler produces a resolved
scene and timeline that contain no unresolved semantic target names.

```text
Catalogue selection
  -> CharacterPackage + SemanticRecipe + RenderConfiguration
  -> capability negotiation
  -> deterministic compile
  -> resolved scene graph + timeline + accessibility metadata
  -> backend render
  -> encoder
  -> immutable asset + provenance record
```

The current `Engine::render(RenderRequest)` is the 0.1 vertical slice. A later
public API must add catalogues, package loading, capability inspection, compile,
and render operations only as corresponding behavior becomes tested. Empty
facade types are not a stable API.

## Internal module boundaries

| Module | Owns | Must not own |
|---|---|---|
| core | IDs, diagnostics, package loading, capability negotiation, compile IR | graphics backend details |
| vector | SVG/vector rasterization | phrase matching or identity policy |
| layered | parented nodes, pivots, depth, parallax | application catalogues |
| glb | GLB loading, materials, camera, lighting | screen-space caption implementation |
| animation | recipes, typed tracks, easing, sampling, reduced-motion policy | backend drawing |
| text | fonts, shaping/layout, safe areas, captions, alt-text metadata | mascot geometry |
| author | drafts, validation reports, package publication | production application state |
| cli | orchestration and human-readable diagnostics | unique rendering behavior |

## Capability negotiation

A package declares capabilities such as face expressions, gaze, articulated
hands, reactive shadows, full-body framing, 3D materials, or reduced-motion
alternatives. A recipe declares required and optional capabilities.

Compilation has only three valid outcomes:

1. all requirements resolve;
2. an explicitly declared fallback recipe resolves;
3. compilation fails with structured diagnostics.

Silently dropping a gesture, assistive device, caption, or accessibility rule
is forbidden.

## Catalogue boundary and Trie integration

Phrase matching is an application/catalogue concern, not renderer state:

```text
typed text -> Trie terminal -> phrase ID -> recipe ID
           -> selected character package -> render/cache lookup
```

Trie terminals store semantic phrase IDs. They do not contain one terminal per
character or per rendered asset. This keeps matching complexity independent of
the number of mascot identities.

## Determinism boundary

An immutable output key includes:

- engine and compiler profile versions;
- package content digest and package version;
- recipe digest and locale presentation;
- camera and output configuration;
- deterministic seed where variation is explicitly allowed;
- backend capability/profile identifier.

Wall-clock time, system fonts, unordered iteration, remote URLs, user identity
inference, and ambient backend settings cannot influence a build.

## Repository strategy

Keep one repository until component APIs stabilize. Use source directories,
CMake targets, namespaces, tests, and optional Conan components to enforce
boundaries. Extract repositories only when independent ownership or release
cadence provides a measurable benefit.
