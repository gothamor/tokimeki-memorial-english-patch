# Game internals — Tokimeki Memorial: forever with you (PS1, SLPM-86053)

Everything here was found on the *PlayStation the Best* disc (SLPM-86053),
using `tools/extract.py`, `tools/find_text.py`, `tools/mipsdis.py` and the
emulator tools in `tools/emu/` (see [testing.md](testing.md)). Addresses are
KSEG0 RAM addresses unless noted. "File offset" means an offset inside a file
on the disc.

Each section says how a fact was established, so it can be re-checked.

---

## 1. Disc image

| | |
|---|---|
| Track 1 | MODE2/2352 data, 298,500 sectors (702,072,000 bytes) |
| Track 2 | CD-DA audio, 45,151,344 bytes, INDEX 00 at 00:00:00, INDEX 01 at 00:02:00 |
| Volume ID | `VX009J2` (system ID `PLAYSTATION`) |
| SYSTEM.CNF | `BOOT = cdrom:SLPM_86.053;1`, `TCB = 8`, `EVENT = 32`, `STACK = 801FFF00` |

Sector layout (MODE2/2352): 12 sync, 4 header (BCD MSF + mode 02), 8 subheader
(4 bytes repeated), 2048 data, 4 EDC, 276 ECC. The patcher only touches Form 1
sectors and regenerates EDC/ECC (`tokipatch/cd.py`). Our EDC/ECC code
reproduces the stored values on untouched sectors byte for byte, so it's
known correct.

**Quirk:** LBA 14515, the first sector of the `/CDROM` directory, has a mangled
subheader (`30 00 80 38 00 00 80 00`), and its directory records start at byte
0x10 instead of 0x18. The game never reads it (it uses hard-coded LBAs), but
our ISO walker does. `Track.read_data` falls back to offset 0x10 when the two
subheader copies differ.

Filesystem: ISO 9660, root holds `SYSTEM.CNF` (LBA 23), `SLPM_86.053` (LBA 24),
`KONAMIC3.STR` (LBA 400), `OPENXA.STR` (LBA 2080) and `/CDROM/` with 31
subdirectories (~1,370 files). `CDROM/DADIR/TR02.DA` points at LBA 298650,
which is the audio track (track 1 length + 150-sector pregap).
`tools/extract.py` writes a full LBA listing to `files.tsv`.

## 2. Main executable `SLPM_86.053`

| | |
|---|---|
| Header | PS-X EXE, 0x800 bytes |
| Load address | `0x80041000` (t_size `0xA2800`) |
| Entry point | `0x800420D0` |
| File offset → RAM | `RAM = offset + 0x80040800` |

It contains system/UI text (see §6), the CD loader, and the overlay loader.

## 3. Code overlays (`CDROM/EXEDIR/*.EXN`)

- 27 files, each exactly 196,608 bytes (96 sectors). They're MIPS code plus data,
  uncompressed (the first bytes are instructions).
- Loaded to **`0x80132000`** (pointer stored at `*(0x800B6D3C)`).
  `RAM = 0x80132000 + file offset`. Confirmed by a pointer table in
  `NAME_ENT.EXN` at 0x1AD28, whose pointers (`0x8014B150`…) land on strings at
  0x19150.
- Each game mode has its own overlay. `NAME_ENT.EXN` holds the new-game flow:
  memory card prompts, prologue narration and script, name/birthday entry.
  It's loaded as the title screen comes up. When its checksum failed, the game
  stuck on the white transition before the title menu appeared.

### Overlay loader (in `SLPM_86.053`)

A switch around `0x80078DC0`–`0x80078F84` picks a hard-coded LBA per mode, then:

```
a2 = LBA ; *(u8*)0x800B6D38 = 0x60 (sectors)
if (current == a2) state = 3            ; already loaded
else { *(u32*)0x800B6D40 = a2; CdRead(0x60, *(0x800B6D3C), a2); state = 1 }
```

Loader state lives at `0x800B6D34` (u8): 0 = idle, 1 = reading, 2 = read done
(set by `0x80078FE0` when the sync function `0x800460CC` returns bit 0),
3 = loaded and verified. The current LBA is at `0x800B6D40`.

`0x80079014` verifies the read with the checksum routine (§4):
on success state = 3 and it calls `0x80042458`. On failure it sets state = 0 and
LBA = 0, so the load is requested again: **an infinite reload loop**.

