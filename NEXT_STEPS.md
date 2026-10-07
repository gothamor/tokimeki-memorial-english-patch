# Next steps — translate Shiori's regular dates (`SERIFU/DATE_FU.BIN`)

The only active task. Keep this file's status current as batches land;
put technical findings in `docs/`, not here. Earlier plans (main loop,
EVENT_FU, settings) are finished or parked; see git history
(`b167460` and before) if you need them.

## Goal and scope

Translate every string of `DATE_FU.BIN` into
`translation/shiori_dates.json`: **476 strings in 27 sections**, ~26,700
pooled bytes. Done so far: section 0, the Art Museum (30 strings, verified,
in normal builds). Remaining: **446 strings in 26 sections.**

Everything needed is mapped (game-internals §6k): which section belongs to
which place, how each picks its part, choices and replies, the `{n}` empty
option, and how to force any of it in the emulator.

Out of scope here (note them, don't do them): the impression thoughts after
each choice (`SERIFU/SERIFU.BIN`, shown in every date), the walk-home talks
(`GEKO.BIN`), other girls' `DATE_*` files and the `SPEAKTST/TEST_FU.BIN`
copies of these lines.

## Testing policy for this task (user's request, 2026-10-07)

**Limit on-screen testing.** Do enough to trust a batch, then move on to
the next area of the file. Concretely:

- **Always (static, cheap):** the build succeeds; `dialogue_budget.py` shows
  no `OVER-GAP` and the block packs; structure, width and `{n}` checks pass
  (the patcher enforces them); only DATE_FU's sectors change against the
  default build; checksum valid.
- **Per batch, on screen:** one forced date per place in the batch (one
  version, whatever choice comes up first), plus **one** `date_choices.ps1`
  run on one place of the batch to see all its options and replies. For the
  shared sections, one or two forced dates with `-Break` rules covering a
  few parts, not every combination. Look at the contact sheets: text
  English, fits the box, no stalls, the date ends and the week continues.
- **Don't** chase every version × choice × mood, natural triggers, or
  unpatched comparisons for each place (the museum already established
  that the engine handles English choices/replies the same way). Compare
  with the unpatched game only if something looks wrong.
- If the spot check is clean, promote the batch and move on. Record what
  was and wasn't seen (one short paragraph per batch in `docs/testing.md`,
  the AGENTS.md row) — never claim untested branches were seen.

The hard rules in AGENTS.md still apply (checksum, sizes, structure, no
committed dumps).

## Batches (in order)

| # | Sections | Strings | Pool bytes | Why this order / notes |
|---|---|---:|---:|---|
| 1 | 23 meeting, 22 ending, 26 going home, 24 seasonal small talk | 85 | 3,048 | Shown in every date, so every later test exercises them. Many repeats (61 unique). Short strings: space is easy. Force with `-Break` rules (testing.md). |
| 2 | 7 neighborhood park (place 0), 25 hobby notes | 25 | 1,348 | Park = `force_date.py 0 0 ...`; first unlabelled narration (`07`), action choice (`08`), notes (`04`). Keep the "・・・" pause lines in Japanese punctuation. |
| 3 | 21 Kirameki Park, 14 Shopping | 48 | 2,880 | Common early dates. Shopping is choice-driven (no versions): walk it with `date_choices.ps1`. Park in April also triggers EVENT_FU's spring scene (already English). |
| 4 | 1 Bowling, 6 Karaoke, 10 Pool, 12 Beach, 13 Botanical, 15 Skating, 16 Ski, 19 Library | 78 | 4,620 | Eight small 2-version places, same shape as the museum. Spot-check 2–3 of them on screen, the rest statically. |
| 5 | 3 Zoo, 18 Aquarium, 11 Planetarium, 5 Arcade, 17 Stadium | 82 | 5,252 | 3–4 version places; Arcade starts with an `08` choice and has no parts-per-version byte. |
| 6 | 2 Concert Hall, 8 Cinema, 4 Shrine | 37 | 2,084 | Choice-driven; Cinema has an announcement line (`07`) with its own 「 and indentation; Shrine has the `{n}` yukata pair (keep `{n}{n}` at the option ends). |
| 7 | 20 Theme Park, 9 parade | 91 | 5,896 | Biggest: 57 parts, 25 choices, long branch tree, longest replies (up to 152-byte slots). Parade is a Theme Park sub-scene; reaching it may need a step jump (not designed yet). Do last, maybe in two halves. |

Totals: 446 strings. Batch sizes are a guide; split a batch if the space
or the review gets awkward.

## Per-batch workflow

