# Codex Performance Monitor

Local desktop monitor for OpenAI Codex Desktop on Windows.

It works like a focused task manager for Codex: it watches Codex processes, Node/MCP runtimes, browser/WebView helpers, system memory, Codex SQLite log health, model configuration, enabled plugins, MCP server count, and recent local Codex threads.

## Languages

- English: this page
- [简体中文](docs/README.zh-CN.md)
- [日本語](docs/README.ja.md)
- [한국어](docs/README.ko.md)
- [Español](docs/README.es.md)
- [Français](docs/README.fr.md)
- [Deutsch](docs/README.de.md)

The desktop app includes an in-app language switcher for the same languages.

## Why

Codex Desktop can become unstable when several heavy tasks run at the same time, especially with high reasoning settings, browser automation, Vite/Node dev servers, image generation, or large SQLite log files. This tool makes that pressure visible.

## Features

- Codex-related process table sorted by memory.
- Live CPU estimate and working-set memory.
- System memory and pagefile summary.
- `~/.codex/logs_2.sqlite` size, WAL size, row count, level counts, and trigger status.
- Current `~/.codex/config.toml` model and reasoning effort.
- Enabled plugin and MCP server counts.
- Recent local Codex threads from `state_5.sqlite`.
- Risk score with concrete reasons.
- Action panel for practical remediation steps.
- Optimize memory by trimming monitored process working sets.
- End a selected process after explicit confirmation.
- Copy a selected process PID for manual investigation.
- One-click `logs_2.sqlite` WAL checkpoint/truncate.
- One-click TRACE/DEBUG log guard installation.
- JSON report export.
- CLI snapshot mode for automation.

## Requirements

- Windows 10/11
- Python 3.11+ with Tkinter
- PowerShell

No third-party Python packages are required.

## Run

From PowerShell:

```powershell
.\run.ps1
```

Or:

```powershell
python .\src\codex_monitor_app.py
```

CLI snapshot:

```powershell
python .\src\codex_monitor_app.py --once
```

Compact CLI summary:

```powershell
python .\src\codex_monitor_app.py --summary
```

Install TRACE/DEBUG log guard:

```powershell
python .\src\codex_monitor_app.py --install-guard
```

Checkpoint/truncate Codex logs WAL:

```powershell
python .\src\codex_monitor_app.py --checkpoint
```

## Validate

Run the same local smoke checks used by CI:

```powershell
.\scripts\validate.ps1
```

This checks Python syntax, CLI help, compact JSON summary output, and a Tkinter startup smoke test.

## Build EXE

Build a double-clickable Windows executable:

```powershell
.\scripts\build-exe.ps1
```

The script creates an isolated `.venv-build` environment, installs PyInstaller there, and writes:

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## Safety

The monitor is read-only by default. The two manual action buttons modify only the local Codex logs SQLite database:

- `Checkpoint Logs WAL`: runs `PRAGMA wal_checkpoint(TRUNCATE)`.
- `Install TRACE/DEBUG Guard`: creates a SQLite trigger that ignores new `TRACE` and `DEBUG` rows while keeping `INFO`, `WARN`, and `ERROR`.
- `Optimize Memory`: asks Windows to trim reclaimable working-set memory for monitored processes. It does not kill processes.
- `End Selected Process`: terminates only the process row you explicitly select and confirm.

It does not install Codex, reinstall Codex, or modify Codex projects.

## Repository

Published at:

https://github.com/lys1988866-arch/codex-performance-monitor

## License

MIT
