"""Set up a date in the isolated emulator, optionally forcing a date event.

Usage:
  python tools/emu/force_date.py GIRL PLACE MONTH DAY
  python tools/emu/force_date.py 0 PLACE MONTH DAY --scene N [--any-step] [--timeout S]
  python tools/emu/force_date.py GIRL PLACE MONTH DAY --set-at PC ADDR VALUE [--timeout S]
  python tools/emu/force_date.py 0 PLACE MONTH DAY --version N [--timeout S]
  python tools/emu/force_date.py 0 PLACE MONTH DAY [--version N] -- BREAK_SET_RULES

Writes appointment slot 0 (0x800E67CC, game-internals §6j): active, GIRL,
PLACE (1-based outing id; 0 is also accepted by the game), MONTH/DAY. Run it
on the Sunday-night planning screen for a holiday later that week; the
holiday screen then says you have a date and the heart icon starts it.

--scene N (Shiori only, scenes 3-6) also breaks in DATE.EXN's date-event
chooser (0x8013272C, just after its prologue) and, at the date step the
scene normally needs, clears the scene's one-shot flag and jumps to the call
that picks it. That skips the season and affection checks, which can't be
met early in the game. --any-step jumps at the first chooser call instead.

--set-at PC ADDR VALUE breaks once at PC while DATE.EXN is loaded and writes
the byte VALUE to ADDR, e.g. the museum date's exhibition: --set-at
0x80134F74 0x800CA2FC N (N = 0-5, DATE_FU section 0; game-internals §6k).

--version N does that for any place whose setup picks a version: it breaks
where the place's setup first reads the version byte 0x800CA2FC (found in
extracted/CDROM/EXEDIR/DATE.EXN by tools/date_sections.py) and writes N.
Shopping, Theme Park, Cinema, Concert Hall and Shrine have no version byte.

Anything after `--` is a set of tools/emu/break_set.py rules (--at PC ...),
armed together with --version / --set-at in the same session, e.g. to pick
the meeting, ending or going-home part too (game-internals §6k).

This changes game state: use it only on the harness's test cards, and do the
same forcing on the unpatched game for the comparison run.
"""

from __future__ import annotations

import socket
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gdbstub import REG_NAMES, Gdb  # noqa: E402

SLOT0 = 0x800E67CC
GIRL_ID = 0x800E71DF
STEP = 0x800E7389            # u8 sub-step, then u8 step at 0x800E738A
LOADED_LBA = 0x800B6D40      # LBA of the overlay in memory
DATE_EXN_LBA = 37418
CHOOSER = 0x8013273C         # DATE.EXN 0x8013272C after its prologue (ra saved)

# Shiori's date events: call site that loads the helper's arguments, the
# one-shot flag, and the (sub-step, step) the chooser checks (None = any).
SCENES = {
    3: (0x8013290C, 0x800E67EE, (1, 1)),
    4: (0x801327C4, 0x800E67EF, (None, 13)),
    5: (0x8013298C, 0x800E67F0, (1, 0x23)),
    6: (0x80132894, 0x800E67F1, (1, 10)),
}


def main() -> None:
    args = sys.argv[1:]
    extra = []
    if "--" in args:
        extra = args[args.index("--") + 1:]
        args = args[:args.index("--")]
    scene, any_step, timeout, set_at = None, False, 600.0, None
    if "--set-at" in args:
        i = args.index("--set-at")
        set_at = tuple(int(a, 0) for a in args[i + 1:i + 4])
        del args[i:i + 4]
    if "--version" in args:
        i = args.index("--version")
        version = int(args[i + 1], 0)
        del args[i:i + 2]
        place = int(args[1], 0)
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import date_sections
        exn = (Path(__file__).resolve().parents[2] / "extracted/CDROM/EXEDIR/DATE.EXN").read_bytes()
        load = date_sections.scan_places(exn).get(place, {}).get("load")
        if load is None:
            sys.exit(f"place {place}'s setup doesn't read a version byte (see tools/date_sections.py)")
        set_at = (load, 0x800CA2FC, version)
    if "--any-step" in args:
        any_step = True
        args.remove("--any-step")
    for opt in ("--scene", "--timeout"):
        if opt in args:
            i = args.index(opt)
            value = args[i + 1]
            del args[i:i + 2]
            if opt == "--scene":
                scene = int(value, 0)
            else:
                timeout = float(value)
    if len(args) != 4:
        sys.exit(__doc__)
    girl, place, month, day = (int(a, 0) for a in args)
    if scene is not None and (girl != 0 or scene not in SCENES):
        sys.exit("--scene is only mapped for Shiori (girl 0), scenes 3-6")

    g = Gdb()
    word = 1 << 29 | girl << 25 | day << 16 | month << 12 | place
    g.cmd(f"M{SLOT0:x},4:" + struct.pack("<I", word).hex())
    print(f"appointment slot 0 = {word:#010x} (girl {girl}, place {place}, {month}/{day})", flush=True)
    if extra or set_at is not None:
        import break_set
        rules = break_set.parse(extra + ["--timeout", str(timeout)])[2] if extra else []
        if set_at is not None:
            rules.append({"pc": set_at[0], "actions": [("mem8", set_at[1], set_at[2])],
                          "times": 1, "hits": 0})
        break_set.run(g, rules, DATE_EXN_LBA, timeout)
        return
    if scene is None:
        g.detach()
        return

    site, flag, (sub, step) = SCENES[scene]
    g.break_at(CHOOSER)
    t0 = time.time()
    try:
        while (left := timeout - (time.time() - t0)) > 0:
            try:
                g.cont(timeout=left)
            except socket.timeout:
                g.interrupt()
                print("timed out without forcing", flush=True)
                return
            lba = struct.unpack("<I", g.mem(LOADED_LBA, 4))[0]
            if lba != DATE_EXN_LBA or g.mem(GIRL_ID, 1)[0] != girl:
                continue
            s1, s2 = g.mem(STEP, 2)
            print(f"chooser at step {s1}/{s2}", flush=True)
            if not any_step and (s2 != step or (sub is not None and s1 != sub)):
                continue
            g.cmd(f"M{flag:x},1:00")
            g.cmd(f"P{REG_NAMES.index('pc'):x}=" + struct.pack("<I", site).hex())
            print(f"forced scene {scene}: pc -> {site:#x}, flag {flag:#x} cleared", flush=True)
            return
    finally:
        g.clear_break(CHOOSER)
        g.detach()


if __name__ == "__main__":
    main()
