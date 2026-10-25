"""Generate English labels for character creation's pre-drawn words (NAME_ENT.NBN).

Usage:  python tools/make_name_labels.py

The pink captions of the name page (名前: あだ名:), the birthday page
(誕生日: 月 日 血液型: 型, 誕生月 / 誕生日 / 血液型, 1月-12月, A型 ...) and the
"Is this OK?" summary (名前 あだ名 誕生日 血液型, 月 日 型, はい いいえ) are
sprite frames in CDROM/NAME_ENT/NAME_ENT.NBN (game-internals 6d): a frame
table at file 0x1AF58 (RAM 0x801AAF58, file loaded at 0x80190000) points at
frames of `s16 parts, x, y, 0` plus 14-byte parts `x, y, cell, attr, 0, w,
h`. `cell` counts 8x8 tiles of a 128 px wide 4bpp strip starting at file
0x200 (64-byte rows). Frame 1 is the name page, 2 the birthday page, 3 the
player's summary, 15 Shiori's summary (no nickname row).

The glyph cells are shared (名 by 名前 and あだ名, 日 by 誕生日 and the day,
い by はい and いいえ, 月 by every month), so the cells can't simply be
redrawn: this tool clears the tiles of the glyphs only these labels use,
draws each English word once into them, and rewrites the parts that drew
the Japanese. The digits, A/B/AB/O and the ':' stay. 月 after a value becomes
"/", 日 and 型 after a value and in the lists are dropped, and the
birthday page's day row loses its label (誕生月 becomes "Birthday", no room
for "Month" and "Day": the sheet has 28 free tiles, all used).

Every frame keeps its part count and order. A dropped part draws one
transparent texel (a 8x1 run of colour 0) instead of being removed.
Free-looking tiles that no frame uses (the X pattern after は い え, the
keypad digits) are left alone: code may draw them (game-internals 6c, 6d).

Writes translation/graphics/name_labels_00200.png and
translation/name_entry_labels.json. Re-run after changing a label.
"""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tokipatch import pairfont, png  # noqa: E402

FILE = "CDROM/NAME_ENT/NAME_ENT.NBN"
BASE, TABLE = 0x80190000, 0x1AF58
PIXELS, STRIDE, W, H = 0x200, 64, 128, 128     # the 4bpp label strip
INK, SHADOW = 9, 10                            # shadow one pixel down-right

# Word -> first tile of the run it is drawn into (glyph tiles only these
# labels used: あだ名前月 = 162-171, 誕生日血液型 = 192-203, はいえ = 224-229).
WORDS = {
    "Blood type": 162, "Yes": 169,
    "Nickname": 192, "Birthday": 198,
    "Name": 224, "No": 227, "/": 229,
}

# frame -> {part index: (word, x) or None to drop}; y, attr and every other
# part stay. Japanese in the comments is what the part drew.
EDITS = {
    1: {15: ("Name", 16), 16: (":", 41),                   # 名前 :
        17: ("Nickname", 176)},                            # あだ名 (its : stays at 224)
    2: {19: ("Birthday", 24),                              # header 誕生日 (: stays at 72)
        21: ("/", 117), 22: None,                          # 月 日
        23: ("Blood type", 192), 25: None,                 # 血液型 (: stays at 248), 型
        26: ("Birthday", 40), 27: None,                    # 誕生 月 (the month row)
        28: None,                                          # 誕生日 (the day row)
        29: ("Blood type", 40)},
    3: {24: ("Name", 40), 25: ("Nickname", 40), 26: ("Birthday", 40), 27: ("Blood type", 40),
        28: ("Yes", 140), 29: None, 30: ("No", 199),       # は い / い いえ
        31: ("/", 141), 32: None, 33: None},               # 月 日 型 after the values
    15: {20: ("Name", 40), 21: ("Birthday", 40), 22: ("Blood type", 40),
         23: ("Yes", 140), 24: None, 25: ("No", 199),
         26: ("/", 141), 27: None, 28: None},
}
# The birthday page's month and blood-type lists (frame 2, parts 30-64):
# 月 and 型 are dropped, the numbers and A/B/AB/O move right by 8 into the
# middle of their old "1月" / "A型" slot.
LISTS = (2, 30, {170, 202}, 8)
COLON = 13      # the ':' cell (8x16), kept


