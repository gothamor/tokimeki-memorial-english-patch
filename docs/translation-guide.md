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
§6b), so English is written as *letter pairs*: each 2-byte character code
holds two letters (ASCII with the top bit set), and a hook in the game's text
renderer draws the pair from a narrow font as it lays the text out
(game-internals §6f). On screen that's 7 px per letter; on disc it's 1 byte
per letter (odd lengths are padded with a space).
- Supported characters: `A–Z a–z 0–9`, space, and `. , ! ? ' " - : ; ( ) / & + %`.
  Anything else is rejected with an error. To add a character, draw it in
  `tokipatch/pairfont.py` (5 px wide, same metrics as the rest); the hook's
  font table covers all of ASCII 0x20–0x7F, so no code change is needed.
- Every pair is available, so there's no glyph budget: vocabulary costs
  nothing, only bytes do.
- The hook is in the EXE's shared renderer, so pair-encoded text works on any
  screen that draws through it (every text screen seen so far). Graphics
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

Strings with capacity `-` are usually dialogue: use the `dialogue` format
below, not `strings`.

## Dialogue (`dialogue`)

Dialogue strings are repacked instead of fitted one by one: the space of every
translated string in a block is pooled, the English is packed into it, and
every pointer to a moved string is rewritten (game-internals §6e). Example:
[translation/prologue.json](../translation/prologue.json).

```json
{
  "dialogue": [{
    "file": "CDROM/EXEDIR/NAME_ENT.EXN",
    "base": "0x80132000",
    "lines": [
      {"offset": "0x1b1d0",
       "original": "俺の名前は{P}。\nここ、私立きらめき高校の\n新入生だ。",
       "text": "My name's {P}.\nI'm a freshman at\nKirameki High."}
    ]
  }]
}
```

- `base`: the file's load address (its pointers are absolute). Overlays are
  0x80132000; SERIFU bases are listed in game-internals §6e.
- `\n` is a line break; `{P}`, `{G}`, ... insert names; `{q}` separates choice
  options (game-internals §6e has the full list).
- A line with `"text": ""` is left alone, so a file can be translated a bit at
  a time.
- Start from a dump: `python tools/dump_dialogue.py extracted/CDROM/SERIFU/EVENT_KI.BIN -o extracted/dumps/EVENT_KI.json`
  (it finds the base). **Keep dumps out of the repo** (they're the Japanese
  script; AGENTS.md rule 9). Only commit lines you've translated.

**Rules the patcher enforces:**
- **Same number of display lines and choices as the Japanese, with the same
  name codes on each line.** Scene code can wait for a specific line to start
  typing (Rei's introduction plays his animation on its 4th line). With
  fewer lines the game waits forever. Reflow the English to the original's
  line count.
- **At most 28 letters per line** (`max_cells`, default 28). A name code
  counts as its longest name (`script.TOKEN_CELLS`, e.g. `{P}` = 12).
- **The English must fit in the space of the strings it replaces.** It's
  about 1 byte per letter, the same as the Japanese bytes for a typical
  translation, so write tightly. The log line `dialogue: N string(s),
  X of Y bytes used` shows the margin.

**Style notes (from the prologue):**
- The box shows 3 lines at a time; 4–5 line strings scroll, which is fine.
- The game draws the speaker label and the opening bracket (`「`, `『`, or `（`
  for thoughts). Thought lines end with `)` and have no opening `(`.
- A text run with an odd number of letters before a name code wastes a cell,
  showing as a double space (`"My name is {P}"` → "is  Name"). Prefer an even
  run (`"My name's {P}"`).

Only UI strings with a numeric budget go through `strings`. Pair encoding
halves the bytes English needs, which makes many more UI strings fit in place
than full-width did.

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
