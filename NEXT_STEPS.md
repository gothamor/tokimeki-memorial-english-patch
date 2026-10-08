# Next steps: translate Yuko's special events (`SERIFU/EVENT_AS.BIN`)

This is the only active task. Keep the Status table current as steps land.
Technical findings go in `docs/`, not here.

Finished before this (all 2026-10-08, in normal builds; what was and
wasn't seen is in the AGENTS.md status table):
- Shiori's dates `shiori_dates.json` (game-internals §6k), the shared date
  lines `date_shared.json` (§6l), phone calls `phone_calls.json` (§6m),
  walking home `walk_home.json` (§6n), invitations `invitations.json` (§6o);
- Yuko's regular dates `yuko_dates.json` (§6k). Its plan, a good template
  for a date file, is in git history (`NEXT_STEPS.md` at commit `31d8608`);
- the first meetings `meetings.json` (§6p; added in-string speaker labels
  `{>部長}` to `script.py`, `meet_run.ps1`, the hidden-emulator option);
- the club welcome `club_welcome.json` (§6q; `force_club_welcome.py`).

## Why this file, and what was checked (2026-10-08, static)

- **It interrupts English text.** A spring Arcade date with Yuko plays her
  crane-game event instead of the (English) date conversation: seen on a
  forced 4/30 Arcade date (testing.md "Yuko's dates").
- **Small.** 8,192 bytes at LBA 44577 (4 sectors), base `0x80198000`
  (like EVENT_FU), checksum trailer. **89 strings**, about 1,200 Japanese
  characters; the dumper finds all 89 (`extracted/dumps/EVENT_AS.json`,
  local only).
- **Layout.** Entries **0–5** of the shared 237-word event table (79 × 3;
  GEKO.EXN `0x80145EC0`, filled by `0x8013799C`–`0x80138828`, game-internals
  §6j) are Yuko's: they reach exactly the 89 strings, each once. (Shiori's
  are entries 6–13.) Each entry has the EVENT_FU layout.

| Entry | Master | Parts | Strings | Scene | Runs in | Trigger / how to force |
|---|---|---:|---:|---|---|---|
| 0 | `0x304` | 6 | 21 | the staff room: Yuko being scolded for lateness (has a `{>先生}` teacher label and a centered `・` pause) | GEKO, girl 8 scene 1 (handler `0x80139470` → setup `0x80139640`) | day record `45 08 01 00`: `force_event.py 8 1`. Natural selector: the girl-8 case of `0x8006FB4C` (§6j), not traced |
| 1 | `0x7BC` | 4 | 14 | Arcade: she wins a plush from the crane game | DATE, scene 2 | Arcade (place 9), months 3–5, flag `0x800E6823`, date step sub 1 / step 12. **Plays by itself on a forced 4/30 Arcade date** |
| 2 | `0xB9C` | 3 | 13 | Theme Park parade: "I always wanted to see it with someone I like" | DATE, scene 3 | Theme Park (12), months 6–8, `*(u8*)0x8015B680` = 1, flag `0x6824`, step 1 / `0x3C` |
| 3 | `0xE94` | 4 | 11 | Concert: she gets carried away, the player stands with her | DATE, scene 4 | Concert Hall (15), months 9–11, `*(u8*)0x8015B688` = 10, flag `0x6825`, step 1 / `0x11` |
| 4 | `0x11B8` | 4 | 12 | Skating Rink: she falls on the melting ice | DATE, scene 5 | Skating Rink (19), months 12–2, flag `0x6826`, step 1 / 8 |
| 5 | `0x1608` | 6 | 18 | Library: she makes him write cram sheets | DATE, scene 6 | Library (8), 95/12/10, 96/12/8 or 97/12/7 with bit 17 of `0x800E6374`, flag index `0x3B` (`0x800E6827`), step 1 / 0 |

DATE's chooser call sites for Yuko (`0x8013272C`, her block from
`0x80133618`; each loads `a0` = scene then calls `0x801326B0`): scene 2
`0x80133684`, 3 `0x801336FC`, 4 `0x80133760`, 5 `0x801337BC`, 6
`0x80133860`. Conditions on the rank values (`sp+0x31`/`0x33`) weren't
decoded (game-internals §6k "Her date events").

**Check first (cheap, static):** SHOUGATU (`0x8013D4D8`) and SHUGAKU
(`0x80137824`) also contain EVENT_AS's LBA. They are probably the same
per-girl EVENT loader as GEKO's and DATE's (§6j "Loading"), used for other
scenes; confirm they don't run Yuko entries outside 0–5 or a different
table before calling the file complete.

## Scope

Translate every string of `EVENT_AS.BIN` into
`translation/yuko_events.json`: one `dialogue` block for
`CDROM/SERIFU/EVENT_AS.BIN`, base `0x80198000`, `share_identical: true`.
The centered `・` pause lines stay Japanese, as in Shiori's files.
Out of scope: Yuko's dates (done), the `SPEAKTST` copy, other girls'
EVENT files.

