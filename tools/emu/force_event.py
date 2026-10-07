"""Force one girl special event in the isolated emulator (test cards only).

Usage:  python tools/emu/force_event.py GIRL SCENE [--clear-flag ADDR] [--timeout S]

Breaks where the main loop is about to read the next day record from its
event queue (0x80071DD0, game-internals §6j) and, at the first ordinary
record (type 0x00), writes a special-event record `45 GIRL SCENE 00` in its
place, so that day runs the girl's scene instead of the chosen command.
--clear-flag zeroes a one-shot "seen" byte first (Shiori's scene 2 uses
0x800E67ED). Then it detaches and the game continues on its own.

Start it on the Sunday-night planning screen, then pick a weekly command.
This changes game state: use it only on the harness's test cards and do the
same forcing on the unpatched game for the comparison run.
"""

from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gdbstub import Gdb  # noqa: E402

READ_RECORD = 0x80071DD0   # index already advanced; next insn reads the record
QUEUE = 0x800E691C         # records: type, girl, scene, flags
QUEUE_INDEX = 0x800E699C
DATE = 0x800E62BE


def main() -> None:
    args = sys.argv[1:]
    flag = None
    timeout = 300.0
    for opt in ("--clear-flag", "--timeout"):
        if opt in args:
            i = args.index(opt)
            value = args[i + 1]
            del args[i:i + 2]
            if opt == "--clear-flag":
                flag = int(value, 0)
            else:
                timeout = float(value)
    if len(args) != 2:
        sys.exit(__doc__)
    girl, scene = int(args[0], 0), int(args[1], 0)

    g = Gdb()
    if flag is not None:
        print(f"flag {flag:#x} was {g.mem(flag, 1).hex()}, clearing", flush=True)
        g.cmd(f"M{flag:x},1:00")
    g.break_at(READ_RECORD)
    t0 = time.time()
    try:
        while (left := timeout - (time.time() - t0)) > 0:
            try:
                g.cont(timeout=left)
            except socket.timeout:
                g.interrupt()
                print("timed out without forcing", flush=True)
                return
            index = g.mem(QUEUE_INDEX, 1)[0]
            addr = QUEUE + 4 * index
            record = g.mem(addr, 4)
            y, m, d, wd = g.mem(DATE, 4)
            print(f"{y}/{m}/{d} wd{wd} index {index} record {record.hex(' ')}", flush=True)
            if record[0] == 0x00:
                new = bytes([0x45, girl, scene, 0])
                g.cmd(f"M{addr:x},4:{new.hex()}")
                print(f"forced {new.hex(' ')} at {addr:#x} (was {record.hex(' ')})", flush=True)
                return
    finally:
        g.clear_break(READ_RECORD)
        g.detach()


if __name__ == "__main__":
    main()
