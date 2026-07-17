#!/usr/bin/env python3
"""Generate deterministic semantic GLB review counterparts for Wave 2 humans."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import generate_canonical_human_glbs as glb_generator
from generate_human_wave2_candidates import WAVE2


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "art" / "human-pack-wave2" / "candidates")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.input.resolve()
    glb_generator.MASTERS.update(WAVE2)
    for master_id in sorted(WAVE2):
        identity_path = root / master_id / "identity.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        source_sha = hashlib.sha256(identity_path.read_bytes()).hexdigest()
        payload = glb_generator.build_glb(master_id, identity, source_sha)
        output = root / master_id / f"{master_id}-review.glb"
        if args.check:
            if not output.is_file() or output.read_bytes() != payload:
                raise ValueError(f"Wave 2 GLB is missing or not deterministic: {master_id}")
        else:
            output.write_bytes(payload)
            second = glb_generator.build_glb(master_id, identity, source_sha)
            if payload != second:
                raise ValueError(f"Wave 2 GLB generation is not deterministic: {master_id}")
    print(f"{'validated' if args.check else 'generated'} {len(WAVE2)} Wave 2 GLB review counterparts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
