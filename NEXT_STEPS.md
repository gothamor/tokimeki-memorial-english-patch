# Next steps: translate the Christmas party (`SERIFU/XMAS.BIN`)

This is the only active task. Keep the Status table current as steps land.
Technical findings go in `docs/`, not here.

Finished so far (all 2026-10-08, in normal builds; what was and wasn't
seen is in the AGENTS.md status table, how in docs/testing.md):
- Shiori: her dates `shiori_dates.json` (§6k) and special events
  `shiori_events.json` (§6j);
- shared: date lines `date_shared.json` (§6l), phone calls
  `phone_calls.json` (§6m), walking home `walk_home.json` (§6n),
  invitations `invitations.json` (§6o);
- Yuko: her dates `yuko_dates.json` (§6k; plan template in git at
  `31d8608`) and special events `yuko_events.json` (plan template at
  `7f899d5`);
- first meetings `meetings.json` (§6p), the club welcome
  `club_welcome.json` (§6q), the player's birthday `birthday.json` (§6r),
  the girls' birthdays and gift names `girl_birthdays.json` (§6s);
- the Christmas party `christmas.json` (§6t, 2026-10-09).

## Why this file (2026-10-08, static survey)

- **Every playthrough, every year.** The Christmas party is a fixed yearly
  event (December); the first one comes in year 1. Shiori's walk home
  after it is already English (EVENT_FU entry 12), so today the party
  itself is Japanese around an English ending.
- **Small, and the overlay is known.** 28,672 bytes at LBA 44988,
  **358 strings** (about 6,200 Japanese characters), base `0x80197000`
  (dump: `extracted/dumps/XMAS.json`, local only; 3 rejected targets with
  no Japanese text, check them). Loaded by **SHOUGATU.EXN** at
  `0x8013D7D4`, the Christmas-party flow (main state `0x52`, stage
  dispatcher `0x8013D180`; game-internals §6j "SHOUGATU flows").
- **A forcer exists:** `tools/emu/force_christmas.py` swaps the next
  weekday into the party flow at Shiori's stage 6. For the party itself
  it needs to enter at the party's first stage instead (see Tools).
- **Content (first lines):** the player runs into girls at the party
  ("{G}も来てたのか", "しばらく{G}と話し込んだ"), Yoshio is mistaken for
  someone, presents (TARA_OBJ/XMAS_PRE.BIN is the present graphics).

## Scope

All of `XMAS.BIN` into `translation/christmas.json` (one `dialogue`
block, base `0x80197000`, `share_identical: true`), plus any in-place
words in SHOUGATU.EXN the party code `strcpy`s (banners, labels; check
with `tools/code_strings.py extracted/CDROM/EXEDIR/SHOUGATU.EXN --range
...` near the party code, as for §6p). Pure-punctuation pauses stay.
Out of scope: Shiori's walk home (done), the present graphics, White Day
(`WHITE.BIN`, also SHOUGATU; next candidate).

**Watch for:** `{>…}`/`{-…}` speaker labels (re-dump with the current
dumper), `0C`/`0D` pairs, gift names (`{A}` may use the gift table already
translated in SHOUGATU, §6s), odd-length names before punctuation.

## Steps

1. **Map the file** (static): find SHOUGATU's section-table fill for XMAS
   (the code near `0x8013D7D4`), walk the sections with the EVENT_FU
   layout, confirm they reach all 358 strings, and map stages / girl ids
   to sections (stage dispatcher `0x8013D180`, girl selector
   `0x80140030`). Add `--xmas` to `tools/geko_sections.py`.
2. **Forcer:** extend `force_christmas.py` with `--stage N` (and, if the
   party picks a girl, `--girl G`), so each stage can be entered from the
   Sunday state. Verify on the untranslated text first.
3. **Translate** (draft in `translation/extra/christmas.json`),
   `dialogue_budget.py`, candidate build into `.emu/review_dates`, diff
   (only XMAS's sectors and any SHOUGATU word sectors), checksums.
4. **Test on screen, emulator hidden:** every stage/girl variant the
   forcer reaches; the party ends and the week continues.
5. **Promote:** move to `translation/christmas.json`, build without `-t`,
   byte-identical check; JSON description, AGENTS row, README list and
   progress, game-internals (a new §6t), testing.md, this file.

## Status

| Step | State |
|---|---|
| Survey (loader, size, base, forcer) | Done 2026-10-08 |
| Map sections, stages, girls | Done 2026-10-09 (§6t, `geko_sections.py --xmas`) |
| Forcer for the party's stages | Done 2026-10-09 (`force_christmas.py --party`, `xmas_run.ps1`) |
| Translate + candidate | Done 2026-10-09 (357 strings + 8 SHOUGATU words) |
| On-screen tests | Done 2026-10-09 (testing.md "The Christmas party") |
| Promote | Done 2026-10-09: `translation/christmas.json`, normal build byte-identical |

**The party is finished.** Pick the next file from "Later candidates" and
rewrite this plan for it.

## Later candidates

- **White Day (`WHITE.BIN`, ~3,600 chars) and Valentine's (`VALEN.BIN`,
  ~3,000, VALEN.EXN):** the other yearly events, small; White Day is day
  record type `0x30` in SHOUGATU (§6j). Good follow-ups to the party.
- **The big yearly events:** New Year (`SHOGATU.BIN`, ~21,000), school
  trip (`SHUGAKU.BIN`, ~18,700), training camp (`GASSHUKU.BIN` ~28,000 +
  `GASSH_FU.BIN` ~21,800, KANGEI.EXN, record type `0x42`).
- **The culture festival (`CDROM/BUNKA/`, 46 files, ~217,000 chars: over a
  third of the game's text)**, per girl and club; very repetitive. Needs its
  own survey and plan.

- **Birthdays are done** (`birthday.json`, `girl_birthdays.json`;
  §6r/§6s). Left: the different gift tables in BUNKAKEN, BUNKASAI and GYOZI
  (same 33-byte layout), when those events are translated.
- **Other girls' `EVENT_*.BIN`**: follow Yuko's plan (git `7f899d5`); their entries are the
  other blocks of the 79-entry table (find them by which entries reach the
  file's strings, as for Yuko).
- **Megumi's meeting**: she isn't in `G_APPEAR.BIN` (girl 9 has no
  handler in SHOUGATU's meeting switch); find where she's introduced
  (probably through Shiori) before calling the meetings complete.
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
