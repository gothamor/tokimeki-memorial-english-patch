# Next steps

No task is active. The last two finished on 2026-10-08:

- **Shared date lines** (`SERIFU/SERIFU.BIN` and the `DATE.EXN` place
  names): `translation/date_shared.json`. See game-internals §6l and
  testing.md "SERIFU.BIN". Its full plan is in git history (`184fe39`).
- **Phone calls** (`EXEDIR/TEL.EXN`): `translation/phone_calls.json`, all 680
  strings. See game-internals §6m, testing.md "Phone calls" and
  translation-guide (strings the code addresses directly).

What was and wasn't seen on screen is in the AGENTS.md status table.

## Candidates for the next task

1. **`SERIFU/GEKO.BIN`, the walk-home talks** (1,011 strings, ~13,100
   characters). A plain script file, like `EVENT_FU`/`DATE_FU`, so the
   dump/budget/repack workflow carries over unchanged. Plan it in batches
   (the DATE_FU plan in git history `ba3bbf3` is the template), with the
   same limited-testing policy. Forcing a walk home with a given girl needs
   a forcer (GEKO's event selector is partly mapped in game-internals §6j).
2. **`FUKUTEST/JOHO.NBN`**: the values on Yoshio's girl info card (sign,
   blood type, club, notes, §6m). It's an `.NBN` file, so check first
   whether the text is plain Shift-JIS strings or graphics.
3. **`DATE.EXN` `0x8015D108`**: 93 birthday-present item names in 33-byte
   records (`slot` makes them fittable). Find the code that reads them
   first (`0x80149D04` copies the table).
4. **Other girls' `DATE_*.BIN` / `EVENT_*.BIN`**. They're reachable on
   phone calls now, but the test save only has Shiori in its phone book, so
   testing needs a save with more girls met, or a RAM poke to add them.

## Working notes (Windows dev box)

- `PYTHONIOENCODING=utf-8` when redirecting patcher output; close the
  emulator before building (it locks the review disc's BIN).
- `drive.ps1` and `tools/emu/*.ps1` need `powershell.exe` 5.1.
- A save state reopens the disc it was made with, and keeps that build's
  EXE in RAM: EXE changes need a fresh boot to be seen.
- Test states: `.emu/savestates_backup/dates_sunday_0423_candidate.sav`
  (Sunday 95/4/23), `phone_sat0429.sav` (Saturday, phone available), both
  on `.emu/review_dates/`.
- Command icons: `Down` steps through them one per press; give each press
  ~900 ms or it's dropped.
