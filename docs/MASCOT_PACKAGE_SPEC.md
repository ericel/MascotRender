# Portable `.mascot` Package Specification

Status: draft v1 direction. The 0.1 engine continues to accept trusted local
pack directories while this container is implemented and security-reviewed.

## Purpose

A `.mascot` file is a deterministic, versioned container for one character
identity and its authored capabilities. Recipes and localized phrase catalogues
may be embedded or supplied separately. The container is portable across
applications and render backends.

## Container

Version 1 uses a ZIP-compatible container with UTF-8 path names and a required
root `manifest.json`. Implementations must write entries in bytewise path order,
use fixed timestamps and permissions, and reject duplicate, absolute,
backslash, parent-traversal, symlink, device, and external-URL entries.

Custom compression, encryption, executable content, and network resolution are
outside v1. Package signing may be added without changing character semantics.

```text
character.mascot
  manifest.json
  identity.json
  appearance.json              optional when included by identity.json
  rig.json
  anchors.json                 optional
  expressions.json             optional
  poses.json                   optional
  animations.json              optional
  effects.json                 optional
  materials.json               optional
  recipes/                     optional embedded recipes
  assets/vector/
  assets/raster/
  assets/glb/
  fonts/
  accessibility/
  provenance/
  licenses/
```

## Manifest responsibilities

The manifest declares:

- package ID, semantic version, format version, and character ID;
- required engine/API range;
- entry points and SHA-256 for every declared file;
- supported backends, outputs, framings, and semantic capabilities;
- default locale and available locale presentations;
- provenance and license document paths;
- whether the package is a technical fixture, review candidate, or production
  release.

Unknown required capabilities fail loading. Unknown optional metadata may be
preserved. A package cannot claim production status without provenance,
licensing, accessibility metadata, and recorded review state.

## Engine loading model

Loading and rendering are separate operations. A loader verifies paths, size
limits, hashes, JSON/schema versions, and capabilities before making a package
available to catalogues. Rendering never opens undeclared files or resolves
network resources.

## Versioning

- format version changes when container interpretation changes;
- package semantic version changes when authored character content changes;
- immutable releases never replace bytes under an existing version;
- the complete package digest participates in output cache keys;
- application catalogues select versions and rollback policy explicitly.

## Licensing

The engine license does not silently license pack artwork. Every package
contains machine-readable provenance and human-readable license documents for
art, fonts, models, textures, and other redistributed material.
