# MR-102 Layered 2.5D Animation Review

Product/Design approved the corrected robot hop on 2026-07-14.

The first review accepted the depth-layered parallax technique but rejected the
hop because its contact shadow did not communicate the midpoint apex strongly
enough and the side-panel geometry was visually ambiguous. The correction:

- retimed the apex to the middle of the cycle;
- contracts and fades the ground shadow with height;
- keeps explicit side-panel pixels visible at rest, apex, and loop end; and
- preserves a clear top margin around the antenna.

The accepted asset is `tests/golden/robot-2_5d-animated-hop.webp`: a lossless
512 x 512, 1200 ms, 15-frame looping WebP with SHA-256
`c656d66e8d12bea49cebdcd45d2f12d3bba18fc45dbdac6ddce9c99168fe9674`.
CTest verifies animation metadata and timestamps, compares every decoded RGBA
sample against the accepted golden, and separately asserts the reviewed shadow,
panel-presence, and top-clearance properties.

The encoded asset was intentionally revised during MR-114 to apply the shared
`robot-004` palette and proportion contract. This changes the art pixels but
does not change the previously approved motion timing or depth behavior.
MR-115 revises the art pixels again for identity-contract v2 and makes the
sparkle explicitly screen-fixed; hop timing, shadow response, and loop closure
remain unchanged.
