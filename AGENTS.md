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
   more. `apply_string` enforces this. Don't loosen it. The one exception is
   a string in a fixed-size record whose size is proven from the reading
   code and documented (`"slot"`, translation-guide): it may fill its
   record, and the patcher checks the record's tail is all NUL.
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
| `translation/character_names.json` (speaker labels, full/short name tables, special Shiori/Yoshio paths) | Builds successfully. Shiori's full name ("S. Fujisaki", added with the phone work) seen in the phone book after a fresh boot. The user booted and played the patched game and confirmed that character names appear translated. Individual label paths and the longest names have not all been checked at the dialogue-box edge. |
| `translation/clubs.json` + club strings in `main_events.json` | Verified by the user's follow-up screenshots and play test: Literature appears and fits its column, and joining Soccer reaches the corrected captain's Club Day notice with no overlapping text. Literature extends slightly beyond the green selector; the notice has a wide gap before “miss it.”. **Both cosmetic issues are accepted by the user for now; leave them unchanged.** Earlier screenshots verify the other ten English club names, Cancel and the join result. All 12 club-table pointers validate; the build also boots, loads a card save and plays onward. |
| Remaining `translation/main_events.json`, `outings.json`, `town_news.json` main-loop EXE text | Build successfully. Review screenshots verify the first News issue's introduction, Closed movie listing, KNM Symphony concert listing and event announcement. Other consumers/issues remain unverified; the stat-name table is not the sprite-based main stat panel. |
| `translation/album_panel_exe.json` (21 panel-style labels in `SLPM_86.053`) | Included in normal builds after user verification in `.emu/review_settings/`: populated Load slots 1 and 2, number/colon headings, dates 95/4/9 and 95/4/16, Name/Nickname/Club/Cleared labels and values, clubs None/Soccer. Screenshots show readable separators and no apparent overlap. Save-mode copy, empty/error/System entries and longest club values remain unverified. |
| `translation/system_settings.json` (114 strings: in-game system settings screen in `SLPM_86.053`) | Included in normal builds after the user visually verified the settings screen and all submenus as translated. Screenshots specifically show the main title/list/help (Icon Mode highlighted) and Text Speed submenu with Slow/Normal/Fast and its help; Normal fits. Individual confirmations, alternate Cursor Speed label-set coverage and hardware/unlock-dependent paths were not separately reported. |

