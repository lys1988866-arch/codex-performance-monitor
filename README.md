# Codex Performance Monitor

Local desktop monitor for OpenAI Codex Desktop on Windows.

It works like a focused task manager for Codex: it watches Codex processes, Node/MCP runtimes, browser/WebView helpers, system memory, Codex SQLite log health, model configuration, enabled plugins, MCP server count, and recent local Codex threads.

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

Install TRACE/DEBUG log guard:

```powershell
python .\src\codex_monitor_app.py --install-guard
```

Checkpoint/truncate Codex logs WAL:

```powershell
python .\src\codex_monitor_app.py --checkpoint
```

## Build EXE

Optional:

```powershell
.\scripts\build-exe.ps1
```

This creates a PyInstaller build if `pyinstaller` is available. If not, install it in your own Python environment first:

```powershell
python -m pip install pyinstaller
```

## Safety

The monitor is read-only by default. The two manual action buttons modify only the local Codex logs SQLite database:

- `Checkpoint Logs WAL`: runs `PRAGMA wal_checkpoint(TRUNCATE)`.
- `Install TRACE/DEBUG Guard`: creates a SQLite trigger that ignores new `TRACE` and `DEBUG` rows while keeping `INFO`, `WARN`, and `ERROR`.

It does not kill processes or modify Codex projects.

## GitHub

Create a new GitHub repository, then from this folder:

```powershell
git init
git add .
git commit -m "Initial Codex performance monitor"
git branch -M main
git remote add origin https://github.com/<your-name>/codex-performance-monitor.git
git push -u origin main
```

## License

MIT
