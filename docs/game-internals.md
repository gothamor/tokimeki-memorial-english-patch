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
- **In dialogue** (`SERIFU/*.BIN`, the prologue in `NAME_ENT.EXN` 0x1B1D0–, and
  probably `BUNKA/`, `SPEAKTST/`, `EVENT/`): NUL-terminated strings with
  1-byte ASCII control codes mixed in (`0x20` = line break, `P` = player's
  name, ...), reached through tables of absolute RAM pointers. There is no
  separate bytecode for the text itself. `find_text.py` shows these as capacity
  `-` because the control bytes break its runs; use `tools/dump_dialogue.py`.
  Full details in §6e.
- **Where things are:**

| Location | Content |
|---|---|
| `SLPM_86.053` 0x6EB40–0x76000 | system/UI: memory card, save/load, options screen, calendar, places, weekday/holiday command prompts, club names |
| `EXEDIR/NAME_ENT.EXN` 0x19150– | kana tables for name entry, memory-card/album prompts, prologue narration, name-entry questions (0x1ACE4 surname, 0x1AD04 name, 0x1AD10 nickname), default nicknames, prologue script |
| `EXEDIR/OPTION.EXN` 0xA880–0xA8EF | Options page items (title ▸ OPTIONS), one string per item |
| `SLPM_86.053` 0x6FA08–0x70290 | in-game system settings screen: item list, choices, help lines and confirmation messages (`translation/system_settings.json`, included in normal builds). The user reports all submenus translated; main list and Text Speed choices/help are screenshot-verified. Individual confirmation/conditional-path coverage is not itemized (§6i). **Not** used by the title Options sub-screens. |
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

### 6e. Dialogue

Found by dumping the prologue strings, disassembling the EXE code that compares
bytes against them, and stepping through the prologue in the emulator
(testing.md, "Reaching the prologue"). Everything here was checked on screen
with English text unless marked otherwise.

