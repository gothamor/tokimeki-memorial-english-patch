# Tokimeki Memorial: Forever with You — English patcher

Patches the Japanese PS1 disc image (*PlayStation the Best*, SLPM-86053) with an
English translation. Pure Python 3.8+ standard library, so it runs as-is on
Windows, Linux and macOS.

## Usage

```bash
python -m tokipatch "path/to/Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best).cue"
```

The original files are never modified. The patched `.cue`/`.bin` set is written to a
new folder next to the input called `<input folder> [English]`.

Options: `-o/--output DIR`, `-t/--translation FILE.json` (repeatable; replaces
the default of every `translation/*.json`), `-f/--force` to overwrite an
existing output folder.

## What's translated so far

- **Title menu:** ゲームスタート / オプション → **GAME START / OPTIONS**, both
  highlighted and unselected ([translation/title_menu.json](translation/title_menu.json)).
- **Options page:** the item list (Text Speed, Icon Mode, Mouse, Menu Mode,
  Cursor Speed, Voice Mode, Extras, Exit Options) and the Menu Mode sub-screen
  (choices + descriptions) ([translation/options.json](translation/options.json)),
  drawn with the letter-pair font described below. The choices on the Text
  Speed, Icon Mode, Cursor Speed and Voice Mode sub-screens are pre-drawn
  graphics and still Japanese.
- **New game:** the album (save slot) screen's message box, the shared
  Yes/No button prompts, and the name-entry questions
  ([album.json](translation/album.json), [common.json](translation/common.json),
  [name_entry.json](translation/name_entry.json)). The buttons, panel labels
  and the kana grid are still Japanese.
- **Prologue dialogue:** the 43-line entrance-ceremony scene after name entry
  ([prologue.json](translation/prologue.json)), the first dialogue in the
  translation. The speaker labels are still Japanese.
- **Main game loop:** the weekly command screen's stat panel (Health, Art,
  Looks, Lit., Sport, Guts, Sci., Trivia, Stress), the calendar
  (`95 / 4 / 23 (Su)`), the player's thought prompts, and the in-game
  Save/Load messages ([main_screen.json](translation/main_screen.json)).
  The command icons are pictures; what they open is still Japanese.
- **Renderer hook:** the game's text renderer draws English two letters per
  character cell, composed on the fly from a narrow font, so any amount of
  English text fits the font ([tokipatch/renderer.py](tokipatch/renderer.py)).
- **Spacing fix:** English letter pairs are drawn evenly at the game's 14 px
  glyph advance, and the name-entry screen is patched from 16 px to 14 px
  ([code.json](translation/code.json)).
- *Not applied by default:* the in-game system settings screen
  ([translation/extra/system_settings.json](translation/extra/system_settings.json)),
  pending an on-screen check.

## Documentation

| | |
|---|---|
| [AGENTS.md](AGENTS.md) | **Start here when changing anything.** Rules that keep the output bootable, the checklist, and verification status |
| [docs/game-internals.md](docs/game-internals.md) | Disc, executable, overlays, loader, checksums, text, font and graphics formats, with addresses |
| [docs/translation-guide.md](docs/translation-guide.md) | Adding text and graphics patches |
| [docs/testing.md](docs/testing.md) | Verifying in an isolated, scriptable DuckStation, with GDB tracing and VRAM dumps |

## Layout

| Path | Purpose |
|---|---|
| `tokipatch/` | The patcher (stdlib only): sector I/O + EDC/ECC (`cd.py`), ISO 9660 (`iso9660.py`), game font + letter-pair encoder (`font.py`, `pairfont.py`), renderer hook + MIPS assembler (`renderer.py`, `mips.py`), full-width encoder (`text.py`), dialogue codec + pointer relocation (`script.py`), indexed PNG (`png.py`), patch engine + checksum fix (`patcher.py`) |
| `translation/*.json` | The translation: `strings`, `dialogue` and `images` entries |
| `translation/graphics/` | Replacement graphics (indexed PNGs using the game's palettes) |
| `translation/font/free_glyphs.txt` | Font glyphs the game never uses (research data; no longer used by the patcher) |
| `tools/` | Developer tools: disc extraction, text search, free-glyph finder, MIPS disassembly, graphics generation (`make_title_menu.py`, `make_main_screen.py`), renderer check |
| `tools/emu/` | Emulator test harness: isolated DuckStation, input driver with screen detection, GDB client, file-load tracer, read-watchpoint logger |

## Key findings in brief

- Text is uncompressed Shift-JIS. UI strings live in `SLPM_86.053` and the
  `CDROM/EXEDIR/*.EXN` overlays. Dialogue (`SERIFU/`, the prologue) is
  NUL-terminated strings with 1-byte name/line-break codes, reached through
  absolute pointers, so the patcher repacks it and rewrites the pointers.
- **Most files end with a 16-bit checksum.** The game re-verifies it after
  loading and silently retries forever on a mismatch. That was the white-screen
  hang. The patcher now recomputes it for every file it changes.
- Overlays are loaded by hard-coded LBA, so files can't move or grow yet.
- **The game can't draw ASCII.** Its own 12×12 font (in `SLPM_86.053`) only
  covers 2-byte Shift-JIS codes. English is drawn as *letter pairs*: a hook in
  the renderer turns each 2-byte code in a range Japanese never uses into a
  glyph holding two narrow letters, giving 1 byte and 7 px per letter.
- Menu graphics are raw 8bpp bitmaps with separate CLUTs (e.g. `FUKUTEST/TITLE.NBN`).

## Prior work
- [XEUPIU](https://github.com/vgarciasc/xeupiu): screen-reading overlay
  translator for this PS1 version (no disc patching). Its CSV of translations
  could feed this project.
- [tetracorp's "Exploring Tokimeki Memorial"](https://tetracorp.github.io/tokimeki-memorial/):
  reverse-engineering notes on this game.
- [romhacking.net thread](https://www.romhacking.net/forum/index.php?topic=34599.0);
  a finished Super Famicom translation; an in-progress Saturn translation of
  *Forever with You*.

## Roadmap
1. ~~Compose letter-pair glyphs on the fly in the renderer.~~ Done
   (game-internals §6f).
2. Translate `SERIFU/` dialogue file by file, verifying each scene, and find
   where speaker labels come from.
3. Find the LBA tables for data files, then support relocating or growing files.
4. Text renderer: variable-width English. The renderer hook (game-internals §6f)
   is the place for it; it needs more code space.
5. Remaining graphics (logo, menus, MDEC stills).
6. Distribution: PyInstaller builds per OS, or ship xdelta/PPF patches.
