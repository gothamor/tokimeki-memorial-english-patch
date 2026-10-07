# Restart the isolated DuckStation (visible) from a save state.
#
#   powershell.exe -File tools\emu\launch_state.ps1 -State .emu\savestates_backup\X.sav [-Build review_dates]
#
# -Build names a folder under .emu holding a patched CUE, or "orig" for the
# unpatched disc. NOTE: DuckStation reopens the disc the state was made with,
# whatever CUE is passed, so rebuild candidates into the state's own folder
# (docs/testing.md, "Testing date conversations").
param([Parameter(Mandatory)][string]$State, [string]$Build = "review_dates", [int]$Wait = 9)
Get-Process duckstation* -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false
Start-Sleep -Seconds 2
$root = (Get-Location).Path
$name = "Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best).cue"
$cue = if ($Build -eq "orig") { "$root\Tokimeki Memorial - Forever with You (Japan) (PlayStation the Best)\$name" } else { "$root\.emu\$Build\$name" }
$statePath = (Resolve-Path $State).Path
Start-Process .emu\duckstation\duckstation-qt-x64-ReleaseLTCG.exe -ArgumentList '-batch','-statefile',"`"$statePath`"","`"$cue`""
Start-Sleep -Seconds $Wait
"launched $State ($Build)"
