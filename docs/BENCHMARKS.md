# Pipeline benchmark baseline

Measured 2026-07-13 on macOS arm64 with AppleClang 21, Python 3.14, ThorVG
0.15.16, and libwebp 1.6.0. The Release build used 512 x 512 lossy WebP assets
at quality 90 plus 256 x 256 thumbnails. Times are wall-clock measurements from
`/usr/bin/time -p`; generated output was written to the local APFS volume.

| Workload | Generate | Validate and render | Assets | Encoded bytes |
|---|---:|---:|---:|---:|
| 1 identity / 10 stickers | 0.57 s | 1.03 s | 20 | 259,663 |
| 5 identities / 50 stickers | 0.30 s | 4.84 s | 100 | 1,305,940 |

Generation time is dominated by filesystem startup and font copies, so the
larger run can be faster after the filesystem cache is warm. The render baseline
is approximately 10.3 stickers/second or 20.7 encoded assets/second. These
numbers establish a regression reference, not a cross-machine performance SLA.

Reproduce the 50-sticker run:

```bash
/usr/bin/time -p python3 tools/generate_mascot_packs.py \
  --output generated/mascots --count 5 --seed 20260713 --force

/usr/bin/time -p python3 tools/render_mascot_packs.py \
  --input generated/mascots \
  --output generated/bundle \
  --mascotrender build/Release/mascotrender \
  --force
```
