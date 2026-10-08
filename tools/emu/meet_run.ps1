# Force a meeting scene (G_APPEAR.BIN) with a girl and screenshot the boxes.
#
#   powershell.exe -File tools\emu\meet_run.ps1 -Girl 8 [-Scene 0] [-Presses 14]
#       [-Prefix name] [-Keys "C"] [-State ...] [-Build review_dates] [-Hidden]
#
# Launches the Sunday-night state, runs tools/emu/force_event.py with a
# type-0x48 record `48 GIRL SCENE 00` detached (log .emu\meet_run.log), picks
# the first weekly command, then presses -Keys (default C) with a screenshot
# per box. SCENE is the meeting's variant byte (game-internals 6p). Contact
# sheet: .emu\shots\<Prefix>_sheet.png. -Hidden hides the emulator window.
param([Parameter(Mandatory)][int]$Girl, [int]$Scene = 0, [int]$Presses = 14,
      [string]$Prefix = "", [string]$Keys = "C",
      [string]$State = ".emu\savestates_backup\dates_sunday_0423_candidate.sav",
      [string]$Build = "review_dates", [switch]$Hidden)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Prefix) { $Prefix = "m${Girl}s${Scene}" }
& "$here\launch_state.ps1" -State $State -Build $Build -Hidden:$Hidden | Out-Null
$a = @("tools/emu/force_event.py", "$Girl", "$Scene", "--type", "0x48", "--timeout", "300")
Start-Process python -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput .emu\meet_run.log -RedirectStandardError .emu\meet_run.err | Out-Null
Start-Sleep -Seconds 3
$seq = "C,wait:10000"
$names = @()
for ($i = 1; $i -le $Presses; $i++) { $n = "{0}_{1:D2}" -f $Prefix, $i; $seq += ",shot:$n,$Keys,wait:3500"; $names += $n }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$here\drive.ps1" -Seq $seq | Out-Null
Get-Content .emu\meet_run.log, .emu\meet_run.err -ErrorAction SilentlyContinue | Select-Object -First 12
python "$here\contact_sheet.py" ".emu\shots\${Prefix}_sheet.png" @names
"sheet: .emu\shots\${Prefix}_sheet.png"