Hard-coded overlay LBAs (instruction address → LBA → file):

| Insn | LBA | File | | Insn | LBA | File |
|---|---|---|---|---|---|---|
| 80078dc0 | 38570 | OLH.EXN | | 80078e9c | 39434 | TEL.EXN |
| 80078dd4 | 37706 | EN_NICHI.EXN | | 80078eb0 | 37610 | ENDING.EXN |
| 80078de8 | 38282 | MASTER.EXN | | 80078ec4 | 37802 | ETC.EXN |
| 80078dfc | 38954 | RPG_BAT.EXN | | 80078ed8 | 37418 | DATE.EXN |
| 80078e10 | 37322 | BUNKA_SD.EXN | | 80078eec | 37514 | DATE2.EXN |
| 80078e24 | 39338 | TAIIKU.EXN | | 80078f00 | 38666 | OMIMAI.EXN |
| 80078e38 | 38186 | KANGEI.EXN | | 80078f14 | 37994 | GEKO.EXN |
| 80078e4c | 38858 | RENSYU.EXN | | 80078f28 | 39146 | SHUGAKU.EXN |
| 80078e60 | 37226 | BUNKASAI.EXN | | 80078f3c | 39626 | VALEN.EXN |
| 80078e74 | 37130 | BUNKAKEN.EXN | | 80078f50 | 39050 | SHOUGATU.EXN |
| 80078e88 | 38378 | NAME_ENT.EXN | | 80078f64 | 38762 | OPTION.EXN |
| | | | | 80078f74 | 39530 | TT.EXN |
| | | | | 80078f84 | 39242 | TACO.EXN |

Not in this switch: `EVENT.EXN`, `GYOZI.EXN`, `O.BIN` (loaded elsewhere; not yet traced).

**Consequence:** files can't be moved or resized without patching these
constants (and any other LBA tables for data files) as well as the ISO 9660
directory.

## 4. CD read and file checksum

| Address | Function |
|---|---|
| `0x80046318` | `read(a0 = sector count, a1 = RAM buffer, a2 = LBA)`, used for every file load seen so far |
| `0x800460CC` | returns the read status byte at `0x8012512A` |
| `0x8004636C` | `checksum_ok(a0 = sector count, a1 = buffer)` |

`checksum_ok` sums every byte of the first `count*2048 - 4` bytes into a
16-bit total, then compares it with the **big-endian u16** at
`buffer + count*2048 - 4`. The two bytes after it are always `12 10`.

So a file's last 4 bytes are `[sum16 hi][sum16 lo][0x12][0x10]`, where the sum
covers everything before them. This holds for every file whose size is a
whole number of sectors. All files with a valid trailer were.

Files with a valid trailer, by directory (from a scan of the extracted disc):
all 27 `EXEDIR` overlays, all 45 `SERIFU` dialogue files, 45/46 `BUNKA`,
all 164 `BUSTUP`, 76/78 `EVENT`, 12/12 `SPEAKTST`, most of `TACO`, `TAIIKU`,
`TARA_OBJ`, `FUKUTEST` (incl. `TITLE.NBN`), `END_OBJ`, `PROLODIR`, `*_SD`,
`MASTER`, `LASTPHOT`, `STAFF2`. None in `BS` (MDEC stills), `VAB_SE`, `VAB_SEQ`.

Only the overlay loader's call to the check has been confirmed. Assume
every file with a trailer is checked: the patcher fixes any trailer that
was valid in the original (`patcher.has_checksum`).

## 5. Boot sequence

From `tools/emu/trace_reads.py` (breakpoint on `0x80046318`), unpatched game:

| Order | File | Sectors | Buffer |
|---|---|---|---|
| 1 | `FUKUTEST/MAINROM.NBN` | 53 | 0x80180000 |
| 2 | `TMD/DUM.TMD` | 1 | 0x801F0000 |
| 3 | `FUKUTEST/TITLE.NBN` (title logo, menu, CLUTs) | 214 | 0x80180000 |
| 4 | `EXEDIR/NAME_ENT.EXN` | 96 | 0x80132000 |
| 5+ | `FUKUTEST/O_31_*.NBN` (opening/prologue images) | 33–65 | 0x80180000 / 0x801B0000 |

