# Golden render baseline

`cat-text-sample.webp` is the lossless 512 x 512 engineering baseline for the
version-1 cat pack, Changa One text, balanced wrapping, and outlined glyphs. It
was generated and visually inspected on 2026-07-13 with MascotRender 0.1.0,
ThorVG 0.15.16, and libwebp 1.6.0 on macOS arm64.

The test compares decoded BGRA pixels instead of encoded WebP bytes. A mean
channel error up to 2 and at most 5% of pixels differing by more than 8 channel
levels accommodates small supported-platform raster differences while still
detecting layout, layer, color, transparency, and outline regressions.

Changing this asset requires an intentional renderer or art revision and an
updated entry in `docs/STATUS.md`. Product/Design approval of the complete
50-sticker set remains the separate M6 coherence gate.

`robot-2_5d-animated-hop.webp` is the lossless 512 x 512, 1200 ms,
15-frame MR-102 motion baseline. Its 2026-07-14 MR-114 revision intentionally
aligns the robot palette and normalized geometry with
`examples/robot-004/identity.json`; the approved motion, responsive shadow,
side-panel continuity, and loop timing remain unchanged. CTest compares all
decoded frames and metadata.
