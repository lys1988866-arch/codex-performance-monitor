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

  $languageSmoke = @'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
import tkinter as tk
import codex_monitor_app as app

root = tk.Tk()
root.withdraw()
ui = app.CodexMonitorApp(root)
for code, label in app.SUPPORTED_LANGUAGES.items():
    ui.language.set(label)
    ui._apply_language()
    if not ui.refresh_button.cget("text") or not ui.notebook.tab(0, "text"):
        raise RuntimeError(f"Language {code} rendered empty UI text")
root.destroy()
print("language_smoke_ok")
'@
  $languageSmoke | & $python.Source -
  if ($LASTEXITCODE -ne 0) {
    throw "Language switch smoke test failed."
  }

  & $python.Source -c "import os, sys; sys.path.insert(0, 'src'); import codex_monitor_app as app; result = app.terminate_process(os.getpid()); assert result['ok'] is False and result['error'] == 'cannot_terminate_self'; print('terminate_self_guard_ok')"
  if ($LASTEXITCODE -ne 0) {
    throw "Terminate self guard test failed."
  }

  Write-Host "Validation passed"
  Write-Host ("Risk: {0} ({1}/100)" -f $summary.risk.level, $summary.risk.score)
  Write-Host ("Processes: {0}; recent threads: {1}" -f $summary.processes.total, $summary.recent_threads)
}
finally {
  Remove-Item -LiteralPath $summaryPath -Force -ErrorAction SilentlyContinue
}
