# Tokimeki Memorial: Forever with You — PS1 Version English patcher

<img width="1950" height="738" alt="image-1791685033388" src="https://github.com/user-attachments/assets/149fcef0-dcd5-4e17-841a-39a48dde3a7f" />

Patches the Japanese PS1 disc image (*PlayStation the Best*, SLPM-86053) with an
English translation. Pure Python 3.8+ standard library, so it runs as-is on
Windows, Linux and macOS.

The patcher and translation was done entirely with Opus 5.5.

## Which disc image you need

The patcher works with exactly one release:

- *Tokimeki Memorial: forever with you*, **PlayStation the Best** reprint,
  serial **SLPM-86053** (Japan).
- As a **redump-style BIN/CUE** with two tracks: a `.cue` file plus
  `(Track 1).bin` (the data) and `(Track 2).bin` (audio). The usual file
  names are:

  ```text
  Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best).cue
  Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best) (Track 1).bin
  Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best) (Track 2).bin
  ```

Other releases (the original 1995 edition, other reprints, other
consoles) won't work. Other image formats (`.chd`, `.pbp`, `.iso`) aren't
supported: the patcher has only been tested with the two-track BIN/CUE.

Every change is checked against the original Japanese text and graphics
before anything is written. If your image is a different version, the
patcher stops with an error and writes nothing.

## How to patch the game

You only need Python and this project. Nothing else gets installed.