**String format.** NUL-terminated. A byte that is one of the control codes
below takes 1 byte; anything else is a 2-byte Shift-JIS character (the
renderer doesn't check lead-byte ranges, it just skips 2). The patcher writes
these as `\n` and `{X}` in translation files (`tokipatch/script.py`).

| Byte | Meaning |
|---|---|
| `0x20` | end of display line |
| `q` (0x71) | end of a choice option (also ends the line) |
| `P` | player's full name, family + given with no space (on screen: "My name's みみ.") |
| `G` | the girl's name (RAM 0x800CA190) |
| `p`, `m` | RAM 0x800CA16C / 0x800CA174 (likely family / given name; unverified) |
| `F` | `sprintf("%s%s", p-buffer, 0x800CA174)` (unverified) |
| `Y` | the fixed string 好雄 (Yoshio) at 0x800B2240; a parallel expansion path uses 0x800B2250 |
| `S`, `O`, `W`, `A`, `M` | RAM 0x800CA23C / 0x800CA248 / 0x800CA250 / 0x800CA25C / 0x800CA280 (place, item, ...? unverified) |

Unpatched dynamic names are inserted as full-width Shift-JIS, 14 px per
character. Fixed names and name-table entries translated with `pairs` retain
their pair encoding when the renderer inserts them.

**Renderer:** `0x80081190` (EXE), called with (x, y, attr, string, ...). It
copies the string to a 512-byte stack buffer, splits it at `0x20`/`q`, copies
each line into a 64-byte buffer (`strncpy`, so a line must stay under 64 bytes
after name expansion), expands the name codes, and draws each line with
`add_text` (§6a) at 16 px line spacing. So dialogue uses the same font, glyph
cache and 14 px advance as the UI, and **letter-pair English works unchanged**.
- The speaker label and an opening bracket are drawn by the game before the
  first line: `「` for other characters, `『` for the player, `（` for the
  player's thoughts. In the prologue, thought strings end with `）` but never
  start with `（`; in English, end them with `)` only. In `EVENT_FU.BIN`
  the game draws **both** brackets: its thought strings contain neither, and
  an English `)` showed up doubled on screen (§6j). The patcher therefore
  requires the English to end with `)` exactly when the original ends with
  `）`.
- **Speaker-label source:** EXE function `0x80051438` constructs the normal
  character label. Character 0 copies Shiori from `0x800AFB7C`; the other
  character IDs select a pointer from the 16-entry table at `0x800B35F4`.
  It then appends `ちゃん` from `0x800AFB84` for its special case, or `さん`
  from `0x800AFB8C` normally. `translation/character_names.json` replaces the
  short-name strings and blanks both suffixes, because English uses bare given
  names here. This was found by statically following the string references and
  table loads in `SLPM_86.053`; EXE RAM addresses convert to file offsets by
  subtracting `0x80040800` (§2).
- **Name tables:** the adjacent full-name strings occupy file offsets
  `0x72C80`–`0x72D37` (Shiori's at `0x72C80`), with their 16-entry pointer table
  beginning at `0x72D38`.
  The 16 short speaker names occupy `0x72D78`–`0x72DF3`, followed immediately
  by their pointer table at `0x72DF4` (`0x800B35F4` in RAM). Both string areas
  are pooled and repointed by the dialogue patcher. The English full-name pool
  uses all 184 available bytes (with Shiori's "S. Fujisaki", §6m), so several given names have to be initials;
  the short-name pool uses 100 of 124 bytes.
- Four special Shiori literals and four special Yoshio literals live at file
  offsets `0x71980`–`0x719DC` (RAM `0x800B2180`–`0x800B21DC`) and bypass the
  normal short-name table. The fixed `{Y}` expansions are at file offsets
  `0x71A40` and `0x71A50` (RAM `0x800B2240`/`0x800B2250`). These all need to be
  translated along with the two name tables for names to be consistent across
  normal dialogue and special paths.
- Lines that start with `（` are outdented by 14 px.
- A first pass (0x800812D4) sets `*(u32*)0x80122D1C = 0` unless every
  character is one of `…‥「。、`. Purpose unknown (silent lines?). English
  never matches, like normal Japanese text. Keep pure-punctuation lines in
  Japanese punctuation to be safe.
- String helpers it uses are BIOS A-functions (`0x800AE0F0` strcpy,
  `0x800AE090` strncpy, `0x800AE0E0` strlen), all byte-wise, so **strings need
  no alignment**.

**Text box:** shows **3 lines**. Strings with 4 or 5 lines (both occur) scroll
up one line at a time as the typewriter reaches them. Width: measured ≈29
letters after the speaker label, so the patcher limits a line to **28 cells**
(1 per letter, 2 per full-width character; `script.MAX_CELLS`).
"Hey, she just looked at you!" (28) reaches the right edge.

**Typewriter** (EXE, used by the prologue; probably by all dialogue):
`0x800B3F60` text-list entry count, `0x3F62` total glyphs, `0x3F64` first
dialogue entry, `0x3F66` speed, `0x3F68` glyphs revealed. `0x8004EC24` reveals
one glyph every speed+1 frames and returns 1 when all are shown;
`0x8004ECF0` returns the text-list entry (display line) currently being typed.

**Scene scripts time events to display lines.** The prologue is hand-written
code in `NAME_ENT.EXN`: step machines indexed by `0x800E738D`, each step
calling *start line* `0x80144B44` (line index in `*(u8*)0x8014D180`) and
*run line* `0x80144C8C` every frame. Rei's step (0x80148380) waits until
`0x8004ECF0() == 0x800E71E1 + 3`, i.e. until his **4th** display line starts,
then plays his entrance. With a 3-line translation it waited forever (a clean
hang with no error, the box just stays up). **Rule: a translation must keep
the original's number of display lines and choices.** The patcher enforces it
(`script.structure`).

**Voiced lines advance by themselves** (`0x80144E34`–): once the XA clip
reaches its end sector and the text is fully typed, a counter at
`0x800E7384` runs to 61 frames (~1 s) and the scene moves on. Pressing ○
also advances. Per prologue line `i`: speaker/voice byte at
`NAME_ENT.EXN` 0x1BA04+i (low nibble 0xF = no voice), XA position at
0x1BA30+8i, a second table at 0x1BB88+8i.

**Pointers and relocation.** Every dialogue string found so far is reached
only through 32-bit pointers in its own file, as absolute RAM addresses
(file offset + load address). So strings can be repacked freely inside the
space of the strings they replace, if every pointer is updated
(`patcher.apply_dialogue`). The patcher refuses strings that code builds
addresses for (`lui`/`addiu`), and pointers into the middle of a string.

| File | Load address (from its pointers) |
|---|---|
| `EXEDIR/NAME_ENT.EXN` prologue | 0x80132000 (overlay); 43 strings 0x1B1D0–0x1B957, table 0x1B958 |
| `SERIFU/DATE_*`, `EVENT_*` | 0x80198000 (`DATE_FU` and `EVENT_FU` confirmed at runtime; §6j, §6k) |
| `SERIFU/SERIFU, G_APPEAR, G_INVITE, GASSHUKU, GEKO, GROUP_D, HAGEMASI, NYUBU, OMIMAI, SHOGATU, SHUGAKU, VALEN, WHITE, XMAS` | 0x80197000 |
| `SERIFU/G_BIRTH, KARADATA, P_BIRTH, ZAKOSEN` | 0x801B0000 |
| `SERIFU/GASSH_FU` | 0x801B4400 (not on the 0x800 grid; see below) |
| `SERIFU/EPILOG` | 0x80180000 |
| `SERIFU/ENDING` | 0x801F0000 |
| `BUNKA/*` (46 files) | 0x801E8000 |
| `SPEAKTST/TEST_*` (12 files) | 0x80180000 |

(The table is from a scan for the base that makes the most pointers land on
string starts. Only the prologue has been verified in the game.) Sizes, from
`tools/dump_dialogue.py` after the 2026-10-07 extraction fix below (Japanese
bytes, excluding NULs): `SERIFU/` 16,727 strings / ~652 KB, `BUNKA/` 12,898 /
~454 KB, `SPEAKTST/` 16,340 / ~629 KB. The earlier figures (~9,000 / ~9,100
strings) missed every string that follows a pointer table. `EVENT/` has no
dialogue strings.
A few strings (mostly `SPEAKTST`) also contain bytes such as `<`, `>`, `-`,
`n` that the renderer doesn't treat as control codes; `script.decode`
rejects them, so `dump_dialogue.py` leaves them out. Find out what reads them
before translating those files.

**Strings directly after pointer tables (extraction fix, 2026-10-07).** Script
files interleave short pointer lists with the strings they list, so many
strings start right after an aligned pointer word, not after a NUL. In
`SERIFU/EVENT_FU.BIN` the word at `0x648` points at `0x62C` and is
immediately followed by the string at `0x64C`; `0x69C`–`0x6A7` holds three
pointers followed by the string at `0x6A8`. Some words point at other lists
rather than at strings (`0x6F4` → the list at `0x648`, `0x6F8` → the list at
`0x69C`), so scene mapping has to decode a nested table structure; that
structure isn't understood yet.

The old dumper accepted a pointer target only if the byte before it was NUL,
which dropped all of these. `dump_dialogue.starts_string()` now also accepts
an aligned target preceded by a word that points into the same file. That is
a safe boundary: such a word's third byte is below 0x20 for every base in the
table above (0x13–0x1F), which is neither a Shift-JIS byte nor a control
code, so no decodable string can run through it. Effect: `DATE_FU` 186 → 474 strings,
`EVENT_FU` 119 → 157, `GEKO` 615 → 1,011, `TEST_FU` 2,473 → 2,474. All the
pilot offsets below are now dumped. Synthetic regression tests are in
`tests/test_dialogue_extraction.py`.

Method: for every aligned word, take the target `word − base`; if it decodes
as dialogue, classify the byte before it. Across all SERIFU, SPEAKTST and
BUNKA files, 10,658 targets with a non-NUL preceding byte follow an in-file
pointer word. Apart from `GASSH_FU` (wrong base, next paragraph), **no
Japanese-text target is rejected as an interior pointer**. The dumper still
reports left-out targets on stderr (`--rejected` lists them): 691, all
"no Japanese text". The sampled ones are 4-byte binary records
(`code, 0, 0, n`, e.g. `DATE_FU.BIN` `0x548C`, `0x6E38`, `0x6FA0`) whose first
byte happens to be a name-code letter (`A`, `P`, `p`); they are data, not lines.
The patcher's guard against pointers into the middle of translated text is
unchanged and tested.

**`GASSH_FU.BIN` loads at `0x801B4400`**, not `0x801BE000`. Its first pointer
list (file `0x4C`) holds `0x801B4400` and `0x801B441C`, matching the strings at
file offsets 0 and `0x1C`. At that base it has 1,207 strings and no rejected
Japanese targets; at the old base, 183 strings and 969 Japanese targets
that land mid-string. The old search only tried 0x800-aligned bases; `guess_base()` now
also votes on candidates from pointer value minus string start. Every other
SERIFU, SPEAKTST and BUNKA file keeps the base it had before. Static only;
the load address hasn't been traced in the game.

**Character-pack planning inventory (2026-10-07).** With the fixed dumper,
`SERIFU/DATE_FU.BIN` (47,104 file bytes) has 474 pointer-target strings
(25,417 Japanese bytes), `SERIFU/EVENT_FU.BIN` (12,288 bytes) has 157
(4,831 bytes), both at inferred base `0x80198000`; `SPEAKTST/TEST_FU.BIN`
(186,368 bytes) has 2,474 (94,496 bytes) at `0x80180000`. There are 11
`SERIFU/DATE_*` files. These are string counts, including choices and player
replies, not display-line or scene counts. Japanese bytes approximate the
repack pool only for the strings actually translated (each slot also gets its
NUL and alignment padding). The user has selected Shiori for the first pack;
per-scene consumers and runtime load addresses still need tracing. The staged
plan is in `NEXT_STEPS.md`; this inventory doesn't establish full-file or
full-route coverage.

**Early Shiori pilot candidates (2026-10-07, static inspection only).**
`SERIFU/EVENT_FU.BIN` contains a short early-morning school-walk exchange:
file offsets `0x62C`, `0x64C`, `0x668`, `0x6A8` (inferred RAM `0x8019862C`,
`0x8019864C`, `0x80198668`, `0x801986A8`). The entries cover getting up early,
a greeting, the player addressing Shiori, and a thought after walking to
school; they have 2/2/3/3 display lines with no choices or name codes.
Each has exactly one pointer, at file `0x648`, `0x6A0`, `0x6A4`, `0x6F0`
respectively, and no code references. A dry run of `patcher.apply_dialogue`
with placeholder English on the extracted file accepted all four, rewrote
only those pointers, and reported a 180-byte pool for those four; with the
scene's fifth string `0x2AA8` (§6j) the pool is **188 bytes**. This is a
compact candidate, but **not an early-game event**: §6j decodes its trigger
(Shiori affection ≥ 61 plus another score ≥ 50, nonzero interaction counters,
about a 1% roll per check, once per game). The scene also includes the string
at `0x2AA8`.

A fallback is the shared `SERIFU/GEKO.BIN` Shiori walk-home dialogue (inferred
base `0x80197000`): candidate clusters start at file `0x1A24` (her invitation),
`0x1B50` (accepting a player invitation), `0x1C54` (declining it). The last
contains the two-choice prompt at `0x1C9C` and response at `0x1CD0`. Some of
these strings follow pointer tables; the fixed dumper now includes all five.
Ownership is supported by explicit Shiori references in the exchange, not
just a filename. Actual early-game availability, relationship thresholds,
scene boundaries and shared consumers remain unverified. These candidates
were found by enumerating aligned pointer values in the inferred file range,
decoding their targets and inspecting the local text; no script dumps or
screenshots are committed. Prefer whichever scene is naturally encountered
and replayable near the start, then trace its real loader and scene driver.

**Budgets: the two limits for translating the whole script.**
1. **Space.** English pair text costs 1 byte per letter, Japanese 2 bytes per
   character, and English needs ~2× the characters, so a translation uses
   about as many bytes as the original. The prologue fits (1912 of 1928
   bytes) only after tightening the English. The zero tail of `NAME_ENT.EXN`
   (0x1BCD0–) is **not** free: code references reach 0x253A4 (BSS). Other
   files may have slack; check each.
2. **Pair glyphs: solved.** Pre-drawn pair glyphs needed one free kanji per
   distinct pair (the UI plus the prologue used 383 of 993; prose passes
   ~1,000 distinct pairs after ~80,000 letters). The renderer now composes
   every pair on the fly (§6f), so vocabulary no longer costs anything.

### 6a. Text renderer (all in `SLPM_86.053`, shared by every screen seen so far)

Found by arming a GDB read watchpoint on an Options string *before* opening
the page (`tools/emu/watch_reads.py`). The text is laid out once, when the
screen opens, not every frame.

| Address | Role |
|---|---|
| `0x8004E788` | `add_text(a0 = x, a1 = y, a2 = colour/attr byte, a3 = string, [sp+0x38] = extra byte)`. Appends an 8-byte entry to the text list at `0x800B3DC0` (x s16, y s16, attr u8, glyph count u8, extra u8, 1). Entry count is at `0x800B3F60` (max 52 = 0x34). Called e.g. from `OPTION.EXN` at `0x80132CF0`. |
| `0x8004F268` | `layout_string(string)`. Reads **2 bytes per character, always**, combining them into a 16-bit code; stops at a NUL in either byte. Codes `< 0x8140` go to an error routine (`0x800AE0B0`) and the rest of the string is dropped. Other codes go through the range table to a glyph index. Returns the number of glyphs used. **Patched:** codes ≥ 0xA000 are English letter pairs, composed by the renderer hook (§6f). |
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
- **English solution in use: letter pairs composed by a renderer hook** (§6f).
  English costs 1 byte and 7 px per letter, any pair of letters is available,
  and the font itself is left untouched.
- **Unused kanji.** `tools/find_free_glyphs.py` → `translation/font/free_glyphs.txt`
  lists 993 level-1 kanji that never appear in the game's text (the heuristic
  is described in that tool). Earlier builds redrew them as pre-drawn letter
  pairs; that pool ran out after a few scenes, which is why the hook replaced
  it. The list isn't used by the patcher any more. It's kept as spare font
  slots (18 bytes each, in runs of at most 11) for future renderer work.

### 6f. Renderer hook: letter pairs composed on the fly (`tokipatch/renderer.py`)

**Why one hook is enough.** A scan of the EXE and every overlay for calls and
address constants found exactly one path into the font: `add_text`
(`jal` at 0x8004E82C) → `layout_string` → `render_glyph` (`jal` at
0x8004F32C) → glyph expander (`jal` at 0x8004F390), which is the only code
that builds the font address (0x8004F4FC) or the range table address
(0x8004F2CC, 0x8004F304). Dialogue goes through the same path (§6e).

**Encoding.** English is ASCII with the top bit set (0x20–0x7E → 0xA0–0xFE),
1 byte per letter, read by `layout_string` two at a time as a code
0xA0A0–0xFEFE. These codes are free:
- No game text uses a lead byte ≥ 0xA0. The font ends at 0x9872 and the
  original lookup draws nothing for higher codes (the range loop at
  0x8004F30C falls off the end of the table without calling `render_glyph`).
- The dialogue renderer (0x80081190) only compares bytes against its ASCII
  control codes (0x20, `q`, `P`, ...) and specific `0x81xx` punctuation;
  every other lead byte is a 2-byte character. Bytes ≥ 0x80 never match.
- `"  "` (two spaces) is still written as 0x8140, the font's own blank, so the
  icon cells on Yes/No lines are unchanged (translation-guide, patterns).

**The hook.** In `layout_string`, 0x8004F2CC/0x8004F2D0 (`lui t1,0x800b;
lhu t1,0x402c(t1)`, the start of the range lookup) become
`j 0x8004443C; andi t0,v1,0xffff` (t0 = the code, as the game computes it at
0x8004F2D4). The hook:
1. Code < 0xA000: runs the two replaced instructions and jumps back to
   0x8004F2D8, so Japanese takes exactly the original path.
2. Otherwise: builds the 18-byte glyph from two 5×12 letters (letter 1 in
   columns 0–4, letter 2 in columns 7–11, the same layout the pre-drawn pairs
   had, so text looks identical), stores it in a scratch glyph, calls
   `render_glyph(index)` with an index that points at the scratch glyph, and
   continues at the loop top 0x8004F294 with `v0 = s1`, exactly like the
   game's own glyph path. It only uses t/a registers; s0/s1/ra are untouched.

The scratch glyph lies *before* the font, so its index is negative
(0xFFFF9A36 = −26058): the expander computes `FONT + index·18` in 32-bit
arithmetic, which wraps to the scratch address 0x8004451C. The scratch only
has to live until the expander has run (it copies the glyph into the 4bpp
upload buffer at 0x801255F0 straight away), so one buffer serves every glyph.

**Where it lives.** Two functions in the EXE that nothing calls:

| Address | Size | Was | Now holds |
|---|---|---|---|
| `0x8004443C` | 708 | a leaf-ish routine reading 0x800B3D10– (GPU state?) | hook code (216 bytes), scratch glyph at 0x8004451C |
| `0x8004B778` | 948 | a leaf routine masking bytes at stride 0x40 | 5×12 font: 96 characters (ASCII 0x20–0x7F) × 8 bytes = 768 bytes |

Font entry format: two little-endian words, rows 0–5 then rows 6–11, row `r`
at bits `5r…5r+4`, bit 4 = leftmost pixel (`renderer.narrow_font()`).

**How "unused" was established** (redo this before using any other region):
- *Static:* no `jal`/`j` to either address in the EXE or any `EXEDIR/*.EXN`;
  no 32-bit word equal to either address in **any file on the disc**; no
  `lui`+`addiu/ori/load` pair building either address, even with the low half
  up to 200 instructions after the `lui`.
- *Runtime:* `tools/emu/watch_exec.py` with execution breakpoints on both
  entry points (and 0x80044700) for 15 minutes of the **unpatched** game:
  boot, title, Options page and sub-screens, album load, name entry, the whole
  prologue, several weeks of the main loop, and a SERIFU dialogue event
  (meeting 如月). 0 hits.
- *Patched:* the patched game ran from boot to the first in-game screen.
  A call into either region would now run hook code or font data and crash.

Other unreferenced functions in the game's own code (static scan only, not
checked at runtime): 0x80049140 (616 bytes, non-leaf), 0x80054C74 (504),
0x8008EFE4 (368), 0x8008D8A0 (364), 0x8005A410 (336), 0x8008F934 (280),
0x80058DA0 (272). The scan treats each `jr ra` + delay slot as a function end
and each `jal` target as a start; 0x8009xxxx and above looks like PsyQ
library code and was left alone.

**Checks.** `renderer.install` refuses to patch unless the hook site holds
the original two instructions and both regions match their original CRC32
(0x95CF8D48, 0xC57F80EA). `tokipatch/mips.py` is a small assembler for the
hook source; capstone disassembles its output back to the same instructions.
`tools/check_renderer.py` runs the hook in a minimal MIPS interpreter (load
delay slots modelled): it produces byte-identical glyphs to
`pairfont.render_pair` for all 6,084 supported pairs and leaves Japanese
codes on the original path. Run it after changing the hook or the font.

**Verified on screen:** title Options page and Menu Mode descriptions, album
prompts with the ○/× icons, all name-entry questions, the whole prologue
(including Rei's line-timed entrance), then the first in-game screen.

### 6g. Main game loop screen (`translation/main_screen.json`)

The weekly command screen: stat panel, vertical calendar, command icons and
the player's thought line in the message box.

- **What's text:** only the speaker name and the thought line (the live
  `add_text` list had 3 entries: a hidden 8-glyph one, the name, the
  13-glyph line). The stat labels, numbers, calendar and icons are sprites
  (§7, "Sprite frames" and `MAINROM.NBN`). A read watchpoint on the 体調
  string at `SLPM_86.053` 0x72AD0 never fired while the panel redrew, so the
  stat-name strings there are used elsewhere (now translated in `outings.json`,
  but their consuming screens remain unverified).
- **Thought lines** are EXE strings reached from code (`lui`/`addiu`), so each
  must fit its own slot. They contain `0x20` line breaks and go through the
  dialogue renderer. The game draws `（`, so they end with `）` and the English
  ends with `)`:
  - **Weekday screen** (Sunday night, "plans for the week"):
    `SLPM_86.053` 0x6F624–0x6F754 (明日から何をしようかな？） and the variants
    for exams, the baseball tournament, summer camp, the school festival,
    the school trip, make-up classes, illness).
  - **Holiday screen** (Sundays and holidays during the day): 0x70DA4–0x70EF8
    (今日は何をしようかな？）, date day, club practice, meeting place, phone).
    Some lines are built from pieces with a name in between, e.g.
    今日は、 + girl + とデートだ）, and それじゃ、⏎ + place + で、⏎ + girl +
    を待つか。）. The English keeps each piece's line breaks and reads with
    the inserted word at the same spot ("Well then," / "<place> it is" /
    "<girl> will come.)").
  - 0x6F610 平日コマンド画面 / 0x70D90 休日コマンド画面 look like debug labels
    and aren't translated.
- **In-game Save/Load (memory card icon, Sunday night only):** 0x6F76C–0x6F9E4.
  The slot panel's labels (名前…, あだ名…, 所属部‥, クリア人数‥) are
  `translation/album_panel_exe.json` (included in normal builds). The user has
  verified English labels, dates and values on populated Load slots 1/2
  (None/Soccer); Save-mode and empty/error/System branches remain unverified (§6i).
- **Date in RAM:** 0x800E62BE year (95), 0x800E62BF month, 0x800E62C0 day,
  0x800E62C1 weekday (0 = Monday … 6 = Sunday). Found by diffing RAM dumps
  of two Sundays. The calendar code at 0x80064CA0– sets the weekday sprite's
  frame to `0x52 + weekday`, and its colour byte to 0x43 (Saturday) or 0x44
  (Sunday or a holiday from the table at 0x800E62C4 + day).

### 6h. Main-loop EXE text tables

The remaining main-loop text in `SLPM_86.053` is not one screen-sized block.
It includes ordinary in-place strings plus several contiguous, pointer-backed
string pools. The latter are declared as `dialogue` blocks even when they are
short labels, so all pointers can be relocated within the original pool:

| File offsets | Contents | Translation |
|---|---|---|
| `0x6F3FC`–`0x71A50` | system title fragments; recurring club, term/holiday, health, Christmas/New Year and sound-effect text; phone/news labels; special name paths | `main_events.json`, `character_names.json` |
| `0x72AD0`–`0x72B1B` | nine textual stat names (not the sprite-based main stat panel) | `outings.json` |
| `0x72B4C`–`0x72C2B` | 20 outing-place names | `outings.json` |
| `0x72C8C`–`0x72DF3` | full and short character-name pools (§6e) | `character_names.json` |
| `0x730A4`–`0x73107` | 11 clubs plus None, including Literature at the start | `clubs.json` |
| `0x751F8`–`0x75FFC` | memory-card check, concert/movie listings, town-news copy and magazine reactions | `town_news.json` |

The stat-name strings at `0x72AD0` still do not drive the main screen's stat
panel: that panel is graphics (§6g/§7). Their exact consumer remains to be
confirmed on screen. Likewise, the place and club tables are identified by
their contents and pointer structure, but every screen that consumes them has
not yet been reached.

The club-list screen is a confirmed consumer of the pool at
`0x730A4`–`0x73107`. The user's original screenshots show ten translated club
names, untranslated Literature, Cancel, a successful Soccer selection and the
“Soccer club joined.” result. Literature at `0x730A4` was omitted when the
pool started at `0x730AC`; it is now included. The complete pool uses 94/100
bytes, and all 12 relocated pointers were checked against the encoded text.
Disassembly of `0x8006B648` confirms that the menu draws only the first eleven
entries from the pointer table at `0x800B3908` (file `0x73108`); None is the
twelfth table entry and Cancel is a separate literal at file `0x70860`.

**Club Day notice: fixed coordinates, not concatenation.** Disassembling
`0x800607E0`–`0x800608B4` shows six separate calls to `add_text` with these
positions (game pixels relative to the text origin):

| String file offset | x | y | Current English |
|---|---:|---:|---|
| `0x7029C` | -86 | 50 | ` Each ` |
| `0x702A4` | -44 | 50 | `3rd Sunday` |
| `0x702B0` | 26 | 50 | ` is` |
| `0x702B8` | -72 | 66 | ` Club Day, so` |
| `0x702CC` | -72 | 82 | `don't   ` (three trailing spaces) |
| `0x702D8` | -16 | 82 | `miss it.` |

At 7 px per English letter, the last two fragments have only eight letters
between their starting positions. The previous `don't miss` used ten encoded
cells including padding, so the final fragment overprinted it. Repartitioning
the words respects that eight-cell limit. The speaker label is drawn through
`0x80050DFC`; a six-byte name starts at x = -128 and ends at -86, immediately
before the first fragment. `Capt.` plus the leading space in ` Each ` gives
the label a visible gap. The old claim that a leading pair-space was dropped
was not established; fixed-position overlap explains the screenshot.

The user's follow-up screenshots and play test verify both corrections:
Literature fits its list column and joining Soccer reaches the captain's
notice without overlapping text. The Literature label extends slightly beyond
the green selector rectangle; the fixed-position notice retains a wide gap
between “don't” and “miss it.”. The user accepts these cosmetic issues for now
and explicitly requests leaving both unchanged. This verifies the corrected
list and notice, not every other consumer of the club-name table.

Not every Shift-JIS-looking run in these regions is player-facing text. The
main-loop translation deliberately leaves the debug labels at `0x6F610`,
`0x70940`, `0x709AC` and `0x70D90`, obsolete album fragments at
`0x6EB40`–`0x6EB67`, renderer punctuation/control literals around
`0x71804`–`0x71A3F`, fixed-width blank town-news rows, and unreferenced
single-kanji data unchanged. These exclusions are also recorded in the JSON
descriptions so a later audit does not repeatedly rediscover them.

### 6i. Save/Load panel and in-game settings (review and user verification, 2026-10-07)

These are `translation/album_panel_exe.json` and `system_settings.json`, now
included in normal builds after testing in the combined `.emu/review_settings/`
candidate. The user reports successful translation of the panel and all
in-game settings submenus. Screenshots show
the main settings list, Text Speed choices/help, and populated Load slots 1/2
with dates and None/Soccer club values. No overlap or clipping was reported.
Detailed coverage and remaining checks are in `testing.md` under the settings
handoff. Promotion changes file discovery only, not the tested patch contents.
The static findings below come from string-reference searches and Capstone
disassembly of the original `extracted/SLPM_86.053`, mapped at `0x80040800`.
They do not establish untested branch behavior or unlock title Options graphics.

**Save/Load panel (`album_panel_exe.json`, 21 strings).** The two literal
groups at file `0x70790`–`0x707F7` and `0x707F8`–`0x70853` are consumed by
the panel code around RAM `0x80069758`–`0x80069F94`. The first branch reads
card metadata indexed by `*(u8*)0x800E7D36`; the second uses the index at
`0x800E7397` into records at `0x80123120`, stride `0xF00`.

- Names and labels are **concatenated**, not independently positioned.
  `strcpy` (`0x800AE0F0`) copies a label into a stack buffer, followed by
  `strncat` (`0x800AE110`) or `strcat` for the value. The buffers are 32 bytes
  apart: date `sp+0xC8`, name `sp+0xA8`, nickname `sp+0x88`, club `sp+0x68`,
  cleared count `sp+0x48`. Name appends are bounded at 6 + 6 bytes, nickname
  at 13; clubs come from the table at `0x800B3908` (current English maximum
  10 bytes), cleared count uses one or two full-width digits (up to 4 bytes).
  `Name: ` / `Nickname: ` / `Club: ` / `Cleared: ` therefore preserve a visible
  separator while using at most 19 / 24 / 17 / 15 bytes including NUL.
  These byte bounds do not prove the fields fit their on-screen panel.
- The number heading appends **only two bytes** from file `0x70790` or
  `0x7080C`. See RAM `0x80069770`–`0x80069784` and
  `0x80069C48`–`0x80069C58`: the latter calls `strncat` with `a2 = 2`.
  The former draft `: Album` would show only `: `; the translation now
  explicitly stores that suffix. The heading is the existing full-width
  slot number plus a colon, not a promised full English "Album" heading.
- Year/month/day suffixes are also two-byte appends, in the date builders
  around `0x80069848` onward and `0x80069CB0`–`0x80069E30`.
  The year/month replacements `/` each encode as one two-byte `/ ` pair;
  the empty day replacement starts with NUL, so it appends nothing.
  No copy lengths, date digits or code instructions are changed.
- The fields share an x origin and draw at y = -64 (date), -48 (name),
  -32 (nickname), -16 (club), 0 (cleared count); the heading is at y = -80,
  x = field origin + 12. Empty/error slots and the System entry use separate
  paths. Test both Save and Load: two copies do not imply both were exercised.

**In-game settings (`system_settings.json`, 114 strings).** Initialization
at RAM `0x8005DC4C` uses file `0x6FA08`–`0x70290`; the main title is passed
to `0x8006612C`. Choices, help and confirmations use the shared text drawer
`0x8004E788`, not title Options' pre-rendered choice graphics.

- Icon Mode confirmations use two distinct rows, x = -128, y = 50 and 66
  (Type A references at `0x8005E660` and `0x8005E67C`; B/Free follow the
  same layout). Cursor Speed and Voice Mode confirmations likewise use
  separate rows (around `0x8005FABC`–`0x8005FD90`, and `0x80060000` onward).
  Their drafts already read correctly across those rows.
- Menu Mode descriptions occupy three rows at y = 50, 66, 82 (around
  `0x8005F380`). Its confirmations also occupy three rows, not a concatenated
  sentence: first x = -128, second x = -86 with color attribute 1, third
  x = -128. The first choice's references are `0x8005F518`, `0x8005F534`,
  `0x8005F550`; the other choices repeat the arrangement. All four now use
  `Menu mode:` / `<mode>` / `selected.`, preserving all three visible pieces.
  The longest mode, `Mouse-like + Menu A`, is 18 bytes / 126 px and fits the
  row's static bounds. The user reports submenu translation success, but
  individual confirmation states and selection rectangles were not itemized.
- Menu Mode confirmation code writes values 0–3 to `0x800E7312`, corresponding
  to Mouse-like, Menu A, Menu B, and Mouse-like + Menu A. This is a static
  mapping, not a runtime identification of the old 95/4/23 test card's mode.
- Cursor Speed has **two label sets**, file `0x6FFEC`–`0x7000C` and
  `0x70014`–`0x7003C`. The branch around `0x8005F7FC` checks bytes at
  `0x800E7D2C` (threshold 9) and `0x800E67C4` (threshold 2) to choose a set.
  The meaning of those input/device conditions remains unverified; do not
  assume one set is dead because only the other appears with a controller.
- Help/confirmation lines retain their separate draws and fit within a
  256 px row at the normal 14 px pair-cell advance. Padding-using labels
  are screenshot-verified for Text Speed (`Normal` fits) and the main list
  with Icon Mode highlighted. Every highlight state was not individually
  documented; the user's broader report covers all submenus' translations.
  No navigation, settings values, selector sizes or coordinates were patched.

### 6j. Girl special events (`SERIFU/EVENT_*.BIN`) and how they're triggered

Found 2026-10-07 by static disassembly (capstone, `tools/mipsdis.py`) of the
original `SLPM_86.053` and overlays, then a GDB run of the **unpatched** game
from the 95/4/23 test card to 95/5/17 (`tools/emu/watch_events.py`). Shiori
is girl id 0 throughout. Nothing here has been patched.

**Scene data in an EVENT file.** A scene is a *master* list of pointers to
string lists, one list per part; a parallel list points at one byte list per
part (one byte per string, `FF`-terminated; probably speaker/expression codes,
not decoded), and a third pointer per scene leads to further per-scene records
(not decoded). In `EVENT_FU.BIN`, scene 2 (the early-morning walk) is master
`0x6F4` → lists `0x648` {`0x62C`}, `0x69C` {`0x2AA8`, `0x64C`, `0x668`},
`0x6F0` {`0x6A8`}; byte lists via `0x70C` → `06` / `0C 0D 00` / `06`. The
string at `0x2AA8` lies far from the rest and is part of the scene too.
Scene 1 is master `0x390`, byte lists via `0x3C0`.

**Event table.** GEKO, DATE, GYOZI, SHOUGATU and SHUGAKU each contain the
same 237-word table (GEKO: `0x80145EC0`, written by code at
`0x8013799C`–`0x80138828`): 79 masters, then 79 byte-list pointers, then 79
third pointers. Shiori's events are entries **6–13**. Each event has a setup
function that copies entry k of the three tables to the current-event slots
`0x80146274/78/7C`; entry 7 (scene 2) is set up at `0x8013AA1C`, which also
sets girl id `0x800E71DF = 0`. `EVENT.EXN` contains a similar per-girl table,
but its offsets don't match the disc's `EVENT_FU.BIN` (e.g. `0x6F8` for
`0x6F4`) and its code calls addresses outside the main EXE, so it looks like
a stale build; the overlay loader never loads it (§3).

**Loading.** GEKO's `0x80138F7C` switches on girl id `*(u8*)0x800E71DF`
(14 cases) and reads that girl's EVENT file: Shiori's case reads LBA 44581
(`EVENT_FU.BIN`), 6 sectors, to `0x80198000`. This confirms the
`0x80198000` base statically; DATE, SHOUGATU and SHUGAKU have the same loader
(immediates `0x8014C840`, `0x8013D3F8`, `0x80137744`).

**Dispatch.** `*(u32*)0x80122CD4` = girl id, `*(u32*)0x80122CD0` = scene.
GEKO's `0x80138840` jumps through `0x80144910` on the girl id; Shiori's
handler `0x80139A8C` runs scene 1 → `0x80139B08`, scene 2 → `0x8013A144`,
scene 8 → `0x8013A230`. Each scene is a step machine: a copied list of
function pointers indexed by the step byte `0x800E738A` (scene 2's list is at
`0x801464BC`, starting with the setup above and later the EVENT loader).

**Main-loop event queue.** The EXE's main state is set by `0x80042878(state)`
(`0x800E7388`). Each day's event is a 4-byte record `type, girl, scene, flags`
in a queue starting at `0x800E691C`, current index `0x800E699C`. The day
handler around `0x800714D0`–`0x800722B8` switches on the record type: case
`0x800721B0` copies girl/scene into `0x80122CD4/CD0` (special events), case
`0x80072210` sets the girl id and enters state `0x5B` (meeting scenes). In
the test run, type-`0x48` records produced meetings with girl 1 (95/5/10) and
girl 8 (95/5/17); no Shiori special event occurred.

**Why the walk is rare: `0x8006FB4C`.** The queue builder (`0x80070B80`)
asks this selector for a (girl, scene) pair and writes it as a type-`0x45`
record. The selector loops over girls 0–10 and, for each, requires:
the met flag (bit 1 of `0x800E6448 + 0x38·g`), rank `0x80051B48(g) < 2`,
a nonzero sum of 20 per-girl counters (`0x800E6451 + 0x38·g`; all were 0 at
95/5/17), and `rand() & 15 < 5`, then jumps through `0x800B1314` by girl.
Shiori's case `0x8006FC70` requires `rand() % 100 < 3`; then if bit 0 of
`0x800E7378` is 1 it may pick scene 1 (needs `0x80066ACC() == 1`,
`0x80051A68(0) & 0x7F < 2` and flag `0x800E67EC == 0`), otherwise **scene 2,
once, if flag `0x800E67ED == 0`** (the flag is then set).

The rank function returns 4 if A < 10, 3 if A < 50, 2 if B < 50, 1 if
B < 80, else 0, with A = `0x80052C88(g)` = weight × affection / 100, clamped
to 0–100 (weight byte at `0x800B41A0 + g`, Shiori 83; affection = s16 at
`0x800E6442 + 0x38·g`) and B = `0x80052648(g)` (another score, not decoded).
So scene 2 needs **A ≥ 50 (Shiori's affection ≥ 61) and B ≥ 50**, the
counters above, and a roll of about 1% per check. On the test card at 95/5/17
her affection was 47 (A = 39). **The walk is not an early-game event.**

Other Shiori scenes found on the way: scene 8 is chosen by the EXE directly
(`0x80075628`) when `0x800754C0()` returns 1: two packed month/day fields
(`0x800E6378` vs `0x800E644C`, probably birthdays) must match, in March or
early April, among other checks. The injury message step machine
(`0x80073198`, string file `0x709D0`) can start a one-shot event for girl
`0x0B` scene 2 when `0x800E7378 & 0xFF < 0x19`, flag `0x800E6837 == 0` and
`0x800E62BD == 0`.

**Forced in the emulator (2026-10-07, unpatched).** The day handler's
record-type switch is the jump table at `0x800B1340`, indexed by the type
itself (`type < 0x4B`): type `0x45` → `0x800721B0`, type `0x48` →
`0x80072210`. `tools/emu/force_event.py 0 2 --clear-flag 0x800E67ED` stops
at `0x80071DD0` (index already advanced, record about to be read) and turns
the next type-`0x00` record into `45 00 02 00`. From the 95/4/23 test card
that was Tuesday 95/4/25; the scene played in full and the rest of the week
ran normally, twice. `trace_reads.py` during the replay showed
`EVENT_FU.BIN` (LBA 44581, 6 sectors) read to **`0x80198000`** from
`ra = 0x80138FC4` (the GEKO loader above), then Shiori's portrait
`BUSTUP/HU02.BIN` to `0x80180000`. That confirms the load address at
runtime. What the screen showed, in order:
1. `0x62C`: the player's thought (`（`), 2 lines, over a morning street.
2. `0x2AA8` + `0x64C` **in one box**: label 藤崎 and `「`, then
   "あっ、{P}" as line 1 and the two-line greeting as lines 2–3. The part's
   byte list gives these two strings `0C` and `0D`.
3. `0x668`: the player speaking (`『`, code `00`), 3 lines.
4. `0x6A8`: the player's thought (code `06`), 3 lines.
With this test save `{P}` displayed as ま君 in both the unpatched and the
English build; whether the 君 comes from a name field or the code isn't
established. A translation of `0x2AA8` + `0x64C` must still fit
the 3-line box together, since they share it.

**All of `EVENT_FU.BIN` (2026-10-07, static).** Every one of the file's
157 strings belongs to exactly one of Shiori's eight table entries; a part's
string count is the length of its `FF`-terminated byte list (string lists
can be back to back). Per-string codes: `00` player (『), `01` Shiori (「),
`06` thought (both brackets drawn by the game), `0C` + `0D` two Shiori
strings sharing one box, `07` and `10` sound-effect lines (a click, a phone
ringing). Short one-word strings are stored together at `0x2AA8`–`0x2AF0`;
each still belongs to one scene. Who runs each entry (setup function found by its table
loads, then its scene step list, then the dispatcher):

| Entry | Master | Overlay, selector | Strings | Content | Trigger (static) |
|---|---|---|---:|---|---|
| 6 | `0x390` | GEKO, scene 1 | 21 | sudden rain on the way home, Shiori without an umbrella | selector `0x8006FB4C` (bit 0 of `0x800E7378` set): `0x80066ACC() == 1` (a date-window check), rank `0x80051A68(0) & 0x7F < 2`, flag `0x800E67EC` |
| 7 | `0x6F4` | GEKO, scene 2 | 5 | morning walk (translated) | see above |
| 8 | `0xA78` | DATE, scene 3 | 19 | "do you remember this place?" | `0x800CA2F8 == 0`, months 9–11, both ranks best, flag `0x800E67EE`, date step `0x800E7389/738A == 1/1` |
| 9 | `0xFFC` | DATE, scene 4 | 18 | park date in spring | place 1 (Kirameki Park), months 3–5, flag `0x800E67EF`, date step `0x738A == 13` |
| 10 | `0x14DC` | DATE, scene 5 | 15 | theme park in winter, stuck on the Ferris wheel | place 12 (Theme Park), months 12–2, both ranks best plus bit `0x80` of `0x80051A68`, flag `0x800E67F0`, `*(u32*)0x80122CDC == 2`, step `1/0x23` |
| 11 | `0x18FC` | DATE, scene 6 | 16 | pool in summer, Shiori goes missing | place 16 (Pool), year ≥ 96, months 6–8, `0x80051A68 & 0x7F < 3`, rank < 2, flag `0x800E67F1`, girl byte `0x800E646D`, step `1/10` |
| 12 | `0x1D78` | SHOUGATU, Christmas party stage 6 | 21 | walking home after the Christmas party, white Christmas | Christmas-party flow (state `0x52`); stage 3's girl selector `0x80140030` picks stage 6 when `*(u8*)0x80145FE4 == 0` (set in stage 2), writes girl 0 / scene id 7 and counts up flag `0x800E67F2` |
| 13 | `0x2584` | GEKO, scene 8 | 42 | Shiori phones the player | EXE `0x800754C0` (two packed month/day fields equal, March or early April) |

DATE's top-level switch (`0x8014C0C8`, table `0x8015B3D0`) is on the girl id
in `0x80122CD4` too; case 0 runs Shiori's dispatcher `0x8014F370`, which maps
scene ids 3/4/5/6 to step machines `0x8014FAE0`/`FBA0`/`FC80`/`FE90`. Date
events are chosen by `0x8013272C` (girl id first) through the helper
`0x801326B0(scene, one_shot, flag_index)`, which sets `0x80122CD0`, sets the
one-shot byte `0x800E67EC + flag_index` and enters state `0x5E`. Flags come
in blocks of 7 per girl; Shiori's are indices 0–6 (`0x800E67EC`–`F2`).
**Place ids are 1-based** indexes of the outing-name table (file
`0x72C30`): the scene texts match (park, Ferris wheel, swimming). Place 0
(entry 8) is the neighborhood park (近所の公園, seen on screen); its name isn't in the outing table. GYOZI.EXN does not run any Shiori event: its
read at `0x80135BC8` takes index 8 of its own scene tables, and the third
word only coincides with the event table.

**On screen (2026-10-07, forced, unpatched and English).** Sound lines
(codes `07`, `10`) are drawn at the box's left edge in light blue with no
label or bracket. Strings with 4 lines scroll and the label scrolls away
with the first line; a `0C` + `0D` pair longer than 3 lines scrolls the same
way. In the English build `{G}` showed "Shiori" in the player's line, so it
expands from the translated name table; `{p}` showed the test save's ま and
Shiori's `{P}` showed ま君. The rain scene starts in the classroom, the phone
call moves to Shiori's room.

**Dates and the other event flows (2026-10-07, traced and forced).**
- **Appointments.** Eight slots at `0x800E67CC + 4·i`: bits 0–4 place
  (1-based; 0 = neighborhood park), 12–15 month, 16–20 day, 24 a flag,
  25–28 girl, 29 active. `0x8006AEC4(year, month, day)` checks the slots
  against today's date; on a match the holiday screen says "today I have a
  date with <girl>" and the heart icon starts it. The launcher `0x80076DA0`
  copies slot 0's girl/place into a `[0x80, girl, place]` queue record and
  enters state `0x50` (DATE.EXN). Writing slot 0 on the 95/4/23 test save
  (`tools/emu/force_date.py`) gives a real date with Shiori on 4/30.
- **Date-event chooser.** DATE.EXN calls `0x8013272C` at each date step
  (`0x800E7389`/`738A`); the steps seen were 0/15, 0/41, then 1/x. A park
  date reached 1/13 and picked scene 4 by itself. The other three need a
  season and affection ranks the test save lacks, so the tool jumps to the
  scene's call (PC write through the GDB stub) at its step: 1/1 (scene 3,
  place 0), 1/35 (scene 5, theme park), 1/10 (scene 6, pool). The scene
  plays and the date ends normally. The theme-park date asks which ride
  first (DATE_FU text); the forced Ferris-wheel scene doesn't follow that
  choice.
- **SHOUGATU flows.** State `0x52` runs the Christmas-party flow through
  the stage dispatcher `0x8013D180` (stage in `0x800E7389`; stages 6/7/8 are
  Shiori/KG/MI's after-party scenes, their entries 12/36/60). The day-record
  type `0x30` runs White Day (state `0x55`; Ijuin in the hallway, then a
  reply event when a girl gave chocolate). A forced type-`0x48` record
  (meeting) with girl 0 returned the game to the title screen: don't force
  it for Shiori. `tools/emu/force_christmas.py` swaps the next weekday's
  state `0x40` for `0x52` and sets stage 6 / girl 0 / scene id 7.
- **Overlay entry points** (GEKO `0x8013882C`, DATE `0x8014C0A0`,
  SHOUGATU `0x8013D180`) aren't referenced by any `jal`, data word or
  `lui`/`addiu` pair in the EXE or overlays; how the EXE calls them isn't
  known yet.

**Overlay selection.** The loader switch (§3) is indexed by
`*(u8*)0x800E738E − 0x11` through the jump table at `0x800B19E8`
(0x81 entries). GEKO.EXN is loaded for values `0x45`, `0x46`, `0x48`, `0x49`,
`0x4C` of that index (mapped by following each case to its LBA constant;
cases falling through to a shared default weren't separated).

### 6k. Regular dates (`SERIFU/DATE_FU.BIN`) and choices

Found 2026-10-07 by static disassembly of `DATE.EXN` and the EXE, then forced
museum dates in DuckStation (unpatched and English; testing.md "Testing date
conversations"). All 27 sections are translated in
`translation/shiori_dates.json` (2026-10-08; 471 of 476 strings, the five
pure-punctuation pause lines stay Japanese).

**Section table.** `DATE.EXN` holds three parallel 27-entry tables at
`0x8015BDC0` (masters), `0x8015BE2C` (byte lists) and `0x8015BE98` (third
pointers), statically holding Shiori's `DATE_FU.BIN` offsets (code from
`0x80141050` on rewrites them for other girls, like GEKO's event table).
Each section has the EVENT_FU layout (§6j): master → one string list per
part, a parallel `FF`-terminated code byte per string. **All 474 strings are
reached from these 27 sections, each exactly once, and each string has
exactly one pointer.** A section's setup copies its entry to
`0x800CA160/164/168`.

**Places.** The date setup switches on the place `*(u8*)0x800CA2F8` − 1
through the jump table at `0x8015B060` (20 cases, `0x80144A70`–`0x80144BA0`),
each storing one setup function. Place ids are the 1-based outing ids (§6j):

| Section | File range | Strings | Place / use | Setup |
|---:|---|---:|---|---|
| 0 | `0x0`–`0x6A8` | 30 | 7 Art Museum | `0x80134C64` |
| 1 | `0xB48`–`0xD50` | 10 | 10 Bowling Alley | `0x80135620` |
| 2 | `0xF44`–`0x1168` | 8 | 15 Concert Hall | `0x80136340` |
| 3 | `0x1330`–`0x166C` | 15 | 4 Zoo | `0x801344C8` |
| 4 | `0x2414`–`0x26AC` | 17 | 18 Shrine (festival, yukata) | `0x80136A74` |
| 5 | `0x2A78`–`0x2E44` | 15 | 9 Arcade | `0x801353F8` |
| 6 | `0x3B10`–`0x3D38` | 10 | 11 Karaoke | `0x80135804` |
| 7 | `0x3F40`–`0x4178` | 12 | 0 Neighborhood park: talk, ask about her hobbies or favorite places | `0x80133DE8` |
| 8 | `0x4B0C`–`0x4D68` | 8 | 14 Cinema | `0x80135E7C` |
| 9 | `0x4F40`–`0x5020` | 6 | parade invitation, inside the Theme Park date's flow | `0x8013BBF0` |
| 10 | `0x5130`–`0x5324` | 10 | 16 Pool | `0x801366A4` |
| 11 | `0x5514`–`0x5984` | 16 | 6 Planetarium | `0x801349A0` |
| 12 | `0x5E08`–`0x5FB4` | 8 | 17 Beach | `0x80136870` |
| 13 | `0x6170`–`0x6354` | 10 | 5 Botanical Garden | `0x801347B8` |
| 14 | `0x6534`–`0x6C9C` | 30 | 2 Shopping | `0x80135B4C` |
| 15 | `0x71A0`–`0x73BC` | 10 | 19 Skating Rink | `0x80136B70` |
| 16 | `0x7594`–`0x7764` | 10 | 20 Ski Resort | `0x80136D3C` |
| 17 | `0x7958`–`0x7E60` | 21 | 13 Stadium | `0x80135C14` |
| 18 | `0x81F0`–`0x84F0` | 15 | 3 Aquarium | `0x8013426C` |
| 19 | `0x8774`–`0x8964` | 10 | 8 Library | `0x8013518C` |
| 20 | `0x8B4C`–`0xA25C` | 85 | 12 Theme Park | `0x80135A34` |
| 21 | `0xAF94`–`0xB348` | 18 | 1 Kirameki Park (walk) | `0x80133EA0` |
| 22 | `0x18F4`–`0x1EDC` | 36 | end of every date (her verdict, the player's answer) | `0x8013B488`, `0x80140CE0` |
| 23 | `0x3104`–`0x3630` | 35 | meeting at the place (waiting, her being late) | `0x8013AE5C` |
| 24 | `0x4368`–`0x449C` | 10 | seasonal small talk | `0x8013AF1C` |
| 25 | `0x461C`–`0x4900` | 13 | "found out that her hobby is ..." notes (code `04`) | `0x8013B884` |
| 26 | `0x5CCC`–`0x5D3C` | 4 | "let's go home, {P}" | `0x8013B7B0` |

(The place switch, sections 0, 4, 7, 21 and 17, and the part selection of
22, 23, 24 and 26 below were confirmed by forcing them; 9 and 25 statically.) A date runs 23 → 24 (on
certain days) → the place's section → 22 → 26, with an impression thought
after each choice (below). `tools/date_sections.py` prints this table with
part/choice counts and each place's forcing address.

**The date's step machine.** DATE.EXN runs a date as a list of step
functions indexed by the step byte `0x800E738A` (`0x8004284C` advances it;
`0x8007C784` waits for a CD read, then advances). The runner `0x801449D4`
copies the list for the place — jump table `0x8015B0B0` on the place byte
`0x800CA2F8` (0–20) picks one of 21 lists; place 0's is at `0x8015BF50`,
the Theme Park's (104 steps) at `0x8015C738` — and replaces the placeholder
entry `0x80133DE8` with the place's setup for places 1–20. Place 0 keeps it,
so **section 7 is the neighborhood-park date**. The first steps load the
files: step 3 `SERIFU.BIN` (LBA 44870) to `0x80197000`, step 5 the girl's
`DATE_xx.BIN` (`DATE_FU` LBA 44329, 23 sectors) to `0x80198000` and fills the
section tables (`0x80141004` for Shiori), step 7 `TAKU3.BIN` (LBA 44969) to
`0x801A4000` (the impression tables at `0x801A427C`/`0x801A4D2C` are in
it). The parade setup `0x8013BBF0` sits at steps 61, 72 and 74 of the Theme
Park list, so **section 9 is a Theme Park sub-scene** (not forced yet).

**Kirameki Park in spring.** On 4/30 a Kirameki Park date reaches date step
13 right after the "let's go" exchange and plays EVENT_FU scene 4 instead
of the version's remark and choice. Setting its one-shot flag
`*(u8*)0x800E67EF` = 1 before then lets the section-21 part play (seen with
the pond version). **Shopping (section 14)** with the clothes option ran:
part 0 → reply → part 4 ("can I go look?") → pause (part 5) → part 6
(sorry + waiting choice) → reply → ending; which of the later parts
(carrying, cute item, necklace, junk shop) follow other first choices
wasn't traced.

**Arcade and Theme Park, seen 2026-10-08.** The Arcade's version byte picks
its part directly (version 0 → part 2, the "I don't come here much" choice;
1 → part 4, which games); the video/medal action choice (part 1) did not
come up with either. A forced Theme Park date on 4/30 went straight to
"where to next?" (part 9: roller coaster / Ghost House / Ferris wheel), one
ride with its remark, choice and reply, then the ending; the hero show
(parts 1–8) and the parade (section 9) did not come up, and their
conditions weren't traced.

**Neighborhood park (section 7, place 0).** Seen on screen: Shiori's
remark, an unlabelled narration line (`07`), a two-option action choice
(`08`: ask about her hobbies / find out places she likes), a centered
"・・・" pause (`07`), then the hobby note (`04`) as a thought with brackets
drawn by the game, then the ending. The part is 2·mood, set by
`0x8013A898` (a step of the park list): force with
`--at 0x8013A8B0 --reg v0=RANK`.

**Versions of a place.** Fifteen places pick a version byte `0x800CA2FC` in
their setup and the parts-per-version byte `0x8015B658`; `0x801324DC` then
adds version × parts-per-version to the part index `*(s16*)0x800CA148`. The
first read of `0x800CA2FC` in each setup is where `force_date.py --version N`
writes it (`date_sections.py` lists the addresses; checked for places 7, 1
and 13). Shopping, Theme Park, Cinema, Concert Hall and Shrine have no
version byte: they branch on choices.

**Shared sections: which part plays** (found statically, then forced on
screen with `tools/emu/break_set.py` rules; mood = `(r ≥ 2) + (r ≥ 3)` and
band = `(r ≥ 2) + (r ≥ 3) + (r ≥ 4)` for `r = 0x80051A68(girl) & 0x7F`,
lower is better):
- **23 meeting.** At date start `0x801447C4` sets the arrival byte
  `*(u8*)0x8015B654` = 1 (both on time), or 0 (she's late) when
  `*(u32*)0x800E7378 & 3 == 0` and the girl isn't 2; the flow at
  `0x8013F214` sets 2 (the player is late) when the meeting place doesn't
  match (`0x800E69A4`/`69A5`; not traced further). `0x80132564` computes the
  part into `*(s16*)0x8015BF04`: arrival 0 → 2·mood (player waits) then +1
  (her apology); arrival 1 → 6 + mood; arrival 2 → 9 + mood. If the s16 at
  `0x800E6396` (probably the player's Looks) is below 30 (35 for girl 7),
  `0x8013F544` uses part 12 (silence) then 13 (she runs off, the player goes
  home) and the date ends. Forced: arrival 2 / mood 1 → part 10, arrival 0 /
  mood 2 → parts 4–5, `0x800E6396` = 10 → parts 12–13.
- **24 small talk.** `0x8013AF1C`, at the date's first step, by calendar
  day only: part 0 on 3/21 (3/20 in 96), part 1 on 7/23 (95), 7/28 (96) or
  7/27 (97), part 2 or 3 at random on 9/23 (9/22 in 96), part 4 on 12/23;
  other days have none (`0x8013B0D4`). Forced part 0 by jumping from
  `0x8013B0D4` to `0x8013B0E4` with `0x8015BF0C` = 0.
- **22 ending.** `0x8013B488`: part = 3·band + the date's result (s16 at
  `0x800CA234 + 2·*(u32*)0x80122CDC`, 0–2, from the choices) via
  `0x800CA158`; special cases set 10 (`0x800E69DC` ≠ 0), 11 (a repeat of the
  last place), 18/19 (girl 6). The value lives at `sp+0x3A` and is
  recomputed every frame up to `0x8013B6F8`. Parts 12–17 (thanks for the
  anthology the player gave her) come from `0x80140C84`: 12 + mood + 3 if
  year ≥ 96. Forced part 9 (rewriting `sp+0x3A` at every hit).
- **26 going home.** `0x8013B7B0`: part = band (0–3) in `0x8015BF14`.
  Forced band 3 and band 1.
- **25 hobby notes.** Shown after section 7's choice: part = the choice
  (`*(u32*)0x80122CDC` → `0x8015BF1C`), line = `rand % count` in
  `0x8015BF20` (`0x8013AA4C`–); part 4 (she likes a boy) needs the best
  rank and bit 5 of the girl's byte at `+0x1C8`. Seen after a park date
  (place 0) choosing "ask about her hobbies": a part-0 note.

**Code bytes** (per string, as in EVENT_FU): `00` player (『), `01` Shiori
(「), `02` Shiori's reply to the last choice, `03` player choice (a spoken
line), `04` narration, `06` thought, `07` sound or narration line, `08`
action choice (e.g. "praise her yukata / don't"). **`n` marks an empty
option**: in section 4 the player's compliment `0x2450` ends in `nn` and
Shiori's reply `0x2478` is "thanks{q}nn". Seen on screen at the Shrine:
choosing to praise shows the compliment (no trace of `nn`) and her thanks;
choosing not to skips both lines. The picker skips an option that starts
with `n` (`0x80081024`); the renderer drops `nn` as an invalid code. Every
girl's DATE file (and its SPEAKTST copy) has the same pair; no other script
uses `n`. `script.py` decodes it as `{n}` only as a run ending an option,
and the structure check keeps it there.

**Speaking a part: EXE `0x8007EF48(string, code, option, ...)`.** It
`strcpy`s the string to a stack buffer (`sp+0x7C`) and switches on the code
through `0x800B22A8` (20 cases). For a reply (`02`) the loop at
`0x80080F48`–`0x80081020` walks the copy, stepping 1 byte over control codes
(space, `m M A W O F Y p G P S`) and 2 bytes over anything else, and cuts it
at the option-th `q` (or NUL); an option whose first byte is `n` is skipped
(`0x80081024`). The chosen option is then drawn with the label and bracket
by the dialogue renderer `0x80081190`. **The script string itself is never
written**, so several pointers may share one copy of identical text
(`share_identical`, translation-guide). Pair-encoded English is 2 bytes per
pair, both ≥ `0xA0`, so the walk stays in step.

**Choices on screen.** A `03` string's options are shown in a full-width box
without a label, each wrapped in `『』` drawn by the game, **in a shuffled
order** (seen 3-1-2, 1-2-3, ...). The reply is the option *chosen*, not its
position. Option widths: Japanese uses up to 17 characters; the box is about
33 letters wide, so the 28-cell dialogue limit is safe. An option with an
odd letter count shows its pair padding as a space before `』`, so keep
options even.

**Museum (section 0) flow.** 19 parts: five exhibitions × (`01 00` going in,
`01 03` remark + choice, `02` reply), then variant 5 (part 15 going in, then
one of parts 16–18). Setup `0x80134C64` sets the exhibition byte
`0x800CA2FC`: year 97 (`0x800E62BE == 0x61`) months 9–11 → 2, year 97
months 3–5 → 3, year 95 months 9–11 → 4, otherwise 0 or 1 by bit 0 of
`0x800E645B + 0x38·girl`; 2–4 become 5 if that girl's per-exhibition seen
byte (`0x800E645C/D/E + 0x38·girl`) is set. `0x801324DC` adds
variant × parts-per-variant (byte `0x8015B658`, 3 here) to the part index
`*(s16*)0x800CA148`. Variant 5's line is part 16 + mood, added at `0x801392F0` (rank call just
before): affection 48 → `0x6A8`, 200 → `0x688`; forcing `v0 = 0` at
`0x801392F0` showed `0x660`. (`0x80132570` is the meeting's mood, not
this.) The talk runner is EXE `0x80082764`. The
tables `*(0x8015B520)` = `0x801A427C` and `*(0x8015B524)` = `0x801A4D2C`
(15 bytes per girl, loaded from another file) give each choice's
impression level, copied to `0x800CA21C`–`0x800CA230`.

**Impression thoughts** after each choice (the player's thought, in levels
from a great impression to a bad one) are not in `DATE_FU`: they are in the
shared `SERIFU/SERIFU.BIN` (§6l), with copies in `SPEAKTST/TEST_OT.BIN`.

### 6l. Shared date lines (`SERIFU/SERIFU.BIN`)

Found 2026-10-08 by dumping the file and statically tracing `DATE.EXN`,
then forced in DuckStation (testing.md, "SERIFU.BIN"). Translated in
`translation/date_shared.json`.

**File.** 4,096 bytes (2 sectors, LBA 44870), checksum trailer, loaded by
DATE step 3 to `0x80197000` for every girl's date (§6k). 48 strings, each
with exactly one pointer; 2,324 bytes of string space in 12 gaps. The rest
is section lists, code bytes and zeroed work areas (`0x300`–`0x44F`,
`0x79C`–`0x9B7`, `0xB14`–`0xBDB`, `0xEB8`–`0xFFB`: 24-byte records filled at
run time; the pointer runs at `0x420`, `0x94C`, `0xBBC`, `0xFC0` point into
them, not at text). Other `SERIFU` files load at the same address, so words
in other overlays that point into `0x80197xxx` belong to those files.

**Section table.** `DATE.EXN` holds three parallel 4-entry tables at
`0x8015BD90` (masters), `0x8015BDA0` (code-byte lists) and `0x8015BDB0`
(third pointers, into the work areas), the same layout as DATE_FU's (§6k):

| Sec | Strings (file) | Count | Codes | Content | Setup / selector |
|---:|---|---:|---|---|---|
| 0 | `0x0`–`0x260` | 12 | `06` | concert blurbs ("X is a ... band"), one per concert, in the order of the EXE concert-name table (`town_news.json`: KNM Symphony, Chisa Morita, Chage & Aska, WIZARD, Riko Kodama, XeXeX, KNM Symphony, Bees, SNACK, KNM Symphony, prf, Rinsu) | `0x8013BAD4`: line = byte `0x8015B688`, set by the Concert Hall setup `0x80136340` (by date); confirmed by forcing 0 and 11 |
| 1 | `0x454`–`0x6EC` | 18 | `00 06 08 03 07` | the player alone at the meeting place: she's late, "did I get the place wrong?", the choice of where to go, or she never comes | `0x8013EFA0` (below); part in s16 `0x8015BF3C` |
| 2 | `0x9B8`–`0xAA8` | 7 | `04` | impression thoughts after a choice, levels 0–4 (great → bad), then two "but my lie was exposed: I can't really swim / skate" lines | `0x8013B174`: line = s16 at `0x800CA22C + 2·choice` (the impression level copied from `TAKU3.BIN`, §6k); forcing all three to N there once shows level N (seen 0 and 1). The swim lie line followed the Pool boast option on screen; `0x8013B208` is a second caller, presumably the lie lines (not traced) |
| 3 | `0xBDC`–`0xE40` | 11 | `06` | movie blurbs, one per film, in the order of the EXE movie-name table (`town_news.json`: I'm Doing It, Forrest Gump, Summer Saw, Fungaa, Kanpanman, Sleep Fist II, Love Melody, Speed King, BANPO, The Mask, Love and Youth) | `0x8013B964`: line = byte `0x8015B684`, set by the Cinema setup `0x80135E7C` (by date); confirmed by forcing 3 and 6 |

Codes `04` and `06` are drawn as the player's thought with **both brackets
drawn by the game** (seen on screen in the English dates: `（…。）` around
strings that contain neither), so English gets no parentheses. An odd
letter count on the last line shows its pair padding as a space before the
game's `）` ("a bad impression. )", seen), so thoughts end on an even run. Each blurb
and impression section is a single part whose line is chosen by the value
above; all four go through the talk runner `0x80082764`, which copies the
string before cutting it (`share_identical` is safe, as in §6k).

**Section 1, the missed meeting** (`0x8013EFA0`, a step of every date).
Parts and codes:

| Part | Strings | Content |
|---:|---|---|
| 0 | `0x454` `00`, `0x474` `06`, `0x4A4` `08` | "{G} isn't here yet" / "late… did I get the place wrong?" / action choice: "it was here" or `{A}` |
| 1 | `0x4D4` `00` | "no, it was here; I'll wait" |
| 2 | `0x508` `00` | "let's go to `{A}`" |
| 3 | `0x520` `00`, `0x540` `06`, `0x570` `03` | as part 0 with three options: here, `{A}`, `{M}` |
| 4–6 | `0x5B0`, `0x5E4`, `0x5FC` `00` | wait here / go to `{A}` / go to `{M}` |
| 7 | `0x614` `06`, `0x630` `00` | "{G} never came" / "oh well, home" |
| 8 | `0x650` `00`, `0x670` `06`, `0x694` `07`, `0x6D0` `06`, `0x6EC` `00` | stood up: waiting, the centered "・・・" pause, she never came, home |

The function copies a 21 × 33-byte place-name table from `DATE.EXN`
`0x8015B9DC` (file offset `0x299DC`; index = place id 0–20 as in §6k:
近所の公園 … スキー場) to the stack (the `0x2D6`-byte loop at `0x8013EFB8`),
then:
- If the girl's rank (`0x80051A68(girl) & 0x7F`, read at `0x8013F008`) is
  4, part 8 plays (stood up) and the step skips ahead (`0x738A` += `0x24`).
- Otherwise it reads the meeting bytes: `0x800E69A4` = **where the player
  went**, `0x800E69A5` = **the agreed place**, `0x800E69A6`/`69A7` = the
  other places the player half-remembers (`0xFF` = none; the main loop asks
  "where were we meeting?" on the date day, `main_screen.json`). If the
  player is at the agreed place (and the arrival byte `0x8015B654` is 1),
  or `69A6` is `0xFF`, the normal meeting runs (`0x738A` += `0x11`).
- On a mismatch, `{A}` (`0x800CA25C`) gets `69A6`'s name and, when `69A7`
  isn't `0xFF`, `{M}` (`0x800CA280`) gets `69A7`'s and part 3 (three
  options) replaces part 0. A candidate equal to where the player stands is
  replaced by the agreed place, so the right answer is always offered.
  Names are `strcpy`'d from the table (stride 33, `0x8013F0C0`).

Forced on screen (2026-10-08, testing.md "SERIFU.BIN"; this corrects the
first, static reading, which had `69A4`/`69A5` swapped): staying ("it was
here") or a wrong place leads to part 1/4 or 2/5/6, then part 7 ("she never
came"). Back home **an answering-machine message** from the girl follows
("ひどい事するのね…"); it is in `EXEDIR/TEL.EXN` (§6m), not here. Being stood up (part 8) ends the same way.
Choosing the agreed place goes there and continues as the player-late
meeting (§6k arrival 2), and **the date then takes place at the agreed
place**, not the appointment's original one (a forced museum date became a
Kirameki Park walk).

**The place-name table is the only source of `{A}`/`{M}` here.** It's read
only by this function (the one reference to `0x8015B9DC`). Every slot is the
Japanese name followed by NULs up to 33 bytes, so the in-place budget
(original + NUL + padding to 4 bytes, AGENTS rule 5) is often below the
English: 海 allows 2 letters, 神社 4, 遊園地/図書館/動物園/プール 6. Fitting
"Beach" or "Theme Park" needs the whole 33-byte record (the bytes after each
name are NUL up to the next record, and `strcpy` stops at the first NUL):
`date_shared.json` writes them with `"slot": 33` (translation-guide). The same function family at `0x80149D04` copies a second
93 × 33-byte table at `0x8015D108`: birthday-present item names, a separate
job.

`{A}` and `{M}` are inserted by the renderer from those buffers; a
pair-encoded name keeps its pairs (§6e), and an odd-length name ends in its
padding space.

### 6m. Phone calls (`EXEDIR/TEL.EXN`)

Found 2026-10-08 by dumping the overlay, listing its code's string
references (`tools/code_strings.py`), and calling Shiori, Yoshio and Ijuin
in DuckStation. Translated in `translation/phone_calls.json`.

**File.** Overlay, 196,608 bytes at LBA 39434, base `0x80132000`, checksum
trailer. Opened from the main loop's phone icon (holiday screen; Down
×8 from the first icon). Its text sits in two areas that work differently:

- **Data area `0xE5F0`–`0x14F0C`** (470 strings): the call scripts. Strings
  are followed by lists of pointers to them, one list per exchange; a
  12-entry list is indexed by girl (Shiori, Mio, Yuina, Ayako, Saki, Yukari,
  Nozomi, Mira, Yuko, Megumi, Yumi, then Ijuin), an 11-entry list by girl
  without Ijuin, and 13-entry lists probably by mood or day. Between the
  lists are tables of 4-byte records (`xx 0x 00 yy`, e.g. `5a 00 00 02`),
  and some strings start right after such a record, without a NUL.
  `dump_dialogue.py` treats a byte below `0x40` (other than the `0x20` line
  break), or an aligned word ending `00 00 xx`, as a string start for this
  reason. Every one of these strings has a pointer and none is addressed by
  code, so the block is repacked like a SERIFU file; 8 strings have two
  pointers (shared answers).
- **Code area `0xC430`–`0xE4F4`** (219 strings): addressed directly by the
  code (`lui` + `addiu`), so they stay in their own slots (the patcher keeps
  code-referenced strings in place). They're printed one line at a time
  (`0x80051010(text, line, speaker)`; speaker `13` = the callee, `15` the
  player, `31` a thought, `47` a sound, `10` Yumi), a whole box at a time
  (`0x80050E8C`), or are **fragments the code concatenates** with
  `strcpy`/`strcat` (`0x800AE0F0`/`0x800AE100`) into a stack buffer:
  - the player's greeting to Yoshio: "もしもし、" + player name + "ですけど。";
    Yoshio's reply "おっ、" + name + "か。";
  - the invitation (`0x80136A80`–): month digits (EXE table `0x800B3288`,
    full-width) + 月 + day digits + 日 + "に、 " + place name (EXE table
    `0x800B342C`, already English via `outings.json`) + "へ 行かない？";
    the confirmation adds "の前で 待ち合わせということで。" and the
    player's "やったー。 " + date + "が、楽しみだぜ。 ";
  - Yoshio's girl info: name + "、" + name + "‥‥と。"; the request
    name + "の" + "ことについて"; the missed-date thoughts
    "しまった！！今日は、 " + name + "と デートの約束があったんだ。）" and
    "そうかっ！ " + name + "は、 怒って来なかったのか。）".

  In English the fragments are written as pieces of one sentence ("4／30, would
  ⏎Theme Park⏎work for you?"). 月 became "／" and 日 ", ".
- `0x80050DFC(text)` sets a custom speaker label: 留さん (Tome, the
  fireworks man), 部長 (the club captain), and Yoshio's label for his own
  lines. 自宅 ("Home") is a location banner.
- The Yoshio menu ("ask about the girls / date spots") is drawn by
  `0x80050D78`; the girl-info card labels (`0xE478`–`0xE4BC`) by
  `0x8004E788` at fixed x positions. The card's label column is narrow:
  "BWH." and "Notes" overlapped the colon the game draws, so they became
  "B W H" and "Memo". The card's values (sign, blood type, club, notes) come
  from `FUKUTEST/JOHO.NBN` and are still Japanese.
- `0xCED4` ("くそ、次こそ絶対 誘ってみせるぜ。）") has no reference
  anywhere: unused, translated anyway.

**The phone book** lists full names from the EXE table at `0x72C80`
(§6e). That table's first entry, 藤崎詩織 at `0x72C80`, wasn't in
`character_names.json` (the pointer table at `0x72D38` starts one entry
earlier than documented before); it's now "S. Fujisaki", and the full-name
pool is 184 of 184 bytes. Only a fresh boot shows EXE changes: a save state
keeps the EXE it was made with in RAM.

**Calls seen** (2026-10-08): Shiori answers, the player introduces himself
("Um...⏎This is {P}."), her greeting by mood, then the date picker ("Choose
a day / place for the date.", the date-spot book), the assembled
invitation, her answer, the confirmation and goodbye, "Click.", then the
player's thoughts. A missed date (§6l) is followed at home by the
answering-machine message (data area, one list per girl × 3 moods) and
the player's realization.

### 6n. Walking home from school (`SERIFU/GEKO.BIN`)

Found 2026-10-08 by tracing `GEKO.EXN` and the EXE's day handler, then
forced in DuckStation (`tools/emu/force_walk.py`, testing.md "Walking
home"). Translated in `translation/walk_home.json`.

**Trigger.** Day record type `0x44` (`44 GIRL 00 00`, the girl in byte 1)
in the event queue (§6j): the handler `0x80072030` enters state `0x59`
(GEKO.EXN) if the girl has been met (bit 1 of `0x800E6448 + 0x38·girl`),
unless the previous record was type `0x28`/`0x47` or `0x800E6375 & 0xF ==
3`. GEKO.EXN serves several states: `0x5A` (record type `0x46`) is a girl
asking the player out for Sunday, from `SERIFU/G_INVITE.BIN` (not this
file); `0x5D` (type `0x45`) the special events (§6j). The weekly picker
`0x80070850` writes the type-`0x46` records; who writes type `0x44` wasn't
traced. The walk's entry is `0x80132244`: substate `0x800E7389` 0 runs the
step list `0x80144C5C` (the walk), 1 the list `0x80144D40` (the talk on the
way).

**File.** 73,728 bytes at LBA 44744 (36 sectors), base `0x80197000`,
checksum trailer. 1,011 strings (492 distinct texts: the same lines recur
across girls), all reached from 12 sections. Three parallel 12-entry tables
in GEKO.EXN at `0x80144BA0` (masters), `0x80144BD0` (code-byte lists),
`0x80144C00` (third pointers), the EVENT_FU layout (§6j). The section isn't
the girl id: the switch at `0x801327AC` (jump table `0x80144724`) maps
girls 0–10 to sections **1, 5, 2, 3, 9, 6, 7, 4, 0, 8, 11** (Shiori, Mio,
Yuina, Ayako, Saki, Yukari, Nozomi, Mira, Yuko, Megumi, Yumi), and section
10 is the player's own thoughts (set up for every walk at `0x801326D4`).
`tools/geko_sections.py --strings [--girl S]` lists them.

**Parts** (each girl's section, ~40 parts; s16 part index at `0x80144C3C`,
read through `0x800CA134` like DATE's):

| Parts | Content |
|---|---|
| 0 | (section 10) "Phew, what a long day" thought |
| 1–5 | she waited for the player: invitation + action choice (`08`), accepted (2, 3 "{G} and I had a nice walk home"), turned down (4, 5 / section 10 regret thoughts) |
| 6–11 | the player spots her and calls out; `0C`+`0D` "Oh, {P}." + "Heading home?" share one box; his choice; she agrees (8) |
| 12–17 | same, but she has other plans (14) |
| 18–21 | she runs off ("‥‥‥‥‥。"), the player wonders if he hurt her |
| 22 | "And then..." (code `07`) |
| 23–38 | the talk on the way, one per topic: exams, culture festival (24–27 by club), sports day, school trip (29–30), New Year, her birthday, summer/winter/spring break, moving up to 2nd/3rd year, graduation |
| 39 | "We talked about things like that on our walk home" |
| 40–42 | Saki only: Koshien / National Stadium / future (club manager lines), Mira only: she parts at a corner (40–41) |

The opening is chosen by the girl's rank (`0x80051A68`, §6j) at
`0x801331A0`: base part 0 for rank 0/1, +6 for rank 2, +12 for rank 3,
+18 for rank 4 (or flag byte `0x80144C58`). The talk on the way only runs
when a topic is pending: byte `0x80144C50` (0 = none) is proposed from the
calendar by `0x80132A4C(topic)`; the talk's part is 22 + the topic id
(`0x80133F94`). Forced: ranks 0, 2, 3, 4 and topics 1 (exams) and 12
(winter break) by `force_walk.py --rank R --topic P`.

Code bytes as in EVENT_FU: `00` player, `01` girl, `03`/`08` choices, `06`
thought (the game draws both brackets), `07` narration, `0C`/`0D` two girl
strings in one box, `09` and some empty strings (`0x11CC8`–`0x11EB8`) are
placeholders. `{M}` in the culture-festival lines is the player's club.
Oddities: Mira's part-7 choice (`0x68F0`) separates its two options with a
line break instead of `{q}`; on screen it shows as two normal options like
the others (the choice box splits on line breaks too), so the English keeps
the line break. Shiori's lines use 詩織 instead of `{G}` in three places.

## 7. Graphics

### General
- Most graphics are **raw pixel data with separate palettes**, not TIM files.
- Uploads go through `0x8004435C(x, y, w, h, [sp+0x10] = source)` (x and w
  in halfwords). `TITLE.NBN` comes in 64×128-halfword blocks (16 KiB: 128 px
  at 8bpp, 256 px at 4bpp); `MAINROM.NBN` in **32×128-halfword chunks**
  (8 KiB, 64-byte rows). Palettes are uploaded as 256×1 (256-colour CLUTs).
  Log the uploads to learn a file's layout (testing.md, "Does this code ever
  run?", `--stack 6`).
- **Get the row width right before reading anything into the art.** Rendering
  64-byte rows as 128-byte rows interleaves two rows: every glyph looks half
  height and the sheet looks like two copies side by side.
- To tell 8bpp from 4bpp: render a region as 4bpp. If shapes show vertical
  1-pixel striping, it's really 8bpp.
- `BS/*.BS` and `*.STR` are MDEC-compressed stills and movies (different tooling,
  not yet handled).

### Sprite frames (`SLPM_86.053`)

Most UI sprites (the main-screen stat panel, calendar, ...) aren't drawn
from coordinates in code. Sprite objects (e.g. at 0x8011F2xx) hold a **frame
number**, and the renderer (`0x80047804`–) looks the frame up in a pointer
table at **`0x800C975C`** (190 entries, static data in the EXE, file offset
= address − 0x80040800). Found with a read watchpoint on an object's frame
field while the screen was showing.

Frame data: `s16 part count, x offset, y offset, 0`, then one 14-byte part
each: `s16 x, y, cell, attr, 0, w, h`. `cell` counts 8×8 tiles in a 128 px
wide strip: tile `c` is at x = (c % 16)·8, y = (c / 16)·8. For the main-screen
sheet the strip is `MAINROM.NBN` chunk 4 (rows 0–127) followed by chunk 9
(rows 128–255). `attr` selects texture page/CLUT (0x3100 for the calendar
characters and labels, 0x3080/0x308D/0x30Fx for frame art); not decoded
further.

Changing a part's `cell` is a 2-byte patch (`translation/main_screen.json`),
which is how cells shared by two meanings get separated.

| Frame | What |
|---|---|
| `0x3C` | vertical calendar: parts 3/4/5 = 年/月/日 suffixes (cells 44/14/42), part 6 = the `( )` around the weekday (cell 98), plus borders |
| `0x3D` | stat panel: parts 25/26/27 = the three 32×40 label columns (cells 268/348/428), parts 14–24 the dashes (cell 100) and borders |
| `0x44`–`0x4D` | digits 0–9 (8×16) |
| `0x52`–`0x58` | weekday Monday…Sunday (cells 14, 32, 34, 36, 38, 40, 42). Monday **shares** the 月 cell and Sunday the 日 cell with the calendar suffixes |

### `FUKUTEST/MAINROM.NBN` (108,544 bytes, no checksum trailer)

Main-screen and command-screen art: command icons, stat panel, calendar
characters, girl-info labels, town-news banners. Loaded at boot to
0x80180000 (53 sectors, before the title) and uploaded once, so a change
needs a reboot to show (a save state keeps the old VRAM). 4bpp, 13 chunks of
8 KiB = 128×128 px, **64 bytes per row**. Uploads (file offset → VRAM
halfword x, y): 0x00000 → (0x380,0x180), 0x04000 → (0x380,0x100),
0x06000 → (0x2C0,0x100), 0x08000 → (0x300,0x180), 0x0A000 → (0x3C0,0x180),
0x0C000 → (0x3E0,0x180), 0x0E000 → (0x340,0x100), 0x10000 → (0x2C0,0x180),
0x12000 → (0x340,0x180), 0x16000 → (0x3C0,0x100), 0x18000 → (0x300,0x100).

- **Chunk 4 (0x8000):** row 0: digits 0–9 (8 px each), ● × ▲ ?, 月 (x112);
  row 16: 火 水 木 金 土 日 年 (16 px cells, x 0–96); row 48: the `( )`
  weekday bracket cell (x16) and the stat dash (x32). Glyph fill index 9,
  drop shadow index 10 at (+1,+1).
- **Chunk 9 (0x12000):** x 96–127, rows 0–119: the stat labels, one 40-row
  block per panel column (体調 芸術 容姿 / 文系 運動 根性 / 理系 雑学 ストレス),
  a label every 14 rows. The dash sprite starts ~27 px into the label, so
  that's the usable width. x < 96: panel frame art.
- Chunk 0 is the command icons, chunk 1 girl-info labels (星座, B.W.H, 電話,
  血液型), chunks 2 and 7 town-news banners, chunk 11 date-spot art. Not
  translated yet.

`CALROM.NBN` (loaded at 0x801A0000 on the main screen) holds the Calendar
command's month pages, which are already in English (MON TUE …).

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

1. **Dialogue beyond the prologue** (§6e): confirm the SERIFU load addresses
   in the game, find which scene code drives each file (and any line-timed
   events like Rei's), and where the remaining name codes (`S O W A M p m F`)
   come from. The ordinary speaker-label source and `{Y}` are now mapped.
   Check `BUNKA/`, `SPEAKTST/`, `EVENT/`.
2. **Text renderer leftovers:** the sprite drawer that places cached glyphs (for
   a true variable-width font later). Dialogue does go through
   `add_text`/`layout_string` (§6e).
3. **Pointer tables:** systematically map them in the EXE and overlays, so strings
   can be relocated into free space instead of only fitting in place.
4. **Data-file LBA tables:** how non-overlay files (e.g. `TITLE.NBN`, `SERIFU/*`) are
   located (hard-coded constants like the overlays?). Needed before files can grow.
5. Where `GYOZI.EXN` and `O.BIN` are loaded from. `EVENT.EXN` looks like a
   stale build that is never loaded (§6j).
6. Which title-menu graphics remain: the logo (ときめきメモリアル) is Japanese art
   in the same file and hasn't been touched.
7. **More room for code.** The renderer hook (§6f) uses two unused EXE
   functions. Anything bigger (a variable-width font, relocation helpers)
   needs more: the dead-code scan in §6f lists further candidates, each to be
   checked the same way before use.
8. **The rest of the main loop** (§6g): what each command icon opens (study
   choices, outing places at 0x72B40–, club commands, phone list, the
   stat-result messages after a week), where the stat-name strings at
   0x72AD0 are used, and the `MAINROM.NBN` art not translated yet (girl-info
   labels, town-news banners, date-spot art). The command grid's hand
   doesn't respond predictably to the test driver's key holds (testing.md),
   so reaching each command needs a better input method first.
9. **Regular dates** (§6k): the other places' flows (step lists) and how to
   reach the Theme Park parade (section 9) without walking every ride.
   Resolved 2026-10-07: section 7 is place 0, the `n` marker, the museum's
   variant-5 selector, and DATE2.EXN, which loads `GROUP_D.BIN` (group
   dates; its table at `0x8013A384` holds `GROUP_D` offsets at base
   `0x80197000`), `G_BIRTH`/`P_BIRTH`/`KARADATA.BIN` to `0x801B0000` and
   `TARA_OBJ` files, and never reads `DATE_FU.BIN`.
