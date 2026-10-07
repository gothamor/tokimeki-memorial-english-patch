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
   `pairs` encoding (default; `tokipatch/font.py`): ASCII with the top bit
   set, drawn two letters at a time by the renderer hook
   (`tokipatch/renderer.py`, game-internals §6f), or `fullwidth` as a
   fallback. Never write raw ASCII bytes into game text, and don't use codes
   0xA0A0–0xFEFE for anything else.
8. **New code goes only where nothing runs.** The renderer hook lives in two
   EXE functions shown to be unused statically *and* with execution
   breakpoints over a long play session (game-internals §6f). Any new code or
   data region needs the same evidence, documented, and a CRC check of the
   original bytes before writing. Don't redraw font glyphs: Japanese text
   that isn't translated yet still uses them.
9. **Don't commit game data.** No disc images, extracted files, RAM dumps or
   screenshots (`.gitignore` covers `extracted/` and `.emu/`). Don't copy long
   stretches of the Japanese script (or the song lyrics stored in
   `NAME_ENT.EXN`) into docs or code. Short identifiers and the strings being
   patched are fine. `tools/dump_dialogue.py` output is a copy of the script:
   keep it in `extracted/`, and commit only lines you've translated.
10. **Dialogue keeps the original's line structure.** Same number of display
    lines, same choices, same name codes per line. Scene code waits for
    specific lines (game-internals §6e); with fewer lines the game hangs on that
    line. `script.structure` enforces this. Don't loosen it.

## Checklist for any change that affects the output

- [ ] `python -m unittest discover tests` passes.
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

## Translation promotion workflow

The user requests that **tested new translation files always be included in
normal builds**. Keep drafts in `translation/extra/` only while they await
testing. After the user or agent completes the relevant on-screen checks,
move the tested JSON into `translation/` as part of the same follow-up; do not
leave it opt-in after reporting success. Preserve explicit notes about unseen
error, hardware-dependent and other conditional branches rather than claiming
exhaustive coverage. If a known failure blocks promotion, explain it clearly.

After promotion, build using the normal command **without `-t`** to verify
default discovery, update paths/status in the docs, and check the output
against the tested candidate when promotion should not change game bytes.

## Verification status of current patches

