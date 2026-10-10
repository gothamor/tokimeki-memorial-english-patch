# Next steps: translate the rest of the game

This is the only active task: a long-running, file-by-file translation of
everything that's still Japanese. Work through the queue below in order.
For each item: investigate (only if the queue says so), translate, check,
build, test on screen with the emulator hidden, promote, document, commit,
then move to the next item. Keep the Status table current. Technical
findings go in `docs/`, not here.

**Where we are (2026-10-10):** 35% of the game's text (206,711 of 587,342
characters, `tools/progress.py`). About 380,000 characters are left:

| Area | Characters left | Queue |
|---|---:|---|
| Culture festival `CDROM/BUNKA/` (46 files) | 217,000 | phase B |
| Other girls' dates `SERIFU/DATE_*` (9 files) | 99,700 | phase A |
| Overlay words (in-place UI strings in `EXEDIR/*.EXN`, EXE) | 15,000 | phases A–F |
| Ending, epilogue `SERIFU/ENDING`, `EPILOG` | 14,400 | phase C |
| Club contests `MASTER/*.BIN`, `SHIAI/SIAI_TX` | 13,200 | phase E |
| Other `SERIFU/` (group dates, sickbed visits, …) | 10,100 | phase D |
| Sports day, festival shows, info card, minigames | 6,000 | phase F |
| Not text (graphics/animation data the scan counts) | ~5,000 | skip |

Everything already done is listed in the AGENTS.md status table and the
README.

## The per-file loop

Every tool below exists and is documented in its docstring. Paths in
`extracted/` and `.emu/` are local only (game data, rule 9).

1. **Survey.** `python tools/script_survey.py CDROM/<DIR>/<FILE>.BIN`: who
   loads it, its base, which section tables reach its strings and how
   many (`all tables together cover N/M`). The whole remaining map is in
   game-internals §6aa; read the file's paragraph there first. If the
   tables don't cover every string, find the rest before translating
   (dates: `tools/date_sections.py`; §6k lists the known gaps).
2. **Draft.** `python tools/draft.py CDROM/<DIR>/<FILE>.BIN -o
   translation/extra/<name>.json [--name <Girl>]`. It fills every line the
   translation memory already knows (identical Japanese translated before,
   always the same way), keeps punctuation-only pauses Japanese, writes
   the remaining distinct strings to `extracted/todo/<FILE>.txt` (with
   speaker code and offsets) and checks the draft.
