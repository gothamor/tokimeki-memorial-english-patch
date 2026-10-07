"""Force a girl's after-Christmas-party scene in the isolated emulator (test cards only).

Usage:  python tools/emu/force_christmas.py [--girl 0] [--timeout S]

At the next ordinary weekday state change (state 0x40, a study day), swaps
the requested state for 0x52, which runs SHOUGATU.EXN's Christmas-party
flow. When that flow's stage dispatcher (0x8013D180, stopped at 0x8013D190
before it reads the stage byte) first runs, it writes what the party's
girl selector (0x80140030) would: stage 6 with girl 0 / scene id 7 for
Shiori (game-internals §6j). Stages 7 and 8 belong to two other girls and
aren't mapped here, so only --girl 0 is accepted.

Graphics left over from the weekday screen show behind the scene; the text
boxes are unaffected. Use it only on the harness's test cards, and do the
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

SET_STATE = 0x80042878       # set_state(a0)
DISPATCH = 0x8013D190        # SHOUGATU stage dispatcher, before it reads 0x800E7389
LOADED_LBA = 0x800B6D40
SHOUGATU_LBA = 39050
STAGES = {0: (6, 7)}         # girl -> (stage, scene id written to 0x80122CD0)


def main() -> None:
    args = sys.argv[1:]
    girl, timeout = 0, 300.0
    for opt in ("--girl", "--timeout"):
        if opt in args:
            i = args.index(opt)
            value = args[i + 1]
            del args[i:i + 2]
            if opt == "--girl":
                girl = int(value, 0)
            else:
                timeout = float(value)
    if args or girl not in STAGES:
        sys.exit(__doc__)
    stage, scene = STAGES[girl]

    g = Gdb()
    g.break_at(SET_STATE)
    waiting_for_dispatch = False
    t0 = time.time()
    try:
        while (left := timeout - (time.time() - t0)) > 0:
            try:
                g.cont(timeout=left)
            except socket.timeout:
                g.interrupt()
                print("timed out without forcing", flush=True)
                return
            r = g.regs()
            if not waiting_for_dispatch:
                if r["pc"] == SET_STATE and r["a0"] == 0x40:
                    g.cmd(f"P{REG_NAMES.index('a0'):x}=" + struct.pack("<I", 0x52).hex())
                    print(f"state 0x40 -> 0x52 on {list(g.mem(0x800E62BE, 4))}", flush=True)
                    g.clear_break(SET_STATE)
                    g.break_at(DISPATCH)
                    waiting_for_dispatch = True
                continue
            if struct.unpack("<I", g.mem(LOADED_LBA, 4))[0] != SHOUGATU_LBA:
                continue
            g.cmd("M800e7389,2:" + bytes([stage, 0]).hex())
            g.cmd("M80122cd4,4:" + struct.pack("<I", girl).hex())
            g.cmd("M80122cd0,4:" + struct.pack("<I", scene).hex())
            g.cmd(f"M800e71df,1:{girl:02x}")
            print(f"stage {stage}, girl {girl}, scene id {scene}", flush=True)
            return
    finally:
        g.clear_break(SET_STATE)
        g.clear_break(DISPATCH)
        g.detach()


if __name__ == "__main__":
    main()
