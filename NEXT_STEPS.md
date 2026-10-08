# Next steps: translate Yuko's regular dates (`SERIFU/DATE_AS.BIN`)

This is the only active task. Keep the Status table current as batches land.
Technical findings go in `docs/`, not here.

Finished before this (2026-10-08), all in normal builds; what was and
wasn't seen is in the AGENTS.md status table:
- Shiori's dates `shiori_dates.json` (game-internals §6k);
- the shared date lines `date_shared.json` (§6l);
- phone calls `phone_calls.json` (§6m);
- walking home `walk_home.json` (§6n);
- girls asking you out `invitations.json` (§6o).

## Why Yuko, and what was checked (2026-10-08)

- **Size.** `DATE_AS.BIN` is the smallest of the ten untranslated date
  files:
  - 460 strings, 324 distinct lines, about 8,700 Japanese characters
    (Shiori's had 344 distinct lines, about 11,000);
  - only 55 of her lines are identical to Shiori's.
- **Already reachable.** Her invitation and walk home are English. In the
  invitation test, accepting her arcade invitation started her Sunday date
  (testing.md "A girl asks the player out").
- **Same layout, verified statically** (game-internals §6k "Other girls'
  date files"):
  - DATE.EXN fills the 27 section tables per girl (Yuko's fill function is
    `0x80143814`) and loads `DATE_AS.BIN` to `0x80198000`, the same base as
    Shiori's.
  - All 27 sections are valid and reach exactly the 460 strings the dumper
    finds, each once.
  - `python tools/date_sections.py --girl 8 [--strings]` lists them.
- **Differences from Shiori's file:** Shrine 13 parts (Shiori 15), Shopping
  11 (20), Library 5 (6), Theme Park 55 (57).

**Open question to settle first: the Library.** Its setup (girl-independent)
assumes 2 versions of 3 parts, but Yuko's section has only 5 parts. Force a
Library date with `--version 1` on the **unpatched** game and see what plays.
If it reads past her list, leave that version's lines alone and document it.

## Scope

Translate every string of `DATE_AS.BIN` into a new file,
`translation/yuko_dates.json`: one `dialogue` block for
`CDROM/SERIFU/DATE_AS.BIN`, base `0x80198000`, `share_identical: true`.
Pure-punctuation pause lines ("・・・", "‥‥‥‥。") stay Japanese, as in
Shiori's file.

**Out of scope:**
- the impression thoughts and blurbs (already English, `date_shared.json`);
- her walk-home talks (`GEKO.BIN`, done);
- her special events (`EVENT_AS.BIN`);
- the `SPEAKTST` copies.

## Batches (same order as Shiori's; counts from `date_sections.py --girl 8`)

| # | Sections | Strings | Notes |
|---|---|---:|---|
| 1 | 22 ending, 23 meeting, 24 small talk, 26 going home | 85 | Seen in every date. Same selectors as Shiori's: the `-Break` rules in testing.md "Testing date conversations" apply. Check that they fire for girl 8. |
| 2 | 0 Art Museum, 7 neighborhood park, 25 hobby notes | 55 | Museum: `--set-at 0x80134F74 0x800CA2FC N`. Park: `--at 0x8013A8B0 --reg v0=RANK`. |
| 3 | 21 Kirameki Park, 14 Shopping | 34 | Her Shopping is shorter (11 parts): walk it with `date_choices.ps1`. `0x800E67EF` is Shiori's park-event flag; Yuko's event flags aren't mapped. |
| 4 | 1 Bowling, 6 Karaoke, 10 Pool, 12 Beach, 13 Botanical, 15 Skating, 16 Ski, 19 Library | 76 | Settle the Library question first. |
| 5 | 3 Zoo, 18 Aquarium, 11 Planetarium, 5 Arcade, 17 Stadium | 81 | |
| 6 | 2 Concert Hall, 8 Cinema, 4 Shrine | 34 | Shrine has 13 parts (Shiori 15): check whether the `{n}` yukata pair is there. |
| 7 | 20 Theme Park, 9 parade | 95 | Largest. The parade wasn't reachable for Shiori either. |

Total 460.

## How to test (limited-testing policy, same as Shiori's dates)

- **Forcing.** `force_date.py` takes the girl as its first argument:
  `force_date.py 8 PLACE 4 30 [--version N] -- RULES`. `date_run.ps1`
  hard-codes girl 0 in its force_date call, so add a `-Girl` parameter
  first.
  - **Verify before relying on it:** that appointment slot 0 with girl 8
    gives a Yuko date, i.e. the date's girl byte `0x800E69DD` = 8 and
    `DATE_AS.BIN` is the file read (`trace_reads.py`, or the DATE_AS LBA).
  - Her arcade invitation (`force_event.py 8 0 --type 0x46`, then accept)
    is a known-good fallback that books a real Yuko date.
- **Per batch:** one forced date per place, one `date_choices.ps1` run on
  one place of the batch, and `-Break` rules for the shared sections. Look
  at the sheets: English, fits, no stalls, the date ends and the week
  continues.
- **Static checks every time:**
  - the build succeeds;
  - `dialogue_budget.py` shows no `OVER-GAP`;
  - only DATE_AS's sectors change (LBA from `extracted/files.tsv`);
  - checksum valid.
- Compare with the unpatched game only if something looks wrong (and for
  the Library question).

## Per-batch workflow

1. `python tools/dump_dialogue.py extracted/CDROM/SERIFU/DATE_AS.BIN -o extracted/dumps/DATE_AS.json`
   (local only; never commit dumps).
2. Draft into `translation/extra/yuko_dates.json`.
   - For a line identical to one in `shiori_dates.json`, start from
     Shiori's English, but re-voice her lines for Yuko. Player lines can
     usually stay as they are.
   - Translate repeated Japanese identically so the copies are shared.
3. `python tools/dialogue_budget.py translation/extra/yuko_dates.json`.
4. Build into `.emu/review_dates` from every default file plus the draft
   (testing.md "Testing date conversations"). Close the emulator first,
   then diff against a default build.
5. Spot test per the policy above.
6. Promote:
   - move the draft to `translation/yuko_dates.json`;
   - build without `-t` and confirm it's byte-identical to the candidate;
   - update the JSON description, the AGENTS.md row, `docs/testing.md` and
     the status below.

## Translation conventions

- **Yuko's voice:** a carefree, slangy party girl. Already set in
  `walk_home.json` / `invitations.json` ("Totally excited", "What a drag",
  "Lucky!", "Wanna..."). Keep her teasing and her impatience with study.
  Her replies still encode how well a choice went (the graded impression
  thought follows).
- **Everything else as in Shiori's dates** (her old plan is in git history,
  commit `ba3bbf3`, section "Translation conventions"):
  - the same option count and order;
  - even letter counts per option;
  - ≤ 28 cells per line; `{G}` counts 18 cells, `{P}` 12;
  - the same line count as the Japanese;
  - thoughts get no parentheses (the game draws both) and end on an even
    letter count;
  - `{n}{n}` stays at the end of its option;
  - place names as in `outings.json`.
- Reuse the player's lines from `shiori_dates.json` where the Japanese is
  identical (meeting, ending, going home).

## Status

| Batch | State |
|---|---|
| Layout check (`date_sections.py --girl 8`) | Done 2026-10-08, static |
| `date_run.ps1 -Girl`, verify a forced Yuko date | Next |
| Library version-1 question (unpatched) | Next |
| 1–7 | Not started |

## Later candidates

- **The other nine girls' date files**, in rough size order: Megumi
  (DATE_MI), Nozomi (KY), Yuina (HI), Saki (NI), Yumi (SA), Yukari (KO),
  Ayako (KA), Mio (KI), Mira (KG).
  - Before Mio, Yuina, Ayako or Megumi: one of their sections has a
    pointer outside the file.
  - Before Mio, Yuina, Nozomi, Mira, Megumi or Yumi: their tables reach
    4–9 strings the dumper misses.
  - See game-internals §6k.
- `FUKUTEST/JOHO.NBN` (the values on Yoshio's girl info card).
- `DATE.EXN` `0x8015D108` (93 birthday-present names, 33-byte records).
- Other girls' `EVENT_*.BIN`. Testing them needs a save with more girls
  met, or a RAM poke to add them.

## Working notes (Windows dev box)

- `PYTHONIOENCODING=utf-8` when redirecting patcher output.
- Close the emulator before building; it locks the review disc's BIN.
- `drive.ps1` and `tools/emu/*.ps1` need `powershell.exe` 5.1.
- A save state reopens the disc it was made with, and keeps that build's
  EXE in RAM: EXE changes need a fresh boot to be seen.
- Test states:
  - `.emu/savestates_backup/dates_sunday_0423_candidate.sav` (Sunday
    95/4/23);
  - `phone_sat0429.sav` (Saturday, phone available).

  Both are on `.emu/review_dates/`.
- Command icons: `Down` steps through them one per press. Give each press
  about 900 ms on the main screen and about 3.5 s in dialogue, and
  screenshot before pressing `Down`; early presses get dropped.
- A forcer left waiting on a rule holds the GDB connection until the
  emulator restarts.
