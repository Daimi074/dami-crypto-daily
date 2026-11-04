# Sync new report data into the repo and push to GitHub Pages.
# Usage: powershell -ExecutionPolicy Bypass -File tools\sync.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
git pull -q --rebase --autostash
$zip = Join-Path $repo "_sync.zip"
if (Test-Path $zip) { Expand-Archive -Force $zip $repo; Remove-Item $zip }
python tools/build.py
git add -A
$changed = git status --porcelain
if (-not $changed) { Write-Output "NO_CHANGES"; exit 0 }
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -q -m "Sync reports $stamp (Asia/Taipei)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
Write-Output ("PUSHED " + (git log -1 --format=%h))
