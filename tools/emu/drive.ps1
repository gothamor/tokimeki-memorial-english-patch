# Drives the isolated DuckStation (.emu/duckstation) by posting key messages to
# its window, so no focus is needed and nothing is typed into other windows.
# Run with Windows PowerShell 5.1 (System.Drawing/Add-Type work out of the box):
#
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\emu\drive.ps1 -Seq "Return,wait:3000,shot:title"
#
# Steps (comma separated):
#   KEY[:holdms]  press a key: Return X C Z S Up Down Left Right Backspace Tab
#                 (C = Circle = CONFIRM, X = Cross = BACK; Japanese convention)
#                 F1 (load state) F2 (save state) F10 (screenshot)
#   wait:ms       sleep
#   shot:name     DuckStation screenshot (F10), moved to .emu/shots/<name>.png
#   until:screen:ms  take screenshots until tools/emu/screens.py recognises
#                 <screen> (e.g. "title"), failing after ms. Runs in-process, so
#                 the next step follows within ~2 s (the title times out quickly).
param([string]$Seq)

Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  public static List<IntPtr> Windows(uint pid) {
    var res = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (p == pid && IsWindowVisible(h)) res.Add(h); return true; }, IntPtr.Zero);
    return res;
  }
  public static string Title(IntPtr h) { var s = new StringBuilder(256); GetWindowText(h, s, 256); return s.ToString(); }
}
"@

$Repo = Resolve-Path "$PSScriptRoot\..\.."
$Emu = "$Repo\.emu\duckstation"
$Shots = "$Repo\.emu\shots"
New-Item -ItemType Directory -Force $Shots | Out-Null

$proc = Get-Process | Where-Object { $_.Path -like "$Emu\*" } | Select-Object -First 1
if (-not $proc) { throw "isolated DuckStation ($Emu) is not running" }
$hwnd = [W]::Windows([uint32]$proc.Id) | Where-Object { [W]::Title($_) -ne '' } | Select-Object -First 1

$vk = @{ Return=0x0D; X=0x58; C=0x43; Z=0x5A; S=0x53; Up=0x26; Down=0x28; Left=0x25; Right=0x27;
         Backspace=0x08; Tab=0x09; F1=0x70; F2=0x71; F10=0x79 }
$extended = @('Up','Down','Left','Right')

function Press($name, $hold) {
  $code = $vk[$name]; if (-not $code) { throw "unknown key $name" }
  $scan = [W]::MapVirtualKey($code, 0)
  $l = 1 -bor ($scan -shl 16); if ($extended -contains $name) { $l = $l -bor (1 -shl 24) }
  [void][W]::PostMessage($hwnd, 0x100, [IntPtr]$code, [IntPtr]$l)        # WM_KEYDOWN
  Start-Sleep -Milliseconds $hold
  [void][W]::PostMessage($hwnd, 0x101, [IntPtr]$code, [IntPtr][int64]($l -bor (3 -shl 30)))  # WM_KEYUP
  Start-Sleep -Milliseconds 150
}

function Shoot($dest) {
  $dir = "$Emu\screenshots"
  $before = @(Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue).Count
  Press 'F10' 120
  for ($i = 0; $i -lt 30 -and @(Get-ChildItem $dir -Filter *.png -ErrorAction SilentlyContinue).Count -le $before; $i++) { Start-Sleep -Milliseconds 200 }
  Start-Sleep -Milliseconds 1200   # let DuckStation finish writing the file
  $latest = Get-ChildItem $dir -Filter *.png | Sort-Object LastWriteTime | Select-Object -Last 1
  Move-Item -Force $latest.FullName $dest
}

foreach ($step in $Seq.Split(',')) {
  $parts = $step.Trim().Split(':')
  switch ($parts[0]) {
    'wait' { Start-Sleep -Milliseconds ([int]$parts[1]) }
    'shot' { Shoot "$Shots\$($parts[1]).png"; "saved .emu\shots\$($parts[1]).png" }
    'until' {
      $screen = $parts[1]; $deadline = (Get-Date).AddMilliseconds([int]$parts[2])
      while ($true) {
        Shoot "$Shots\_until.png"
        & python "$Repo\tools\emu\screens.py" $screen "$Shots\_until.png"
        if ($LASTEXITCODE -eq 0) { "reached $screen"; break }
        if ((Get-Date) -gt $deadline) { throw "timed out waiting for screen '$screen'" }
      }
    }
    default { $hold = if ($parts.Length -gt 1) { [int]$parts[1] } else { 120 }; Press $parts[0] $hold }
  }
}