The opening movie plays from `OPENXA.STR`. Pressing Start skips to a white
fade, then the title. Left idle, the title returns to the attract loop
within roughly 10 seconds (not measured exactly).

**Controls follow the Japanese convention: ○ (Circle) confirms, × (Cross)
cancels/goes back.** This applies on the title menu and elsewhere. In the test
harness, ○ is the `C` key and × is the `X` key. (Confirmed by the user playing
the game.)

## 6. Text

- **Encoding:** plain Shift-JIS (JIS X 0208 double-byte), uncompressed,
  NUL-terminated.
- **In the EXE and overlays:** C string literals, 4-byte aligned, padded with NULs,
  reached through pointer tables (e.g. `NAME_ENT.EXN` 0x1AD28).
  An in-place replacement may use the original's bytes + NUL + padding to the
  next 4-byte boundary.
- **In script/dialogue files** (`SERIFU/*.BIN`, `BUNKA/*.BIN`, `SPEAKTST/*.BIN`,
  `EVENT/*.BIN`, and the prologue section of `NAME_ENT.EXN` from ~0x1B1D0):
  strings are packed at odd offsets, mixed with script bytecode, and often not
  NUL-terminated. **The bytecode format isn't reverse-engineered yet.** Don't
  patch these until it is; `find_text.py` marks them with capacity `-`.
- **Where things are:**

| Location | Content |
|---|---|
| `SLPM_86.053` 0x6EB40–0x76000 | system/UI: memory card, save/load, options screen, calendar, places, weekday/holiday command prompts, club names |
| `EXEDIR/NAME_ENT.EXN` 0x19150– | kana tables for name entry, memory-card/album prompts, prologue narration, name-entry questions (0x1ACE4 surname, 0x1AD04 name, 0x1AD10 nickname), default nicknames, prologue script |
| `EXEDIR/OPTION.EXN` 0xA880–0xA8EF | Options page items (title ▸ OPTIONS), one string per item |
| `SLPM_86.053` 0x6FA08–0x70290 | in-game system settings screen: item list, choices, help lines and confirmation messages (translated in `translation/extra/system_settings.json`, not verified on screen yet). **Not** used by the title Options sub-screens. |
| `EXEDIR/*.EXN` | per-mode UI text |
| `SERIFU/`, `BUNKA/`, `SPEAKTST/`, `EVENT/` | dialogue (thousands of lines) |

- The title menu text is **not** text. It's graphics (§7).
- **Strings aren't always referenced by data pointers.** No 32-bit pointer to
  the `OPTION.EXN` items exists, so the code builds their addresses in
  instructions. Relocating such strings means patching code, not a table.

### 6c. Options page sub-screens (title ▸ OPTIONS ▸ item)

`OPTION.EXN` runs the page and loads `FUKUTEST/OPTION.NBN` (61 sectors →
0x801B0000, checksum trailer) for its graphics. The sub-screens split into
**text** (drawn with the game font via `add_text`, translatable now) and
**graphics** (pre-drawn glyph cells, not yet translatable):

| Item | Contents | Source | Status |
|---|---|---|---|
| Text Speed | 遅い / 普通 / 速い | **graphics** (OPTION.NBN sheet) | Japanese |
| Icon Mode | ＴＹＰＥ‐Ａ / ＴＹＰＥ‐Ｂ / フリー + icon preview | **graphics** | Japanese |
| Mouse | (disabled without a PlayStation Mouse) | ? | not reachable in testing |
| Menu Mode | 4 choices + 3-line description box | text: `OPTION.EXN` 0xB30C– (choices), 0xA8F0–0xAA6B (descriptions, 3 lines per choice) | English, verified |
| Cursor Speed | 超遅い / 遅い / 普通 / 速い / 超速い | **graphics** | Japanese |
| Voice Mode | ＯＮ / ＯＦＦ / ×ボタンでカット | **graphics** | Japanese |
| Extras | フリートーク / エンディング (`OPTION.EXN` 0xAA6C/0xAA7C) | text | translated, box is empty until unlocked |

- `OPTION.EXN` 0xAC10–0xAFFF holds a debug menu's strings (XA/VAB/SEQ test
  calls, "設定メニュー１…Ｆ"). It's not reachable normally and isn't translated.
