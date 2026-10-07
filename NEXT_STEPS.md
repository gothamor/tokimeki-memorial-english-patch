# Next steps (temporary handoff plan)

Temporary planning note for the next agent. Delete it (or fold what's still
useful into `docs/`) once the work is done.

**Recommendation: finish the on-screen checks for Steps 1 and 2 first.** Their
patches now build and the names have had an initial user smoke test, but the
remaining main-loop consumers and longest speaker labels have not all been
seen. Step 3 (dialogue) is the bulk of the game, but its own pilot should come
first to measure space. Step 4 (graphics) matters less.

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
- Steps 1 and 2 now have implementations in the working tree. They are not
  committed, and most of the new main-loop screens still need visual checks.
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

## Step 0: make the command grid drivable (prerequisite for testing 1 and 2)

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
  - `translation/extra/album_panel_exe.json` is the Save/Load slot panel
    (名前…, あだ名…, 所属部‥, クリア人数‥). Check the English on screen, then
    move it into `translation/`. It also has the panel's 番/年/月/日 pieces;
    the date there (９５年４月４日) needs a look.
  - `translation/extra/system_settings.json` (114 strings) is the in-game
    system settings screen. Reach it from the main loop, verify, then move it
    in.
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
| `SERIFU/` | 9,530 | 358 KB |
| `BUNKA/` | 9,083 | 331 KB |
| `SPEAKTST/` | 16,145 | 627 KB |

Strings are found by a scan, so the counts are approximate. Load addresses
for each file are in game-internals §6e; only the prologue is verified in
the game.

- **Choose by frequency, not size.** GASSHUKU (50 KB) is summer camp, once a
  year. The eight `SERIFU/DATE_*` files (about 8–9 KB each, one per girl) and
  `G_APPEAR` (about 11 KB) come up constantly.
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
