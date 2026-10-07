# Next steps: translate the shared date lines (`SERIFU/SERIFU.BIN`)

This is the only active task. Keep the Status table current as batches land.
Technical findings go in `docs/`, not here. The previous plan (Shiori's
regular dates, `DATE_FU.BIN`) finished on 2026-10-08. For it and earlier
plans, see git history (`cc0cbcc` and before).

## Goal and scope

Translate every string of `SERIFU.BIN` into a new file,
`translation/date_shared.json`: **48 strings, 2,324 pooled bytes**. One of
them, the centered "・・・" pause `0x694`, stays Japanese, so **47 get
translated**. Also translate the **21 place names** in `DATE.EXN` that the
file's `{A}`/`{M}` codes insert.

These lines appear in **every girl's dates**, not just Shiori's. They are the
last Japanese left in the date screens that `DATE_FU` already made English:
- the impression thought after every choice,
- the concert and movie blurbs at the Concert Hall and Cinema,
- the "did I get the meeting place wrong?" monologue.

Everything is mapped statically in game-internals §6l. None of it has been
forced in the emulator yet. The four sections:

| Sec | Strings | Count | Pool / gaps | Shown |
|---:|---|---:|---|---|
| 2 | `0x9B8`–`0xAA8` | 7 | 304, one gap | Impression thought after **every** date choice (levels 0–4), plus two "my lie was exposed" lines (swim / skate) |
| 0 | `0x0`–`0x260` | 12 | 696, one gap | Concert Hall: blurb about the act, after the seat exchange |
| 3 | `0xBDC`–`0xE40` | 11 | 668, one gap | Cinema: blurb about the film, after sitting down |
| 1 | `0x454`–`0x6EC` | 18 (17 + the pause) | 656 in 9 gaps; several strings sit alone in 20–48-byte gaps | Meeting-place mix-up or being stood up; options insert `{A}`/`{M}` |

