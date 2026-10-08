"""List SERIFU/GEKO.BIN's walk-home sections: parts, speaker codes, strings.

Usage:
  python tools/geko_sections.py [--strings] [--girl N]

GEKO.EXN holds three parallel 12-entry tables at 0x80144BA0 (masters),
0x80144BD0 (code-byte lists) and 0x80144C00 (third pointers), one entry per
girl (game-internals 6n). Each section has the EVENT_FU layout (6j): master
-> one string list per part, a parallel FF-terminated code byte per string.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tokipatch import script  # noqa: E402

BASE = 0x80197000
EXN_BASE = 0x80132000
TABLE = 0x80144BA0
# Section index -> whose lines (GEKO.EXN's switch on the girl id at
# 0x801327AC maps girl 0..10 to sections 1,5,2,3,9,6,7,4,0,8,11; section 10
# is the player's own thoughts, set up for every walk at 0x801326D4).
GIRLS = ["Yuko", "Shiori", "Yuina", "Ayako", "Mira", "Mio", "Yukari",
         "Nozomi", "Megumi", "Saki", "(player)", "Yumi"]
CODES = {0: "player", 1: "girl", 2: "reply", 3: "choice", 4: "note", 6: "thought",
         7: "sound", 8: "action", 0x0C: "girl+", 0x0D: "girl+2"}


def sections(geko: bytes, exn: bytes):
    """[(girl, master, [(part, [(offset, code)])])]"""
    tab = struct.unpack_from("<36I", exn, TABLE - EXN_BASE)
    inside = lambda w: BASE <= w < BASE + len(geko)
    word = lambda o: struct.unpack_from("<I", geko, o)[0]
    out = []
    for g in range(12):
        master, codes = tab[g] - BASE, tab[12 + g] - BASE
        parts, k = [], 0
        while inside(word(master + 4 * k)) and inside(word(codes + 4 * k)):
            lst, cl = word(master + 4 * k) - BASE, word(codes + 4 * k) - BASE
            strings, t = [], 0
            while geko[cl + t] != 0xFF:
                s = word(lst + 4 * t)
                if not inside(s):
                    break
                strings.append((s - BASE, geko[cl + t]))
                t += 1
            if not strings:
                break
            parts.append((k, strings))
            k += 1
        out.append((g, master, parts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "extracted/CDROM/SERIFU/GEKO.BIN"))
    ap.add_argument("--exn", default=str(ROOT / "extracted/CDROM/EXEDIR/GEKO.EXN"))
    ap.add_argument("--strings", action="store_true", help="print each string's Japanese")
    ap.add_argument("--girl", type=int)
    args = ap.parse_args()
    geko, exn = Path(args.file).read_bytes(), Path(args.exn).read_bytes()
    total = 0
    for g, master, parts in sections(geko, exn):
        n = sum(len(s) for _, s in parts)
        total += n
        if args.girl is not None and g != args.girl:
            continue
        offs = [o for _, s in parts for o, _ in s]
        print(f"section {g:2d} {GIRLS[g]:<8} master {master:#07x}  {min(offs):#07x}-{max(offs):#07x}"
              f"  {len(parts):3d} parts {n:4d} strings")
        for k, strings in parts:
            if args.strings:
                for o, c in strings:
                    text = script.decode(script.read_string(geko, o)).replace("\n", "/")
                    print(f"    part {k:2d} {o:#07x} {CODES.get(c, hex(c)):<7} {text}")
            else:
                print(f"    part {k:2d}: " + "  ".join(f"{o:#06x}:{CODES.get(c, hex(c))}" for o, c in strings))
    print(f"{total} strings")


if __name__ == "__main__":
    main()