| `translation/shiori_events.json` (all of `EVENT_FU.BIN`: Shiori's 8 special events, 157 strings) | Verified in DuckStation on real boots with the 95/4/23 card save, every event **forced** (they naturally need mid-game affection, seasons, matching birthdays or a Christmas party): GEKO scenes via `force_event.py`, the four date events via `force_date.py` (a real date with Shiori, then a jump to the event at its date step), the after-Christmas-party walk via `force_christmas.py`. Every box seen in English except a few first lines of 4-/5-line strings that scroll away before a screenshot and one transition line (also not captured unpatched); shared `0C`/`0D` boxes, scrolling, sound lines, `{G}`/`{p}`/`{P}`, single brackets on thoughts, embedded `( )` thoughts. Each compared with the unpatched game forced the same way; dates end normally and play continues. Not tested: natural trigger paths, the ride choice before the Ferris-wheel scene, `{P}` with other names. |
| `translation/shiori_dates.json` (all of `DATE_FU.BIN`: Shiori's regular dates, 27 sections, 471 strings; the 5 pure-punctuation pause lines stay Japanese) | Museum verified in depth in DuckStation with forced dates (`force_date.py --set-at` choosing the exhibition) from a same-build Sunday state: all five exhibitions' going-in, remark, shuffled three-way choice list and every reply, plus variant 5's three "seen before" lines; compared with the unpatched museum date. The other sections were translated in batches, each promoted after a spot check per the user's limited-testing policy (testing.md, batches 1–7): meeting parts 4–6, 9, 12–13; small talk 0 and 4; ending 6, 9, 15; going home bands 0, 1–2, 3; a park-0 date with both options and two hobby notes; Kirameki Park's pond version with all options; one Shopping path; Bowling, Beach, Karaoke (all options), Zoo, Aquarium, Planetarium, Stadium, two Arcade versions; the Cinema announcement, a Concert Hall choice and reply, the Shrine's yukata choice with both options (`{n}`); the Theme Park's three rides with choice and reply. Every forced date ended normally and the week continued. Nine note/thought endings were later made even (no space before the game's `)`), which repacks DATE_FU; a park date was replayed on that build. **Checked only statically:** other versions, branches and moods; the Arcade's video/medal action choice; the Shrine after the goldfish minigame (needs real play); the Theme Park hero show, later ride rounds and the parade (not reached); natural triggers. The impression thoughts are in `date_shared.json`. |
| `translation/date_shared.json` (all of `SERIFU.BIN`, the lines shared by every girl's dates, 47 strings; plus the 21 `DATE.EXN` place names via `"slot": 33`) | Verified in DuckStation on forced dates: impression levels 0–4 (3 and 4 before their final wording) and the swim lie line; concert blurbs 0 and 11 and movie blurbs 3 and 6 via their force rules; being stood up; a two- and a three-option wrong-place meeting with every option, the inserted names and the late arrival that follows. **Checked only statically:** the other blurbs, the skate lie line, the other place names, natural triggers, other girls' dates. The answering-machine message after a missed date is in `TEL.EXN` (`phone_calls.json`). |
| `translation/phone_calls.json` (all of `TEL.EXN`, the phone: 461 repacked script lines + 219 in-place strings the code addresses directly) | Verified in DuckStation from a Saturday state: calling Shiori through the date picker, place book, the assembled invitation, her yes and the goodbye; calling Yoshio (both menu items, the girl list, Shiori's info card with its labels, compared with the unpatched card); calling Ijuin; a missed date's answering-machine message. **Checked only statically:** other girls' calls, declined dates, cold/stood-up calls, Yoshio's warnings, Yumi, Miharu's wrong numbers, anthology thanks, Tome, the club captain, the ratings screen. Info card values (`JOHO.NBN`) are still Japanese. |
| `translation/walk_home.json` (all of `SERIFU/GEKO.BIN`, walking home from school with each girl: 996 strings, 492 distinct texts) | Verified in DuckStation with `tools/emu/force_walk.py` from the Sunday state: Shiori waiting and asking (rank 0) plus the exams talk; Yuko when the player calls out (rank 2) plus the four-line winter-break talk; Mira rank 2 (her line-break choice shows as two options) and rank 3 (other plans); Megumi rank 4 (runs off). **Checked only statically:** Mio, Yuina, Ayako, Saki, Yukari, Nozomi and Yumi's sections, declined invitations and the regret thoughts, the other topics, girl-specific extras, natural triggers. |
| `translation/invitations.json` (all of `SERIFU/G_INVITE.BIN`, a girl asking the player out for Sunday: 351 strings; plus 19 GEKO.EXN meeting-place names via `"slot": 33`) | Verified in DuckStation with `force_event.py --type 0x46`: Shiori's invitation accepted (through "Meet at {M}") and refused (her reply, the regret thought); Yuko's invitation accepted with the English meeting place. **Checked only statically:** the other nine girls, other places and meeting-place names, the unused section 7, natural triggers. |
| `translation/yuko_dates.json` (all of `DATE_AS.BIN`: Yuko's regular dates, 27 sections, 456 strings; the 4 pure-punctuation pause lines stay Japanese) | Spot-checked in DuckStation per batch on forced Yuko dates (`date_run.ps1 -Girl 8`) from the Sunday state: meeting parts 1, 4–5, 6, 9 with their thoughts; small talk 0, 1, 4; ending parts 3 and 12 and the player's replies; going home bands 0, 1–2, 3; museum exhibition 0, Kirameki Park's cherry-blossom version, Bowling, Beach v1, Stadium v1, Arcade v1, the Concert Hall and Cinema choices, each with every option; Shopping's first choice and accessories list; a park-0 date with both actions and two notes; the Zoo, Planetarium and Aquarium; the Shrine up to the goldfish minigame; the Theme Park's three first rides; Library version 1, which reads one part past her list and shows an empty choice exactly as the unpatched file does. Every forced date ended normally. **Checked only statically:** other versions, branches and moods, the Shrine after the minigames, the hero show, later ride rounds and the parade, the Arcade's medal branch, natural triggers. Her date events (`EVENT_AS.BIN`, e.g. the spring Arcade one) are still Japanese. |
| `translation/meetings.json` (all of `SERIFU/G_APPEAR.BIN`, the first meetings with nine girls: 409 strings, the 7 pure-punctuation pauses stay; plus 28 in-place `SHOUGATU.EXN` words: Yuko's "Girl" label and the location banners) | Verified in DuckStation with forced type-0x48 meetings (`meet_run.ps1`, emulator hidden): Yuko's first collision and her whole introduction, Yuina's lab scene, Ayako painting outside, Mira, Mio's drama-club scene (the in-string `{>Capt}` labels), Yukari's tennis ball, Nozomi's morning run, Saki's baseball recruiting, Yumi's whole scene (`{-???}` labels); banners Hall, Local Park, Drama. **Checked only statically:** the other variants of each girl (club-dependent branches, Yuko's 2nd/3rd collision), the other banners, natural triggers. Yumi's `{P}` keeps the game's さん, as other scenes keep 君. |
| `translation/club_welcome.json` (all of `SERIFU/NYUBU.BIN`: a girl welcoming the player to her club, 91 strings; the 2 pure-punctuation pauses stay) | Verified in DuckStation with `force_club_welcome.py` (main state 0x60, hidden emulator): every section; Shiori's baseball, soccer and general parts (forced with a club set: with none her scene hangs, unpatched too), Yuina, Ayako (Art Club and Band), Mio, Yukari, Nozomi, Saki (soccer), section 7 (the default for other girls). **Checked only statically:** the other parts and the natural trigger. |

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
- When the user says they're working on the same machine, run the
  emulator **hidden** (`-Hidden`, or `TOKI_EMU_HIDDEN=1`; testing.md
  "Running the emulator hidden") so their input can't disturb a test.
- Run `tools/emu/drive.ps1` with **Windows PowerShell 5.1** (`powershell.exe`),
  not pwsh 7. Its `Add-Type` code relies on assemblies that pwsh 7 doesn't load
  by default.
