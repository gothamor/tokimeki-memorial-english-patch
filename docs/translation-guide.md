# Translation guide

How to add English to the patch. Read [game-internals.md](game-internals.md)
for the formats, and the rules in [../AGENTS.md](../AGENTS.md) first.

## Translation files

`python -m tokipatch` applies every `translation/*.json` (not subfolders).
Put work that isn't ready in `translation/extra/`, and apply it on purpose
with `-t translation/extra/<file>.json` (`-t` replaces the default set, so
list every file you want).

One JSON file per screen or feature. It can have a `strings` list, an
`images` list, or both:

```json
{
  "description": "What this file covers.",
  "strings": [ ... ],
  "images":  [ ... ]
}
```

## Text (`strings`)

```json
{
  "file": "CDROM/EXEDIR/OPTION.EXN",
  "offset": "0xA880",
  "original": "文字表示速度",
  "text": "Text Speed"
}
```

- `file`: path on the disc (case-insensitive, no `;1`).
- `offset`: file offset of the first byte of the string (hex string).
- `original`: the exact Japanese currently there. The patcher refuses to run
  if it doesn't match and isn't NUL-terminated.
- `text`: plain English.
- `encoding` (optional): `"pairs"` (default) or `"fullwidth"`.

### Encodings

**`pairs` (default, use this).** The game can't draw ASCII (game-internals
§6b), so English is written as *letter pairs*. Each distinct two-letter
chunk ("Te", "xt", " S", …) gets an unused kanji code, and the patcher redraws
that kanji's font glyph with the two letters. On screen that's 6 px per
letter; on disc it's 1 byte per letter (odd lengths are padded with a space).
- Supported characters: `A–Z a–z 0–9`, space, and `. , ! ? ' " - : ; ( ) / & + %`.
  Anything else is rejected with an error. To add a character, draw it in
  `tokipatch/pairfont.py` (5 px wide, same metrics as the rest).
- The glyph pool is `translation/font/free_glyphs.txt` (993 glyphs). Each
  *distinct* pair uses one glyph, shared by every string in the game, so the
  pool is consumed by vocabulary, not by text length. The patch log lists
  the glyph used for each pair. If the pool ever runs out, the patcher says so.
- The glyphs live in the shared font in `SLPM_86.053`, so pair-encoded text
  works on any screen that draws through the game's text renderer. Graphics
  baked into images (like the title menu) still need image patches.

**`fullwidth`.** Each letter becomes a full-width Shift-JIS character
(`Name?` → `Ｎａｍｅ？`): 2 bytes and 12 px per letter, using the font's
original Latin glyphs. Space → ideographic space, `'` → `’`, `"` → `”`,
`-` → `−`, `~` → `〜`. Only use it where pair glyphs can't be used.

### Space budget
Original bytes + 1 (NUL) + NUL padding up to the next 4-byte boundary.
With `pairs` that's `budget - 1` letters (rounded down to even); with
`fullwidth`, `(budget - 1) // 2` letters. Too-long text is rejected with the
limit in the error. Shorten the English; don't touch the rule.

Screen width matters too: menus are sized for the Japanese. With `pairs`,
English that uses **no more letters than the original had bytes** is never
wider than the Japanese was. The patch log prints a `note:` for any string
that goes beyond that (using the padding), so check those on screen. For
multi-line text (description boxes), keep every line within its original
width.

### Code and data patches (`bytes`)

```json
{"file": "CDROM/EXEDIR/NAME_ENT.EXN", "offset": "0x1B8",
 "original": "10000424", "replacement": "0e000424",
 "comment": "set_glyph_advance(16) -> 14"}
```
These are raw bytes, verified against `original` before patching. Keep them
in `translation/code.json`, give each one a comment saying what the
instruction is, and document the reasoning in game-internals.

### Patterns to watch for
- **Icons and numbers drawn over text cells.** The game draws ○/× icons and
  numbers at fixed character cells, over blank characters in the string. Keep
  a blank glyph (`"  "`, i.e. two spaces, which maps to the font's blank
  0x8140) in exactly those cells, and arrange the English around them.
  Examples: the Yes/No lines (`"    Yes...       No...  "` keeps "Yes..."
  ending at cell 4 and "No..." at cell 10). A leading full-width space before
  an icon becomes a leading `"  "`. Strings after a game-drawn number (3番…)
  start with `": "`.
