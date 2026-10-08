"""Make the player's birthday happen, optionally with a girl's present.

Usage:  python tools/emu/force_birthday.py [GIRL] [--date M/D] [--timeout S]

Run it on the Sunday-night planning screen of a test card, then pick a
weekly command. It writes the player's birthday (bits 0-3 month, 4-8 day of
the u32 at 0x800E6378; game-internals 6r) as M/D (default 4/25, the Monday
after the 95/4/23 test save), so the birthday scene (SERIFU/P_BIRTH.BIN)
plays that day by itself. On that save nobody brings a present, so it is
the "nobody gave me a present" lines.

With GIRL (0 Shiori ... 10 Yumi) the tool also waits for the overlay that
runs the scene: on a school day GEKO.EXN (state 0x56), in other flows
KANGEI.EXN; each has its own copy of the selector, which takes the met girl
with the best rank and gives the present only if that rank is below 2. It
polls RAM for the overlay's code at its selector (both addresses are other
code in the main-screen overlay, so a breakpoint armed early would fire
constantly), then breaks there and sets the girl and her rank to 0.

This changes game state (RAM and registers only): use it on test cards.
"""

from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gdbstub import REG_NAMES, Gdb  # noqa: E402

BIRTHDAY = 0x800E6378
# overlay: (selector pc, its code bytes, girl register, rank register)
SELECTORS = {
    "GEKO": (0x80134930, "0200e12d08002010", "fp", "t7"),
    "KANGEI": (0x8013907C, "0200a12d07002010", "s7", "t5"),
}


def setreg(g: Gdb, name: str, value: int) -> None:
    g.cmd(f"P{REG_NAMES.index(name):x}=" + struct.pack("<I", value).hex())


def main() -> None:
    args = sys.argv[1:]
    month, day, timeout = 4, 25, 300.0
    for opt in ("--date", "--timeout"):
        if opt in args:
            i = args.index(opt)
            value = args[i + 1]
            del args[i:i + 2]
            if opt == "--date":
                month, day = (int(x) for x in value.split("/"))
            else:
                timeout = float(value)
    if len(args) > 1:
        sys.exit(__doc__)
    girl = int(args[0], 0) if args else None

    g = Gdb()
    old = struct.unpack("<I", g.mem(BIRTHDAY, 4))[0]
    new = (old & ~0x1FF) | day << 4 | month
    g.cmd(f"M{BIRTHDAY:x},4:" + struct.pack("<I", new).hex())
    print(f"player birthday {old:#x} -> {new:#x} ({month}/{day})", flush=True)
    g.detach()
    if girl is None:
        return

    t0 = time.time()
    found = None
    while found is None:
        time.sleep(0.2)
        g = Gdb()
        for name, (pc, code, _, _) in SELECTORS.items():
            if g.mem(pc, 8) == bytes.fromhex(code):
                found = name
                break
        else:
            g.detach()
            if time.time() - t0 > timeout:
                sys.exit("no birthday overlay loaded")
    pc, _, girl_reg, rank_reg = SELECTORS[found]
    print(f"{found}.EXN loaded after {time.time() - t0:.1f}s", flush=True)
    g.break_at(pc)
    try:
        g.cont(timeout=timeout)
        setreg(g, girl_reg, girl)
        setreg(g, rank_reg, 0)
        print(f"girl {girl} brings a present ({girl_reg}, {rank_reg})", flush=True)
    finally:
        g.clear_break(pc)
        g.detach()


if __name__ == "__main__":
    main()
