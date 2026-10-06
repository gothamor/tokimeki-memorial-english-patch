# AGENTS.md — working on the Tokimeki Memorial English patcher

Read this first. This is the contract for anyone (human or AI agent) changing
the patcher or the translation. The detailed knowledge lives in `docs/`:

| Doc | What's in it |
|---|---|
| [docs/game-internals.md](docs/game-internals.md) | Everything known about the disc, executable, overlays, loader, checksums, text and graphics formats, with addresses |
| [docs/translation-guide.md](docs/translation-guide.md) | How to add text and graphics patches, and their constraints |
| [docs/testing.md](docs/testing.md) | How to verify a patch in an emulator: isolated DuckStation, input driver, GDB tracing, VRAM dumps |

**When you learn something new about the game, write it into `docs/` in the same
change.** Record addresses, offsets, and how you found them. That's the only
way the next person doesn't have to redo the work.

## What the project is
- `python -m tokipatch <game.cue>` copies the disc image to a new folder and
  applies every `translation/*.json` to the copy.
- Target disc: *Tokimeki Memorial: forever with you*, PlayStation the Best,
  SLPM-86053 (Japan), redump-style 2-track BIN/CUE (MODE2/2352 + audio).
- Pure Python 3.8+ standard library, so it runs on Windows, Linux and macOS.
  Developer tools under `tools/` may use extra packages (e.g. capstone via
  `uv run --with capstone`), but `tokipatch/` must not.

## Rules that keep the output bootable

These are hard-won. Every one of them has broken the game, or would.

1. **Never modify the user's original files.** All writes go to the output
   copy. `__main__.py` validates everything against the original *before* copying.
2. **Fix the file checksum after every change.** Most data files end with
   `[sum16 BE][12 10]`. On a mismatch the game reloads the file forever, which
   looks like a hang on a white or black screen. `patcher.plan()` does this
   automatically via `has_checksum`/`fix_checksum`. Never bypass `plan()` to
   write data, and never let a patch touch a file's last 4 bytes.
3. **Regenerate EDC/ECC for every rewritten sector.** `cd.Track.write_file_bytes`
   does it. Only Mode 2 Form 1 sectors may be patched; it refuses others.
4. **Don't change file sizes or LBAs.** The game loads files by hard-coded sector
   numbers (see game-internals), not through ISO 9660. Growing or moving a file
   needs relocation support that doesn't exist yet. Design it, document it, and
   test it before relying on it.
5. **In-place strings must fit.** A replacement may use the original's bytes,
   its NUL terminator, and NUL padding up to the next 4-byte boundary. Nothing
   more. `apply_string` enforces this. Don't loosen it.
6. **Every patch must prove it's patching the right thing.** String patches carry
   the exact Japanese `original`. Image patches carry `original_crc32` of the
   pixels they replace. Keep these checks.
7. **The game font is full-width only (as far as we know).** `text.encode` turns
   ASCII into full-width JIS X 0208. Don't emit half-width ASCII or cp932
   extension characters unless the renderer has been changed to support them
   and that change is documented and tested.
8. **Don't commit game data.** No disc images, extracted files, RAM dumps or
   screenshots (`.gitignore` covers `extracted/` and `.emu/`). Don't copy long
   stretches of the Japanese script (or the song lyrics stored in
   `NAME_ENT.EXN`) into docs or code. Short identifiers and the strings being
   patched are fine.

## Checklist for any change that affects the output

- [ ] `python -m tokipatch <cue> -o <scratch dir> --force` succeeds, and every
      touched file reports `checksum updated` (if it has a trailer).
- [ ] Only the expected sectors changed. Diff against the original track or
      read the patcher log; unexpected sectors mean a bug.
- [ ] **Booted in an emulator and checked on screen** ([docs/testing.md](docs/testing.md)).
      A clean patch run doesn't prove the game works; the first build passed every
      static check and still hung.
- [ ] Compared against the **unpatched** game at the same point, so you know a
      problem is caused by the patch and not by the emulator or BIOS setup.
- [ ] Played a little past the changed screen, so the next file load is
      exercised too.
- [ ] New findings written into `docs/`. New translation entries follow
      [docs/translation-guide.md](docs/translation-guide.md).

## Verification status of current patches

| Patch | Status |
|---|---|
| `translation/title_menu.json` (GAME START / OPTIONS) | Verified in DuckStation: renders correctly, selecting GAME START proceeds into the opening. The highlighted OPTIONS state and the Options screen itself are **not yet verified**. |
| `translation/extra/name_entry.json` (name-entry prompts) | Builds, and its file now passes the in-game checksum (the overlay loads). The prompts haven't been seen on screen yet. Not applied by default. |

Update this table when you verify something.

## Working in this environment (Windows dev box)

- Use `tools/emu/` for testing, never the user's own DuckStation install or
  settings. Never send keystrokes to whatever window has focus; the driver
  posts messages straight to the isolated emulator's window.
- Run `tools/emu/drive.ps1` with **Windows PowerShell 5.1** (`powershell.exe`),
  not pwsh 7. Its `Add-Type` code relies on assemblies that pwsh 7 doesn't load
  by default.
