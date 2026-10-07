# Testing a patch in an emulator

A patch that builds cleanly can still break the game. The first build passed
every static check (strings matched, EDC/ECC valid, one sector changed) and
still hung, because of the file checksum. **Always boot the result.**

The tools in `tools/emu/` drive DuckStation on Windows without touching the
user's own install, settings, memory cards or focused window.

## One-time setup

```bash
python tools/emu/setup_duckstation.py --bios "D:\Emulation\PS1 BIOS"
```

This copies the installed DuckStation (default
`%LOCALAPPDATA%\Programs\DuckStation`, override with `--source`) to
`.emu/duckstation/` as a **portable** install (`portable.txt`), so all its data
stays in that folder. It seeds settings from the user's `settings.ini` and
then sets:
- keyboard controls: arrows, `C`=Circle (**confirm**), `X`=Cross (**back**),
  `Z`=Square, `S`=Triangle,
  `Enter`=Start, `Backspace`=Select
- GDB stub on port 2345
- no power-off confirmation, no save state on exit
- RetroAchievements **off**. The user's `[Cheevos]` section is not copied, so
  their login token never ends up in `.emu/`. With achievements on, a login
  prompt appears every boot, and hardcore mode disables save states.
- **Memory cards in `.emu/duckstation/memcards`.** Portable mode does *not*
  redirect absolute paths inherited from the user's settings. An early harness
  version kept the user's `[MemoryCards] Directory` (`G:\Emulation\PS1_MEM`),
  and a test run created an album + system file on the user's real
  Tokimeki card. After setup, check that the only absolute path left in
  `settings.ini` is the BIOS folder.

Hotkeys inherited from DuckStation defaults: `F10` screenshot, `F2` save
state, `F1` load state.

The current dev box only has a PAL BIOS (SCPH-1002) and the unpatched game
runs fine with it, so BIOS region isn't a factor in the bugs seen so far.

## Build, boot, look

```bash
python -m tokipatch "<game>.cue" -o .emu/build --force
```

```powershell
Start-Process .emu\duckstation\duckstation-qt-x64-ReleaseLTCG.exe -ArgumentList '-batch','-fastboot','".emu\build\<game>.cue"'
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\emu\drive.ps1 -Seq "wait:26000,Return,until:title:60000,shot:title,Down,wait:500,shot:options_highlighted"
```

Screenshots land in `.emu/shots/<name>.png`.

`drive.ps1` steps: `KEY[:holdms]`, `wait:ms`, `shot:name`, `until:screen:ms`.
Keys go to the emulator window with `PostMessage`, so the window doesn't need
focus and no other window ever receives input.