1. **Install Python 3.8 or newer.**
   - Windows: download it from [python.org](https://www.python.org/downloads/)
     and, in the installer, tick **"Add python.exe to PATH"**.
   - macOS: download it from [python.org](https://www.python.org/downloads/).
   - Linux: it's almost certainly already installed (`python3 --version`).
2. **Download this project.** On the GitHub page, click **Code → Download
   ZIP** and unzip it anywhere, or `git clone` it.
3. **Open a terminal in the project folder** (the one holding this README
   and the `tokipatch` folder).
   - Windows: open the folder in Explorer, click the address bar, type
     `cmd` and press Enter.
   - macOS: right-click the folder in Finder → **New Terminal at Folder**.
   - Linux: right-click in the folder → **Open in Terminal**, or `cd` to it.
4. **Run the patcher on your `.cue` file:**

   ```bash
   python -m tokipatch "path/to/Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best).cue"
   ```

   Tip: type `python -m tokipatch ` (with a space at the end), then drag the
   `.cue` file onto the terminal window to paste its path, and press Enter.
   On macOS and Linux use `python3` instead of `python`. On Windows, if
   `python` isn't found, try `py`.
5. **Wait for `Done`.** It takes a few seconds plus the time to copy the
   disc image. The patcher checks every change against your disc, copies
   the game, writes the patched files, and ends with the folder it wrote
   to. Your original files are never changed. The English copy goes in a
   new folder next to the original, with ` [English]` added to its name:

   ```text
   Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best) [English]/
   ```

6. **Play.** Open the `.cue` file in that new folder with your PS1 emulator
   (DuckStation was used for all the testing; real hardware hasn't been
   tried).

Options, if you need them:

| Option | What it does |
|---|---|
| `-o FOLDER` | Write the patched game to `FOLDER` instead of the default |
| `-f` | Overwrite the output folder if it already exists (for re-patching after an update) |
| `-v` | List every string written, not just a summary per file |
| `-t FILE.json` | Apply only the given translation file(s); repeatable. Mainly for development |

**Controls are Japanese-style:** ○ (Circle) confirms and × (Cross) goes back.

## What's still in Japanese

All of the game's dialogue, menus and on-screen text are translated,
including the pre-drawn menu graphics most players will see. What's left:

**On purpose**

- **The title logo, the copyright line and the staff roll.**
- **Song lyrics:** the lyrics of the song at the end of the game are left
  as in the original.
- **The kana grid on the name-entry screen.** It's the input method: you
  still type your name in Japanese characters, as in the original, so
  your name shows in Japanese inside the English text.
- **Voice acting.** The girls' confession lines at the ending are voice
  only in the original, with no text on screen, so there's nothing to
  translate there.
- A few dialogue boxes that are nothing but punctuation (a pause like
  ……) are kept as they are.

**Not done yet (pictures, not text)**

- The pink 名前: / あだ名: (Name / Nickname) captions on the name-entry
  screen. Where they're stored hasn't been found yet.
- The **Mouse** sub-screen of the title Options and the pre-drawn
  **Extras** entries (there's no room for English letters in that sheet).
- The ひだり / みぎ (left / right) speech bubbles in the sports day's
  three-legged race.
- The Town News magazine's masthead and issue labels (the headlines are
  translated).
- Full-screen still pictures and movies (`BS/*.BS`, `*.STR`), which are
  stored in a video format the patcher doesn't handle yet.

**Translated but not yet seen on screen**

Every file is checked automatically, but a few scenes are hard to reach and
haven't been looked at in an emulator yet: karaoke, the street thugs, the
club practice matches, the parts of sports day after a minigame (the
folk dance and the extra scenes for Mio and Nozomi), the opening of a
new game, the room hints, the exam results board and the Town News
headline banners. Many rare branches elsewhere (moods, other years, less
common choices) are also only checked statically. The full record is the
status table in [AGENTS.md](AGENTS.md). If something looks wrong in one of
these, please report it with a screenshot.

**Known cosmetic issues**

- "Literature" runs slightly past the green box in the club list, and the
  soccer captain's Club Day notice has a wide gap before "miss it."
- A name with an odd number of letters right before 』 in a menu option is
  followed by an extra space.
- English is drawn at a fixed width (two letters per Japanese character
  cell), so spacing is even rather than proportional.

Two oddities come from the original game, not the patch: Megumi's culture
festival tour can return to the title screen after the club menu, and
some birthday gift lists for Megumi and Yumi in 1995 show an empty box.

## Helping improve the translation

The whole game is translated, but it was a lot of text and plenty of it
can read better. Corrections, better wording and consistent character
voices are all welcome, and so are bug reports from playing.

### Reporting a problem

Open an issue with a screenshot, what was happening (the date in the game,
which girl, which menu) and, if you can, what the line should say. Text
that runs off the box, overlaps an icon, or shows a stray space or a
double space is worth reporting too. If the game hangs or goes back to
the title, say so: check the same spot in the unpatched game if you can,
since a few of those come from the original (see above).

### Where the English lives

Everything is in [`translation/`](translation/), one JSON file per scene or
screen. The names say what they cover: `shiori_dates.json`,
`christmas.json`, `phone_calls.json`, `main_screen.json` and so on. Each
entry pairs the exact Japanese (`original`) with the English (`text`):

```json
{"offset": "0x1b1d0",
 "original": "俺の名前は{P}。\nここ、私立きらめき高校の\n新入生だ。",
 "text": "My name's {P}.\nI'm a freshman at\nKirameki High."}
```

**Only change `text`.** `file`, `offset`, `base` and `original` tell the
patcher where the line is and prove it's the right one. To find a line,
search the `translation/` folder for the English you saw on screen.

### Steps for a change

1. **Extract the disc once** (the checks need the original files; the
   output is game data, so it stays out of the repo):

   ```bash
   python tools/extract.py "path/to/game.cue" extracted
   ```

2. **Edit `text`** in the JSON file.
3. **Check the file.** It reports the line count, width, spacing and
   space problems described below, with the offset of each:

   ```bash
   python tools/draft.py --check translation/christmas.json
   ```

   Fix everything until it says `0 problem(s)`. `warn:` lines are worth
   fixing when it's easy.
4. **Build a test copy** in a scratch folder:

   ```bash
   python -m tokipatch "path/to/game.cue" -o "path/to/scratch" --force
   ```

   The patcher refuses to build if anything doesn't fit or doesn't match,
   and says what's wrong.
5. **Look at it in an emulator** and play a little past the changed screen.
   A clean build doesn't prove the screen looks right.
   [docs/testing.md](docs/testing.md) describes the scripted test setup
   used here, including tools that jump straight to a date, an event or
   a holiday instead of playing up to it.
6. **Send a pull request** saying what you changed and what you checked on
   screen. Screenshots go in the pull request, not in the repo.

If you change a line that appears in more than one place (common lines are
shared between girls and scenes), change every copy the same way: search
for the old English. Identical lines are stored once on disc, and the
drafting tool reuses an English line only when every copy of it agrees.

### Rules for the English

The game was never built for English, and the text has to fit around
that. The patcher and `draft.py --check` enforce most of these.

- **Keep the line structure.** Every `\n` is a line break on screen. Keep
  the same number of lines, the same choices and the same name codes on
  each line as the Japanese. Some scenes wait for a specific line before
  they continue; with fewer lines the game hangs.
- **28 letters per line at most,** and 26 on the second and third lines
  where the "next page" hand sits. The box shows three lines; longer
  strings scroll.
- **Space is tight.** English has to fit in the bytes the Japanese used,
  about one letter per byte, so it can't be much longer than a literal
  translation. Dialogue in a file shares one pool of space; menu labels
  each get only their own slot. When something doesn't fit, shorten it.
- **Allowed characters:** `A–Z a–z 0–9`, space and
  `. , ! ? ' " - : ; ( ) / & + %`. No accents, curly quotes, `…` (use
  `...`), `~` or dashes other than `-`. A new character has to be drawn
  in [`tokipatch/pairfont.py`](tokipatch/pairfont.py) first.
- **Count letters in pairs.** The game draws English two letters per
  Japanese character cell, so an odd number of letters gets padded with a
  space. That shows up in three places:
  - before a name code: `"My name is {P}"` shows "is  Name"; prefer
    `"My name's {P}"`;
  - at the end of a choice option, as a space before the game's `』`;
  - at the end of a thought, as a space before the game's `)`.
- **Don't type the opening bracket or the speaker name.** The game draws
  the speaker label and the 「, 『 or ( itself. End a line with `)` only
  if the Japanese ends with `）`.
- **Codes** in curly braces are inserted by the game; keep them where they
  are:

  | Code | What it inserts |
  |---|---|
  | `{F}` | the player's full name |
  | `{P}` | the player's name, in most scenes with the game's 君 (or さん) after it |
  | `{p}` | the player's short name |
  | `{m}` | what Yoshio calls the player |
  | `{G}` | the girl's name (up to 10 letters, e.g. "Shiori") |
  | `{Y}` | Yoshio |
  | `{S}` `{O}` `{W}` `{A}` `{M}` | a word chosen by the game: a place, a present, a club, a destination |
  | `{q}` | separates the options of a choice; keep the count and order |
  | `{n}` | an empty option the game skips; leave it exactly where it is |
  | `{>Capt}`, `{-???}` | a speaker label inside the line; at most 4 (`>`, `<`), 6 (`-`) or 2 (`+`) letters |

  The player's name is typed with the Japanese kana grid, so `{F}`, `{P}`,
  `{p}` and `{m}` always show in Japanese.
- **Some menu lines leave blank cells for icons** (the ○/× buttons, a slot
  number). Keep those spaces where they are; moving them puts the icon on
  top of a word.
- **Some messages are pieces glued together** by the game, with a name or
  a date in between. Translate them as one sentence and check the joined
  result on screen.
- **Lines that are only punctuation** (a pause like `……`) stay Japanese.
- **Keep each character's voice** (Yuko's slang, for example). Read a
  girl's other files before changing her lines.
- **Don't commit Japanese script** beyond the lines being patched, and no
  disc images, extracted files or screenshots.

Graphics (menus, signs, cards) are indexed PNGs in
[`translation/graphics/`](translation/graphics/) that must keep the game's
palette. The pictures listed under "Not done yet" above are open for
anyone who wants them.

The details behind all of this are in
[docs/translation-guide.md](docs/translation-guide.md), and the rules that
keep the patched game bootable are in [AGENTS.md](AGENTS.md).

## For developers

| | |
|---|---|
| [AGENTS.md](AGENTS.md) | **Start here when changing anything.** Rules that keep the output bootable, the checklist, and verification status |
| [docs/game-internals.md](docs/game-internals.md) | Disc, executable, overlays, loader, checksums, text, font and graphics formats, with addresses |
| [docs/translation-guide.md](docs/translation-guide.md) | Adding text and graphics patches |
| [docs/testing.md](docs/testing.md) | Verifying in an isolated, scriptable DuckStation, with GDB tracing and VRAM dumps |

| Path | Purpose |
|---|---|
| `tokipatch/` | The patcher (stdlib only): sector I/O + EDC/ECC (`cd.py`), ISO 9660 (`iso9660.py`), game font + letter-pair encoder (`font.py`, `pairfont.py`), renderer hook + MIPS assembler (`renderer.py`, `mips.py`), full-width encoder (`text.py`), dialogue codec + pointer relocation (`script.py`), indexed PNG (`png.py`), patch engine + checksum fix (`patcher.py`) |
| `translation/*.json` | The translation: `strings`, `dialogue`, `images` and `bytes` entries, one file per scene or screen |
| `translation/graphics/` | Replacement graphics (indexed PNGs using the game's palettes) |
| `tools/` | Developer tools: disc extraction, text search, drafting and checking translations, graphics generation, translation progress (`progress.py`) |
| `tools/emu/` | Emulator test harness: isolated DuckStation, input driver, GDB client, file-load tracer and scene forcers |
| `tests/` | Unit tests on synthetic data (`python -m unittest discover tests`) |

How it works, in brief:

- Text is uncompressed Shift-JIS. Dialogue is repacked and its pointers
  rewritten. Files can't move or grow, because the game loads them by
  hard-coded sector number.
- Most files end with a 16-bit checksum that the game re-verifies after
  loading, retrying forever on a mismatch. The patcher recomputes it for
  every file it changes.
- The game can't draw ASCII. A small hook in its text renderer draws
  English as letter pairs: each 2-byte code in a range Japanese never uses
  becomes a glyph holding two narrow letters.

## Prior work
- [XEUPIU](https://github.com/vgarciasc/xeupiu): screen-reading overlay
  translator for this PS1 version (no disc patching).
- [tetracorp's "Exploring Tokimeki Memorial"](https://tetracorp.github.io/tokimeki-memorial/):
  reverse-engineering notes on this game.
- [romhacking.net thread](https://www.romhacking.net/forum/index.php?topic=34599.0);
  a finished Super Famicom translation; an in-progress Saturn translation of
  *Forever with You*.
