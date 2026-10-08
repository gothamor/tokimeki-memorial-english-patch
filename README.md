# Tokimeki Memorial: Forever with You — English patcher

Patches the Japanese PS1 disc image (*PlayStation the Best*, SLPM-86053) with an
English translation. Pure Python 3.8+ standard library, so it runs as-is on
Windows, Linux and macOS.

<!-- progress:start -->
**Translated: 15%**

```text
Whole game             ███░░░░░░░░░░░░░░░░░    15%
Dialogue               ███░░░░░░░░░░░░░░░░░    13%
Menus and other text   ██████░░░░░░░░░░░░░░    31%
```

<sub>88,823 of 587,342 Japanese characters of in-game text, measured by <code>tools/progress.py</code>. Pre-drawn graphics text isn't counted.</sub>
<!-- progress:end -->

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
  translation. Character-name tables and speaker labels are translated by
  [character_names.json](translation/character_names.json).
- **Shiori's special events (all 8):** the morning walk to school, the
  umbrella in the rain, the shared-birthday phone call, the four date events
  (neighborhood park, Kirameki Park, Ferris wheel, pool) and the walk home
  after the Christmas party ([shiori_events.json](translation/shiori_events.json)).
  They're rare in normal play.
- **Shiori's regular dates (all):** meeting her, every place's
  conversations, choices and replies, the end of the date and the way home
  ([shiori_dates.json](translation/shiori_dates.json)).
- **Yuko's regular dates (all):** the same for Yuko Asahina, in her slangy
  voice ([yuko_dates.json](translation/yuko_dates.json)).
- **Yuko's special events (all 6):** the staff room, and her date events
  at the arcade, the theme park parade, the concert, the skating rink and
  the library ([yuko_events.json](translation/yuko_events.json)).
- **Your birthday:** the girl who brings you a present, or the lonely
  version ([birthday.json](translation/birthday.json)).
- **The girls' birthdays:** choosing and giving her a present, her
  reaction, and calling her out on a holiday
  ([girl_birthdays.json](translation/girl_birthdays.json)).
- **The Christmas party:** getting past Ijuin's doorman, his speeches,
  chatting with the girls (or meeting them for the first time), the present
  exchange, and the lonely evening at home if you're turned away
  ([christmas.json](translation/christmas.json)).
- **Walking home from school** with any of the girls: her invitation or
  yours, her answer, and the chat on the way about upcoming events
  ([walk_home.json](translation/walk_home.json)).
- **First meetings** with nine of the girls (Yuko, Yuina, Ayako, Mira,
  Mio, Yukari, Nozomi, Saki, Yumi), including the location banners
  ([meetings.json](translation/meetings.json)).
- **Joining a club:** the girl already in it welcomes you
  ([club_welcome.json](translation/club_welcome.json)).
- **Girls asking you out** for Sunday: the invitation for every place,
  your answer and the meeting place
  ([invitations.json](translation/invitations.json)).
- **Lines shared by every girl's dates:** the impression thought after each
  choice, the concert and movie blurbs, and the "did I get the meeting place
  wrong?" monologue with its place names
  ([date_shared.json](translation/date_shared.json)).
- **Phone calls:** calling the girls to ask them out (greetings, yes/no,
  the date and place picker), calling Yoshio for advice and girl info,
  Ijuin, the answering-machine messages after a missed date, and the other
  calls in `TEL.EXN` ([phone_calls.json](translation/phone_calls.json)).
  The girl info card's values are still Japanese.
- **Main game loop:** the weekly command screen's stat panel (Health, Art,
  Looks, Lit., Sport, Guts, Sci., Trivia, Stress), the calendar
  (`95 / 4 / 23 (Su)`), the player's thought prompts, and the in-game
  Save/Load messages ([main_screen.json](translation/main_screen.json)).
  Club names, recurring notices, outing names and town-news text also have
  translations. Coverage and on-screen verification vary; see the status table
  in [AGENTS.md](AGENTS.md). The command icons themselves are pictures.
- **Renderer hook:** the game's text renderer draws English two letters per
  character cell, composed on the fly from a narrow font, so any amount of
  English text fits the font ([tokipatch/renderer.py](tokipatch/renderer.py)).
- **Spacing fix:** English letter pairs are drawn evenly at the game's 14 px
  glyph advance, and the name-entry screen is patched from 16 px to 14 px
  ([code.json](translation/code.json)).
- **In-game Save/Load info panel and System Settings:** included in normal
  builds ([album_panel_exe.json](translation/album_panel_exe.json),
  [system_settings.json](translation/system_settings.json)).
  Both have passed static review and a combined test build. The user has now
  verified populated Load panels and reports all in-game settings submenus
  translated. Remaining branch coverage is recorded in
  [docs/testing.md](docs/testing.md). Tested new translation files are promoted
  into normal builds; only work still awaiting testing stays in `extra/`.

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
| `tools/` | Developer tools: disc extraction, text search, free-glyph finder, MIPS disassembly, graphics generation (`make_title_menu.py`, `make_main_screen.py`), renderer check, translation progress (`progress.py`), code-string lister (`code_strings.py`), walk-home section lister (`geko_sections.py`) |
| `tests/` | Unit tests on synthetic data (`python -m unittest discover tests`) |
| `tools/emu/` | Emulator test harness: isolated DuckStation, input driver with screen detection, GDB client, file-load tracer, read-watchpoint logger, girl-event watcher and event/date/Christmas forcers |

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
2. Translate `SERIFU/` dialogue file by file, verifying each scene, and check
   longer translated speaker labels across more dialogue paths.
3. Find the LBA tables for data files, then support relocating or growing files.
4. Text renderer: variable-width English. The renderer hook (game-internals §6f)
   is the place for it; it needs more code space.
5. Remaining graphics (logo, menus, MDEC stills).
6. Distribution: PyInstaller builds per OS, or ship xdelta/PPF patches.
