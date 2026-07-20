# MascotRender Bundle Protocol v1

MascotRender's public distribution boundary is a storage-neutral directory of
JSON documents and content-addressed assets. It has no dependency on a
consuming application, cloud, CDN, or application database.

The protocol separates four concerns:

1. A phrase dictionary maps normalized chat triggers to semantic phrase IDs.
2. A catalogue maps phrase and character variants to rendered assets.
3. An immutable release binds exact catalogue and dictionary hashes.
4. A small mutable channel pointer selects the current immutable release.

The JSON Schemas in `schemas/bundle-*.schema.json` are the normative document
shapes. `tools/mascot_bundle.py` performs the semantic, path, size, and hash
checks that JSON Schema alone cannot provide.

## Source bundle

A generated source bundle has this layout:

```text
bundle/
├── assets/<pack-id>/<sticker-id>.webp
├── thumbnails/<pack-id>/<sticker-id>.webp
├── reduced-motion/<pack-id>/<sticker-id>.webp
├── models/<identity-id>.glb                 # optional
├── catalogue.json
├── dictionary.json
└── build-report.json
```

Every sticker has:

- a stable `phrase_id`, such as `chat.no-wahala`;
- a primary WebP;
- a static thumbnail;
- an explicit static semantic equivalent for reduced-motion users;
- dimensions, encoded byte size, and a SHA-256 digest for every asset.

Reduced motion is an authored output, not a client-side instruction to freeze an
arbitrary animation frame.

Bundles may also declare an optional `models[]` catalogue. Each model binds an
identity ID to a GLB path, SHA-256 digest, byte size, semantic-node count, and
the animation clip names exposed by that model. Model objects are validated and
content-addressed exactly like rendered sticker assets. Consumers that only
support WebP can ignore this optional catalogue without changing sticker
selection behavior.

## Semantic dictionary and Trie integration

Dictionary terminal nodes contain semantic phrase IDs, never filenames or
sticker IDs:

```json
{
  "trigger": "no wahala",
  "match": "unicode-word-boundary",
  "phrase_ids": ["chat.no-wahala"]
}
```

An application can compile these entries into a Trie. Matching returns an
intent-like phrase ID. Selection then happens separately:

```text
message text
  -> normalized Unicode Trie match
  -> semantic phrase ID
  -> eligible character/recipe variants
  -> user and reduced-motion preferences
  -> concrete catalogue asset
```

This prevents the Trie from becoming coupled to a bundle version, CDN URL,
character demographic, or storage provider. Applications may add their own
ranking and deterministic rotation policies without changing the public
protocol.

## Validate and stage a release

Validate the source bundle:

```bash
python3 tools/mascot_bundle.py validate \
  --bundle generated/bundle
```

Stage a provider-neutral release:

```bash
python3 tools/mascot_bundle.py stage \
  --bundle generated/bundle \
  --output generated/distribution \
  --channel stable \
  --force
```

The staged layout is:

```text
distribution/
├── objects/sha256/<prefix>/<hash>.webp
├── objects/sha256/<prefix>/<hash>.glb
├── bundles/<bundle-id>/catalogue.json
├── bundles/<bundle-id>/dictionary.json
├── bundles/<bundle-id>/release.json
├── channels/stable.json
└── publish-plan.json
```

Assets are addressed by their content hash. Identical bytes are uploaded once,
and old messages can continue to reference an immutable object even after a
new release is activated.

For incremental staging, provide the preceding plan:

```bash
python3 tools/mascot_bundle.py stage \
  --bundle generated/bundle \
  --output generated/distribution-next \
  --channel stable \
  --previous-plan generated/distribution/publish-plan.json \
  --force
```

`publish-plan.json` marks every object as `upload` or `skip` and assigns its
content type and cache policy. It is a local deployment instruction, not a
public runtime document.

## Publish and activate

A storage adapter must:

1. Upload all `upload` objects except the channel pointer.
2. Verify uploaded sizes or SHA-256 metadata.
3. Upload `channels/<channel>.json` last.

The generated policies are:

- immutable objects and release documents:
  `public,max-age=31536000,immutable`;
- mutable channel pointer:
  `no-cache,max-age=0,must-revalidate`.

Clients resolve:

```text
channels/stable.json
  -> bundles/<bundle-id>/release.json
  -> catalogue.json + dictionary.json
  -> objects/sha256/...
```

They should verify hashes before accepting a newly downloaded release. A failed
activation must leave the last verified release available.

## Retention and garbage collection

Never delete an object merely because it is absent from the newest release.
Historical messages, offline clients, and pinned application releases may still
reference it.

Garbage collection is safe only after computing reachability from:

- every retained channel and immutable release;
- application-pinned bundle IDs;
- message-history retention requirements;
- any rollback window.

Provider-specific uploaders belong in integrations or consuming applications.
They consume `publish-plan.json`; they do not change this protocol.
