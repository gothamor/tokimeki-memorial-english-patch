# Next steps — character dialogue and special events

Active implementation plan and handoff notes. Keep the current plan/status
up to date; fold completed technical findings into `docs/`.

**Next priority: a character-focused dialogue and special-event pack.** The
settings and Save/Load panel work is tested and included in normal builds.
The character plan below is the next execution order; the older Step 0–4
sections later in this file are background/backlog, not prerequisites to
finishing every unrelated screen first. No character translation has been
implemented as part of writing this plan.

## Active plan: Shiori's complete conversations

Confirmed target: **Shiori Fujisaki**, explicitly selected by the user.
Prioritize a short conversation near the beginning of the game so testing
does not require late-game progress or a high-affection date. The `FU` scripts
contain Shiori-specific dialogue, but their runtime consumers/load addresses
and event conditions still need tracing; choosing the character does not
complete that technical mapping.

First release goal: Shiori's date dialogue and character-specific
special events, including player replies, thoughts and choices. This is a
bounded dialogue/events pack, **not a claim that the entire character route
is translated**. Shared scenes and the larger conversation pool are a later
milestone. Existing settings, names and accepted club cosmetics stay unchanged.

Inventory with the fixed dumper, 2026-10-07 (method in game-internals §6e):

| Candidate source file | Strings (old dumper) | Japanese bytes | Inferred RAM base |
|---|---:|---:|---|
| `CDROM/SERIFU/DATE_FU.BIN` | 474 (186) | 25,417 | `0x80198000` |
| `CDROM/SERIFU/EVENT_FU.BIN` | 157 (119) | 4,831 | `0x80198000` |
| `CDROM/SPEAKTST/TEST_FU.BIN` | 2,474 (2,473) | 94,496 | `0x80180000` |
| `CDROM/SERIFU/GASSH_FU.BIN` | 1,207 (186, wrong base) | 45,166 | `0x801B4400` |

These are string counts, not scenes or display lines. They now include the
strings that follow pointer tables, which the old dumper dropped. Strings
with unknown control bytes (`<`, `>`, `-`, `n`, mostly `SPEAKTST`) are still
left out by `script.decode` and need their consumer identified first.

### Early pilot candidates (static inspection; not yet played/traced)