**Watch for:**
- `{>先生}` (entry 0, `0x5C`): a 4-byte in-string label. In English at most
  4 letters, e.g. `{>Tchr}` (translation-guide "Speaker labels").
- Entry 2 begins with the same line as DATE_AS's parade section 9
  ("パレードやってるよ"): translate it consistently with `yuko_dates.json`.
- `0C`/`0D` pairs and `06` thoughts, as in EVENT_FU (§6j): thoughts get no
  parentheses unless the Japanese ends with `）`, and end on an even letter
  count.
- Lines that address her: avoid an odd-length run before `{G}`, and put
  the name at the line end where punctuation would follow it.

## Tools to add before testing

1. **`force_date.py --scene` for Yuko.** Its `SCENES` table is Shiori-only.
   Make it per girl: `{(girl, scene): (call site, flag, (sub, step))}`,
   adding Yuko's five from the table above (flags `0x800E6823`–`6827`), and
   accept `--scene` for girl 8. Keep Shiori's entries unchanged.
2. Optionally `date_run.ps1 -Scene N` passing it through (`-Girl 8` exists).
3. Entry 0 needs no new tool: `meet_run.ps1 -Girl 8 -Scene 1 -Type 0x45
   -Hidden`.

Verify each forcer on the **unpatched** text first (the current default
build already has DATE_AS in English but EVENT_AS Japanese, so the default
build is the "before" reference): the scene plays, ends, and the date or
week continues.

## Test plan (all scenes; it's one small file)

From the Sunday state (`.emu/savestates_backup/dates_sunday_0423_candidate.sav`,
built on `.emu/review_dates/`), emulator **hidden** while the user works:

| Entry | How | Look for |
|---|---|---|
| 0 | `meet_run.ps1 -Girl 8 -Scene 1 -Type 0x45` | the `{>Tchr}` label, the centered pause, the `0C`/`0D` box, the week continues |
| 1 | `date_run.ps1 -Girl 8 -Place 9` with the on-time meeting rule (no `0x800E6823` rule) | the crane-game scene on 4/30, then the date's ending |
| 2 | Theme Park date, `--scene 3` | parade lines, the thought, the date ends |
| 3 | Concert Hall date, `--scene 4` | her lines, the player standing with her, ending |
| 4 | Skating Rink date, `--scene 5` | ending |
| 5 | Library date, `--scene 6` | the pause line, 3-line replies, ending |

If a jumped-to scene misbehaves, compare with the same forcing on the
default build before blaming the patch. Then the static checks: build
succeeds, `dialogue_budget.py` shows no `OVER-GAP`, only EVENT_AS's
sectors change, checksum valid.

## Workflow

1. Dump is already in `extracted/dumps/EVENT_AS.json` (re-dump if the
   dumper changes).
2. Draft into `translation/extra/yuko_events.json`, Yuko's voice as in
   `yuko_dates.json` (slangy: "super", "sooo", "a teeny bit", "lame").
3. `python tools/dialogue_budget.py translation/extra/yuko_events.json`.
4. Build the candidate into `.emu/review_dates` (emulator closed) from every
   default file plus the draft; diff against a default build.
5. Run the test plan.
6. Promote: move to `translation/yuko_events.json`, build without `-t` and
   confirm byte-identical; update the JSON description, AGENTS.md row,
   README feature list and progress (`tools/progress.py --update-readme`),
   game-internals §6j/§6k (Yuko's entries and triggers), testing.md, and
   this file.

## Status

| Step | State |
|---|---|
| Survey: entries 0–5, 89 strings, triggers | Done 2026-10-08, static |
| SHOUGATU/SHUGAKU loader check | Next |
| `force_date.py --scene` for Yuko | Next |
| Draft translation | Not started |
| On-screen tests (entries 0–5) | Not started |
| Promote | Not started |

## Later candidates

- **Megumi's meeting**: she isn't in `G_APPEAR.BIN` (girl 9 has no
  handler in SHOUGATU's meeting switch); find where she's introduced
  (probably through Shiori) before calling the meetings complete.
- **KANGEI.EXN's other text**: the training camp (`GASSHUKU.BIN`,
  `GASSH_FU.BIN`) and the birthdays (`G_BIRTH.BIN`, `P_BIRTH.BIN`) are
  run by the same overlay (§6q); day record type `0x42` forces the camp.
- **Other SERIFU files with label prefixes**: `EVENT_OT.BIN` starts a
  line with `-女生徒`; re-dump such files with the current dumper.
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
- Run the emulator hidden when the user is working on the same machine
  (`-Hidden` or `$env:TOKI_EMU_HIDDEN = "1"`).
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