- **The OPTION.NBN glyph sheet:** 8bpp, 128 px wide rows, 16×16 cells, 8 per
  row, starting at file offset **0xC000** (row 0 = the yellow highlight bar).
  It's a *deduplicated* character set (Y T P E A B ビ O / 左 右 初 期 状 態 N F / …)
  covering every character used by the graphical labels, apparently
  pre-rendered from the game font with outline + gradient. Labels are drawn
  as one 16×16 sprite per character, 14 px apart, twice (shadow at +1,+1 with
  CLUT 0x7E10, text with 0x7E11; the highlighted item uses 0x7E50/0x7E51).
- **Where the label definitions live is still unknown.** None of these exist,
  in `OPTION.EXN`, `OPTION.NBN` or `SLPM_86.053`:
  Shift-JIS strings of the labels (no 遅い/ＴＹＰＥ in RAM while the screen
  shows them), cell-index lists for ＴＹＰＥ‐Ａ under any numbering origin
  (u8/u16, strides 1–4), or u-coordinate lists (u8/u16, strides 1–8). A write
  watchpoint on one label sprite packet didn't fire within 10 s (the packet
  is probably built once, when the sub-screen opens). Next step: arm the write
  watchpoint *before* opening the sub-screen, or trace from `OPTION.EXN`'s
  sub-screen handler (jump table at 0x80132110, `*(0x8013CA8C + 4·item)`).
- Since cells are shared between labels (い in 遅い and 速い), redrawing
  cells in place can't produce English. The label definitions have to be found
  and re-pointed at new cells (the sheet has spare rows).

### 6d. New game: album screen and name entry (`NAME_ENT.EXN`)

After GAME START, about 15 s pass, then the **album (save slot) screen**:
- **Message box: text.** `NAME_ENT.EXN` 0x197B4–0x1A14B, ~88 strings
  (memory-card checks, create/copy/erase/restart album, system-file prompts).
  - Lines starting with a full-width space leave room for an icon (○ before
    ボタン…) or for indentation.
  - `番アルバム…` lines follow an album number that the game draws in front.
- **Yes/No.** The no-save prompt uses `NAME_ENT.EXN` 0x19A0C (○ at cell 5,
  × at cell 11). Other prompts use the shared lines in `SLPM_86.053` 0x73470 /
  0x73488 (`　はい……　　ボタン`; ○/× drawn at cell 6).
- **Graphics (not translated):** the buttons コピー/ニュー/クリア/ロード,
  システム 有/無, slot numbers 1–14, the info-panel labels (年 月 日, 名前,
  あだ名, 所属部, クリア人数, 人). `SLPM_86.053` 0x70790–0x70853 holds similar
  labels (名前…, あだ名…), but changing them does not affect this screen.
- **Navigation:** the default Mouse-like menu mode moves the hand freely with
  the D-pad. To pick album 1 from the "Which album" prompt, hold ←, ↑, then
  nudge ↓/→ (see testing.md for exact timings).

Then **name entry**:
- **Questions: text.** `NAME_ENT.EXN` 0x1ACE4 / 0x1AD04 / 0x1AD10, then
  birthday/blood type 0x194C0, 0x19510, 0x19534, 0x1955C.
- **Graphics:** 名前:/あだ名: labels, side buttons かな/カナ/記号/漢字/終了.
- **Kana grid:** strings at 0x19150– (rows like あいうえお) plus conversion
  tables (0x192D8–). These are the characters the player can type on the
  かな/カナ pages.
- **English names already work, no patch needed.** The **記号** page isn't a
  table: it lists font characters in Shift-JIS order from 0x8140, with
  scroll arrows. Three clicks of the ▼ arrow reach ０–９, **Ａ–Ｚ and ａ–ｚ**.
  Fields hold 3 (family) + 3 (given) + ~6 (nickname) characters. A typed
  letter is a full-width character (2 bytes, drawn with the font's own wide
  Latin glyph). × moves the input cursor back a slot.
  - Decision (with the user): short English names via 記号 are acceptable.
    The kana pages stay as they are (they keep the hidden cheat names
    reachable).
  - Longer or narrower names would need the ASCII/narrow-letter renderer
    change (open question 2).
- **Data, not UI:** the default names 藤崎/詩織 (0x1956C/0x19574) and the
  cheat-name list (0x19590–).
- This screen sets glyph advance 16 at init; it's patched to 14. The typed
  name characters still line up with their underscores (checked).

