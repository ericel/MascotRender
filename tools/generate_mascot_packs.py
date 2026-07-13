#!/usr/bin/env python3
"""Generate deterministic, schema-v1 MascotRender demo packs.

The generator is intentionally standard-library-only. It creates vector layers,
sticker specifications, and pack-local copies of the approved Changa One font.
It never downloads assets or depends on platform fonts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


GENERATOR_VERSION = 4
MASK64 = (1 << 64) - 1


@dataclass(frozen=True)
class Palette:
    primary: str
    secondary: str
    dark: str
    light: str
    accent: str


PALETTES = (
    Palette("#FF9F43", "#F47B35", "#26324A", "#FFF0D9", "#FFD84D"),
    Palette("#6CC5D3", "#3996A8", "#173B57", "#E6FBFF", "#FF718D"),
    Palette("#A98BFF", "#7659D6", "#30244F", "#F2ECFF", "#64E6B3"),
    Palette("#70CF76", "#3A9B52", "#203D36", "#E8FFE9", "#FFD052"),
    Palette("#FF7FA5", "#D94C7C", "#462641", "#FFF0F5", "#6ED7FF"),
    Palette("#FFD166", "#E49B36", "#3C3042", "#FFF7DA", "#7AE1D2"),
)

SPECIES = ("cat", "bear", "bunny", "robot", "alien")

PHRASES = (
    ("hello", "HELLO!", "happy", "front"),
    ("nice-one", "NICE ONE", "happy", "round"),
    ("you-got-this", "YOU GOT THIS!", "happy", "front"),
    ("no-wahala", "NO WAHALA", "sleepy", "round"),
    ("well-done", "WELL DONE!", "happy", "front"),
    ("big-mood", "BIG MOOD", "sleepy", "round"),
    ("lets-go", "LET'S GO!", "surprised", "front"),
    ("thank-you", "THANK YOU", "happy", "round"),
    ("oh-wow", "OH, WOW!", "surprised", "front"),
    ("no-stress", "NO STRESS", "sleepy", "round"),
)


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def svg(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">\n'
        f"{body.rstrip()}\n"
        "</svg>\n"
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def shadow_layer(palette: Palette) -> str:
    return svg(
        f'<ellipse cx="256" cy="382" rx="142" ry="26" fill="{palette.dark}" '
        'fill-opacity="0.24"/>'
    )


def body_layer(species: str, palette: Palette, round_pose: bool) -> str:
    x = 132 if round_pose else 122
    width = 248 if round_pose else 268
    top = 130 if round_pose else 118
    height = 260 if round_pose else 272
    parts: list[str] = []

    if species == "cat":
        parts.extend(
            (
                f'<path d="M{x + 24} 178 L{x + 62} 72 L{x + 114} 164 Z" fill="{palette.secondary}"/>',
                f'<path d="M{x + width - 114} 164 L{x + width - 62} 72 L{x + width - 24} 178 Z" fill="{palette.secondary}"/>',
            )
        )
    elif species == "bear":
        parts.extend(
            (
                f'<circle cx="{x + 48}" cy="142" r="50" fill="{palette.secondary}"/>',
                f'<circle cx="{x + width - 48}" cy="142" r="50" fill="{palette.secondary}"/>',
                f'<circle cx="{x + 48}" cy="142" r="24" fill="{palette.light}"/>',
                f'<circle cx="{x + width - 48}" cy="142" r="24" fill="{palette.light}"/>',
            )
        )
    elif species == "bunny":
        parts.extend(
            (
                f'<rect x="{x + 42}" y="48" width="58" height="152" rx="29" fill="{palette.secondary}"/>',
                f'<rect x="{x + width - 100}" y="48" width="58" height="152" rx="29" fill="{palette.secondary}"/>',
                f'<rect x="{x + 60}" y="70" width="22" height="105" rx="11" fill="{palette.light}"/>',
                f'<rect x="{x + width - 82}" y="70" width="22" height="105" rx="11" fill="{palette.light}"/>',
            )
        )
    elif species == "robot":
        parts.extend(
            (
                f'<rect x="248" y="62" width="16" height="68" rx="8" fill="{palette.dark}"/>',
                f'<circle cx="256" cy="55" r="19" fill="{palette.accent}"/>',
                f'<rect x="{x - 16}" y="190" width="32" height="84" rx="16" fill="{palette.secondary}"/>',
                f'<rect x="{x + width}" y="190" width="32" height="84" rx="16" fill="{palette.secondary}"/>',
            )
        )
    elif species == "alien":
        parts.extend(
            (
                f'<path d="M180 150 Q150 92 126 85" fill="none" stroke="{palette.dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<path d="M332 150 Q362 92 386 85" fill="none" stroke="{palette.dark}" stroke-width="14" stroke-linecap="round"/>',
                f'<circle cx="126" cy="85" r="22" fill="{palette.accent}"/>',
                f'<circle cx="386" cy="85" r="22" fill="{palette.accent}"/>',
            )
        )

    radius = 82 if species == "robot" else 112
    parts.append(
        f'<rect x="{x}" y="{top}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{palette.primary}"/>'
    )
    if species == "robot":
        parts.extend(
            (
                f'<rect x="{x + 22}" y="{top + 24}" width="{width - 44}" height="{height - 48}" rx="54" fill="none" stroke="{palette.secondary}" stroke-width="12"/>',
                f'<circle cx="256" cy="346" r="18" fill="{palette.accent}"/>',
            )
        )
    else:
        parts.append(
            f'<ellipse cx="256" cy="330" rx="72" ry="48" fill="{palette.light}" fill-opacity="0.72"/>'
        )
    return svg("\n".join(parts))


def eyes_layer(expression: str, palette: Palette) -> str:
    if expression == "happy":
        body = (
            f'<path d="M184 246 Q210 218 236 246" fill="none" stroke="{palette.dark}" stroke-width="14" stroke-linecap="round"/>\n'
            f'<path d="M276 246 Q302 218 328 246" fill="none" stroke="{palette.dark}" stroke-width="14" stroke-linecap="round"/>'
        )
    elif expression == "sleepy":
        body = (
            f'<path d="M184 242 Q210 258 236 242" fill="none" stroke="{palette.dark}" stroke-width="12" stroke-linecap="round"/>\n'
            f'<path d="M276 242 Q302 258 328 242" fill="none" stroke="{palette.dark}" stroke-width="12" stroke-linecap="round"/>'
        )
    else:
        body = (
            f'<ellipse cx="210" cy="242" rx="31" ry="38" fill="{palette.light}"/>\n'
            f'<ellipse cx="302" cy="242" rx="31" ry="38" fill="{palette.light}"/>\n'
            f'<circle cx="210" cy="248" r="15" fill="{palette.dark}"/>\n'
            f'<circle cx="302" cy="248" r="15" fill="{palette.dark}"/>\n'
            '<circle cx="204" cy="239" r="5" fill="#FFFFFF"/>\n'
            '<circle cx="296" cy="239" r="5" fill="#FFFFFF"/>'
        )
    return svg(body)


def face_layer(expression: str, palette: Palette) -> str:
    nose = f'<path d="M242 282 L270 282 L256 298 Z" fill="{palette.accent}"/>'
    if expression == "happy":
        mouth = f'<path d="M220 310 Q256 346 292 310" fill="none" stroke="{palette.dark}" stroke-width="11" stroke-linecap="round"/>'
    elif expression == "sleepy":
        mouth = f'<path d="M238 320 Q256 308 274 320" fill="none" stroke="{palette.dark}" stroke-width="10" stroke-linecap="round"/>'
    else:
        mouth = f'<ellipse cx="256" cy="326" rx="23" ry="30" fill="{palette.dark}"/>'
    return svg(nose + "\n" + mouth)


def effect_layer(side: str, palette: Palette) -> str:
    x = 78 if side == "left" else 434
    star = (
        f"M{x} 196 L{x + 10} 226 L{x + 40} 236 L{x + 10} 246 "
        f"L{x} 276 L{x - 10} 246 L{x - 40} 236 L{x - 10} 226 Z"
    )
    return svg(
        f'<path d="{star}" fill="{palette.accent}"/>\n'
        f'<circle cx="{x + (34 if side == "left" else -34)}" cy="292" r="9" fill="{palette.light}"/>'
    )


def pack_document(pack_id: str, species: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "pack_id": pack_id,
        "canvas": {"width": 512, "height": 512},
        "layers": [
            {"id": "shadow", "source": "layers/00-shadow.svg", "z": 0},
            {"id": "body-front", "source": "layers/10-body-front.svg", "z": 10},
            {"id": "body-round", "source": "layers/11-body-round.svg", "z": 11},
            {"id": "eyes-happy", "source": "layers/20-eyes-happy.svg", "z": 20},
            {"id": "eyes-sleepy", "source": "layers/21-eyes-sleepy.svg", "z": 21},
            {"id": "eyes-surprised", "source": "layers/22-eyes-surprised.svg", "z": 22},
            {"id": "face-happy", "source": "layers/30-face-happy.svg", "z": 30},
            {"id": "face-sleepy", "source": "layers/31-face-sleepy.svg", "z": 31},
            {"id": "face-surprised", "source": "layers/32-face-surprised.svg", "z": 32},
            {"id": "effect-left", "source": "layers/40-effect-left.svg", "z": 40},
            {"id": "effect-right", "source": "layers/41-effect-right.svg", "z": 41},
        ],
        "base_layers": ["shadow"],
        "expressions": {
            "happy": ["eyes-happy", "face-happy"],
            "sleepy": ["eyes-sleepy", "face-sleepy"],
            "surprised": ["eyes-surprised", "face-surprised"],
        },
        "poses": {"front": ["body-front"], "round": ["body-round"]},
        "provenance": {
            "creator": "MascotRender procedural generator",
            "license": "CC0-1.0 generated sample artwork; font separately SIL OFL 1.1",
            "source": f"generate_mascot_packs.py v{GENERATOR_VERSION}; species={species}",
        },
        "anchors": {
            "face_center": {"x": 256, "y": 270},
            "effect_left": {"x": 78, "y": 236},
            "effect_right": {"x": 434, "y": 236},
        },
        "pivots": {"body": {"x": 256, "y": 260}},
        "text_slots": {
            "top": {"x": 48, "y": 12, "width": 416, "height": 94},
            "bottom": {"x": 58, "y": 394, "width": 396, "height": 94},
        },
        "avoid_regions": [
            {"name": "mascot", "x": 120, "y": 110, "width": 272, "height": 272}
        ],
        "fonts": [
            {
                "id": "display",
                "source": "fonts/changa-one/ChangaOne-Regular.ttf",
                "license": "fonts/changa-one/OFL.txt",
            }
        ],
        "text_styles": {
            "caption": {
                "font": "display",
                "safe_area": {"x": 58, "y": 394, "width": 396, "height": 94},
                "min_font_size": 22,
                "max_font_size": 52,
                "max_lines": 2,
                "fill": {"r": 255, "g": 255, "b": 255},
                "outline": {
                    "width": 5,
                    "color": {"r": 24, "g": 30, "b": 48},
                },
            }
        },
        "variation_groups": [
            {
                "id": "effect-side",
                "choices": [["effect-left"], ["effect-right"]],
            }
        ],
    }


def sticker_document(
    pack_id: str,
    mascot_number: int,
    phrase_index: int,
    phrase: tuple[str, str, str, str],
    seed: int,
) -> dict[str, object]:
    slug, content, expression, pose = phrase
    sticker: dict[str, object] = {
        "schema_version": 1,
        "sticker_id": f"{pack_id}-{slug}",
        "pack_id": pack_id,
        "alt_text": f"Generated mascot {mascot_number} saying {content}",
        "expression": expression,
        "pose": pose,
        "seed": splitmix64(seed + mascot_number * 1000 + phrase_index),
        "text": {
            "content": content,
            "style": "caption",
            "placement": "auto",
            "preferred_slots": ["top", "bottom"]
            if phrase_index % 2 == 0
            else ["bottom", "top"],
        },
    }
    if phrase_index in {0, 2, 6, 8}:
        sticker["animation"] = {
            "duration_ms": 800,
            "fps": 10,
            "loop": "loop",
            "overlays": ["body_bounce", "text_pop"],
        }
    return sticker


def copy_font(font_source: Path, pack_dir: Path) -> str:
    required = ("ChangaOne-Regular.ttf", "OFL.txt", "METADATA.pb", "UPSTREAM.md")
    destination = pack_dir / "fonts" / "changa-one"
    destination.mkdir(parents=True, exist_ok=True)
    for name in required:
        source = font_source / name
        if not source.is_file():
            raise FileNotFoundError(f"required approved font asset is missing: {source}")
        shutil.copy2(source, destination / name)
    return hashlib.sha256((destination / required[0]).read_bytes()).hexdigest()


def generate_pack(root: Path, number: int, seed: int, font_source: Path) -> dict[str, object]:
    state = splitmix64(seed + number)
    species = SPECIES[(number - 1) % len(SPECIES)]
    palette = PALETTES[state % len(PALETTES)]
    pack_id = f"generated-{species}-{number:03d}"
    pack_dir = root / pack_id
    layers = pack_dir / "layers"

    write_text(layers / "00-shadow.svg", shadow_layer(palette))
    write_text(layers / "10-body-front.svg", body_layer(species, palette, False))
    write_text(layers / "11-body-round.svg", body_layer(species, palette, True))
    for index, expression in enumerate(("happy", "sleepy", "surprised"), start=20):
        write_text(layers / f"{index:02d}-eyes-{expression}.svg", eyes_layer(expression, palette))
        write_text(layers / f"{index + 10:02d}-face-{expression}.svg", face_layer(expression, palette))
    write_text(layers / "40-effect-left.svg", effect_layer("left", palette))
    write_text(layers / "41-effect-right.svg", effect_layer("right", palette))

    font_sha256 = copy_font(font_source, pack_dir)
    write_json(pack_dir / "pack.json", pack_document(pack_id, species))
    for phrase_index, phrase in enumerate(PHRASES):
        sticker = sticker_document(pack_id, number, phrase_index, phrase, seed)
        write_json(pack_dir / "stickers" / f"{phrase[0]}.json", sticker)

    return {
        "pack_id": pack_id,
        "species": species,
        "palette": palette.__dict__,
        "pack": f"{pack_id}/pack.json",
        "sticker_count": len(PHRASES),
        "animated_sticker_count": 4,
        "font_sha256": font_sha256,
    }


def replace_directory(staging: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        raise FileExistsError(f"output already exists (use --force): {destination}")
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        destination.rename(backup)
    try:
        staging.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def parse_args(argv: list[str]) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=project_root / "generated" / "mascots")
    parser.add_argument("--count", type=int, default=5, help="Number of mascot identities (1-50)")
    parser.add_argument("--seed", type=int, default=20260713, help="Unsigned 64-bit generation seed")
    parser.add_argument(
        "--font-source",
        type=Path,
        default=project_root / "examples" / "cat" / "fonts" / "changa-one",
        help="Directory containing the approved Changa One TTF and license",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.count < 1 or args.count > 50:
        raise ValueError("--count must be between 1 and 50")
    if args.seed < 0 or args.seed > MASK64:
        raise ValueError("--seed must be an unsigned 64-bit integer")

    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + ".staging-", dir=destination.parent))
    try:
        packs = [
            generate_pack(staging, number, args.seed, args.font_source.resolve())
            for number in range(1, args.count + 1)
        ]
        manifest = {
            "schema_version": 1,
            "generator_version": GENERATOR_VERSION,
            "seed": args.seed,
            "pack_count": len(packs),
            "sticker_count": len(packs) * len(PHRASES),
            "animated_sticker_count": len(packs) * 4,
            "packs": packs,
        }
        write_json(staging / "generation-manifest.json", manifest)
        replace_directory(staging, destination, args.force)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    print(f"generated {args.count} mascot packs and {args.count * len(PHRASES)} stickers in {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
