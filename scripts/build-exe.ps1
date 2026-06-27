$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python was not found on PATH."
}

$venv = Join-Path $root ".venv-build"
$venvPython = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  & $python.Source -m venv $venv
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create build virtual environment."
  }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
  throw "Failed to upgrade pip in build virtual environment."
}

& $venvPython -m pip install "pyinstaller>=6,<7"
if ($LASTEXITCODE -ne 0) {
  throw "Failed to install PyInstaller in build virtual environment."
}

& $venvPython -m PyInstaller `
  --noconfirm `
  --windowed `
  --name CodexPerformanceMonitor `
  "$root\src\codex_monitor_app.py"

Write-Host "Built: $root\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe"