3. **Translate.** Write `extracted/tables/<FILE>.json` (`{"Japanese":
   "English", "@0x1c": "per-offset English"}`) from the todo list, in the
   character's established voice (see her other files). Re-run step 2
   with `--table extracted/tables/<FILE>.json` until `draft.py` reports
   **0 problems** and the block packs. Fix what it flags:
   - width over 28 cells; `warn:` lines 2–3 over 26 may touch the page
     icon (fix when it's easy, look on screen otherwise);
   - odd letter runs before a name code (double space);
   - text after an odd-length `{G}` (`--name`): end the line on the name;
   - odd endings of thoughts (code 06) and menu options (03/08);
   - "doesn't pack": shorten the longest lines.
   The in-place overlay words go in the same file's `strings`:
   `python tools/exn_words.py EXEDIR/<X>.EXN --todo [--json ...]` lists
   them with their room in letters.
4. **Build.** `python tools/candidate.py translation/extra/<name>.json`:
   builds the normal reference and the candidate into `.emu/review_dates`,
   lists the changed files (only the draft's files may change) and their
   checksums.
5. **Test** with the emulator hidden (`-Hidden`; the user works on the same
   machine), from the Sunday state
   `.emu/savestates_backup/dates_sunday_0423_candidate.sav`. Use the
   forcer listed for the file below, batch the runs in a shell script that
   appends to a log (pattern: `.emu/ev_runs.sh`), then read the sheets
   with `python tools/emu/review_sheets.py <prefix>...` (30 boxes per
   image). Depth: every section/scene the forcer can reach once, plus the
   menus; when a file has many near-identical variants (festival, dates),
   one run per variant family is enough (the user's limited-testing policy,
   testing.md "Yuko's dates"). Fix what the screen shows, rebuild, re-run
   the affected run. Anything odd: compare with the unpatched game forced
   the same way before blaming the patch.
6. **Promote.** Move the JSON to `translation/`, give it a description,
   run `python tools/candidate.py` with no drafts: it must say
   byte-identical (the normal build equals the tested candidate). Run
   `python -m unittest discover tests`.
7. **Document.** AGENTS.md status row (what was seen, what wasn't), README
   feature line and `python tools/progress.py --update-readme`,
   game-internals (new findings, the file's paragraph in §6aa or a new
   §6), testing.md (how it was forced, run prefixes, what wasn't reached).
   Mark the item done in the Status table here.
8. **Commit** (one commit per item or batch, message ending with the
   Co-Authored-By line), then start the next item. The user asked for
   this loop to run on its own; still stop and ask before anything
   destructive or outside the repo.

Rules that keep this safe: AGENTS.md (never write outside the repo, never
send keys to the focused window, never modify the original disc, don't
commit game data, keep line structure). Don't reproduce song lyrics
(`TARA_OBJ/KARAKASI.BIN`, the NAME_ENT songs): leave them Japanese.

## Phase A: the other girls' dates (`SERIFU/DATE_*.BIN`)

Same layout as Shiori's and Yuko's dates (§6k: 27 sections from DATE.EXN's
per-girl tables). Forcer: `date_run.ps1 -Girl G -Place P [-Version V]
[-Extra ...] -Hidden` and `force_date.py` (`--version`, `--set-at`,
`--event`). Shared date lines (`SERIFU.BIN`) are done; the translation
memory carries Yuko's and Shiori's identical lines.

Order (§6k: Mio, Yuina, Ayako, Megumi have a section pointer outside
their file, and Mio, Yuina, Nozomi, Mira, Megumi, Yumi have 4–9 strings
the dumper misses: run `tools/date_sections.py` for the girl and include
those offsets):

| # | File | Girl id | Chars | Note |
|---|---|---:|---:|---|
| A1 | DATE_KY (Nozomi) | 6 | 9,800 | missed strings |
| A2 | DATE_MI (Megumi) | 9 | 10,200 | out-of-file pointer, missed strings |
| A3 | DATE_HI (Yuina) | 2 | 10,300 | out-of-file pointer, missed strings |
| A4 | DATE_SA (Yumi) | 10 | 11,100 | missed strings |
| A5 | DATE_NI (Saki) | 4 | 11,200 | |
| A6 | DATE_KA (Ayako) | 3 | 11,500 | out-of-file pointer |
| A7 | DATE_KO (Yukari) | 5 | 11,500 | |
| A8 | DATE_KG (Mira) | 7 | 11,900 | missed strings |
| A9 | DATE_KI (Mio) | 1 | 12,200 | out-of-file pointer, missed strings |
| A10 | DATE.EXN place banners (76 words, `0x28B20`–`0x28E84`) | | 330 | shown on every date |

Testing per girl: meeting (on time and late), each place's first version
and its choice, a going-home band, one ending part; her event scenes are
done (`*_events.json`).

## Phase B: the culture festival (`CDROM/BUNKA/`)

Mapped in §6aa: base 0x801E8000, tables built by code in BUNKASAI.EXN
(state 0x70) and BUNKAKEN.EXN (0x71). Forcer: `force_event.py 0 0 --type
0x24 --first` plays the whole festival day (probe pb1: BUN_PC's
narration, "invite a girl?", the girl menu, the club menu, the girl's
exhibit, the end). Drive the menus with `xmas_run.ps1 -KeyList`.

**B0, investigation first:** find where BUNKASAI/BUNKAKEN pick each file
(the girl menu's result, the club menu, the player's club, year,
affection) and write `tools/emu/force_festival.py` with `--girl`/`--club`
options at the menu picks (pattern: force_trip.py's `--girl`), so every
file can be reached from the Sunday state. Record the
file↔girl↔club↔stage mapping in a new game-internals section.

Then one girl at a time (each a commit), sharing lines through the
translation memory; the player's file first, since every run shows it:

| # | Files | Chars |
|---|---|---:|
| B1 | BUN_PC (player), BUNKASAI/BUNKAKEN words (menus, exhibit names, girl names), TWINBEE, URANAI | 2,600 |
| B2 | Shiori: FU_S6, FU_S6B, FU_S6O, FU_S6W, FU_S6S, FU_S6I, BUN_FU | 42,000 |
| B3 | Ayako: KT_S61–63, KT_S6B, KT_S6O, KT_S6I | 39,000 |
| B4 | Mio: KS_S61–62, KS_S6B, KS_S6O, KS_S6I | 27,000 |
| B5 | Yuina: HI_S6, HI_S6B, HI_S6O, HI_S6I | 21,000 |
| B6 | Yuko: AS_S6, AS_S6W, AS_S6S | 18,000 |
| B7 | Mira: KG_S6, KG_S6W, KG_S6S | 17,000 |
| B8 | Yumi: SA_S6, SA_S6W, SA_S6S | 16,000 |
| B9 | Yukari: KO_S6, KO_S6W, KO_S6S | 15,000 |
| B10 | Nozomi: KY_S6, KY_S6W, KY_S6S | 13,500 |
| B11 | Saki: NI_S6, NI_S6W, NI_S6S | 10,000 |
| B12 | Megumi: MI_S6, MI_S6W, MI_S6S | 8,000 |
| B13 | Stage shows: BUNKA_SD.EXN words (207), `BUNKASD/*.BIN` (state 0x80) | 3,400 |

The festival's gift table (BUNKAKEN/BUNKASAI, the 33-byte layout of §6s)
goes with B1 or the first file that inserts `{A}`.

## Phase C: the ending

ENDING.BIN (confessions, 17 sections, ENDING.EXN table `0x8013C280`),
EPILOG.BIN (15 sections, `0x8013CAC0`) and ENDING.EXN's 25 words; state
0x63. `force_state.py 0x63` alone plays the ending where nobody waits
(run `fs1`: graduation lines with Yoshio, the epilogue narration, then a
song's lyrics on a black screen: **lyrics stay Japanese**, rule 9; find
which file holds them and leave those strings out). **Investigation
first:** how ENDING picks the girl and the outcome,
and the epilogue's stage; then `force_state.py 0x63 --stage N --girl G`
(or a `force_ending.py`) for each section. Graduation day before the tree
may be ETC/GEKO text: check on screen.

## Phase D: the other `SERIFU/` files

| # | File | Chars | Way in |
|---|---|---:|---|
| D1 | OMIMAI (a girl visits the sick player) + OMIMAI.EXN words | 1,800 | `force_event.py G 0 --type 0x47` (probe pb5: Mio's visit) |
| D2 | HAGEMASI (encouragement, OMIMAI.EXN state 0x62) | 2,300 | find what sets 0x62; `force_state.py 0x62` |
| D3 | GROUP_D (Yoshio's group dates) + DATE2.EXN words | 5,900 | `force_event.py 0 0 --type 0x49` (probe pb6: theme park, ride choices) |
| D4 | KARADATA (DATE2, base 0x801B0000) | 870 | find its stage in DATE2 |
| D5 | ZAKOSEN (DATE.EXN, 7 strings) | 60 | find the caller |

## Phase E: club contests and practice matches

`MASTER/*.BIN` (MASTER.EXN, states 0x74–0x76: TAI_MAS 4,700, SUI_CON,
EN_GP, G_CON, MOKUTEN, NOBEL, UEKI, KOSIEN; one per club) and
`SHIAI/SIAI_TX.BIN` (RENSYU.EXN, state 0x73), plus MASTER.EXN's 36 words.
Probe pb2: `force_event.py 0 0 --type 0x25` played the baseball tournament
(KOSIEN) for the test card's club; 0x26/0x27 returned to the title screen.
**Investigation first:** how MASTER picks the contest from the club
(`force_camp.py --club` shows how to set the player's club) and what
0x26/0x27 need.

## Phase F: overlay words and small files

Each with `exn_words.py` (room per string) and the overlay's forcer:
- ETC.EXN (200 strings: career counselling, university exams, other
  one-day screens; `force_event.py 0 0 --type 0x43` / `0x4A`, probes
  pb9/pb10), OLH.EXN (290, state 0x3A: identify first);
- RPG_BAT.EXN (319: the trip battles; reach them through `force_trip.py`
  with "leave this to me"; the 攻撃/防御 menu is graphics: check);
- TAIIKU.EXN (28) and `TAIIKU/` texts (sports day, `--type 0x20`; a
  minigame needs input), GYOZI, TT, OPTION and NAME_ENT leftovers, the
  EXE's 34 untranslated strings (`exn_words.py SLPM_86.053 --todo`);
- `FUKUTEST/JOHO.NBN` (the girl info card values: sizes, birthdays);
- graphics text (not counted by progress.py): an inventory first
  (testing.md "Finding graphics").

## Status

| Item | State |
|---|---|
| Tools for the loop (survey, draft + memory + checks, candidate, review sheets, state forcer, overlay words) | Done 2026-10-10 |
| Remaining-files map, state/record maps (§6aa), probes pb1–pb12 | Done 2026-10-10 |
| A1–A10 dates | |
| B0 festival forcer, B1–B13 | |
| C ending | |
| D1–D5 | |
| E contests | |
| F overlays and small files | |

## Working notes (Windows dev box)

- `PYTHONIOENCODING=utf-8` when printing Japanese.
- Close the emulator before building (`candidate.py` does it).
- `drive.ps1` and `tools/emu/*.ps1` need `powershell.exe` 5.1.
- Emulator hidden: `-Hidden` or `TOKI_EMU_HIDDEN=1`.
- A save state reopens the disc it was made with (`.emu/review_dates`)
  and keeps that build's EXE in RAM: EXE changes need a fresh boot.
- Command icons: `Down` steps through them one per press; give each press
  about 900 ms on the main screen and 3.5 s in dialogue.
- A forcer left waiting on a rule holds the GDB connection until the
  emulator restarts.
- Hidden-emulator screenshot stalls: drive.ps1 retries F10; a run that
  still stalls is re-run (testing.md "Harness stalls").