def frames(data: bytes):
    out, i = [], 0
    while True:
        p = struct.unpack_from("<I", data, TABLE + 4 * i)[0]
        if not BASE <= p < BASE + len(data):
            return out
        o = p - BASE
        n = struct.unpack_from("<h", data, o)[0]
        out.append((o, [list(struct.unpack_from("<hhhhhhh", data, o + 8 + 14 * k)) for k in range(n)]
                    if 0 < n < 100 else []))
        i += 1


def part_tiles(part):
    _, _, cell, _, _, w, h = part
    return {cell + ty * 16 + tx for ty in range((h + 7) // 8) for tx in range((w + 7) // 8)}


def word_pixels(text: str):
    """(ink width, 16 rows of colour indices): the pair font, proportional
    (inked columns plus a 1 px gap), font row 0 on the cell's row 1 so the
    capitals sit where the kanji did, shadow down-right."""
    cols = []
    for ch in text:
        rows = pairfont.letter_rows(ch)
        used = [c for c in range(5) if any(r >> (4 - c) & 1 for r in rows)]
        if not used:
            cols += [[0] * 12] * 3
            continue
        for c in range(min(used), max(used) + 1):
            cols.append([r >> (4 - c) & 1 for r in rows])
        cols.append([0] * 12)
    cols.pop()
    w = len(cols)
    ink = [[False] * (w + 1) for _ in range(16)]
    for x, col in enumerate(cols):
        for r, bit in enumerate(col):
            ink[1 + r][x] = bool(bit)
    px = [[0] * (w + 1) for _ in range(16)]
    for y in range(16):
        for x in range(w + 1):
            if ink[y][x]:
                px[y][x] = INK
            elif y and x and ink[y - 1][x - 1]:
                px[y][x] = SHADOW
    return w, px


def get(buf, x, y):
    v = buf[y * STRIDE + x // 2]
    return v >> 4 if x & 1 else v & 15


def put(buf, x, y, v):
    i = y * STRIDE + x // 2
    buf[i] = (buf[i] & 0x0F) | (v << 4) if x & 1 else (buf[i] & 0xF0) | v


def main() -> None:
    data = (ROOT / "extracted" / FILE).read_bytes()
    fr = frames(data)
    strip = bytearray(data[PIXELS:PIXELS + STRIDE * H])
    f, first, drop, dx = LISTS
    shift = {}
    for k in range(first, len(fr[f][1])):
        if fr[f][1][k][2] in drop:
            EDITS[f][k] = None
        else:
            shift[k] = dx
    SHIFT = {f: shift}

    words = {}
    for wd, tile in WORDS.items():
        w, px = word_pixels(wd)
        cols = (w + 1 + 7) // 8                         # ink plus shadow column
        if tile // 16 % 2 or (tile + cols - 1) // 16 != tile // 16:
            raise SystemExit(f"{wd!r} doesn't fit its tile run")
        words[wd] = (w, tile, cols)
    reused = {t + dy * 16 + c for t, (_, _, n) in ((t, words[wd]) for wd, t in WORDS.items())
              for c in range(n) for dy in (0, 1)}
    if len(reused) != sum(2 * n for _, _, n in words.values()):
        raise SystemExit("two words share a tile")

    # Every part that keeps its cell must not use a reused tile.
    for f, (_, parts) in enumerate(fr):
        for k, p in enumerate(parts):
            if k in EDITS.get(f, {}):
                continue
            if part_tiles(p) & reused:
                raise SystemExit(f"frame {f} part {k} (cell {p[2]}) still uses a reused tile")

    # A transparent texel for dropped parts: the first 8 px tile row of colour 0.
    blank = next(t for t in range(256) if t not in reused
                 and all(get(strip, (t % 16) * 8 + x, (t // 16) * 8) == 0 for x in range(8)))

    for wd, (w, tile, cols) in words.items():
        _, px = word_pixels(wd)
        x0, y0 = (tile % 16) * 8, (tile // 16) * 8
        for y in range(16):
            for x in range(cols * 8):
                put(strip, x0 + x, y0 + y, px[y][x] if x <= w else 0)

    patches = []
    for f in sorted(set(EDITS) | set(SHIFT)):
        fo, parts = fr[f]
        new = [list(p) for p in parts]
        for k, edit in EDITS.get(f, {}).items():
            p = new[k]
            if edit is None:
                p[2], p[5], p[6] = blank, 8, 1
            elif edit[0] == ":":
                if p[2] != COLON:
                    raise SystemExit(f"frame {f} part {k} isn't the ':'")
                p[0] = edit[1]
            else:
                w, tile, cols = words[edit[0]]
                p[0], p[2], p[5], p[6] = edit[1], tile, cols * 8, 16
        for k, dx in SHIFT.get(f, {}).items():
            new[k][0] += dx
        for k, (old, rep) in enumerate(zip(parts, new)):
            if old == rep:
                continue
            o = fo + 8 + 14 * k
            what = EDITS.get(f, {}).get(k)
            note = "dropped" if k in EDITS.get(f, {}) and what is None else (
                f"-> {what[0]}" if what else f"moved {SHIFT[f][k]:+d}")
            patches.append({"file": FILE, "offset": f"0x{o:X}", "original": struct.pack("<7h", *old).hex(),
                            "replacement": struct.pack("<7h", *rep).hex(),
                            "comment": f"frame {f} part {k} (cell {old[2]}): {note}"})

    changed = [(x, y) for y in range(H) for x in range(W) if get(strip, x, y) != get(data[PIXELS:], x, y)]
    bands = {}
    for x, y in changed:
        bands.setdefault(y // 16, []).append((x, y))
    rects = []
    for _, pts in sorted(bands.items()):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        rects.append([min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1])
    orig = bytearray(get(data[PIXELS:], xx, yy) for rx, ry, rw, rh in rects
                     for yy in range(ry, ry + rh) for xx in range(rx, rx + rw))
    gdir = ROOT / "translation" / "graphics"
    name = f"name_labels_{PIXELS:05x}.png"
    png.write_indexed(gdir / name, W, H, bytes(get(strip, x, y) for y in range(H) for x in range(W)),
                      [(i * 17, i * 17, i * 17) for i in range(16)] + [(0, 0, 0)] * 240)
    doc = {
        "description": ("Character creation's pre-drawn words in NAME_ENT.NBN (game-internals 6d): the name page's "
                        "名前:/あだ名: captions, the birthday page (header, row labels, 月/型 after the months and "
                        "blood types) and the 'Is this OK?' summary (labels, 月/日/型 after the values, はい/いいえ), "
                        "for the player and for Shiori. English drawn with the pair font into the tiles of the "
                        "replaced glyphs, and the frames' parts rewritten (count and order kept; dropped parts draw "
                        "one transparent texel). Generated by tools/make_name_labels.py."),
        "images": [{"file": FILE, "png": f"graphics/{name}", "pixels": f"0x{PIXELS:X}", "stride": STRIDE,
                    "x": 0, "y": 0, "rects": rects, "original_crc32": f"0x{zlib.crc32(orig):08x}", "bpp": 4}],
        "bytes": patches,
    }
    (ROOT / "translation" / "name_entry_labels.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(words)} words in {len(reused) // 2} tile columns, {len(patches)} parts rewritten, "
          f"blank texel tile {blank}")


if __name__ == "__main__":
    main()
