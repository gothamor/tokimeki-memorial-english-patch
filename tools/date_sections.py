"""List the sections of a girl's DATE_*.BIN as a translation/test checklist.

Usage:
  python tools/date_sections.py [--file extracted/CDROM/SERIFU/DATE_FU.BIN]
                                [--exn extracted/CDROM/EXEDIR/DATE.EXN] [--strings]

Reads DATE.EXN's section tables (game-internals §6k) and the place switch,
then prints, per section: the place it belongs to, its file range, string
and part counts, how many parts are choices (03/08) and replies (02), the
parts-per-version byte its setup stores, and the address where the setup
first reads the version byte 0x800CA2FC. Pass that address to
`tools/emu/force_date.py ... --set-at ADDR 0x800CA2FC N` to force version N.

--strings also lists each part's string offsets and speaker codes. Nothing
here prints game text, so the output can go into docs.

The section tables hold Shiori's offsets statically; other girls' files need
their tables (written by DATE.EXN code at run time) and aren't supported.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

EXN_BASE = 0x80132000
FILE_BASE = 0x80198000
TABLE = 0x8015BDC0          # 27 masters, then 27 byte lists, then 27 thirds
SECTIONS = 27
PLACE_JUMPS = 0x8015B060    # place - 1 -> case storing the setup function
PLACES = 20
VERSION_LO = 0xA2FC         # *(u8*)0x800CA2FC, the section's version
PARTS_PER_VERSION_LO = 0xB658   # *(u8*)0x8015B658
CODES = {0x00: "player", 0x01: "girl", 0x02: "reply", 0x03: "choice", 0x04: "narration",
         0x06: "thought", 0x07: "sound/narration", 0x08: "action choice"}
# Sections not reached through the place switch (game-internals §6k).
SHARED = {7: "talk, ask about hobbies", 9: "parade invitation", 22: "end of the date",
          23: "meeting", 24: "seasonal small talk", 25: "hobby notes", 26: "going home"}

ROOT = Path(__file__).resolve().parent.parent


def place_names() -> list:
    doc = json.loads((ROOT / "translation" / "outings.json").read_text(encoding="utf-8"))
    names = [line["text"] for block in doc["dialogue"] for line in block["lines"]
             if line["offset"].upper() >= "0X72B4C"]
    return names[:PLACES]


def scan_places(exn: bytes) -> dict:
    """{place: {place, setup, slot, load, ppv}} from DATE.EXN's place switch.

    `load` is where the setup first reads the version byte 0x800CA2FC (None
    if it never does); `ppv` the parts-per-version values it stores.
    """
    def xw(addr):
        return struct.unpack_from("<I", exn, addr - EXN_BASE)[0]

    places = {}
    for i in range(PLACES):
        # Each case is `lui t, hi; addiu t, t, lo; b ...; sw t, (v0)`.
        case = xw(PLACE_JUMPS + 4 * i)
        hi, lo = xw(case) & 0xFFFF, xw(case + 4) & 0xFFFF
        setup = ((hi << 16) + struct.unpack("<h", struct.pack("<H", lo))[0]) & 0xFFFFFFFF
        info = {"place": i + 1, "setup": setup, "ppv": [], "load": None}
        addr = setup
        while xw(addr) != 0x03E00008:                       # up to `jr ra`
            w = xw(addr)
            op, imm = w >> 26, w & 0xFFFF
            if op == 0x23 and 0xBDC0 <= imm < 0xBDC0 + 4 * SECTIONS and "slot" not in info:
                info["slot"] = (imm - 0xBDC0) // 4          # lw of its master entry
            if op == 0x24 and imm == VERSION_LO and info["load"] is None:
                info["load"] = addr                         # first lbu of the version
            if op == 0x28 and imm == PARTS_PER_VERSION_LO:   # sb of parts per version
                rt = (w >> 16) & 31
                for back in range(addr - 4, addr - 40, -4):
                    v = xw(back)
                    if v >> 26 == 9 and (v >> 21) & 31 == 0 and (v >> 16) & 31 == rt:
                        info["ppv"].append(v & 0xFFFF)
                        break
            addr += 4
        places[i + 1] = info
    return places


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "extracted/CDROM/SERIFU/DATE_FU.BIN"))
    ap.add_argument("--exn", default=str(ROOT / "extracted/CDROM/EXEDIR/DATE.EXN"))
    ap.add_argument("--strings", action="store_true")
    args = ap.parse_args()
    data = Path(args.file).read_bytes()
    exn = Path(args.exn).read_bytes()

    def xw(addr):
        return struct.unpack_from("<I", exn, addr - EXN_BASE)[0]

    def fw(off):
        return struct.unpack_from("<I", data, off)[0]

    in_file = lambda w: FILE_BASE <= w < FILE_BASE + len(data)

    by_slot = {info["slot"]: info for info in scan_places(exn).values()}
    names = place_names()
    for info in by_slot.values():
        info["name"] = names[info["place"] - 1]

    total = 0
    for s in range(SECTIONS):
        master, blists = xw(TABLE + 4 * s) - FILE_BASE, xw(TABLE + 4 * (SECTIONS + s)) - FILE_BASE
        parts = []
        while in_file(fw(master + 4 * len(parts))) and fw(master + 4 * len(parts)) - FILE_BASE < master:
            p = len(parts)
            lst, bl = fw(master + 4 * p) - FILE_BASE, fw(blists + 4 * p) - FILE_BASE
            codes = []
            while data[bl + len(codes)] != 0xFF:
                codes.append(data[bl + len(codes)])
            parts.append([(fw(lst + 4 * k) - FILE_BASE, c) for k, c in enumerate(codes)])
        strings = [o for part in parts for o, _ in part]
        total += len(strings)
        choices = sum(any(c in (3, 8) for _, c in part) for part in parts)
        replies = sum(any(c == 2 for _, c in part) for part in parts)
        info = by_slot.get(s)
        if info:
            what = f"place {info['place']} {info['name']}"
            even = [v for v in info["ppv"] if len(parts) % v == 0]
            if info["load"] is None:
                force = "no version byte: branches on choices"
            else:
                if even:
                    versions = f"{len(parts) // even[0]} versions of {even[0]} parts"
                elif info["ppv"]:
                    versions = f"{info['ppv'][0]} parts per version, irregular tail"
                else:
                    versions = "parts per version not set by the setup"
                force = f"{versions}; --set-at {info['load']:#x} 0x800CA2FC N"
        else:
            what, force = SHARED.get(s, "?"), "shared; see game-internals §6k"
        print(f"section {s:2}  {what:28} {min(strings):#07x}-{max(strings):#07x}  "
              f"{len(strings):3} strings  {len(parts):2} parts  {choices:2} choices  "
              f"{replies:2} replies  {force}")
        if args.strings:
            for p, part in enumerate(parts):
                print(f"    part {p:2}: " + "  ".join(f"{o:#06x}:{CODES.get(c, hex(c))}" for o, c in part))
    print(f"{total} strings in {SECTIONS} sections (the dumper's count leaves out "
          "strings script.decode rejects, e.g. the two with `n` bytes in section 4)")


if __name__ == "__main__":
    main()
