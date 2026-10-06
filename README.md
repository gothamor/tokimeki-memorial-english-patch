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

- **Title menu:** ゲームスタート / オプション → **GAME START / OPTIONS**
  ([translation/title_menu.json](translation/title_menu.json)).
- *Not applied by default:* the name-entry questions
  ([translation/extra/name_entry.json](translation/extra/name_entry.json)).
  Add them with `-t translation/title_menu.json -t translation/extra/name_entry.json`.

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
| `tokipatch/` | The patcher (stdlib only): sector I/O + EDC/ECC (`cd.py`), ISO 9660 (`iso9660.py`), text encoder (`text.py`), indexed PNG (`png.py`), patch engine + checksum fix (`patcher.py`) |
| `translation/*.json` | The translation: `strings` and `images` entries |
| `translation/graphics/` | Replacement graphics (indexed PNGs using the game's palettes) |
| `tools/` | Developer tools: disc extraction, text search, MIPS disassembly, graphics generation |
| `tools/emu/` | Emulator test harness (isolated DuckStation, input driver, GDB client, load tracer) |

## Key findings in brief

- Text is uncompressed Shift-JIS. UI strings live in `SLPM_86.053` and the
  `CDROM/EXEDIR/*.EXN` overlays, and dialogue lives in script files whose
  bytecode isn't decoded yet.
- **Most files end with a 16-bit checksum.** The game re-verifies it after
  loading and silently retries forever on a mismatch. That was the white-screen
  hang. The patcher now recomputes it for every file it changes.
- Overlays are loaded by hard-coded LBA, so files can't move or grow yet.
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
1. Decode the dialogue script bytecode (`SERIFU`, `EVENT`, prologue).
2. Map pointer tables, so strings can be relocated rather than only fit in place.
3. Find the LBA tables for data files, then support relocating or growing files.
4. Text renderer: half-width or variable-width font for readable English.
5. Remaining graphics (logo, menus, MDEC stills).
6. Distribution: PyInstaller builds per OS, or ship xdelta/PPF patches.
