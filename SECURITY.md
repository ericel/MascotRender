# Security Policy

## Current support boundary

The 0.1 engine accepts trusted, repository-controlled local pack directories.
It rejects path traversal and external URLs, but it is not a sandbox for
arbitrary untrusted content.

The draft `.mascot` authoring tool verifies declared hashes, bounded sizes,
sorted unique safe paths, and provenance/license references. `.mascot` files
are not engine inputs until the bounded C++ loader and its security tests are
complete.

## Reporting a vulnerability

Use the repository's private GitHub vulnerability-reporting channel when it is
available. Include the affected version, platform, minimal reproduction,
security impact, and whether public disclosure has already occurred. Do not
publish pack payloads or exploit details in a public issue before maintainers
have had a reasonable opportunity to investigate.

Security-sensitive areas include package/path handling, malformed SVG/font/GLB
inputs, decompression and allocation bounds, integer overflow, unsafe external
resource resolution, archive ambiguity, and deterministic-cache key confusion.

## Non-security reports

Crashes caused only by documented trusted-input misuse may be normal defects
rather than vulnerabilities, but should still receive a minimal reproduction
through the normal issue tracker.