**Out of scope** (note them, don't do them):
- the `SPEAKTST/TEST_OT.BIN` copies;
- the birthday-present item table in `DATE.EXN` at `0x8015D108`
  (93 × 33 bytes, §6l);
- other girls' `DATE_*`/`EVENT_*` files;
- the other `SERIFU/*.BIN` scene files.

## Decision needed before batch 3: the place-name slots

`{A}`/`{M}` come from a table in `DATE.EXN` at `0x8015B9DC` (file offset
`0x299DC`). It holds 21 slots of 33 bytes each, indexed by place id 0–20
(近所の公園 … スキー場). Each slot holds the Japanese name, then NUL bytes to
the end of the slot. The code copies the whole table and `strcpy`s one entry
(§6l), and nothing else reads it.

Under the in-place rule (AGENTS rule 5: original + NUL + padding to 4
bytes), many names can't fit their English:

| Japanese | Letters allowed |
|---|---:|
| 海 | 2 |
| 神社 | 4 |
| 遊園地 / 図書館 / 動物園 / プール / 植物園 | 6 |

That rules out "Beach" and "Theme Park" (the outings.json names).

Options, to put to the user (rule 5 says don't loosen it):
1. **(Recommended) A `slot` field for fixed-record strings.** For example,
   `"slot": 33` on a `strings` entry: the patcher checks that every byte from
   the original's end to the slot end is NUL, and then allows English up to
   slot − 1 bytes. It's narrower than loosening rule 5: it only applies where
   the record size is proven (the 0x2D6-byte copy loop at `0x8013EFB8` and the
   33-byte stride at `0x8013F0C0`). Document it in translation-guide, add a
   unit test, and keep `original` and the NUL-tail check.
2. Short English that fits today's budgets. That means "Sea" and
   abbreviations, and 海 still can't fit "Sea" (it allows 2 letters).
3. Patch the code to read another table (e.g. the EXE's outing names,
   `outings.json`). This is more invasive, and it needs a free-space
   argument (rule 8).

Batches 1 and 2 don't depend on this decision. Ask the user before starting
batch 3.

## Testing policy (same as DATE_FU, user's request 2026-10-07)

- **Always (static):**
  - the build succeeds;
  - `dialogue_budget.py` shows no `OVER-GAP` and the block packs;
  - the structure and width checks pass;
  - only the expected sectors change against a default build (SERIFU.BIN is
    LBA 44870–44871; `DATE.EXN` from LBA 37418 only in batch 3);
  - checksums valid.
- **Per batch, on screen:** a few forced dates covering the batch's lines,
  via `date_run.ps1` and `-Break` rules. Use `date_choices.ps1` where a
  choice matters. Look at the sheets: English, fits, no stalls, and the date
  ends and the week continues.
- **Don't** chase every concert, film, level or girl. Compare with the
  unpatched game only if something looks wrong.
- Record what was and wasn't seen, never claiming unseen lines:
  - in the JSON description,
  - in the AGENTS.md table row,
  - in a short paragraph per batch in `docs/testing.md`.

**Force rules: candidates from static tracing, unverified.** Confirm each one
on its first use and correct game-internals §6l if needed.

| What | Rule (`-Break`) | With |
|---|---|---|
| Concert blurb N (0–11) | `--at 0x8013BAD4 --mem8 0x8015B688=N` | `-Place 15` |
| Movie blurb N (0–10) | `--at 0x8013B964 --mem8 0x8015B684=N` | `-Place 14` |
| Impression level N (0–4) | `--at 0x8013B174 --times 0 --mem16 0x800CA22C=N --mem16 0x800CA22E=N --mem16 0x800CA230=N` (every choice's level) | any place |
| Stood up (part 8) | `--at 0x8013F008 --reg v0=4` (rank 4) | any place |
| Wrong place, 2 or 3 options (parts 0–7) | at `0x8013F03C` set `0x800E69A4` (agreed place) ≠ `0x800E69A5` (where the player went), `0x800E69A6` = another place, `0x800E69A7` = `0xFF` (2 options) or a fourth place (3 options). Work out the exact values from `0x8013F03C`–`0x8013F0B8` first. | any place |
| Lie lines | not traced (second caller `0x8013B208`). Try the boast options first: Pool version 1 "Swimming's my specialty." and Skating Rink version 0 "Leave skating to me.", with `date_choices.ps1`. | `-Place 16 -Version 1`, `-Place 19 -Version 0` |

Keep the meeting rule for a fixed 3-box meeting
(`--at 0x80132570 --reg v0=0 --mem8 0x8015B654=1`) except when testing
section 1, which needs the meeting flow left alone. In April, a Kirameki Park
date needs `--mem8 0x800E67EF=1` (the spring event).

## Batches (in order)

| # | Content | Strings | Notes |
|---|---|---:|---|
| 1 | Section 2: impression levels 0–4 + 2 lie lines | 7 | Seen after every choice, so every later test exercises them. No codes, short lines. Check: one date with `date_choices` (three levels), the level rule for the other two, and a try at the lie lines. |
| 2 | Section 0 concert blurbs + section 3 movie blurbs | 23 | Names must match `town_news.json` (KNM Symphony, Chisa Morita, Chage & Aska, WIZARD, Riko Kodama, XeXeX, Bees, SNACK, prf, Rinsu; I'm Doing It, Forrest Gump, Summer Saw, Fungaa, Kanpanman, Sleep Fist II, Love Melody, Speed King, BANPO, The Mask, Love and Youth). Up to 5 lines (`0x260`) scroll. Plenty of space. Check 2–3 of each, including the longest. |
| 3 | Section 1, the missed meeting (17 strings) + the 21 `DATE.EXN` place names | 17 + 21 | Needs the slot decision. Tight gaps: `0x4D4`/`0x5B0` alone in 48 bytes, `0x508`/`0x5E4`/`0x5FC` alone in 20 bytes. Translate the repeats identically so they share. Check: stood up (part 8), a 2-option and a 3-option mix-up with each choice, then the late arrival that follows (DATE_FU part 9–11). |

## Per-batch workflow

1. **Get the originals:** `extracted/dumps/SERIFU.json`. Regenerate it with
   `python tools/dump_dialogue.py extracted/CDROM/SERIFU/SERIFU.BIN -o extracted/dumps/SERIFU.json`.
   It stays local; never commit it. Parts and codes are in game-internals §6l.
2. **Draft** into `translation/extra/date_shared.json`:
   - one `dialogue` block for `CDROM/SERIFU/SERIFU.BIN`, with base
     `0x80197000` and `"share_identical": true`;
   - in batch 3, a `strings` list for `CDROM/EXEDIR/DATE.EXN`.
3. **Check space:**
   - `python tools/dialogue_budget.py translation/extra/date_shared.json`
   - `extracted/dumps/SERIFU.json --all` to see the gaps.
4. **Build the candidate into `.emu/review_dates`**: the Sunday state reopens
   that disc, and the date loads SERIFU.BIN and DATE.EXN from it. Build from
   every default file plus the draft:
   ```bash
   T=""; for f in translation/*.json; do T="$T -t $f"; done
   PYTHONIOENCODING=utf-8 python -m tokipatch "<cue>" -o .emu/review_dates -f $T -t translation/extra/date_shared.json > .emu/review_dates.log
   ```
   Close the emulator first. Check the log and diff the sectors against a
   default build (`.emu/default_now`).
5. **Spot test** per the policy above. Launch the emulator visibly, ask the
   user to keep hands off, and close it when done.
6. **Promote:**
   - move the draft to `translation/date_shared.json`;
   - build without `-t` and confirm it's byte-identical to the candidate;
   - update the JSON description, AGENTS.md (a new table row),
     `docs/testing.md` and the status below.

   Commit when the user asks.

## Translation conventions

- **Speaker and brackets:**
  - Codes `04` (impressions) and `06` (blurbs, thoughts) are the player's
    thoughts. The game draws **both** brackets, so write no parentheses
    (the patcher enforces it: none of these originals end in `）`).
  - Code `00` lines are the player talking to himself (『』).
- **Voice:** casual, the player's own. Impression levels read as a clear
  scale:
  - 0: nailed it ("Bang on! She liked that.");
  - 2: neutral ("Well, that's about what I expected.");
  - 4: bad ("I think that made a bad impression.").

  Keep it short; two lines at most, like the Japanese.
- **Blurbs:** "<Name> is …" in one to five lines, the same line count as the
  Japanese. They're jokey parodies; keep the joke, not the literal words.
  Names exactly as in `town_news.json`.
- **Choices** in section 1: `0x4A4` (`08`) and `0x570` (`03`).
  - Keep the same options in the same order, ≤ 28 cells.
  - `{A}`/`{M}` count **18 cells**, so a line with one has 10 left.
  - The text run after the code needs an even letter count, or a space
    shows before `』`. Same for the run before it, or a cell is wasted.
  - Example: "Was it at {A}" (no trailing run) or "{A}, maybe?".
- **Place names (batch 3):**
  - They're only used in these lines, so they can carry articles
    ("the zoo", "Kirameki Park").
  - Keep each ≤ 18 letters, so it fits `{A}`'s 18 cells.
  - Prefer even lengths: an odd pair-encoded name ends in a padding space.
- **Pure punctuation** (`0x694`) stays Japanese.
- Lines: same count as the Japanese, ≤ 28 cells. `{G}` counts 18 cells.

## Status

| Batch | State |
|---|---|
| Analysis (game-internals §6l) | Done 2026-10-08, static only |
| 1 impression thoughts (section 2) | Next |
| 2 concert + movie blurbs (sections 0, 3) | Not started |
| Slot decision for `DATE.EXN` place names | Ask the user |
| 3 missed meeting (section 1) + place names | Not started |

## Done when

- All 47 translatable strings and the 21 place names are in
  `translation/date_shared.json`, and the normal build includes them.
- Each force rule used is confirmed (or corrected) in §6l.
- Each batch had its spot check, and the JSON description, AGENTS.md and
  testing.md say what was seen and what wasn't.

## Before you start

- **Read:**
  - `AGENTS.md`: rules 5 and 6, the checklist and the table;
  - game-internals §6e (dialogue, name codes), §6k (dates) and §6l (this
    file);
  - translation-guide "Dialogue" and "Space budget";
  - testing.md "Testing date conversations" and the DATE_FU batch notes.
- **Test assets:**
  - `.emu/savestates_backup/dates_sunday_0423_candidate.sav` (Sunday
    95/4/23, made from `.emu/review_dates`). A state reopens the disc it was
    made with, so always rebuild into `.emu/review_dates`.
  - The 95/4/23 card is in `.emu/duckstation/memcards/` (backups in
    `.emu/memcard_backup/`).

Environment (Windows dev box) and lessons from DATE_FU:
- `PYTHONIOENCODING=utf-8` when redirecting patcher output.
- `drive.ps1` and the `tools/emu/*.ps1` scripts need `powershell.exe` 5.1.
- Close the emulator before building; it locks the review disc's BIN.
- A forcer left waiting on a `-Break` rule holds the GDB connection.
  Restarting the emulator (`launch_state.ps1`) ends it.
- `date_choices.ps1 -Pre` must stop exactly on the choice list. If the state
  is saved one box early, the shuffle changes per relaunch.
- Pressing on past a date's end runs the next week's commands (in RAM only).
  Size `-Presses` to the date.
- Minigames (the Shrine goldfish) need real input; don't drive through them.
- `drive.ps1` occasionally fails to get a screenshot; just rerun.
- `Remove-Item` on the memcard folder is blocked; move files instead.