- **Messages split into pieces.** Some messages are several adjacent strings
  (e.g. `メニュー設定を` + `マウスライク` + `にしました`). You can't always tell
  whether the pieces share a line, so write them to read correctly either
  way. End a leading piece with a space (`"Menu mode set "`), continue in the
  next (`"to Mouse-like"`), and leave a trailing grammatical piece empty (`""`).
- **The same words as graphics.** A screen can show text that isn't a string
  at all (Options ▸ Text Speed / Icon Mode / Cursor Speed / Voice Mode use
  pre-drawn glyph cells). If a translated string doesn't change the screen,
  dump RAM via the GDB stub and search for the Japanese. No hit means it's
  graphics (testing.md).
- **Pointers into the middle of a string.** Possible in principle (code can
  point past a prefix), so if an on-screen label is a suffix of a string you
  translated, check it. (The suspected case on the Voice screen turned out to
  be graphics.)

**Finding strings:**

```bash
python tools/extract.py path/to/game.cue extracted
python tools/find_text.py extracted/CDROM/EXEDIR --grep "名前"
```

Columns: file, offset, budget in bytes (`-` = not NUL-terminated, usually
script bytecode: **don't patch** until the script format is understood), text.
`find_text.py` is pure Python and slow over the whole `extracted/` tree
(minutes), so point it at a directory or file. To find where a known on-screen
phrase lives, search for its Shift-JIS bytes directly (`data.find(text.encode("shift_jis"))`),
which is instant.

A string often exists in **more than one file**. The Options items appear
both in `OPTION.EXN` (title Options page) and in `SLPM_86.053` (in-game
settings). Translate each copy that a screen uses, and check which screen
you're looking at.

**Not yet possible:** dialogue in `SERIFU/`, `EVENT/`, `BUNKA/` and the
prologue script needs the bytecode format (see the open questions in
game-internals §8). Only UI strings from the EXE/overlays with a numeric
budget are safe today. Pair encoding halves the bytes English needs, which
makes many more UI strings fit in place than full-width did.

## Graphics (`images`)

```json
{
  "file": "CDROM/FUKUTEST/TITLE.NBN",
  "png": "graphics/title_menu.png",
  "pixels": "0x60000",
  "stride": 128,
  "x": 0,
  "y": 68,
  "rects": [[0, 0, 128, 32], [0, 32, 48, 16]],
  "original_crc32": "0xe7038d68"
}
```

- `pixels`: file offset of the 8bpp bitmap. `stride`: bytes per row.
- `x`, `y`: where the PNG's top-left pixel lands in that bitmap.
- `rects`: `[x, y, w, h]` areas *of the PNG* that are written. Everything else
  in the PNG is ignored, so it can contain the surrounding original art for
  context.
- `original_crc32`: CRC32 of the original bytes under all `rects`, row by row,
  rect by rect. The patcher refuses to run on a mismatch.
- `png`: path relative to the JSON file. It must be an **8-bit indexed PNG**
  whose pixel values are the game's palette indices. Only 8bpp targets are
  supported for now.

**Editing PNGs:** use an editor that keeps palette indices (Aseprite, GIMP in
Indexed mode with the embedded palette, Pro Motion). RGB PNGs are rejected.
The embedded palette is the game's CLUT for that graphic, so what you see is
what the game shows.

**Generated art:** `tools/make_title_menu.py <cue>` regenerates
`translation/graphics/title_menu.png` and `title_menu_options_selected.png`
from a built-in pixel font, using the original outline and gradient indices,
and prints each `original_crc32`. Follow that pattern for new menus: export
the original region with the right CLUT, draw, record the CRC of the replaced
cells.

**Every state of a graphic is separate art.** Menus usually have a highlighted
and an unselected version, and they may live in different places in the file.
The title menu's highlighted OPTIONS was a separate strip, missed the first
time. When you replace a graphic, check every state on screen (highlight each
item). To find the other versions, shape-match the cells you already know
(zero/non-zero masks) across the file; matching colour indices isn't enough.

**Finding a graphic and its palette:** see
[testing.md](testing.md#finding-graphics-vram-dumps). In short:
dump CPU→VRAM uploads in the isolated emulator, identify the block, then find
those bytes in the file that was loaded (`trace_reads.py`), and match the CLUT
by 5-bit colour values.

## Before you call it done
Run the checklist in [../AGENTS.md](../AGENTS.md#checklist-for-any-change-that-affects-the-output).
At minimum, build to a scratch folder, boot it, look at the changed screen, and
continue past it.
