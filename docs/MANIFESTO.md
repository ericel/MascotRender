# MascotRender Manifesto

MascotRender exists to make expressive digital characters durable, portable,
and programmable.

## Characters are authored identities, not disposable images

A mascot is more than one picture. It is a reusable identity with proportions,
features, colors, a rig, expressions, motion, effects, camera rules, and a
history of approved revisions. Products should be able to render that identity
again without asking a generative model to reinterpret it.

## Recipes should express intent

Applications should request a greeting, apology, celebration, warning, or
other semantic action. They should not have to reproduce backend-specific
pixel instructions. A recipe describes intent; a character pack supplies
capabilities; a renderer produces the asset.

## Determinism is a product feature

The same versioned character, recipe, render configuration, and engine profile
must produce the same reviewed result. Determinism enables testing, moderation,
accessibility review, caching, rollback, provenance, and long-lived character
intellectual property.

## Representation must be authored and reviewed

Human diversity cannot be reduced to a palette swap or a race enum. Complexion,
facial features, hair, age presentation, body shape, clothing, assistive
technology, and cultural presentation are independent authored attributes.
Social identity labels may support coverage audits, but they never infer
geometry and are never inferred from a user.

People from represented communities must participate in production approval.
Passing a schema is not proof that a depiction is respectful.

## One character contract should survive many renderers

Vector, layered 2.5D, and GLB backends should preserve the same recognizable
identity. Backend capability differences must be declared, validated, and
reviewable. Silent degradation is a defect.

## Text and communication remain accessible

Captions, alternate text, contrast, safe areas, animation timing, motion
reduction, and small-size readability are part of the asset contract rather
than application-specific cleanup.

## Open source should create an ecosystem

MascotRender is independent infrastructure. No consuming application defines
its product identity or architectural boundary. Schools, healthcare products,
games, digital assistants, support tools, and community projects should be
able to use the same engine with different packs.

The engine, authoring tools, and pack specification should be open and
inspectable. Character packs remain independently versioned and explicitly
licensed so communities can contribute without coupling their release cycles
to the engine.

## The long-term promise

MascotRender aims to become dependable open-source infrastructure for
expressive characters: small enough to embed, strict enough to trust, and
general enough to outlive any one application or visual backend.
