# Workday Reactions

Workday Reactions is a character-led 96-sticker workplace communication pack.
It is intentionally broader than a formal “business” pack: the vocabulary
covers real daily chat in product teams, remote meetings, operations, sales,
freelance work, and office humor.

## Character

Pace (`pace-red-panda-001`) is an original red-panda office mascot. Identity
anchors are the terracotta head, cream muzzle and brow marks, navy eye mask,
ringed tail, teal tie, and navy outline. Props, poses, expressions, and caption
layouts may change; these anchors may not.

## Scope

The 96 phrases are divided evenly across eight domains:

- workflow;
- meetings;
- decisions;
- teamwork;
- results and commercial progress;
- time and availability;
- energy and workload;
- office humor.

The candidate contains four SIL OFL font voices, eight composition systems,
19 poses, 32 moods, 26 authored motion semantics, 25 visual prop archetypes,
and 93 semantic prop/effect concepts. Every phrase has explicit normalized
Trie triggers rather than relying on substring guessing.

## Generate and review

```bash
python3 tools/generate_workday_reactions_pack.py \
  --mascotrender build/Release/mascotrender \
  --force
```

The canonical sources are written to `art/workday-reactions-v1`. Review-only
outputs are written to `generated/workday-reactions-v1-review` and include:

- `contact-sheet.png` for the complete family;
- eight category sheets;
- `small-display-80-100-160.png`;
- `motion-sample-sheet.png`;
- `animation-review.html` with all 96 live animated WebPs;
- `review.json` and the hash-bound `owner-approval.json`.

## Gate state

The project owner approved the exact generated art and playback hashes on
2026-07-21. The approval covers exact text, Pace identity, workplace semantics,
layout and prop variety, 80/100/160px readability, animation playback, reduced
motion, Trie-trigger completeness, and deterministic generation. The pack is
approved for public production use. Review-image and encoded-WebP hashes are
recorded as render-runtime-specific because image-library and encoder builds
can produce byte-distinct, visually equivalent output across operating
systems. Every runtime still enforces source-tree determinism, two identical
generation passes, visible animation, loop closure, safe margins, and the full
semantic contract.