| Patch | Status |
|---|---|
| `translation/title_menu.json` (GAME START / OPTIONS) | Verified in DuckStation: both items render in English in both the unselected and highlighted states (screenshots of GAME START highlighted and of OPTIONS highlighted). The user has played the patched build past the menu and confirmed that selecting OPTIONS opens the Options page. |
| `translation/options.json` (Options page: 8 items, Menu Mode sub-screen choices + descriptions, Extras items) | Verified in DuckStation: item list, and all four Menu Mode choices with their descriptions. Extras items can't be seen until unlocked. Text Speed / Icon Mode / Cursor Speed / Voice Mode choices are **graphics** and still Japanese (game-internals §6c). Mouse is unreachable without a mouse. |
| `translation/album.json` (album screen message box, 88 strings) | Verified in DuckStation: no-save prompt with Yes/No icons aligned, "Which album", system-file explanation, "Make a system file?", "Album and system file are being made". Other prompts (copy/erase/restart, memory-card errors) are not seen yet. |
| `translation/common.json` (shared Yes/No ○/× button lines) | Verified on the "Make a system file?" prompt; icons line up. |
| `translation/name_entry.json` (name/nickname/birthday questions) | All 7 verified in DuckStation: family name, "Your name?", "And your nickname?", "Birthday and blood type?", "Shiori's birthday & blood type?", and both "Is this OK?". |
| `translation/prologue.json` (43 dialogue lines: entrance-ceremony scene after name entry) | Verified in DuckStation: real boot from title through Rei's introduction; the rest of the scene with the same bytes poked into a save state, through to the first in-game screen. Box width, scrolling of 4–5 line strings, `{P}` name insertion and thought lines all checked. Speaker labels are supplied separately by `character_names.json`. |
| Renderer hook (`tokipatch/renderer.py`, installed whenever English `pairs` text is used) | Verified in DuckStation: Options page and Menu Mode descriptions, album prompts (○/× icons aligned), all name-entry questions, the whole prologue, then the first in-game screen, where untranslated Japanese still renders correctly. The two reused EXE functions had 0 hits from execution breakpoints over 15 min of the unpatched game (boot to in-game weeks and a SERIFU event). |
| `translation/code.json` (glyph advance 16 → 14 on name entry) | Verified: banner evenly spaced, typed name characters still align with their underscores, kana grid still tidy. |
| `translation/main_screen.json` (main game loop: stat panel + calendar graphics in `MAINROM.NBN`, thought prompts, club commands, in-game Save/Load text) | Verified in DuckStation (real boot, loading a Sunday-night save): stat labels, calendar `95 / 4 / 23 (Su)`, weekdays We / Sa / Su seen (Sa in blue, Su in pink), weekday prompt "(What'll I do this week?)" and holiday prompt "(What should I do today?)". Save/Load screen checked by the user: "Save"/"Load", "Choose Save or Load.", "Choose a file to save to.", "OK to overwrite?" with the Yes/No icons aligned. **Not seen yet:** the other prompt variants (exams, camp, festival, trip, illness, date, club, meeting place, phone), club commands, the remaining memory-card messages. Weekdays Mo/Tu/Th/Fr not seen. |
| `translation/character_names.json` (speaker labels, full/short name tables, special Shiori/Yoshio paths) | Builds successfully. The user booted and played the patched game and confirmed that character names appear translated. Individual label paths and the longest names have not all been checked at the dialogue-box edge. |
| `translation/clubs.json` + club strings in `main_events.json` | Verified by the user's follow-up screenshots and play test: Literature appears and fits its column, and joining Soccer reaches the corrected captain's Club Day notice with no overlapping text. Literature extends slightly beyond the green selector; the notice has a wide gap before “miss it.”. **Both cosmetic issues are accepted by the user for now; leave them unchanged.** Earlier screenshots verify the other ten English club names, Cancel and the join result. All 12 club-table pointers validate; the build also boots, loads a card save and plays onward. |
| Remaining `translation/main_events.json`, `outings.json`, `town_news.json` main-loop EXE text | Build successfully. Review screenshots verify the first News issue's introduction, Closed movie listing, KNM Symphony concert listing and event announcement. Other consumers/issues remain unverified; the stat-name table is not the sprite-based main stat panel. |
| `translation/album_panel_exe.json` (21 panel-style labels in `SLPM_86.053`) | Included in normal builds after user verification in `.emu/review_settings/`: populated Load slots 1 and 2, number/colon headings, dates 95/4/9 and 95/4/16, Name/Nickname/Club/Cleared labels and values, clubs None/Soccer. Screenshots show readable separators and no apparent overlap. Save-mode copy, empty/error/System entries and longest club values remain unverified. |
| `translation/system_settings.json` (114 strings: in-game system settings screen in `SLPM_86.053`) | Included in normal builds after the user visually verified the settings screen and all submenus as translated. Screenshots specifically show the main title/list/help (Icon Mode highlighted) and Text Speed submenu with Slow/Normal/Fast and its help; Normal fits. Individual confirmations, alternate Cursor Speed label-set coverage and hardware/unlock-dependent paths were not separately reported. |

| `translation/shiori_events.json` (all of `EVENT_FU.BIN`: Shiori's 8 special events, 157 strings) | Verified in DuckStation on real boots with the 95/4/23 card save, every event **forced** (they naturally need mid-game affection, seasons, matching birthdays or a Christmas party): GEKO scenes via `force_event.py`, the four date events via `force_date.py` (a real date with Shiori, then a jump to the event at its date step), the after-Christmas-party walk via `force_christmas.py`. Every box seen in English except a few first lines of 4-/5-line strings that scroll away before a screenshot and one transition line (also not captured unpatched); shared `0C`/`0D` boxes, scrolling, sound lines, `{G}`/`{p}`/`{P}`, single brackets on thoughts, embedded `( )` thoughts. Each compared with the unpatched game forced the same way; dates end normally and play continues. Not tested: natural trigger paths, the ride choice before the Ferris-wheel scene, `{P}` with other names. |

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
