$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python was not found on PATH."
}

& $python.Source -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller is not installed. Run: python -m pip install pyinstaller"
}

& $python.Source -m PyInstaller `
  --noconfirm `
  --windowed `
  --name CodexPerformanceMonitor `
  "$root\src\codex_monitor_app.py"

Write-Host "Built: $root\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe"
