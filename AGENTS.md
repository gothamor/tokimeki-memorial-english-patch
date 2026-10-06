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
7. **The renderer can't draw ASCII.** Codes below 0x8140 are dropped, and
   level-2 kanji (≥ 0x9873) aren't in the font. English goes through the
   `pairs` encoding (default; `tokipatch/font.py`), which redraws unused kanji
   glyphs as two-letter glyphs, or `fullwidth` as a fallback. Never write raw
   ASCII bytes into game text.
8. **Only redraw font glyphs from `translation/font/free_glyphs.txt`.** Every
   other glyph is (or may be) used by Japanese text that isn't translated
   yet. If a "free" glyph shows up inside Japanese text on screen, remove it
   from the list (and note it in docs). Don't hand-pick glyphs.
9. **Don't commit game data.** No disc images, extracted files, RAM dumps or
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
- [ ] For graphics: checked **every state** on screen (each menu item
      highlighted and unselected). Highlighted versions are often separate art
      elsewhere in the file.
- [ ] Played a little past the changed screen, so the next file load is
      exercised too.
- [ ] New findings written into `docs/`. New translation entries follow
      [docs/translation-guide.md](docs/translation-guide.md).

## Verification status of current patches

| Patch | Status |
|---|---|
| `translation/title_menu.json` (GAME START / OPTIONS) | Verified in DuckStation: both items render in English in both the unselected and highlighted states (screenshots of GAME START highlighted and of OPTIONS highlighted). The user has played the patched build past the menu and confirmed that selecting OPTIONS opens the Options page. |
| `translation/options.json` (Options page: 8 items, Menu Mode sub-screen choices + descriptions, Extras items) | Verified in DuckStation: item list, and all four Menu Mode choices with their descriptions. Extras items can't be seen until unlocked. Text Speed / Icon Mode / Cursor Speed / Voice Mode choices are **graphics** and still Japanese (game-internals §6c). Mouse is unreachable without a mouse. Not yet checked: that no still-Japanese screen uses a redrawn glyph. |
| `translation/album.json` (album screen message box, 88 strings) | Verified in DuckStation: no-save prompt with Yes/No icons aligned, "Which album", system-file explanation, "Make a system file?", "Album and system file are being made". Other prompts (copy/erase/restart, memory-card errors) are not seen yet. |
| `translation/common.json` (shared Yes/No ○/× button lines) | Verified on the "Make a system file?" prompt; icons line up. |
| `translation/name_entry.json` (name/nickname/birthday questions) | "What's your family name?" verified, evenly spaced. Name and nickname prompts and the birthday/blood-type questions not seen yet. |
| `translation/code.json` (glyph advance 16 → 14 on name entry) | Verified: banner evenly spaced, typed name characters still align with their underscores, kana grid still tidy. |
| `translation/extra/album_panel_exe.json` (21 panel-style labels in `SLPM_86.053`) | Doesn't affect the album screen (its panel is graphics). Probably the in-game save/load screen; unverified. |
| `translation/extra/system_settings.json` (114 strings: in-game system settings screen in `SLPM_86.053`) | Builds; **not verified on screen** (needs an in-progress game). Not applied by default. Verify, then move to `translation/`. |
| `translation/extra/name_entry.json` (name-entry prompts) | Builds, and its file now passes the in-game checksum (the overlay loads). The prompts haven't been seen on screen yet. Not applied by default. |

Update this table when you verify something.

## Working in this environment (Windows dev box)

- Use `tools/emu/` for testing, never the user's own DuckStation install or
  settings. **The harness must never write outside the repo** (memory cards,
  save states, screenshots). Settings inherited from the user can carry
  absolute paths to their real folders; `setup_duckstation.py` overrides the
  memory card folder, and any new path-like setting must be overridden too. Never send keystrokes to whatever window has focus; the driver
  posts messages straight to the isolated emulator's window.
- **Controls are Japanese-style: ○ (Circle) confirms, × (Cross) goes back.**
  In the harness that's `C` to confirm, `X` to go back.
- Run `tools/emu/drive.ps1` with **Windows PowerShell 5.1** (`powershell.exe`),
  not pwsh 7. Its `Add-Type` code relies on assemblies that pwsh 7 doesn't load
  by default.
