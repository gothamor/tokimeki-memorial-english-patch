# Force the Christmas party (XMAS.BIN), or another seasonal event, and
# screenshot the boxes.
#
#   powershell.exe -File tools\emu\xmas_run.ps1 [-Opts "--girls 8,1 --met 8"] [-Presses 30]
#       [-Tool "tools/emu/force_white.py"] [-Prefix name] [-Keys "C"] [-Wait 4000]
#       [-State ...] [-Build review_dates] [-Hidden]
#
# Launches the Sunday-night state, runs -Tool (default
# "tools/emu/force_christmas.py --party") with -Opts detached (log
# .emu\xmas_run.log; options in each tool's docstring, game-internals
# 6t/6u/6v), picks the first weekly command, then presses -Keys (default C)
# with a screenshot per box. Contact sheets of 15 boxes each:
# .emu\shots\<Prefix>_sheet0.png, _sheet1.png, ... -Hidden hides the
# emulator window.
param([string]$Opts = "", [string]$Tool = "tools/emu/force_christmas.py --party",
      [int]$Presses = 30, [string]$Prefix = "xmas", [string]$Keys = "C",
      [int]$Wait = 3500,
      [string]$State = ".emu\savestates_backup\dates_sunday_0423_candidate.sav",
      [string]$Build = "review_dates", [switch]$Hidden)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\launch_state.ps1" -State $State -Build $Build -Hidden:$Hidden | Out-Null
$a = $Tool.Split(" ", [StringSplitOptions]::RemoveEmptyEntries) + @("--timeout", "600")
if ($Opts) { $a += $Opts.Split(" ", [StringSplitOptions]::RemoveEmptyEntries) }
Start-Process python -ArgumentList $a -WindowStyle Hidden -RedirectStandardOutput .emu\xmas_run.log -RedirectStandardError .emu\xmas_run.err | Out-Null
Start-Sleep -Seconds 3
$seq = "C,wait:10000"
$names = @()
for ($i = 1; $i -le $Presses; $i++) { $n = "{0}_{1:D2}" -f $Prefix, $i; $seq += ",shot:$n,$Keys,wait:$Wait"; $names += $n }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$here\drive.ps1" -Seq $seq | Out-Null
Get-Content .emu\xmas_run.log, .emu\xmas_run.err -ErrorAction SilentlyContinue | Select-Object -First 16
for ($k = 0; $k -lt $names.Count; $k += 15) {
    $part = $names[$k..([Math]::Min($k + 14, $names.Count - 1))]
    python "$here\contact_sheet.py" ".emu\shots\${Prefix}_sheet$($k / 15).png" @part
    "sheet: .emu\shots\${Prefix}_sheet$($k / 15).png"
}