### 6a. Text renderer (all in `SLPM_86.053`, shared by every screen seen so far)

Found by arming a GDB read watchpoint on an Options string *before* opening
the page (`tools/emu/watch_reads.py`). The text is laid out once, when the
screen opens, not every frame.

| Address | Role |
|---|---|
| `0x8004E788` | `add_text(a0 = x, a1 = y, a2 = colour/attr byte, a3 = string, [sp+0x38] = extra byte)`. Appends an 8-byte entry to the text list at `0x800B3DC0` (x s16, y s16, attr u8, glyph count u8, extra u8, 1). Entry count is at `0x800B3F60` (max 52 = 0x34). Called e.g. from `OPTION.EXN` at `0x80132CF0`. |
| `0x8004F268` | `layout_string(string)`. Reads **2 bytes per character, always**, combining them into a 16-bit code; stops at a NUL in either byte. Codes `< 0x8140` go to an error routine (`0x800AE0B0`) and the rest of the string is dropped. Other codes go through the range table to a glyph index. Returns the number of glyphs used. |
| `0x8004F364` | `render_glyph(index)`. Decodes the glyph (`0x8004F4F0`) into 16×12 4bpp and uploads it to a VRAM glyph-cache slot: x = 0x320 + (slot & 7)·4, y = 0x100 + (slot & 0x78)·2, 4×12 halfwords (`0x8004435C` = LoadImage). The slot counter is at `0x800B3F62`. |
| `0x8004F4F0` | Expands one 18-byte 1bpp glyph into nibbles. |

**Glyph advance:** cached glyphs are placed `index × advance` px apart (the
`multu` at `0x8004EF30` / `0x8004F030`). The advance is a global byte at
**`0x800B3F6A`**, set by `0x8004E750(a0)` to 16 if a0 == 16, else 14. The
text-system reset at `0x8004E708` forces anything other than 14/16 back to 14.
Calls seen: `OPTION.EXN` 0x80132CA0 (14), `NAME_ENT.EXN` 0x801321B4 (**16**,
patched to 14 by `translation/code.json`), 0x80139724 (14), 0x8013BCFC (14).
Pair glyphs are laid out for a 14 px advance (letters at columns 0–4 and
7–11 → an even 7 px per letter). At 16 px they show a gap after every second
letter, so screens that use 16 get patched to 14.

`add_text`'s fifth argument (entry byte 6) is 0 at every call site seen; its
purpose is unknown.

### 6b. Font

- **There is no BIOS font use.** No `Krom2RawAdd` (B0:51) stub exists among the
  EXE's 208 BIOS call stubs. The font is the game's own data.
- **Location:** RAM `0x800B6D50` = `SLPM_86.053` file offset `0x76550`.
  3,418 glyphs × 18 bytes (to `0x855A4`).
- **Format:** 12×12 pixels, 1 bpp, MSB first, rows packed back to back
  (12 bits per row). Latin letters use rows 1–9 for capitals (baseline row 9),
  rows 4–9 for lowercase x-height, and row 10+ for descenders.
- **Code → glyph range table:** RAM `0x800B402C`–`0x800B40E3`, 46 × (u16 first
  code, u16 first glyph index), sorted. Glyph = base + (code − first) of the
  last range with first ≤ code (CRC32 of the table: `0x3CC19FF3`).

  | Codes | Glyphs | Content |
  |---|---|---|
  | 0x8140–0x84BE | 0–452 | punctuation, digits, Ａ–Ｚ, ａ–ｚ, hiragana, katakana, Greek, Cyrillic |
  | 0x889F–0x9872 | 453–3417 | JIS level-1 kanji (亜 … 蓮) |
  | ≥ 0x9873 | none | JIS level-2 kanji aren't in the font; not drawn |

- **ASCII is not supported:** plain ASCII bytes produce codes < 0x8140 and draw
  nothing (tested: the Options item rendered blank). Full-width Ａ–Ｚ works but
  takes 2 bytes and 12 px per letter.
- **English solution in use: letter-pair glyphs.** Glyphs of kanji that never
  appear in the game's text are redrawn to hold two narrow letters each, so
  English costs 1 byte and 6 px per letter with no code changes
  (`tokipatch/font.py`, `tokipatch/pairfont.py`). There are 993 such glyphs
  (`tools/find_free_glyphs.py` → `translation/font/free_glyphs.txt`; the
  heuristic is described in that tool). If a "free" kanji turns out to be
  used, it will show up as two Latin letters inside Japanese text. Report it
  and remove it from the list.