1. **Get the originals.** `extracted/dumps/DATE_FU.json` (local, never
   commit). `python tools/date_sections.py --strings` lists each section's
   parts, speaker codes and offsets; translate whole sections.
2. **Draft** into `translation/extra/shiori_dates.json`: a copy of the
   promoted file plus the batch's lines (one block, `share_identical`
   kept). Translate repeated Japanese lines identically so they share.
3. **Check space while writing:**
   `python tools/dialogue_budget.py translation/extra/shiori_dates.json`
   (and `extracted/dumps/DATE_FU.json --all --range A B` to see a section's
   budgets first). Long replies sit alone in their gap: keep each near its
   own slot size.
4. **Build the candidate into `.emu/review_dates`** (the Sunday save state
   reopens that disc), from every default file **except**
   `translation/shiori_dates.json`, plus the draft:
   ```bash
   T=""; for f in translation/*.json; do [ "$f" = translation/shiori_dates.json ] || T="$T -t $f"; done
   PYTHONIOENCODING=utf-8 python -m tokipatch "<cue>" -o .emu/review_dates -f $T -t translation/extra/shiori_dates.json > .emu/review_dates.log
   ```
   Close the emulator first. Check the log (`dialogue: N string(s) ...`,
   `checksum updated`) and diff against a default build: only DATE_FU
   sectors (LBA 44329–44351) may change.
5. **Spot test** per the policy above with `tools/emu/date_run.ps1`
   (`-Place P [-Version N] [-Break "..."]`) and `date_choices.ps1`; read the
   contact sheets. Launch the emulator visibly; ask the user to keep hands
   off; close it when done.
6. **Promote:** move the draft over `translation/shiori_dates.json`, build
   without `-t`, confirm byte-identical to the candidate. Update the JSON
   description (sections covered, what was seen), the AGENTS.md table row,
   a short paragraph in `docs/testing.md`, and the status below. Commit
   when the user asks.

## Translation conventions

- **Voices:** Shiori is warm, polite and a little reserved (match
  `shiori_events.json` and the museum); the player is casual. Keep her
  teasing or cool replies recognisably so: the replies encode how well a
  choice went, and the impression thought that follows is graded.
- **Names and places:** `{G}`/`{P}` stay as codes; Shiori is "Shiori";
  place names as in `outings.json` (Kirameki Park, Art Museum, Theme Park,
  ...). Place 0 is "the park" / "the neighborhood park".
- **Choices** (`03` spoken, `08` actions): same option count and order,
  **even letter count per option** (else a space shows before `』`), ≤ 28
  cells. Actions read as narration: "Praise her yukata." / "Say nothing."
- **Replies** (`02`): one `{q}` option per choice, in choice order; each
  option keeps its own line count.
- **Thoughts** (`06`) and notes (`04`): the game draws both brackets; end
  with `)` only if the Japanese ends with `）` (patcher-enforced).
- **Pure punctuation lines** ("・・・", "‥‥‥‥。") stay in Japanese
  punctuation.
- **`{n}{n}`** stays at the end of its option.
- Lines: same count as the Japanese (4–5 line strings scroll); ≤ 28 cells;
  `{G}` counts 18 cells, `{P}` 12.

## Status

| Batch | State |
|---|---|
| Museum (section 0) | Done, verified in depth, in normal builds |
| 1 shared sections | Next |
| 2–7 | Not started |

## Done when

All 27 sections are translated in `translation/shiori_dates.json`, the
normal build includes them, each batch had its spot check, and the JSON
description / AGENTS.md / testing.md list what was seen and what wasn't
(e.g. versions, moods and branches only checked statically, the parade if
it couldn't be reached).

## Before you start

- `AGENTS.md` (rules, checklist, status table), game-internals §6e
  (dialogue), §6k (this file), translation-guide "Dialogue", testing.md
  "Testing date conversations" (tools, `-Break` rules, the state/disc gotcha).
- Test assets: `.emu/savestates_backup/dates_sunday_0423_candidate.sav`
  (Sunday 95/4/23, made from `.emu/review_dates`); the 95/4/23 card is in
  `.emu/duckstation/memcards/` (backups in `.emu/memcard_backup/`).

Environment (Windows dev box):
- `PYTHONIOENCODING=utf-8` when redirecting patcher output.
- `drive.ps1` and the `tools/emu/*.ps1` scripts need `powershell.exe` 5.1.
- A forcer left waiting on a `-Break` rule holds the GDB connection;
  restarting the emulator (`launch_state.ps1`) ends it.
- `Remove-Item` on the memcard folder is blocked; move files instead.
