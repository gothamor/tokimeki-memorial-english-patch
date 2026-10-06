"""Dump the dialogue strings of a script file as a translation skeleton.

Usage:
  python tools/dump_dialogue.py extracted/CDROM/SERIFU/EVENT_KI.BIN [--disc-path CDROM/SERIFU/EVENT_KI.BIN]
                                [--base 0x80198000] [--range START END] [-o out.json]

Finds the file's load address (the base its string pointers are relative to)
unless --base is given, then lists every string some pointer points at, as
"dialogue" lines with an empty "text". Fill in "text" and put the file in
translation/ (see docs/translation-guide.md, "Dialogue").

Write dumps outside the repo (e.g. into extracted/): an untranslated dump is
a copy of the Japanese script and must not be committed (AGENTS.md rule 9).
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tokipatch import script  # noqa: E402


def string_at(data: bytes, off: int):
    if not 0 <= off < len(data) or (off and data[off - 1] != 0) or data[off] == 0:
        return None
    try:
        raw = script.read_string(data, off)
        text = script.decode(raw)
    except ValueError:
        return None
    return text if any(ord(c) > 0x7F for c in text) else None


def targets(data: bytes, base: int):
    found = {}
    for pos in range(0, len(data) - 3, 4):
        off = struct.unpack_from("<I", data, pos)[0] - base
        if off not in found:
            text = string_at(data, off)
            if text is not None:
                found[off] = text
    return found


def guess_base(data: bytes) -> int:
    best = (0, 0)
    for base in range(0x80010000, 0x80200000, 0x800):
        lo, hi = base, base + len(data)
        hits = sum(1 for pos in range(0, len(data) - 3, 4)
                   if lo <= struct.unpack_from("<I", data, pos)[0] < hi)
        if hits > best[1]:
            best = (base, hits)
    candidates = [b for b in range(best[0] - 0x10000, best[0] + 0x10000, 0x800)]
    return max(candidates, key=lambda b: len(targets(data, b)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--disc-path", help="path on the disc (default: guessed from PATH)")
    ap.add_argument("--base", type=lambda s: int(s, 0))
    ap.add_argument("--range", nargs=2, type=lambda s: int(s, 0), metavar=("START", "END"),
                    help="only strings at file offsets in [START, END)")
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()

    data = args.path.read_bytes()
    base = args.base if args.base is not None else guess_base(data)
    disc = args.disc_path or "/".join(args.path.parts[args.path.parts.index("CDROM"):]) \
        if "CDROM" in args.path.parts else args.path.name
    lines = []
    for off, text in sorted(targets(data, base).items()):
        if args.range and not args.range[0] <= off < args.range[1]:
            continue
        lines.append({"offset": f"{off:#x}", "original": text, "text": ""})
    doc = {"description": "", "dialogue": [{"file": disc, "base": f"{base:#x}", "lines": lines}]}
    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
        print(f"{len(lines)} strings, base {base:#x} -> {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