1. **Early-morning walk to school with Shiori**, `CDROM/SERIFU/EVENT_FU.BIN`
   scene 2 (event-table entry 7). Strings `0x62C`, `0x2AA8`, `0x64C`, `0x668`,
   `0x6A8` (2 / 1 / 2 / 3 / 3 display lines, no choices; `0x2AA8` is a short
   `{P}` line found through the scene's master list). **Mapped, but not
   early (2026-10-07, game-internals §6j):** it needs Shiori's affection
   ≥ 61 and a second score ≥ 50, nonzero interaction counters, then about a
   1% roll per check, once per game. At 95/5/17 on the test card her
   affection was 47 and the counters were 0. Natural replay needs a
   mid-game save with good Shiori standing.
2. **Fallback conversation: meeting Shiori after school / asking to walk home**,
   `CDROM/SERIFU/GEKO.BIN` at inferred base `0x80197000`. Candidate clusters
   begin at `0x1A24` (her invitation), `0x1B50` (player invitation accepted),
   and `0x1C54` (player invitation declined). The decline cluster includes the
   two-choice entry `0x1C9C` and Shiori's response at `0x1CD0`; it may be useful
   for early/low-affection testing, but the selection thresholds and timing
   are not yet known. Shared-file ownership and complete branch boundaries
   must be mapped before patching; do not translate the entire GEKO pool.

Runtime check done (unpatched, 95/4/23 → 95/5/17, `tools/emu/watch_events.py`):
two meeting events, no Shiori event. Record whichever appears first in later
checks, back up a replay point, and trace its file/scene. The existing 95/4/23 card is useful
for a quick check; it does not guarantee either event. Prefer the earliest
naturally observed replayable Shiori conversation over forcing the preferred
candidate. If neither appears in a short bounded check, ask the user for an
early Shiori encounter/save and investigate the event conditions rather than
grinding weeks or inventing a guaranteed date. The prologue is already
translated and is not new Shiori-pilot coverage.

If the fallback is selected, a small Shiori-only `GEKO.BIN` scene becomes the
pilot exception to the initial DATE/EVENT file scope (feature JSON such as
`shiori_school.json`). The broader first release still targets the FU date
and special-event files. The dumper fix is done (Step 2); no translation or
emulator run has been performed yet.

### Step 1 — lock Shiori's release boundary (target confirmed)

- Target selection is complete: Shiori. Do not ask the user to choose again.
- Name the first milestone `Shiori date dialogue + special events`, preceded
  by the early school-conversation pilot if it is easier to reach.
  Reserve "all character text" for a later cross-file coverage audit.
- Record the selected character, candidate files and excluded shared systems
  here. Do not treat filename suffixes or appearances of a name in text as
  sufficient speaker/ownership evidence.

Character choice is done; confirm the actual pilot after Steps 2–3 establish
the earliest practical replay point.

### Step 2 — map files, scenes, speakers and format limits

- Use `tools/dump_dialogue.py` to make local skeletons under
  `extracted/dumps/`. Do not commit untranslated dumps or copied script text.
  Start from the inferred bases above, then confirm actual CD loads and RAM
  destinations with `tools/emu/trace_reads.py` at representative scenes.
- **Done (2026-10-07): dumper omission fixed.** `dump_dialogue.starts_string()`
  also accepts a target right after an in-file pointer word; `guess_base()`
  finds bases off the 0x800 grid (GASSH_FU is `0x801B4400`, not `0x801BE000`);
  left-out targets are reported (`--rejected`). Synthetic regression tests in
  `tests/test_dialogue_extraction.py` cover interior/foreign/undecodable
  rejection and that the patcher still refuses interior pointers. All four
  pilot strings are now dumped; a dry run of `apply_dialogue` on the real
  file accepted them (one pointer each, no code references, 180-byte pool).
  The re-inventory is in the table above. Local dumps of DATE_FU, EVENT_FU
  and GASSH_FU are in `extracted/dumps/` (not committed).
- Build a scene inventory keyed by disc file, original string offset and
  pointer/scene index. Record speaker, player replies, choices and outcomes,
  variants and the conditions needed to reach them. Inspect the scene tables
  and control flow: adjacent strings need not be sequential conversation.
- Audit omissions from the decoder, aliases/interior pointers, code-built
  references, punctuation-only runs and unusual controls. Record unknown
  offsets and what consumes them; do not silently discard or reinterpret them.
- Record addresses and the discovery method in `docs/game-internals.md` as
  they become established. Keep full originals local; committed tracking
  should use offsets, English scene summaries and status, not script dumps.

Done when one reachable complete scene is mapped and its load base, speaker
identity and branches are confirmed. Unknown formats outside that pilot may
remain explicit blockers for later batches.

### Step 3 — prepare repeatable testing before bulk work

- Try the early school-conversation candidates above before arranging dates
  or seeking later special events. Keep a backed-up
  memory-card save before it in `.emu/`; record date, prerequisites, choices
  and how to replay it. A Sunday-night save alone does not guarantee access
  to a particular date/event.
- Capture the unpatched behavior at the same point using copied cards in the
  isolated harness. Never operate the user's DuckStation or overwrite their
  real cards. Do not assume early saves can reach late-game/affection variants.
- The user may do the gameplay checks. Supply an exact CUE path, scene-entry
  instructions, choices to try and expected text; ask for the needed save or
  test result if reaching the scene requires their progress. Do not spend an
  unbounded run guessing cursor timings or arbitrarily changing game state.
- Fresh-boot the candidate and load a card save. Same-build states can help
  replay branches after that, but old-build states cannot validate new bytes.

Done when the pilot can be replayed and compared without risking user data.
**Done for the morning walk (forced replay; see the status above).**

### Step 4 — translate one complete pilot scene

- Establish a short English style/glossary: names matching existing patches,
  character voice, forms of address, recurring places and tone. Preserve
  meaning, relationship cues and the intent of each choice; review uncertain
  wording in context instead of silently inventing content.
- Translate the entire exchange: the character, player replies/thoughts,
  prompts and all mapped choice branches. Use a small complete scene rather
  than an arbitrary number of neighboring strings.
- Preserve display-line count, choice order/count and name codes on their
  original lines. Keep the 28-cell limit and current `TOKEN_CELLS`; check
  expanded names against the renderer's 64-byte per-line buffer. Keep
  punctuation-only runs unchanged where they may affect scene behavior.
- Draft in the pilot's appropriate feature JSON, such as
  `translation/extra/shiori_events.json` for the early-morning candidate or
  `translation/extra/shiori_school.json` for the shared walk-home scene,
  using a `dialogue` block and the confirmed base. Commit only translated
  entries, not the complete untranslated skeleton.
- Measure actual pooled-space usage with `patcher.plan()`. Only translated
  strings contribute usable slots; an empty `text` does not donate its space.
  A file's total byte size is not its text budget. Preserve meaning while
  tightening prose; if it still cannot fit, report the budget blocker.
  Never grow files, borrow unproven "free" regions or loosen validation.

Done when the complete pilot fits and has had a context/style review.

### Step 5 — build and verify the pilot candidate

- Build from the original disc into a fresh `.emu/` output through the normal
  patcher pipeline. Include all current default JSONs plus the draft: `-t`
  replaces the defaults, so supplying only the new file is not sufficient.
- Check original-byte guards, dialogue structure, line widths, repacked
  pointers, file sizes/LBAs, applicable checksum trailers and sector EDC/ECC.
  Diff the track against the plan; only predicted sectors should change.
- Keep one canonical block per source-file pool when expanding the pack.
  If a draft replaces an already promoted JSON, omit that default JSON from
  the candidate's explicit `-t` list and include its revised draft once.
  Do not apply old and new versions together or duplicate original offsets.
- Record the build path, translated entries, bytes used/available and any
  warnings. A passing build is not an emulator test.

Done when static checks pass and the user has a clearly identified candidate.

### Step 6 — test, then include the accepted batch in normal builds

- Check the pilot from scene entry through the next transition: speaker
  labels, widest inserted names, scrolling, voiced auto-advance, animation
  timing, every mapped choice and its response. Compare with the unpatched
  scene; no new stalls, missing lines, clipping or changed branch behavior.
- If the user tests, distinguish their report from screenshots and record
  exactly which scenes/branches they saw. Give a short targeted retest list
  for any failure; do not claim untested variants were seen.
- **After the relevant tests pass, promote that batch to `translation/`
  immediately.** Move the tested Shiori pilot JSON out of `extra/`, or replace
  its tested default version with the accepted revision. Do not wait
  for the whole route or leave tested files opt-in. Known failures block the
  affected promotion and must be reported explicitly.
- Build without `-t` and compare game bytes to the tested candidate. Update
  `AGENTS.md`, README coverage, JSON descriptions and testing notes. Keep
  unseen-path caveats even after promotion.

Done when the pilot is playable through the normal patcher command, not only
through a manually assembled test build.

### Step 7 — expand the date-dialogue pack in complete-scene batches

- Use the confirmed scene inventory to work through `DATE_FU.BIN`.
  Group branches and affection/location variants with their parent exchange;
  include the player's replies and choices throughout.
- Repeat Steps 4–6 for each manageable batch, retaining one canonical feature
  JSON. Track translated/reviewed/tested/blocked status by source offset and
  scene; counts alone do not measure branch coverage.
- Re-test earlier scenes affected by repacking, especially those with long
  labels/names and shared strings. Do not assume a passing first batch proves
  a larger pool's new pointer placements or widths.

Done when the scoped date file is translated/reviewed, representative mapped
branches pass in-game, and any genuinely missing/blocked content is listed.

### Step 8 — translate character-specific special events

- Apply the same workflow to `EVENT_FU.BIN`, using a separate feature
  JSON such as `shiori_events.json`. Confirm this `SERIFU/EVENT_*` source;
  the separate `CDROM/EVENT/` folder is not automatically dialogue.
- Inventory event triggers and variants first. Use appropriate saved progress
  or user playthrough checkpoints, rather than assuming every event is
  available in April. Check all participants' lines, player thoughts and
  post-event continuation, including line-timed animation/voice behavior.
- Promote each successfully tested batch into normal builds. Keep events
  that cannot yet be reached explicitly pending, with exact requested tests.

Done when the first date/events pack has a source-offset coverage report,
normal-build delivery and an honest list of untested or blocked branches.
If player-facing text in the scoped files is still untranslated or blocked,
label the delivered pack partial; a documented gap is not completed coverage.
Distinguish such content gaps from translated branches awaiting visual tests.

### Step 9 — investigate shared conversations toward full character coverage

- Treat `SPEAKTST/TEST_FU.BIN` as a separate research milestone:
  determine when it loads (phone, hallway or other interaction) and explain
  unsupported controls before bulk translation. Its extractable-entry count
  is not an assurance that all its dialogue is understood.
- Trace shared appearance/invitation, birthday, seasonal, school-trip, camp,
  festival, epilogue/ending and `BUNKA` scenes as encountered. Identify the
  chosen character's scene indices from the consumers, including generic
  dialogue that inserts `{G}`. Name searches alone will miss such text.
- Translate shared strings with all affected speakers/routes in mind and
  regression-test another consumer where feasible. Do not promise that
  finishing `DATE_*` and `EVENT_*` means every line for that character is done.
- End each milestone with remaining source files/unknowns, coverage and test
  prerequisites documented. "All character dialogue" requires a cross-file
  audit, not simply reaching the end of two JSON files.

Status 2026-10-07: **Steps 2 and 3 are done for the pilot.** The walk is
mapped (scene lists, loader, dispatch, trigger; game-internals §6j). It can't
happen early naturally, so with the user's agreement it is **forced** on the
test card (`tools/emu/force_event.py`, recipe in testing.md "Forcing a girl
event"). The unpatched scene was replayed twice from
`.emu/savestates_backup/shiori_0423_unpatched.sav`: 4 boxes, five strings
(`0x62C`; `0x2AA8` + `0x64C` sharing one 3-line box; `0x668`; `0x6A8`), then
the week continues. `EVENT_FU.BIN` → `0x80198000` is confirmed at runtime.
Reference screenshots are `.emu/shots/f_*.png` (not committed).

**Step 4 done (2026-10-07):** `translation/extra/shiori_events.json`
translates all five strings, 178 of 188 pooled bytes, all lines within 28
cells; the shared Shiori box stays 3 lines ("Oh, {P}!" / "Morning!" /
"You're up early."). An in-memory plan of the 15 default files plus the
draft succeeds (EVENT_FU.BIN size unchanged, checksum updated). Not built or
seen on screen yet.

**Steps 5 and 6 done (2026-10-07):** candidate `.emu/review_shiori/` passed
the static checks and the forced on-screen test after one fix (thoughts in
EVENT_FU must not end with `)`; the patcher now enforces matching the
original's `）`). Promoted to `translation/shiori_events.json`; the normal
build `.emu/default_shiori/` is byte-identical to the tested candidate.
Details in testing.md, "Forcing a girl event".

**EVENT_FU mapping done (2026-10-07, static; game-internals §6j table).**
All 157 strings belong to the eight entries 6–13; nothing else uses the
file. Remaining work by how it can be tested:
- **Done (2026-10-07):** GEKO scenes 1 (rain, 21 strings) and 8 (phone
  call, 42) translated, tested by forcing (`force_event.py 0 1` with flag
  `0x800E67EC` cleared, `0 8` with no flag) and promoted with the walk in
  `translation/shiori_events.json` (68 strings, 2162 of 2216 pooled bytes).
- DATE scenes 3–6 (19 + 18 + 15 + 16 strings): chosen inside a date with
  Shiori by place, season and date step. Forcing needs either a real date
  with her (she refuses at low affection) or writing the date state; not
  designed yet.
- SHOUGATU stage 6 (21 strings, snowy walk home): how the stage is reached
  isn't traced.

Earlier note (before mapping): Step 8 order is cheaper than Step 7 here. The remaining seven EVENT_FU
scenes (table entries 6 and 8–13; 157 strings in the file) can be mapped
the same way: master list → strings, then the trigger. GEKO dispatches only
Shiori scene ids 1, 2 and 8 (§6j), so the other entries are presumably run by
DATE, GYOZI, SHOUGATU or SHUGAKU, which carry the same table; find each
one's scene id and overlay before forcing it (`force_event.py` only covers
type-`0x45` day events). Then
`DATE_FU.BIN` (474 strings) needs its own date-flow mapping first.

## Before you start

Read these first. They're the contract and the knowledge base:

- `AGENTS.md`: the rules that keep the output bootable, the checklist, and
  the verification table. **Update the table when you verify something.**
- `docs/game-internals.md`:
  - §6 text and renderer (§6e dialogue, §6f the renderer hook, §6g the main
    game loop)
  - §7 graphics (sprite frames, `MAINROM.NBN`)
  - §8 open questions.
- `docs/translation-guide.md`: the `strings`, `dialogue`, `images` and `bytes`
  formats, budgets, and the patterns to watch for.
- `docs/testing.md`: the isolated DuckStation, `drive.ps1`, GDB tools, and the
  main-loop notes.

State at handoff:
- Current follow-up candidate: `.emu/review_settings/` includes all 13 default
  files from that review plus the 21-string Save/Load panel and 114-string
  in-game settings translations. Both have now been moved to `translation/`
  and are included in normal builds (15 default files). Panel separators and
  Menu Mode confirmation rows have been reviewed and corrected; static checks
  pass. The user's standing rule is to promote tested new translations to
  normal builds after testing; see `AGENTS.md` and the translation guide.
  A normal build without `-t` in `.emu/default_promoted_settings/` loads all
  15 files and is byte-identical (CUE and both tracks) to the tested candidate.
  Planned bytes, sizes, checksums, 37 changed sectors and EDC/ECC validate.
  The user has verified populated Load panels and all settings submenus as
  translated. Screenshots show slots 1/2 (None/Soccer), settings main list and
  Text Speed choices/help. Remaining branch coverage is in `docs/testing.md`
  under "Save/Load panel and settings handoff (2026-10-07)". Findings and
  consumer addresses are in game-internals §6i. Leave accepted club cosmetics
  alone. The previous main-loop work was committed in `567e3bf`; this
  normal-build promotion has not been committed by the agent.
- Steps 1 and 2 have implementations committed in `567e3bf`, but most of the
  new main-loop screens still need visual checks.
- New default translation files are `main_events.json`, `clubs.json`,
  `outings.json`, `town_news.json` and `character_names.json`.
- The default and full builds (the latter also including both `extra/` JSONs)
  completed successfully. The user booted and played the default patch and
  confirmed that character names appear translated.
- User screenshots also verify the Club List, Soccer selection/join result and
  monthly Club Day notice. They exposed one omitted name (`文芸` at `0x730A4`)
  and overlapping fixed-position fragments. Both now have fixes in the source
  and `.emu/review_clubs/` build. The user has now verified Literature and
  joining Soccer through the corrected captain's notice: the text no longer
  overlaps. Literature slightly overhangs the green selector and the notice
  retains a wide gap; the user accepts both for now and requests no changes.
  Results are recorded in `docs/testing.md` and the `AGENTS.md` status table.
- Review verified a real boot, loading the saved game, play to the 4/29 holiday
  and the first News issue. All 12 club-table pointers and original file sizes
  were checked. Longer names and most remaining screens still need visual QA.
- English text goes through the renderer hook. Any pair of letters is
  available; the limits are bytes and line width, not glyphs.
- `translation/main_screen.json` covers the main screen, the thought prompts
  and the in-game Save/Load text.

Environment gotchas (Windows dev box):
- Set `PYTHONIOENCODING=utf-8` when redirecting the patcher's output.
  Otherwise it crashes on Japanese log lines halfway through writing the
  build.
- Run `tools/emu/drive.ps1` with `powershell.exe` (5.1), not pwsh 7.
- `Remove-Item` on the emulator's memcard folder is blocked. Move files into
  `.emu/memcard_backup/` instead of deleting them.
- **The user sometimes plays the test emulator.** Ask them to keep hands off
  during scripted runs.
- Test assets:
  - `.emu/memcard_backup/mainloop_*.mcd` has an in-game save (album 1,
    Sunday night 95/4/23). Copy it over the card in
    `.emu/duckstation/memcards/`, after backing up whatever is there.
  - `.emu/savestates_backup/mainloop_sunday_0423.sav` is a save state at the
    same point. It's from an older build, so its VRAM and graphics are stale.
- The game can only save on the **Sunday-night planning screen**, via the
  lit memory-card icon at the bottom right of the command grid.

## Earlier roadmap / background

The numbered sections below describe the previous main-loop work and wider
backlog. Follow the active character plan above for the next milestone.

## Step 0: make the command grid drivable (earlier testing prerequisite)

The review fixed hidden-window detection and stale-screenshot handling in
`drive.ps1`. The backed-up 95/4/23 card uses discrete list-order navigation:
`Down:300` advances one command, `Up:300` reverses. The exact Menu Mode value
is not yet mapped. Other saves/modes may still require calibration; see
`docs/testing.md` before assuming the hand is free-moving.

- Try switching **Options ▸ Menu Mode** to *Menu A*. Its description says the
  D-pad moves the cursor to the item in that direction. The setting is
  stored in the system file / album, so set it, then make a fresh Sunday-night
  save and back up the card.
- If that doesn't help, write the hand's position or the selected item in RAM
  via the GDB stub (find it by diffing RAM dumps as the hand moves).
- Document whatever works in `docs/testing.md` ("The main game loop").

## Step 1: finish the main loop's EXE text (implemented; visual verification remains)

The player-facing candidates in the EXE's system-text block (`SLPM_86.053`
0x6EB40–0x76000) are now covered by `main_events.json`, `clubs.json`,
`outings.json`, `town_news.json` and `character_names.json`. Ordinary strings
remain in place; pointer-backed contiguous tables use pooled `dialogue` blocks
with base `0x80040800`. The exclusions and reasons are recorded in each JSON
description and in game-internals §6h.

Original inventory, now covered or deliberately excluded by area:

| Around | Contents |
|---|---|
| 0x6E800 | album-creation leftovers (ときめき, アルバ, ム作成, 後未セーブ) |
| 0x6F000 | 詩織 / ちゃん / さん, ときめきメモリアル・システム, debug labels |
| 0x70000 | club joined (部に入部した。), 部長, club-day notice, home, rumour and party prompts, New Year, doorbell |
| 0x70800 | club list (部活一覧), "choose a club to join", term/holiday prompts (明日から夏休みだ）…), injury, burnout (ノイローゼ) |
| 0x71800 | sound effects (ガチャ, ドン, ピンポーン), **speaker names 藤崎 / 好雄 (see Step 2)**, やめる |
| 0x72800 | stat names (文系 理系 …, used somewhere other than the panel), **outing places** (きらめき中央公園, 水族館, …) |
| 0x73000 | **club names** (演劇 科学 … テニス 水泳 バスケ, 無所属) |
| 0x75000 | memory-card check message, concert listings (ＫＮＭ交響楽団, performer names) |
| 0x75800 | **town-news headlines** (中央公園で桜が満開, 遊園地に絶叫マシン完成, …) |

List them with offsets and slot sizes like this:

```python
import sys; sys.path.insert(0, ".")
from tokipatch import script
exe = open("extracted/SLPM_86.053", "rb").read()
p = 0x6EB40
while p < 0x76000:
    if exe[p] == 0: p += 1; continue
    e = exe.index(b"\0", p); raw = exe[p:e]
    slot = e + 1
    while slot % 4 and exe[slot] == 0: slot += 1
    try: print(hex(p), slot - p, script.decode(raw).replace("\n", "\\n"))
    except ValueError: pass
    p = e + 1
```

Validation notes and decisions:
- **Inserted words.** Place and club names (and girls' names, Step 2) are
  inserted into other lines by name codes (`{S}`, `{O}`, …; game-internals
  §6e). Check one insertion end to end, e.g.
  the meeting prompt "Well then," / "<place> it is" (0x70ECC/0x70ED8 + place).
  Confirm that a pair-encoded English name inserts correctly. A display line
  must stay under 64 bytes after expansion (the renderer `strncpy`s into a
  64-byte buffer). If the inserted words' maximum widths change, update
  `script.TOKEN_CELLS`.
- **Leave alone:**
  - debug labels (平日コマンド画面, 休日コマンド画面, ダミー)
  - single odd kanji (慰 釀 榜 at 0x75000, probably not text)
  - anything `script.decode` rejects.
- **Already drafted:**
  - `translation/album_panel_exe.json` is the Save/Load slot panel
    (名前…, あだ名…, 所属部‥, クリア人数‥). The user has verified populated
    Load slots, including number/date pieces and None/Soccer club values.
    Save-mode and empty/error/System branches remain unverified. It is now
    included in normal builds following the user's testing and request.
  - `translation/system_settings.json` (114 strings) is the in-game
    system settings screen. The user reports all submenus visually verified
    as translated; main-list/Text Speed screenshots support the report.
    Individual confirmations and conditional paths were not itemized. It is
    now included in normal builds following the user's testing and request.
- The user liked the label style ("Health", "Lit.", "Sci.", …). Keep the
  wording consistent with `main_screen.json` and the stat panel.
- Put each screen or feature in its own JSON (e.g. `outings.json`,
  `clubs.json`, `town_news.json`), or extend `main_screen.json` for prompts.

Done when every string in the block is translated or deliberately skipped
(note why in the JSON `description`), each screen has been seen in the
emulator, and `AGENTS.md`'s verification table says what was checked.

## Step 2: speaker labels and character names (implemented; breadth/width checks remain)

Normal speaker labels are built by EXE function `0x80051438`: Shiori is read
from `0x800AFB7C`; other characters use the 16-entry short-name pointer table
at `0x800B35F4`, then append `ちゃん` or `さん`. The full-name table begins at
file offset `0x72D3C`; the short-name table begins at `0x72DF4`. Special
Shiori/Yoshio paths and the fixed `{Y}` values use separate literals around
file offsets `0x71980`–`0x71A50`. All are translated by
`character_names.json`; see game-internals §6e for exact ranges and method.

The user has confirmed translated character names during normal play. Still
check each special speaker path and the longest names at the dialogue-box
edge; the existing confirmation does not prove every path or width.

Implementation and remaining checks:

1. Static disassembly established the normal label builder and the separate
   special literals. Dynamic read-watchpoint confirmation was not obtained:
   the automated run failed to leave name entry because tracing changed the
   free cursor's travel. See `docs/testing.md` for the timing caveat.
2. The full-name pool uses 171/172 bytes after translation; abbreviations are
   required unless relocation support is added. The short-name pool uses
   100/124 bytes.
3. Keep watching for these constraints:
   - The **cheat-name list** in `NAME_ENT.EXN` (0x19590–) and the default
     names 藤崎 / 詩織 (0x1956C / 0x19574) are compared with what the player
     types. Don't change those unless you know what reads them.
   - Names stored in RAM or in save data may be copied once (at new game).
     Check that old saves still show sensible names, or document that they
     don't.
   - Label width: labels sit before the bracket, and the dialogue line width
     (`script.MAX_CELLS` = 28) was measured after a two-character label.
     Recheck the right edge with a longer English label.
   - Name insertion width (`script.TOKEN_CELLS`) changes if names become
     English.
4. `script.TOKEN_CELLS` was raised conservatively for the longer translated
   insertions. Recheck lines containing `{G}`, `{Y}`, `{S}`, `{O}`, `{W}`,
   `{A}` and `{M}` when their actual consumers are reached.

## Step 3: dialogue, starting with a pilot to measure space

The bulk of the game, by dialogue folder:

| Folder | Strings | Bytes (Japanese) |
|---|---|---|
| `SERIFU/` | 16,727 | 652 KB |
| `BUNKA/` | 12,898 | 454 KB |
| `SPEAKTST/` | 16,340 | 629 KB |

Counts from `dump_dialogue.py` after the 2026-10-07 fix (pointer targets
only; strings with unknown control bytes are excluded). Load addresses
for each file are in game-internals §6e; only the prologue is verified in
the game.

- **Choose by frequency, not total file size.** The local inventory has
  eleven `SERIFU/DATE_*` files, not eight. Physical file sizes include tables
  and other data, so do not confuse them with decoded text or repack capacity.
  The active plan prioritizes one mapped date/event pack; larger camp/shared
  pools remain later work.
- **Pilot one `DATE_*` file first** to measure space. The English must fit
  in the Japanese bytes of the strings it replaces; the prologue fit with 16
  bytes to spare (game-internals §6e, "Budgets"). If a date file doesn't fit,
  file growth (README roadmap 3: LBA tables, relocation) becomes the blocker
  and needs designing before bulk translation.
- Workflow: `python tools/dump_dialogue.py extracted/CDROM/SERIFU/DATE_xx.BIN -o extracted/dumps/DATE_xx.json`,
  then translate into a `dialogue` block (the original's line breaks and name
  codes are enforced). **Never commit the dumps** (AGENTS.md rule 9). Confirm
  the file's load address in the game (`tools/emu/trace_reads.py`), and play
  through the scene to catch line-timed events (game-internals §6e, Rei's
  hang).
- **Identify `SPEAKTST/`.** It's the biggest folder and nobody knows when it
  loads. Run `trace_reads.py` while calling a girl on the phone, meeting her
  in the hallway, and so on. If it's the phone or random-conversation pool,
  it's the most-read text in the game. Some of its strings contain `<`, `>`,
  `-`, `n` bytes that aren't known control codes; find out what reads them
  before translating.
- **Possible shortcut:** [XEUPIU](https://github.com/vgarciasc/xeupiu), an
  overlay translator for this same release, has a CSV of English lines. Check
  its license and how its lines map to strings before using any of it.

## Step 4: graphics seen every session (lower priority)

- **Album (save slot) screen after GAME START:** the パラメータ panel (stat
  names), 名前 / あだ名 / 所属部 / クリア人数, the コピー/ニュー/クリア/ロード
  buttons, システム 有/無. These are graphics (game-internals §6d). Find the
  file with `trace_reads.py` (likely `FUKUTEST/FILESEL.NBN`) and the layout
  by logging uploads (`watch_exec.py 80 0x8004435c --stack 6`, testing.md).
- **Remaining `MAINROM.NBN` art:** girl-info labels (chunk 1), town-news
  banners (chunks 2, 7), date-spot art (chunk 11).
- **Title logo** (`TITLE.NBN`).
- Tools: `images` entries support 4bpp now (`"bpp": 4`). Sprite frames can be
  repointed with `bytes` patches when a cell is shared (translation-guide,
  "Sprite cells shared by two meanings"). Follow `tools/make_main_screen.py`:
  generate the PNGs, print `original_crc32`, and keep the art reproducible.
- Graphics are uploaded once at boot. A save state shows the old art, so test
  with a real boot and the save card.

## Every change, every time

Follow the `AGENTS.md` checklist:
- Build to a scratch folder and check that only the expected sectors and
  files changed.
- **Boot it and look at every changed screen**, compared with the unpatched
  game.
- Play a little past the changed screen.
- Write new findings (addresses, how they were found) into `docs/` in the same
  change.
- Update the verification table.
