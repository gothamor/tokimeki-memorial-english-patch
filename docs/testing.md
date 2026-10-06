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
  python tools/emu/poke_file.py .emu/b2/SLPM_86.053 0x80040800 0x76550 0x855A4    # the font (new pair glyphs)
  ```
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
The hand moves at roughly 0.8 px per ms of key hold, measured in screenshot
pixels (≈ 4.8 per game px).

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
