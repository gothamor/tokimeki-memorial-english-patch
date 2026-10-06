"""Command-line entry point:  python -m tokipatch <game.cue> [-o OUTPUT_DIR]"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from . import patcher
from .cd import Track

TRANSLATION_DIR = Path(__file__).resolve().parent.parent / "translation"


def parse_cue(cue: Path) -> Tuple[List[str], Optional[str]]:
    """Return (all FILE names in the cue, the FILE holding the MODE2/2352 track)."""
    files: List[str] = []
    data_file = None
    for line in cue.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*FILE\s+"(.+)"\s+\w+', line) or re.match(r"\s*FILE\s+(\S+)\s+\w+", line)
        if m:
            files.append(m.group(1))
        elif re.match(r"\s*TRACK\s+\d+\s+MODE2/2352", line, re.I) and data_file is None:
            data_file = files[-1] if files else None
    return files, data_file


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="tokipatch",
        description="Apply the English translation to Tokimeki Memorial: Forever with You (PS1).")
    ap.add_argument("input", type=Path, help="the game's .cue file (or its Track 1 .bin)")
    ap.add_argument("-o", "--output", type=Path,
                    help="folder for the patched game (default: '<input folder> [English]' next to it)")
    ap.add_argument("-t", "--translation", type=Path, action="append",
                    help="translation JSON file(s) to apply (default: everything in translation/)")
    ap.add_argument("-f", "--force", action="store_true", help="overwrite an existing output folder")
    args = ap.parse_args(argv)

    src: Path = args.input.resolve()
    if not src.is_file():
        ap.error(f"{src} not found")

    if src.suffix.lower() == ".cue":
        cue_files, data_name = parse_cue(src)
        if data_name is None:
            ap.error("no MODE2/2352 data track in the .cue")
        to_copy = [src] + [src.parent / name for name in cue_files]
        data_name = Path(data_name).name
    else:
        to_copy = [src]
        data_name = src.name

    out: Path = (args.output or src.parent.with_name(src.parent.name + " [English]")).resolve()
    if out == src.parent:
        ap.error("output folder must differ from the input folder")
    if out.exists() and any(out.iterdir()) and not args.force:
        ap.error(f"{out} already exists and isn't empty (use --force to overwrite)")

    translations = args.translation or sorted(TRANSLATION_DIR.glob("*.json"))
    try:
        strings, images, byte_patches, dialogue = patcher.load_translations(translations)
        print(f"Loaded {len(strings)} string(s), "
              f"{sum(len(d.lines) for d in dialogue)} dialogue line(s), {len(images)} image(s) "
              f"and {len(byte_patches)} byte patch(es) from {len(translations)} translation file(s).")
        data_src = next(f for f in to_copy if f.name == data_name)
        with Track(data_src) as track:
            edits = patcher.plan(track, strings, images, byte_patches, dialogue)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    for f in to_copy:
        if not f.is_file():
            ap.error(f"{f} (referenced by the .cue) not found")
        print(f"Copying {f.name}...")
        shutil.copyfile(f, out / f.name)

    print("Patching:")
    with Track(out / data_name, writable=True) as track:
        patcher.apply(track, edits)

    print(f"Done. Patched game written to:\n  {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
