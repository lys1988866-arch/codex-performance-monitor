$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python was not found on PATH. Install Python 3.11+ or run with a full python.exe path."
}
& $python.Source "$root\src\codex_monitor_app.py"
