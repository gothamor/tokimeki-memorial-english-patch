"""List the GEKO.EXN script sections: parts, speaker codes, strings.

Usage:
  python tools/geko_sections.py [--invite | --appear | --nyubu | --xmas] [--strings] [--girl N]

Default: SERIFU/GEKO.BIN, walking home (game-internals 6n). --invite:
SERIFU/G_INVITE.BIN, a girl asking the player out (6o), from GEKO.EXN's
13-entry tables at 0x80147630. --appear: SERIFU/G_APPEAR.BIN, the first
meetings (6p), from SHOUGATU.EXN's 9-entry tables at 0x80144D90. --nyubu:
SERIFU/NYUBU.BIN, a girl welcoming the player to her club (6q), from
KANGEI.EXN's 8-entry tables at 0x80139950. --xmas: SERIFU/XMAS.BIN, the
Christmas party (6t), from SHOUGATU.EXN's 13-entry tables at 0x80145AD0.

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
INVITE_TABLE = 0x80147630
# GEKO.EXN's switch at 0x80143804 (jump table 0x80144B68) maps girls 0..10
# to sections 1,5,2,3,10,6,8,4,0,9,12; 11 is the player's thoughts and 7
# isn't selected by any girl id (game-internals 6o).
INVITE_NAMES = ["Yuko", "Shiori", "Yuina", "Ayako", "Mira", "Mio", "Yukari",
                "(unused)", "Nozomi", "Megumi", "Saki", "(player)", "Yumi"]
APPEAR_TABLE = 0x80144D90   # in SHOUGATU.EXN, filled by 0x80136F90
# SHOUGATU.EXN's meeting switch at 0x80137204 (jump table 0x80143730) runs
# girls 1-8 and 10; each girl's handler copies one entry (game-internals 6p).
APPEAR_NAMES = ["Yuko", "Yuina", "Ayako", "Mira", "Mio", "Yukari", "Nozomi",
                "Saki", "Yumi"]
NYUBU_TABLE = 0x80139950    # in KANGEI.EXN, filled by 0x80132090
# KANGEI.EXN's switch at 0x8013260C (jump table 0x80139668) maps girls 0-6
# to sections 0, 3, 1, 2, 6, 4, 5; girl 7 and up get section 7 (6q).
NYUBU_NAMES = ["Shiori", "Yuina", "Ayako", "Mio", "Yukari", "Nozomi", "Saki", "(default)"]
XMAS_TABLE = 0x80145AD0     # in SHOUGATU.EXN, filled by 0x8013C070
# SHOUGATU.EXN's girl switch at 0x8013EE30 (jump table 0x80143990) maps the
# party's girls 1-10 to these sections; Shiori's is loaded directly (6t).
XMAS_NAMES = ["Yuko", "Shiori", "Yuina", "Ayako", "Mira", "Mio", "Yukari", "Nozomi",
              "Megumi", "Saki", "presents", "arrival", "Yumi"]
CODES = {0: "player", 1: "girl", 2: "reply", 3: "choice", 4: "note", 6: "thought",
         7: "sound", 8: "action", 9: "sfx", 0x0A: "Yoshio", 0x0C: "girl+", 0x0D: "girl+2",
         0x0E: "prompt"}


def sections(geko: bytes, exn: bytes, table: int = TABLE, count: int = 12):
    """[(section, master, [(part, [(offset, code)])])]"""
    tab = struct.unpack_from(f"<{3 * count}I", exn, table - EXN_BASE)
    inside = lambda w: BASE <= w < BASE + len(geko)
    word = lambda o: struct.unpack_from("<I", geko, o)[0]
    out = []
    for g in range(count):
        master, codes = tab[g] - BASE, tab[count + g] - BASE
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
    ap.add_argument("--file")
    ap.add_argument("--invite", action="store_true", help="G_INVITE.BIN instead of GEKO.BIN")
    ap.add_argument("--appear", action="store_true", help="G_APPEAR.BIN (tables in SHOUGATU.EXN)")
    ap.add_argument("--nyubu", action="store_true", help="NYUBU.BIN (tables in KANGEI.EXN)")
    ap.add_argument("--xmas", action="store_true", help="XMAS.BIN (tables in SHOUGATU.EXN)")
    ap.add_argument("--exn", default=str(ROOT / "extracted/CDROM/EXEDIR/GEKO.EXN"))
    ap.add_argument("--strings", action="store_true", help="print each string's Japanese")
    ap.add_argument("--girl", type=int)
    args = ap.parse_args()
    name = ("G_INVITE.BIN" if args.invite else "G_APPEAR.BIN" if args.appear else
            "NYUBU.BIN" if args.nyubu else "XMAS.BIN" if args.xmas else "GEKO.BIN")
    if args.nyubu and args.exn == str(ROOT / "extracted/CDROM/EXEDIR/GEKO.EXN"):
        args.exn = str(ROOT / "extracted/CDROM/EXEDIR/KANGEI.EXN")
    if (args.appear or args.xmas) and args.exn == str(ROOT / "extracted/CDROM/EXEDIR/GEKO.EXN"):
        args.exn = str(ROOT / "extracted/CDROM/EXEDIR/SHOUGATU.EXN")
    geko = Path(args.file or ROOT / "extracted/CDROM/SERIFU" / name).read_bytes()
    exn = Path(args.exn).read_bytes()
    table, count, names = ((INVITE_TABLE, 13, INVITE_NAMES) if args.invite else
                           (APPEAR_TABLE, 9, APPEAR_NAMES) if args.appear else
                           (NYUBU_TABLE, 8, NYUBU_NAMES) if args.nyubu else
                           (XMAS_TABLE, 13, XMAS_NAMES) if args.xmas else (TABLE, 12, GIRLS))
    total = 0
    for g, master, parts in sections(geko, exn, table, count):
        n = sum(len(s) for _, s in parts)
        total += n
        if args.girl is not None and g != args.girl:
            continue
        offs = [o for _, s in parts for o, _ in s]
        print(f"section {g:2d} {names[g]:<8} master {master:#07x}  {min(offs):#07x}-{max(offs):#07x}"
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
