$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python was not found on PATH."
}

& $python.Source -m py_compile "$root\src\codex_monitor_app.py"
if ($LASTEXITCODE -ne 0) {
  throw "Python syntax check failed."
}

& $python.Source "$root\src\codex_monitor_app.py" --help | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "CLI help failed."
}

$summaryPath = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-monitor-summary-{0}.json" -f ([guid]::NewGuid()))
try {
  & $python.Source "$root\src\codex_monitor_app.py" --summary | Set-Content -Encoding UTF8 $summaryPath
  if ($LASTEXITCODE -ne 0) {
    throw "CLI summary failed."
  }

  $summary = Get-Content -Raw -Encoding UTF8 $summaryPath | ConvertFrom-Json
  if (-not $summary.app.name -or -not $summary.risk.level) {
    throw "CLI summary JSON is missing expected fields."
  }

  & $python.Source -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy(); print('tkinter_ok')"
  if ($LASTEXITCODE -ne 0) {
    throw "Tkinter smoke test failed."
  }

  Write-Host "Validation passed"
  Write-Host ("Risk: {0} ({1}/100)" -f $summary.risk.level, $summary.risk.score)
  Write-Host ("Processes: {0}; recent threads: {1}" -f $summary.processes.total, $summary.recent_threads)
}
finally {
  Remove-Item -LiteralPath $summaryPath -Force -ErrorAction SilentlyContinue
}