The driver also accepts a hidden game window and matches its title (including
the Japanese title's `forever with you` suffix). It stops if no matching window
exists. Screenshots must be newly created after F10; a timeout is an error,
not permission to reuse the previous file. These checks fixed a test run that
previously continued after null-window input errors and falsely reported a
screen match from a stale screenshot. Launch an isolated test with
`Start-Process -WindowStyle Hidden` and wait for the game window to exist.

### Getting to screens reliably
- **Don't rely on fixed delays.** Boot time varies between runs, so a sequence
  that hit the title once lands in the attract movie the next time.
- **Use `until:<screen>:<ms>`.** It screenshots in a loop until
  `tools/emu/screens.py` recognises the screen (currently `title`: mostly white
  plus the pink logo), then continues immediately. Add detectors to
  `screens.py` for other screens you need to reach.
- **Do the whole interaction in one `drive.ps1` call.** Each launch of
  `drive.ps1` costs ~3 s (PowerShell start + `Add-Type` compile). Detecting the
  title in one call and pressing keys in the next was slow enough for the
  title to time out (~10 s idle) back into the attract loop.
- **Timing reference (DuckStation, fast boot):** the opening movie is playing
  ~25 s after launch. `Start` skips to a white fade, then the title.
- **Always compare with the unpatched game** at the same point before blaming
  the patch.

### Save states
- **`F2` saves** to `savestates/SLPM-86053_1.sav`. **`F1` (hotkey load) doesn't
  work** through the driver (black screen, then the attract movie). Not
  investigated.
- **Loading at launch works:** pass `-statefile` on the command line.
  ```powershell
  Start-Process .emu\duckstation\duckstation-qt-x64-ReleaseLTCG.exe -ArgumentList '-batch','-statefile','"<abs path>\SLPM-86053_1.sav"','"<abs path>\game.cue"'
  ```
  Wait ~8 s before driving it.
- A state holds RAM, so files already loaded (e.g. the `NAME_ENT.EXN`
  overlay, the EXE's font) are whatever build made the state. To test new
  text without replaying, **poke it in** with `tools/emu/poke_file.py`:
  ```bash
  python tools/emu/poke_file.py .emu/b2/NAME_ENT.EXN 0x80132000 0x1B1D0 0x1BA04   # prologue strings + pointer table
  python tools/emu/poke_file.py .emu/b2/SLPM_86.053 0x80040800 0x3C3C 0x3F00    # renderer hook code + scratch
  python tools/emu/poke_file.py .emu/b2/SLPM_86.053 0x80040800 0xAF78 0xB32C    # hook's 5x12 font
  python tools/emu/poke_file.py .emu/b2/SLPM_86.053 0x80040800 0xEACC 0xEAD4    # jump into the hook
  ```
  A state made with a build that already has the renderer hook only needs
  the text poked; the hook code doesn't change with the translation. Poking
  the hook itself into a state from an older build is **untested** (the
  emulator's recompiler may keep stale code), so prefer a state from a hook
  build. If you do poke it, write the jump last, as above.
  (read the patched files out of a build with `Track.read_file`). Poking the
  *original* bytes instead gives an exact unpatched comparison at the same
  point; that's how the Rei hang was pinned on the translation.
  Always finish with one real boot of the build.
- The patcher can't overwrite a build the emulator has open. Build into a
  second folder (`-o .emu/build2`).

### New-game flow (album screen → name entry)
On a blank test card (`rm -rf .emu/duckstation/memcards/*` first):

```
Return,until:title:60000,C,wait:18000,            # GAME START → "no save data" prompt
C,wait:3000,                                       # Yes → "Which album?"
Down,wait:300,Left:1500,wait:300,Up:900,wait:300,  # steer the free hand cursor...
Down:290,wait:300,Right:80,wait:600,               # ...onto album slot 1
C,wait:2500,C,wait:2500,                           # pick slot 1, system-file explanation
C,wait:9000                                        # "Make a system file?" Yes → name entry
```
At normal emulator speed, the hand moved at roughly 0.8 screenshot px per ms
of key hold (≈ 4.8 per game px) in one calibration. On the initial family-name
screen, `Right:150` selected み and `Down:540` reached the Exit button; a
screenshot after the move and another after `C` confirmed that the next name
field opened. Treat these as starting values, not fixed coordinates.

Directional holds are timed in host wall-clock milliseconds, while cursor
movement advances in emulated frames. GDB read/watch/execution breakpoints
slow the emulator enough that the same hold covers fewer game frames and
therefore **undershoots**. Navigate and verify the cursor at normal speed
before arming a watchpoint whenever possible. If the watchpoint must already
be armed, recalibrate the hold under that exact tracing load; adding only a
longer `wait:` after the hold does not recover the missed movement.

With an album already on the test card, GAME START opens the album screen
in Load mode with the hand on slot 1. Pressing `C` twice loads it; an album
whose name was never finished goes straight back to name entry. From name
entry: `Down:180,Left:130,C` opens the 記号 page. Then `Right:1450,Right:110`
puts the hand on the ▼ scroll arrow; each `C` scrolls one row-block.

### Reaching the prologue (dialogue)
From name entry (hand on the かな page), type one kana in each name field and
accept the default birthdays. This worked from boot, as one `drive.ps1` call:

```
$name = "Up:540,wait:200,Right:230,wait:300,C,wait:600,Down:540,wait:200,Left:230,wait:300,C,wait:1500"
wait:22000,Return,until:title:60000,C,wait:16000,C,wait:2500,C,wait:9000,  # title → album 1 → name entry
Right:130,wait:300,C,wait:800,Down:540,wait:200,Left:230,wait:300,C,wait:1500,  # family name, 終了
$name,$name,wait:500,                                                       # given name, nickname
C,wait:1500,C,wait:1500,C,wait:3500,                                        # birthday/blood: 終了 ×3
Right:640,wait:300,C,wait:8000,                                             # "Is this OK?" → はい (save a state here: F2)
Left:700,wait:300,C,wait:1500,C,wait:1500,C,wait:3500,                      # Shiori's birthday: 終了 ×3
Right:670,wait:300,C,wait:12000                                             # はい → prologue starts
```
Then `C,wait:4500,shot:...` per line. Text types out letter by letter and
voiced lines also advance by themselves, so a shot can catch a line
half-typed or skip one; that's normal. To review many lines, crop the text
box (screenshot y 700–1000) from each shot into one contact sheet.

**Keep your hands off the emulator during a scripted run.** Input from the
user mid-run (they were also playing) made one comparison misleading.

### The main game loop (weekly command screen)
- **Making an in-game save:** saving is only possible on the **Sunday-night
  planning screen** ((明日から何をしようかな？) with the night view). The
  memory-card icon at the bottom right of the command grid is then lit
  instead of grey; select it → セーブ → slot → ○ to overwrite. (Told by the
  user; done once.) After that, a boot with that card goes title → GAME START
  → `C,wait:3000,C` straight to the main screen, about a minute.
- `.emu/memcard_backup/mainloop_*.mcd` is a card with such a save (album 1,
  95/4/23). Copy it over the card in `.emu/duckstation/memcards/` to use it;
  back up whatever is there first.
- From the planning screen, `C` on the first icon (study) runs a week and
  lands on the next Sunday, either the holiday screen (今日は…) or, after a
  day off, the planning screen again.
- **Check the loaded save's menu behavior before calibrating.** In the review
  run using the backed-up 95/4/23 card, `Down:300` advanced one item in list
  order (book → science → art → fitness → school icon), even across a row;
  `Up:300` reversed it. This is discrete selection, not free cursor movement.
  The exact saved Menu Mode value has not been traced. Don't interpret every
  sideways move as a timing error, or reuse name-entry free-hand timings here.
  Take screenshots after moves; short holds and behavior in other modes still
  need calibration.
- **Graphics live in VRAM from boot.** `MAINROM.NBN` is uploaded once at boot,
  so a save state shows the art of the build that made it. Test graphics
  changes with a real boot and the save card.

### Controls: ○ confirms, × goes back
This is a Japanese game: **○ (Circle, key `C`) confirms and × (Cross, key `X`)
cancels/goes back.** Use `C` to select menu items and advance text. Early test
runs pressed `X` to "confirm", which explains some of the confusing results
(e.g. landing back in the attract loop). Treat any old note that says `X`
selected something as unverified.

### What failure looks like
- **Hang on a white or black screen during a transition:** almost certainly a
  file checksum mismatch. The loader retries forever (game-internals §3/§4).
  Confirm with the GDB stub: loader state `*(u8*)0x800B6D34 == 1` and LBA at
  `0x800B6D40` stuck on the patched file.
- **Garbage or missing glyphs:** wrong encoding, or a character the font
  doesn't have.
- **A dialogue line that never advances** (text fully shown, ○ does nothing,
  no CD error): the scene is waiting for a display line that doesn't exist,
  because the translation has fewer lines than the Japanese (game-internals
  §6e). The patcher now rejects this. To diagnose another case, set GDB
  breakpoints on the scene's *run line* routine to see whether it's still
  called, and compare `0x8004ECF0`'s result with what the scene step waits
  for.

## Debugging with the GDB stub

`tools/emu/gdbstub.py` is a minimal client. **Connecting halts the emulator**;
call `detach()` to resume it.

```python
import sys; sys.path.insert(0, "tools/emu")
from gdbstub import Gdb
g = Gdb()
print(hex(g.regs()["pc"]))
print(g.mem(0x800B6D34, 1).hex())          # overlay loader state
open(".emu/ram.bin", "wb").write(g.mem(0x80000000, 0x200000))
g.detach()
```

Register replies contain `xxxxxxxx` for unavailable registers; they're read as 0.

### Which files does the game load?

```bash
python tools/emu/trace_reads.py "<game>.cue" 60
```

This breaks on the CD read routine `0x80046318` and prints LBA, sector count,
buffer and the matching disc file for each read. The game runs slower while
traced. Run it in the background and drive the game with `drive.ps1` at the
same time.

### Which code reads a string? (read watchpoints)

```bash
python tools/emu/watch_reads.py 0x8013C880 60 --skip 0x8004636C-0x800463E8
```

This arms a GDB read watchpoint (`Z3`) on an address and logs pc/ra/args for
each read while the game keeps running. Drive the game with `drive.ps1` in
parallel. Tips:
- **Arm it before the screen opens.** Menu text is laid out once when a screen
  opens, so a watchpoint set while the screen is already showing never fires.
  Go back to the previous screen, arm, then re-enter.
- RAM address of a string in an overlay = `0x80132000 + file offset`. In the
  EXE it's `0x80040800 + file offset`.
- `--skip` the checksum loop (`0x8004636C`–`0x800463E8`), which reads every
  byte of a freshly loaded overlay.
- This is how the text renderer was found: the first hit was `add_text`
  (`0x8004E788`), the second `layout_string` (`0x8004F268`).

### Does this code ever run? (execution breakpoints)

```bash
python tools/emu/watch_exec.py 900 0x8004443C 0x8004B778
```

This sets execution breakpoints and logs every hit (pc, ra, a0–a3) while
the game keeps running. `--stack N` also prints N stack words (arguments 5+),
`--max N` stops after N hits. `watch_exec.py 80 0x8004435c --stack 6 --max 120`
during a boot logs every VRAM upload (x, y, w, h, source address): that's how
`MAINROM.NBN`'s chunk layout was found. Drive the game in parallel. It's how the two EXE
functions the renderer hook reuses were shown to be unused (game-internals
§6f): run it on the **unpatched** game and play through as much as you can.
- The emulator runs noticeably slower while breakpoints are armed (a page
  fade took ~10 s instead of ~4 s), so give `drive.ps1` steps longer waits.
  Free-moving cursors also travel less during a fixed directional hold; see
  the calibration warning under "New-game flow" above.
- The Options page and the in-game command grid use the free-moving hand
  (Mouse-like menu mode), so a short `Down` doesn't step one item. `X` on the
  Options page jumps the hand to オプション終了; `C` there returns to the title.
- Pressing `C` repeatedly on the first in-game screen picks the first command
  (study) each week and advances the calendar. It reached a SERIFU event
  (meeting 如月) after ~30 presses, a handy way to exercise dialogue files.

### Which girl events happen? (event watcher)

```bash
python tools/emu/watch_events.py 420 --states > .emu/events.log
```

Breaks where the main loop starts a girl's scene from the daily event queue
and logs the date, record (type, girl, scene) and the queue (game-internals
§6j). `--states` also logs every main-loop state change. Drive the game in
parallel, e.g. `C,wait:2500` repeated to study through the weeks.

First run (2026-10-07, **unpatched** original, 95/4/23 test card, 45 presses
of `C`, about 2 minutes): reached 95/5/17. Two meeting events (type `0x48`,
girl 1 on 5/10 and girl 8 on 5/17), no Shiori special event. Replay
assets from that run:
- `.emu/savestates_backup/shiori_0423_unpatched.sav`: unpatched, 95/4/23
  Sunday night, hand on Study. Only for unpatched comparisons; it holds the
  original EXE and text.
- `.emu/memcard_backup/pre_shiori_<timestamp>_*.mcd`: the harness card from
  before this run (it had the user's 95/4/9 and 95/4/16 saves). The
  95/4/23 test card is installed in its place.

The unpatched original is in the repo folder
`Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best)/`
(gitignored; checked byte-identical to `extracted/` for the EXE, GEKO.EXN and
EVENT_FU.BIN).

### Forcing a girl event (Shiori's morning walk)

Rare special events can be forced on a test card, with the user's agreement
(given 2026-10-07 for Shiori's walk). Do the same forcing on the unpatched
game for the comparison. Recipe, about one minute:

```powershell
Start-Process -WindowStyle Hidden .emu\duckstation\duckstation-qt-x64-ReleaseLTCG.exe -ArgumentList '-batch','-statefile','"<abs>\.emu\savestates_backup\shiori_0423_unpatched.sav"','"<abs>\<game>.cue"'
```

Wait ~9 s, then start the forcer and choose Study:

```bash
python tools/emu/force_event.py 0 2 --clear-flag 0x800E67ED --timeout 120
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\emu\drive.ps1 -Seq "C,wait:4000,shot:walk_01,wait:3000,shot:walk_02,wait:3000,shot:walk_03,C,wait:2500,shot:walk_04,wait:2500,shot:walk_05,C,wait:2500,shot:walk_06,C,wait:2500,shot:walk_07,C,wait:2500,shot:walk_08"
```

The forcer prints `forced 45 00 02 00 at 0x800e6924` (Tuesday 95/4/25). The
first line appears about 10 s after `C`; each later `C` advances one box
(4 boxes, game-internals §6j), and the week then continues to the weekend
command screen. Done twice on the unpatched game, once with
`trace_reads.py` chained after the forcer (`EVENT_FU.BIN` → `0x80198000`).

**English test (2026-10-07).** Candidate `.emu/review_shiori/` (15 default
files plus the draft; log `.emu/review_shiori.log`): only LBAs 44581 and
44586 (EVENT_FU's first and last sectors) differ from the default build,
with valid EDC/ECC and headers; the file keeps its size and checksum; all
five pointers resolve to their English. Real boot, card save loaded, walk
forced on 95/4/25, every box screenshotted (`.emu/shots/q_*.png`) and
compared with the unpatched run (`f_*.png`). The first attempt showed the
thought lines' `)` doubled, because these strings don't contain `）`; fixed,
rebuilt, retested: all four boxes correct, Shiori's label and her 3-line box
fit, and the game returns to the day command screen as in the unpatched run.
After promotion, the normal build (no `-t`, `.emu/default_shiori/`) is
byte-identical to the tested candidate. Not tested: the natural trigger
(needs mid-game affection), other names in `{P}`.

**Rain and phone call (2026-10-07).** Same recipe with `force_event.py 0 1
--clear-flag 0x800E67EC` (rain) and `force_event.py 0 8` (phone call; no
flag needed). Forcers can be chained in one week:
`force 0 1 && force 0 8 && force 0 2 --clear-flag 0x800E67ED` puts the three
scenes on Tuesday, Wednesday and Thursday. Unpatched references:
`.emu/shots/r_*.png` (rain), `h_*.png` (phone). Candidate
`.emu/review_shiori2/` (15 defaults minus the promoted `shiori_events.json`,
plus the revised draft): only EVENT_FU's sectors 44581, 44585, 44586 differ
from the default build, EDC/ECC and headers valid, checksum valid, all 68
strings' pointers resolve, and no byte outside the string slots and their
pointers changed. First on-screen pass showed "happy. )": two thought lines
ended in an odd-length run, padded with a space before the game's bracket;
fixed to even lengths, rebuilt, retested. Every box of the three scenes was
then seen (`ex_*`, plus `fz_*`/`fw_*` for two boxes whose screenshots had
caught them mid-typing). Screenshots need at least ~1.5 s between them;
0.7 s makes `drive.ps1` fail. Promoted; the normal build
`.emu/default_shiori2/` is byte-identical to the candidate.

### Forcing a date with Shiori, and her date events

On the Sunday-night screen of the 95/4/23 test save (state or card save):

```bash
python tools/emu/force_date.py 0 PLACE 4 30 [--scene N] --timeout 400
```

then drive `C,wait:12000,C,wait:12000,C,wait:7000` (Study for the week,
Study on the 4/29 holiday, then the heart icon on 4/30 starts the date) and
step through with `C,wait:2800`. Places are 1-based outing ids (1 Kirameki
Park, 12 Theme Park, 16 Pool), 0 is the neighborhood park. `--scene` jumps to
Shiori's date event when the date reaches its step: 3 (place 0), 4 (place 1;
also happens by itself), 5 (place 12), 6 (place 16). One date per boot; the
event appears about 15–20 presses in, and the date ends back home.

### Forcing the walk home after the Christmas party

```bash
python tools/emu/force_christmas.py --timeout 400
```

Start it on Sunday night and choose Study; at the next weekday it switches to
the Christmas-party flow at Shiori's stage. It can follow a
`force_event.py` chain (it waits for the next weekday). Leftover weekday
graphics show behind the scene.

**All of EVENT_FU (2026-10-07).** Unpatched references: `d3_*`, `dg_*`
(park), `tp_*` (theme park), `d6_*` (pool), `ny_*` (Christmas). Candidate
`.emu/review_shiori3/`: only EVENT_FU's six sectors differ from the default
build, EDC/ECC and headers valid, checksum valid, all 157 strings' pointers
resolve, nothing else in the file changed. Real boots of the candidate:
boot 1 chained rain (4/25), phone (4/26), walk (4/27) and Christmas (4/28),
`p1_*`; boots 2–5 one date event each, `p3_* p4_* p5_* p6_*`. Every box was
English and fit; first lines of 4-/5-line strings scroll away before a
screenshot. Promoted; the normal build `.emu/default_shiori3/` is
byte-identical to the candidate.

Card note: the harness card's frame 63 of block 0 (`0x1F80`, the memory
card write-test frame) changes during these runs; no save data changes.

**For a patched build** the save state can't be used: it holds the original
EXE and text. Boot the patched CUE, load the 95/4/23 card save
(title → GAME START → `C,wait:3000,C`), then run the forcer and the same
drive sequence. The forcer only writes RAM; nothing is saved unless you save
in the game, and a forced run must not be saved over the test card.

### Testing date conversations (`DATE_FU.BIN`, 2026-10-07)

**A save state reopens the disc it was made with**, whatever CUE is passed
on the command line. A state made from `.emu/review_dates/` always reads
`.emu/review_dates/`, so rebuild candidates **into that same folder** (with
the emulator closed) and keep reusing the state. Building to a second folder
and passing its CUE silently tests the old text. The EXE in the state must
come from a build with the renderer hook; DATE files are read from disc when
the date starts, so they always come from the state's disc.

Recipe used for the museum pilot:
1. Boot the candidate from `.emu/review_dates/`, load the 95/4/23 card save
   (`wait:22000,Return,until:title:60000,C,wait:16000,C,wait:3000,C,wait:20000`),
   then `F2` on the Sunday screen. Backed up as
   `.emu/savestates_backup/dates_sunday_0423_candidate.sav`.
2. Per run: launch that state (`-batch -statefile`), wait ~9 s, start
   `python tools/emu/force_date.py 0 7 4 30 --set-at 0x80134F74 0x800CA2FC N`
   (museum, exhibition N = 0–5; game-internals §6k), then drive
   `C,wait:12000,C,wait:12000,C,wait:7000` and `C,wait:3200` per box. The
   meeting before the place is random (4–8 boxes), so screenshot each box.
3. On the choice screen press `F2` and copy the state; relaunch it and press
   `C`, `Down,C` or `Down,Down,C` to see each reply. The options' screen
   order is shuffled per date but fixed in the state; the reply follows the
   option, not its position.
4. Variant 5's other lines: raising Shiori's affection in RAM (s16 at
   `0x800E6442`, 48 → 200) on the Sunday state gave `0x688`; `0x660` was
   shown by writing master entry 16's value over entry 18
   (`0x80198718` ← `*(u32*)0x80198710`) once DATE_FU was loaded.

`watch_reads.py` on DATE_FU's master entries is swamped by an unrelated
reader (`pc 0x80082B3C`) before the file loads; prefer static tracing.

**Tools (2026-10-07).** All run from the repo root with `powershell.exe`
(5.1) and the isolated emulator; they change RAM only.
- `tools/emu/launch_state.ps1 -State X.sav [-Build review_dates|orig]`:
  restart the emulator (visible) from a state.
- `tools/emu/date_run.ps1 -Place P [-Version N] [-Presses K] [-Prefix name]
  [-Break "rules"]`: launch the Sunday state, force a 4/30 date at place P
  (and version N), drive into it and screenshot K boxes; contact sheet in
  `.emu/shots/<prefix>_sheet.png`, forcer log in `.emu/date_run.log` (the
  forcer runs detached so late rules still fire).
- `tools/emu/date_choices.ps1 -Prefix name [-Pre keys]`: from just before a
  choice, save a state there and try every option (sheet
  `<prefix>_choices.png`, state `.emu/savestates_backup/<prefix>_choice.sav`).
- `tools/emu/break_set.py --at PC [--times N] [--reg R=V] [--mem8 A=V]
  [--mem16 A=V] [--sp16 OFF=V] [--pc NEWPC] ...`: breakpoint rules, also
  accepted by `force_date.py` after `--`. Rules used (game-internals §6k):
  meeting `--at 0x80132570 --reg v0=RANK --mem8 0x8015B654=ARRIVAL`
  (RANK 0/2/3 → mood 0/1/2), run-away meeting `--at 0x80132570 --mem16
  0x800E6396=10`, small talk `--at 0x8013B0D4 --mem16 0x8015BF0C=N --pc
  0x8013B0E4`, ending `--at 0x8013B6F8 --times 0 --sp16 0x3a=N` (the value
  is recomputed every frame, so rewrite it at every hit), going home
  `--at 0x8013B810 --mem16 0x8015BF14=BAND`, park (place 0) talk
  `--at 0x8013A8B0 --reg v0=RANK`, museum "seen before" line
  `--at 0x801392F0 --reg v0=RANK` (with `--version 5`).
- `tools/emu/contact_sheet.py OUT NAME...`: stack screenshots' text boxes.
- `tools/date_sections.py`: the section/place checklist and forcing
  addresses; `tools/dialogue_budget.py FILE.json [--all] [--range A B]`:
  per-string space (own slot, gap, English) and a dry-run pack.

Example, every shared selector in one unpatched-section date (checked on
screen: meeting part 4–5, small talk part 0, ending part 9, going home
band 1):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\emu\date_run.ps1 -Place 7 -Version 0 -Presses 20 -Prefix sh2 -Break "--at 0x80132570 --reg v0=3 --mem8 0x8015B654=0 --at 0x8013B0D4 --mem16 0x8015BF0C=0 --pc 0x8013B0E4 --at 0x8013B6F8 --times 0 --sp16 0x3a=9 --at 0x8013B810 --mem16 0x8015BF14=1"
```

`--version` was also checked on Kirameki Park (version 2: the cherry-blossom
lines; afterwards Shiori's spring park event from EVENT_FU starts by itself
on 4/30) and the Stadium (version 3: wrestling). Also seen: a place-0
(neighborhood park) date with its hobby choice and note, the Shrine's yukata
choice with both options (the `{n}` empty option), and museum version 5
with `v0 = 0` at `0x801392F0` (line `0x660`). A forcer left waiting on a
rule keeps the GDB connection; `launch_state.ps1` restarting the emulator
ends it.

**Museum pilot results.** Unpatched reference `mu_*` (exhibition 0, the top
option chosen). Candidate `.emu/review_dates/` (16 default files plus the
draft): only DATE_FU's first and last sectors (LBA 44329, 44351) differ from
the default build; checksum and EDC/ECC valid; 30/30 pointers resolve; file
bytes change only in `0x0`–`0x6CD` and the trailer. On screen (`m0_*`–`m5_*`,
`v1_*`, `h5_*`, `p5_*`): all five exhibitions' going-in, remark, choice list
and all three replies each, English, within the box; variant 5's three
lines (two of them caught while typing); dates end normally and the week
continues. Fixed on the way: odd-length options showed a space before `』`.
Not tested: the natural trigger of each exhibition (by year/month and
whether it was seen) and variant 5's natural selection by standing. After
promotion the normal build `.emu/default_dates/` is byte-identical to the
candidate.

**Batch 1 (shared sections 22, 23, 24, 26).** Candidate in
`.emu/review_dates/` (all default files plus the draft): only six DATE_FU
sectors in LBA 44329–44351 differ from the default build. Three forced
museum dates with `-Break` rules (sheets `b1a`, `b1b`, `b1c`): meeting
arrival 0 / mood 2 (parts 4–5), arrival 2 / mood 0 (part 9 with its
thought), the run-away (parts 12–13, the date ends and the week goes on);
small talk parts 0 and 4; ending parts 15 (anthology thanks, last line
caught while typing) and 9 (the `‥‥‥‥。` line with an English thought on
its second line); going home bands 0 (`{P}` inserted) and 3. All English,
within the box, no stalls, the week continues. The other parts were checked
only statically (structure, width, packing). After promotion the normal
build is byte-identical to the candidate.

**Batch 2 (section 7, neighborhood park; section 25, hobby notes).** Only
DATE_FU sectors differ from the default build. One forced place-0 date
(`date_run.ps1 -Place 0` with `--at 0x80132570 --reg v0=0 --mem8
0x8015B654=1` for a fixed 3-box meeting and `--at 0x8013A8B0 --reg v0=3`
for park part 4), then `date_choices.ps1 -Options 2` (sheets `b2a`, `b2`,
`b2_nar`, `b2e`): meeting part 6, her part-4 remark, the narration, the
action choice, both options each followed by the centered pause and a note
(part 0 "listening to music", part 1 "watching sports"), ending part 6 and
going home band 1–2; the week continues. Parts 0 and 2 and the other notes
were checked only statically. Normal build byte-identical to the candidate.

**Batch 3 (section 21, Kirameki Park; section 14, Shopping).** Only DATE_FU
sectors differ. In April a Kirameki Park date plays Shiori's spring park
event (EVENT_FU scene 4) right after the walk starts, in place of the
version's remark and choice; setting its one-shot flag in the meeting rule
(`--mem8 0x800E67EF=1`) skips it. Seen (sheets `b3k`, `b3kc`, `b3s`): the
pond version (`-Version 1`) going in, remark, all three options and
replies; a Shopping date choosing clothes, then "can I go look?", the
pause, the waiting choice (three options listed, one taken) and its reply,
ending and going home. Not seen: Kirameki Park versions 0 and 2 on this
build, Shopping's other first choices and its carrying, cute-item, necklace
and junk-shop branches (static checks only). Normal build byte-identical to
the candidate.

**Batch 4 (sections 1, 6, 10, 12, 13, 15, 16, 19: the two-version
places).** Only DATE_FU sectors differ. With the on-time meeting rule:
Bowling version 0 and Beach version 1 driven through to the end (one option
each; sheets `b4bo`, `b4be`), and Karaoke version 1 with all three
requests and replies (`b4kc`). Pool, Botanical Garden, Skating Rink, Ski
Resort and Library, and the other version of each place, were checked only
statically. Normal build byte-identical to the candidate.

**Batch 5 (sections 3 Zoo, 18 Aquarium, 11 Planetarium, 5 Arcade, 17
Stadium).** Only DATE_FU sectors differ. Forced with the on-time meeting
rule and driven through one option each: Zoo version 2 (koala), Aquarium
1 (sharks), Planetarium 1 (which picked the Cygnus choice, part 12),
Stadium 3 (wrestling), Arcade versions 0 and 1 (sheets `b5zs`, `b5ap`,
`b5arc`, `b5ar1`). On the Arcade, `date_choices.ps1` was started too early
(on the remark), so its two runs saw the version-0 choice list in two
shuffles and two different replies. The Arcade's version picks the part
directly (version 0 → part 2, 1 → part 4); the video/medal action choice
(part 1) did not come up in either and is checked only statically, like
the other versions of every place in this batch. Normal build
byte-identical to the candidate.

**Batch 6 (sections 2 Concert Hall, 8 Cinema, 4 Shrine).** Only DATE_FU
sectors differ. Forced with the on-time meeting rule (sheets `b6cc`,
`b6coe`, `b6shc`): the Cinema up to its `07` announcement (full-width 「
and indent kept, renders in place); the Concert Hall's seat exchange,
choice and the part-3 reply, then the ending; the Shrine's remark and
yukata action choice with both options (praise → compliment and thanks;
say nothing → both skipped, straight to the goldfish offer). The goldfish
minigame then needs real input (its instruction banner is a graphic) and
was not played, so the reactions after the minigames (parts 7–11), the
shooting gallery and the fireworks choice, and the Cinema's choice and
replies, were checked only statically. The film and concert description
thoughts shown in these dates come from another file and are still
Japanese. Normal build byte-identical to the candidate.

**Batch 7 (section 20 Theme Park, section 9 parade).** Only DATE_FU sectors
differ. A forced Theme Park date (on-time meeting rule) went to "where to
next?", the Ghost House and the ending (sheets `b7a`); then a state saved
on that choice (`.emu/savestates_backup/b7w_choice.sav`) was replayed for
each ride (`b7w`): Ferris wheel, Ghost House and roller coaster, each with
its going-in line, remark, choice list and the reply to the first-listed
option. The hero show (parts 1–8), the later ride rounds (parts 25–56),
the Virtual Ship and the parade did not come up and were checked only
statically. Careful: pressing on past the end of a date runs the next
week's commands (here a library event) in RAM; nothing was saved. The
normal build (all of DATE_FU) is byte-identical to the candidate.

### SERIFU.BIN, the shared date lines (2026-10-08)

Candidate `.emu/review_dates/` (all default files plus the draft): only
SERIFU.BIN (LBA 44870–44871) and DATE.EXN's place-name sector and trailer
(LBA 37501, 37513) differed from the default build. Forced dates from the
Sunday state (sheets `s1p`, `s1m0`, `s1m1`, `s2`, `s3st`, `s3w`, `s3x`):
- **Impressions.** A Pool version-1 date replayed for all three options
  (state `.emu/savestates_backup/s1p_choice.sav`): levels 2, 3 and 4 after
  the replies, and after the boast ("Swimming's my specialty.") the swim lie
  line, then level 3. Levels 0 and 1 forced on museum dates with
  `--at 0x8013B174 --mem16 0x800CA22C=N --mem16 0x800CA22E=N --mem16
  0x800CA230=N`. Use a single hit: with `--times 0` the forcer stops the
  game every frame and the screenshots missed the thought. Levels 3 and 4
  showed a space before `)` (odd last line); fixed, but the new wording
  wasn't re-shot.
- **Blurbs.** `--at 0x8013BAD4 --mem8 0x8015B688=N` on Concert Hall dates
  (N = 11, the 5-line Rinsu blurb, scrolls; N = 0) and `--at 0x8013B964
  --mem8 0x8015B684=N` on Cinema dates (N = 3, 6): the forced blurb shows.
- **Missed meeting.** Stood up: `--at 0x8013F008 --reg v0=4`. Wrong place:
  `--at 0x8013F03C --mem8 0x800E69A4=4 --mem8 0x800E69A5=1 --mem8
  0x800E69A6=12 --mem8 0x800E69A7=4` (three options: here, the theme park,
  Kirameki Park, which is the agreed place) and `69A4=1 69A5=4 69A6=12
  69A7=255` (two options). Every option replayed from a state on the
  choice: waiting or a wrong place lead to "never showed up" and the
  answering-machine message (TEL.EXN, Japanese); the agreed place leads to
  the late arrival, and the date continues at Kirameki Park.
- Odd-length names ("Kirameki Park") show a padding space before the
  option's `』`, as expected.

Not seen: the other ten concert and nine movie blurbs, the skate lie line,
the other place names, natural triggers, other girls' dates.

The same odd-ending space also affected nine DATE_FU notes and thoughts
(hobby notes, the parade and hero-show thoughts); their endings were made
even in `shiori_dates.json`. That repacks the whole of DATE_FU, so a park
date was replayed on the new build (both action options and notes, one of
them an edited note, the ending, the week continuing). EVENT_FU's 157
strings were checked statically: all its `04`/`06` thoughts already end
evenly. The normal build is byte-identical to the candidate.

### Disassembly

```bash
uv run --with capstone python tools/mipsdis.py .emu/ram.bin 0x80000000 0x8004636C 40
uv run --with capstone python tools/mipsdis.py extracted/SLPM_86.053 0x80040800 0x80078DC0 80
```

Don't name a script `dis.py`: it shadows the stdlib module that capstone imports.
When scanning a whole binary with capstone, set `md.skipdata = True`.
Otherwise it stops at the first data word and silently returns a fraction of
the code (an early search for BIOS calls found nothing because of this).

## Finding graphics (VRAM dumps)

1. In `.emu/duckstation/settings.ini` set `[Debug] DumpCPUToVRAMCopies = true`.
2. Boot and get to the screen. Every CPU→VRAM upload is saved as
   `.emu/duckstation/cpu_to_vram_copy_<n>.png`. Movies produce thousands of
   these, so stop soon after the screen appears.
3. Group by size: 24×240 are movie slices, 64×128 are 16 KiB pixel blocks,
   256×1 are 256-colour CLUTs, 16×1 are 16-colour CLUTs. The blocks and CLUTs
   that arrive together belong to the file just loaded (`trace_reads.py`).
4. Render the file's bytes as 8bpp with 128-byte rows (or 4bpp, 256 px) to find
   the art. 4bpp rendering of 8bpp data shows vertical striping.
5. **Matching CLUTs:** DuckStation's PNGs expand 5-bit colour to 8-bit, so
   don't compare with `c<<3`. Convert the dump back with `round(v*31/255)` and
   search the file for the 15-bit words (ignore bit 15). The CLUTs in
   `TITLE.NBN` are stored out of upload order (game-internals §7).
6. Set `DumpCPUToVRAMCopies = false` again afterwards.

## Windows-specific gotchas
- Run `drive.ps1` with **Windows PowerShell 5.1** (`powershell.exe`). In pwsh 7,
  its `Add-Type` code doesn't compile without extra assembly references.
- `SetForegroundWindow` is blocked for background processes (foreground lock),
  and sending real keystrokes risks typing into the user's windows. That's why
  the driver uses `PostMessage`.
- `PrintWindow` returns black for DuckStation's GPU-rendered area. Use
  DuckStation's own screenshot hotkey (what `shot:` does).
- DuckStation keeps the screenshot file locked briefly after writing it. The
  driver waits 1.2 s before moving it.
- Kill only the isolated instance:
  `Get-Process | ? { $_.Path -like "*\.emu\duckstation\*" } | Stop-Process`.

## Club correction handoff (2026-10-07)

The current test image is `.emu/review_clubs/` (open its CUE), built from the
default 13 translation files; `.emu/review_clubs.log` is the build log.
It includes Literature and the revised Club Day fragments. Real boot and
loading the 95/4/23 test card succeeded, and play continued to the 4/29 holiday.
The first News issue also displayed its English introduction, Movie “Closed”,
Concert “KNM Symphony” and event announcement; later issues are unverified.
No unpatched comparison at the corrected club screens has been completed.

Final static checks passed: a full raw-track comparison found exactly the 37
sectors predicted by the patch plan, with valid regenerated EDC/ECC on each.
Every patched file retained its size, and all files that originally had valid
checksum trailers still validate. `SLPM_86.053` and `MAINROM.NBN` do not have
those trailers; earlier session claims of an EXE checksum update were mistaken.
All 12 club-table pointers resolve to their expected English strings, and the
three adjacent notice-fragment pairs fit their fixed x-coordinate gaps.
The driver passes PowerShell syntax validation. The isolated emulator was
stopped after the review.

Follow-up user verification (screenshots and play test):

1. Club List: Literature replaces 文芸 and fits the column. Its selected state
   extends slightly beyond the green selector rectangle; the user accepts this
   for now. The first screenshot shows Literature highlighted.
2. Joining Soccer: the user confirms successful joining and the second
   screenshot shows the corrected captain's notice: “Capt. Each 3rd Sunday is”
   / “Club Day, so” / “don't   miss it.”. There is no text overlap. The wide
   gap before “miss it.” is noticeable but accepted by the user for now.

Leave both cosmetic issues unchanged, as requested. Continuation after this
corrected notice was not explicitly reported; the earlier build's club flow
had already been checked for continuation. For future text tests, boot the CUE
and load a memory-card save: older emulator states retain old EXE strings and
pointer tables.

The test harness's previous card was backed up under
`.emu/memcard_backup/review_before_*` before the main-loop test card was copied
in. This run did not operate the user's DuckStation installation or cards.

## Save/Load panel and settings handoff (2026-10-07)

Candidate: `.emu/review_settings/` (open its CUE); log:
`.emu/review_settings.log`. It originally included the 13 default translation
files plus the two drafts, now at `translation/album_panel_exe.json` and
`translation/system_settings.json`: 397
in-place strings, 173 pooled dialogue entries, 4 images and 3 byte patches
from 15 JSON files. The user has now reported successful visual verification
of populated Load panels and all settings submenus (details below). Both
translations have now been promoted into normal builds at the user's request.
This candidate preserves the user-accepted club selector overhang and notice
gap. It does not translate the title Options' graphics-based choices or the
new-game album panel's graphics.

Changes from the drafts:

- Both Save/Load panel copies now use `Name: `, `Nickname: `, `Club: ` and
  `Cleared: ` before their saved values. Their destination buffers were checked
  as well as the literal byte budgets. Slot headings intentionally use a colon
  after the number: the game only appends two bytes, so `: Album` was misleading.
- All four Menu Mode confirmations now read `Menu mode:` / `<mode>` /
  `selected.` on the original three rows. Other settings translations remain
  as drafted; no coordinates, selector sizes or settings logic were changed.
- Consumer addresses, fixed copy limits, row coordinates and the two Cursor
  Speed label sets are documented in game-internals §6i. The translation guide
  now explains these patterns rather than recommending empty trailing pieces
  without first checking their layout.

Static checks completed on the candidate:

- The normal patcher planned against the original disc and built successfully;
  all 135 extra strings passed original-byte checks and in-place budgets.
- Every output file matched the planned bytes and retained its original size;
  all files with original valid checksum trailers still validate. The EXE and
  `MAINROM.NBN` do not have those trailers.
- A full raw Track 1 comparison found exactly the 37 planned changed sectors;
  every changed sector is Mode 2 Form 1 with valid regenerated EDC/ECC and an
  unchanged header/subheader. Compared with `.emu/review_clubs/`, only EXE
  sectors 247, 248 and 249 differ. The CUE and audio track are identical to
  the originals. All 1,981 incremental EXE byte differences are confined to
  the two documented literal blocks (`0x6FA08`–`0x7028F` and
  `0x70790`–`0x70853`); no code or other default translations changed.
- Slot/date appends obey their two-byte limits. The panel's maximum current
  label/value lengths stay inside their 32-byte stack buffers, including NUL.

### Follow-up user verification

The user supplied four screenshots and reported that these screens were
successfully translated, adding that **all system settings submenus were
visually verified**, although not all were photographed. Record that report
as visual evidence without treating it as an exhaustive per-string test.

1. Settings main screen: `System Settings`, Text Speed, Icon Mode, Mouse,
   Menu Mode, Cursor Speed, Voice Mode and Exit render in English. Icon Mode
   is highlighted; the help reads `Change system settings.`. Mascot is not
   visible in this screenshot, so no unlock-condition conclusion follows.
2. Text Speed submenu: `Text Spd`, Slow (highlighted), Normal, Fast and
   `Change the text display speed.` are legible, without apparent clipping.
   In particular, the padding-using `Normal` label fits.
3. Load slot 1: number/colon heading, date 95/4/9, Name/Nickname/Club/Cleared
   labels and saved values render correctly; the club is None and cleared
   count is 0. The prompt is `Choose a file to load.`. Japanese player-entered
   names remain intact; these are saved user values, not missing translations.
4. Populated slot 2: heading and date change to 2 and 95/4/16, and the club
   changes to Soccer. Labels and values remain readable with separators and
   no apparent overlap. The blank prompt in this screenshot is not evidence
   of Save mode; the screenshots explicitly establish populated Load panels.

The other settings submenus are user-reported visually verified, not individually
screenshot-verified. Individual setting-change confirmations (including the
three-row Menu Mode messages), every highlighted state, which Cursor Speed
label set appeared, and mouse-accessory/unlock-dependent paths were not
separately itemized. Do not infer their detailed coverage from the general
submenu report. The panel's Save-mode copy, empty/error/System entries,
longest club values and nonzero cleared counts also remain unverified.
An unpatched comparison and continuation after these particular screens
were not explicitly reported. No emulator instance, settings or memory cards
were operated by the agent during this documentation update; no screenshots
or game data were added to the repository.

Original test checklist (retain for remaining branch checks; the visual
coverage above has already been completed and should not be discarded):

1. Boot the candidate CUE fresh and load a **memory-card save**, not an old
   emulator save state. Old states preserve old EXE strings and pointer tables.
2. On Sunday night, open the memory-card command. Check populated and empty
   slots in **both Save and Load**, without overwriting a valued save just to
   test. Look at the slot number, date, name, nickname, club and cleared count:
   there should be visible separators, intact values, and no clipping or
   overlap. A saved club such as Literature/Basketball is a useful width test.
   The full-width digits and spaces around date slashes are expected for now.
3. Open **in-game System Settings**, not title OPTIONS. Check the item list,
   highlighted/unselected choices, help text and confirmation for Text Speed,
   Icon Mode, all four Menu Modes, all five Cursor Speeds, Voice Mode and
   available Mascot choices. In particular check `Normal` and the longest
   Menu Mode; its confirmation should have three readable rows. Note which
   Cursor Speed label set appears; both sets exist but may require different
   input/device conditions. Mouse settings need the mouse accessory and can
   remain explicitly unverified without one.
4. Restore preferred settings, exit to the game and play through the next
   transition. Do not force memory-card errors or corrupt saves to exercise
   `Bad data`; leave unseen error branches unverified. If a problem appears,
   compare the original game at the same point before blaming the patch.

The verification table in `AGENTS.md` reflects the user's results. Both JSONs
have now been moved into `translation/`, so the normal command includes them.
Unverified-path notes are retained; inaccessible mouse/error paths are not
marked as seen. The user's standing preference is to promote tested new
translation files into normal builds after testing, not leave them opt-in.

### Normal-build promotion verification

Built `.emu/default_promoted_settings/` from the original CUE with
`python -m tokipatch <original cue> -o .emu/default_promoted_settings --force`,
**without any `-t` options**. Log: `.emu/default_promoted_settings.log`.
Default discovery loaded all 15 JSON files (397 strings, 173 pooled dialogue
entries, 4 images and 3 byte patches). The two old `extra/` paths no longer
exist; their patch entries are unchanged, with only description metadata
updated alongside the moves.

SHA-256 comparisons confirmed that the CUE and both BIN tracks are identical
to `.emu/review_settings/`, the candidate the user tested. An independent
check against the original confirmed exact planned output bytes, unchanged
file sizes, valid applicable checksum trailers, exactly 37 expected changed
sectors and valid EDC/ECC on every changed sector. The original source files
were only read. No new emulator run was performed for this path-only promotion;
the user's candidate verification applies to the byte-identical output, with
the same branch-coverage limitations recorded above.

Rebuild recipe after promotion (PowerShell; no `-t` flags are needed):

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m tokipatch '<original game.cue>' -o .emu/review_settings --force
```