## 7. Graphics

### General
- Most graphics are **raw pixel data with separate palettes**, not TIM files.
- Uploads to VRAM come in 64×128-halfword blocks (16 KiB). 64 halfwords is
  128 px at 8bpp or 256 px at 4bpp. Palettes are uploaded as 256×1 (256-colour
  CLUTs).
- To tell 8bpp from 4bpp: render a region as 4bpp. If shapes show vertical
  1-pixel striping, it's really 8bpp.
- `BS/*.BS` and `*.STR` are MDEC-compressed stills and movies (different tooling,
  not yet handled).

### `FUKUTEST/TITLE.NBN` (438,272 bytes, checksum trailer)
- Holds the title logo, copyright line, the GAME START/OPTIONS menu cells,
  character art and 16 CLUTs. Loaded to 0x80180000 and uploaded from there.
- Pixel data in 16 KiB blocks, 128 bytes per row (8bpp). The layout of every
  block isn't fully mapped. The parts used so far:
  - **Menu cells:** block at file offset **0x60000**, rows 68–115, 16×16 cells:

    | Row y | Cells (x=0…127) |
    |---|---|
    | 68 | ゲームスタート *selected* (x 0–111), オ (x 112–127) |
    | 84 | ゲームスタート *unselected* (x 0–111), プ (x 112–127) |
    | 100 | シ (0–15) ョ (16–31) ン (32–47); x ≥ 48 is unrelated art, **don't touch** |

    The game draws each item's cells next to each other on screen, so a word
    drawn as one strip and sliced into the same cells displays seamlessly.
    The オプション cells here are the **unselected** (grey) version only.
  - **Highlighted OPTIONS:** a separate, contiguous 80×16 strip in the block
    at file offset **0x5C000**, rows 52–67, x 48–127 (オ プ シ ョ ン at x = 48,
    64, 80, 96, 112), in the blue selected style. On those rows **x < 48 is the
    pointing-hand cursor; don't touch it.** Found by shape-matching the grey
    オ/プ/シ cells (zero/non-zero pixel masks) against every 16×16 window of
    the file. A colour-index search missed it.
  - **Styles in the menu CLUT:** selected = outline index 8, fill gradient
    2,3,4,5,6,7,7,6,5,4,3,2 on cell rows 2–13. Unselected = outline 24, gradient
    18–23 the same way. Indices 10–15 and 25–31 are anti-aliasing blends.
  - **CLUTs:** 16 × 512 bytes in 0x4C000–0x4E1FF, **not stored in upload order**.
    VRAM upload # → file offset: 0→0x4C400, 1→0x4C600, 2→0x4C800, 3→0x4CA00,
    4→0x4CC00, 5→0x4CE00, 6→0x4D000, 7→0x4D200, 8→0x4D400, 9→0x4D600,
    10→0x4D800, 11→0x4DA00, 12→0x4DC00, **13→0x4E000 (menu)**, 14→0x4DE00,
    15→0x4C000.
- Colours are 15-bit BGR (`r = c & 31`, `g = c>>5 & 31`, `b = c>>10 & 31`; bit 15 = STP).
  Index 0 / colour 0x0000 is transparent.

## 8. Open questions / next research targets

1. **Script bytecode** in `SERIFU`/`EVENT`/prologue: control codes, line breaks,
   name insertion, how string lengths are encoded. Needed before any dialogue
   can be translated.
2. **Text renderer leftovers:** the sprite drawer that places cached glyphs (for
   a true variable-width font later); whether dialogue goes through the same
   `add_text`/`layout_string` path (likely, unverified); line-wrapping and
   box-width rules for dialogue.
3. **Pointer tables:** systematically map them in the EXE and overlays, so strings
   can be relocated into free space instead of only fitting in place.
4. **Data-file LBA tables:** how non-overlay files (e.g. `TITLE.NBN`, `SERIFU/*`) are
   located (hard-coded constants like the overlays?). Needed before files can grow.
5. Where `EVENT.EXN`, `GYOZI.EXN` and `O.BIN` are loaded from.
6. Which title-menu graphics remain: the logo (ときめきメモリアル) is Japanese art
   in the same file and hasn't been touched.
