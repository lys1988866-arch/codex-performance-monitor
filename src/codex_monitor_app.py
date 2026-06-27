from __future__ import annotations

import argparse
import json
import os
import queue
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:  # pragma: no cover
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]


APP_NAME = "Codex Performance Monitor"
APP_VERSION = "0.1.0"
WATCHED_PROCESS_PATTERN = (
    "Codex|codex|codex-command-runner|node|node_repl|chrome|msedge|msedgewebview2|python|dotnet"
)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def utc_from_epoch(value: int | float | None) -> str:
    if not value:
        return ""
    seconds = value / 1000 if value > 10_000_000_000 else value
    return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def human_bytes(value: int | float | None) -> str:
    if value is None:
        return "-"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def normalize_json(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def run_powershell_json(script: str, timeout: int = 8) -> Any:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    output = completed.stdout.strip()
    if not output:
        return []
    return json.loads(output)


def collect_processes() -> list[dict[str, Any]]:
    script = rf"""
$pattern = '{WATCHED_PROCESS_PATTERN}'
$items = Get-Process | Where-Object {{ $_.ProcessName -match $pattern }} | ForEach-Object {{
  $path = $null
  $startTime = ''
  try {{ $path = $_.Path }} catch {{ $path = $null }}
  try {{ $startTime = $_.StartTime.ToString('yyyy-MM-dd HH:mm:ss') }} catch {{ $startTime = '' }}
  [pscustomobject]@{{
    id = $_.Id
    name = $_.ProcessName
    cpuSeconds = if ($_.CPU -eq $null) {{ 0 }} else {{ [double]$_.CPU }}
    workingSet = [int64]$_.WorkingSet64
    startTime = $startTime
    path = $path
  }}
}}
$items | Sort-Object workingSet -Descending | ConvertTo-Json -Depth 4
"""
    rows = normalize_json(run_powershell_json(script))
    processes: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", ""))
        path = str(row.get("path") or "")
        category = "Other"
        if name.lower() in {"codex", "codex-command-runner"} or name.lower().startswith("codex"):
            category = "Codex"
        elif name.lower() in {"node", "node_repl"}:
            category = "Runtime"
        elif name.lower() in {"chrome", "msedge", "msedgewebview2"}:
            category = "Browser"
        elif "codex" in path.lower():
            category = "Codex"
        processes.append(
            {
                "id": int(row.get("id") or 0),
                "name": name,
                "category": category,
                "cpu_seconds": float(row.get("cpuSeconds") or 0),
                "working_set": int(row.get("workingSet") or 0),
                "start_time": row.get("startTime") or "",
                "path": path,
            }
        )
    return processes


def collect_system_memory() -> dict[str, Any]:
    script = """
$os = Get-CimInstance Win32_OperatingSystem
$pf = Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage
[pscustomobject]@{
  totalPhysical = [int64]$os.TotalVisibleMemorySize * 1024
  freePhysical = [int64]$os.FreePhysicalMemory * 1024
  totalVirtual = [int64]$os.TotalVirtualMemorySize * 1024
  freeVirtual = [int64]$os.FreeVirtualMemory * 1024
  pageFiles = $pf
} | ConvertTo-Json -Depth 5
"""
    data = run_powershell_json(script)
    total = int(data.get("totalPhysical") or 0)
    free = int(data.get("freePhysical") or 0)
    used = max(total - free, 0)
    return {
        "total_physical": total,
        "free_physical": free,
        "used_physical": used,
        "used_percent": (used / total * 100) if total else 0,
        "total_virtual": int(data.get("totalVirtual") or 0),
        "free_virtual": int(data.get("freeVirtual") or 0),
        "page_files": normalize_json(data.get("pageFiles")),
    }


def collect_log_health(home: Path) -> dict[str, Any]:
    db_path = home / "logs_2.sqlite"
    wal_path = Path(str(db_path) + "-wal")
    result: dict[str, Any] = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "db_size": db_path.stat().st_size if db_path.exists() else 0,
        "wal_size": wal_path.stat().st_size if wal_path.exists() else 0,
        "count": None,
        "max_id": None,
        "levels": [],
        "triggers": [],
        "error": None,
    }
    if not db_path.exists():
        return result
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
        cur = con.cursor()
        result["count"] = cur.execute("select count(*) from logs").fetchone()[0]
        result["max_id"] = cur.execute("select max(id) from logs").fetchone()[0]
        result["levels"] = cur.execute(
            "select level, count(*) from logs group by level order by count(*) desc"
        ).fetchall()
        result["triggers"] = [
            row[0]
            for row in cur.execute(
                "select name from sqlite_master where type='trigger' order by name"
            ).fetchall()
        ]
        con.close()
    except Exception as exc:
        result["error"] = str(exc)
    return result


def collect_config(home: Path) -> dict[str, Any]:
    path = home / "config.toml"
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "model": "",
        "reasoning_effort": "",
        "mcp_count": 0,
        "enabled_plugins": [],
        "memories_enabled": None,
        "error": None,
    }
    if not path.exists():
        return result
    if tomllib is None:
        result["error"] = "tomllib is unavailable; use Python 3.11+"
        return result
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        result["model"] = data.get("model", "")
        result["reasoning_effort"] = data.get("model_reasoning_effort", "")
        mcp_servers = data.get("mcp_servers", {}) or {}
        result["mcp_count"] = len(mcp_servers)
        plugins = data.get("plugins", {}) or {}
        enabled = []
        for name, cfg in plugins.items():
            if isinstance(cfg, dict) and cfg.get("enabled") is True:
                enabled.append(name)
        result["enabled_plugins"] = enabled
        memories = data.get("memories", {}) or {}
        if isinstance(memories, dict):
            result["memories_enabled"] = memories.get("use_memories")
    except Exception as exc:
        result["error"] = str(exc)
    return result


def collect_recent_threads(home: Path, limit: int = 20) -> list[dict[str, Any]]:
    db_path = home / "state_5.sqlite"
    if not db_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        for row in cur.execute(
            """
            select id, title, cwd, updated_at_ms, tokens_used, model, reasoning_effort, archived
            from threads
            where archived = 0
            order by updated_at_ms desc
            limit ?
            """,
            (limit,),
        ):
            rows.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "cwd": str(row["cwd"]).replace("\\\\?\\", ""),
                    "updated": utc_from_epoch(row["updated_at_ms"]),
                    "tokens_used": row["tokens_used"],
                    "model": row["model"] or "",
                    "reasoning_effort": row["reasoning_effort"] or "",
                }
            )
        con.close()
    except Exception:
        return []
    return rows


def checkpoint_logs(home: Path) -> dict[str, Any]:
    db_path = home / "logs_2.sqlite"
    wal_path = Path(str(db_path) + "-wal")
    if not db_path.exists():
        return {"ok": False, "message": "logs_2.sqlite not found"}
    con = sqlite3.connect(db_path, timeout=10)
    cur = con.cursor()
    checkpoint = cur.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    con.close()
    return {
        "ok": True,
        "message": "WAL checkpoint/truncate completed",
        "checkpoint": checkpoint,
        "wal_size": wal_path.stat().st_size if wal_path.exists() else 0,
    }


def install_trace_guard(home: Path) -> dict[str, Any]:
    db_path = home / "logs_2.sqlite"
    if not db_path.exists():
        return {"ok": False, "message": "logs_2.sqlite not found"}
    con = sqlite3.connect(db_path, timeout=10)
    cur = con.cursor()
    cur.execute("DROP TRIGGER IF EXISTS codex_block_logs_insert")
    cur.execute("DROP TRIGGER IF EXISTS codex_block_trace_debug_logs_insert")
    cur.execute(
        """
        CREATE TRIGGER codex_block_trace_debug_logs_insert
        BEFORE INSERT ON logs
        WHEN NEW.level IN ('TRACE', 'DEBUG')
        BEGIN
          SELECT RAISE(IGNORE);
        END;
        """
    )
    con.commit()
    cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    return {"ok": True, "message": "TRACE/DEBUG guard installed"}


def assess_risk(snapshot: dict[str, Any]) -> dict[str, Any]:
    processes = snapshot["processes"]
    log_health = snapshot["log_health"]
    config = snapshot["config"]
    memory = snapshot["system_memory"]
    codex_processes = [p for p in processes if p["category"] == "Codex"]
    runtime_processes = [p for p in processes if p["category"] == "Runtime"]
    browser_processes = [p for p in processes if p["category"] == "Browser"]
    codex_mem = sum(p["working_set"] for p in codex_processes)
    runtime_mem = sum(p["working_set"] for p in runtime_processes)
    max_proc = max((p["working_set"] for p in processes), default=0)
    recent_threads = len(snapshot.get("recent_threads", []))
    effort = str(config.get("reasoning_effort") or "").lower()
    triggers = set(log_health.get("triggers") or [])
    wal_size = int(log_health.get("wal_size") or 0)
    db_size = int(log_health.get("db_size") or 0)
    score = 0
    reasons: list[str] = []

    if max_proc > 1.8 * 1024**3:
        score += 40
        reasons.append("A single monitored process is above 1.8 GB.")
    if codex_mem > 3.5 * 1024**3:
        score += 35
        reasons.append("Total Codex process memory is above 3.5 GB.")
    elif codex_mem > 2.0 * 1024**3:
        score += 20
        reasons.append("Total Codex process memory is above 2 GB.")
    if len(codex_processes) >= 6:
        score += 12
        reasons.append("Many Codex processes are loaded.")
    if len(runtime_processes) >= 12:
        score += 10
        reasons.append("Many Node/node_repl runtime processes are loaded.")
    if len(browser_processes) >= 10:
        score += 8
        reasons.append("Many browser/WebView processes are loaded.")
    if effort in {"xhigh", "max"}:
        score += 15
        reasons.append(f"Default reasoning effort is {effort}.")
    if db_size > 250 * 1024**2:
        score += 25
        reasons.append("logs_2.sqlite is very large.")
    if wal_size > 100 * 1024**2:
        score += 25
        reasons.append("logs_2.sqlite WAL is very large.")
    if "codex_block_trace_debug_logs_insert" not in triggers:
        score += 15
        reasons.append("TRACE/DEBUG log guard is not installed.")
    if memory.get("free_physical", 0) < 4 * 1024**3:
        score += 30
        reasons.append("System free physical memory is below 4 GB.")
    if recent_threads >= 20:
        score += 8
        reasons.append("Many recent threads are in local state.")

    level = "OK"
    if score >= 70:
        level = "CRITICAL"
    elif score >= 35:
        level = "WARN"
    return {
        "score": min(score, 100),
        "level": level,
        "reasons": reasons or ["No immediate Codex performance risk detected."],
        "totals": {
            "codex_processes": len(codex_processes),
            "runtime_processes": len(runtime_processes),
            "browser_processes": len(browser_processes),
            "codex_memory": codex_mem,
            "runtime_memory": runtime_mem,
        },
    }


def collect_snapshot() -> dict[str, Any]:
    home = codex_home()
    snapshot = {
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "collected_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "codex_home": str(home),
        "processes": collect_processes(),
        "system_memory": collect_system_memory(),
        "log_health": collect_log_health(home),
        "config": collect_config(home),
        "recent_threads": collect_recent_threads(home),
    }
    snapshot["risk"] = assess_risk(snapshot)
    return snapshot


@dataclass
class Columns:
    name: str
    headings: tuple[str, ...]
    widths: tuple[int, ...]


class CodexMonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1220x820")
        self.root.minsize(980, 680)
        self.queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.last_snapshot: dict[str, Any] | None = None
        self.previous_cpu: dict[int, tuple[float, float]] = {}
        self.auto_refresh = tk.BooleanVar(value=True)
        self.refresh_interval = tk.IntVar(value=3)
        self.status_text = tk.StringVar(value="Starting...")
        self._build_ui()
        self.refresh()
        self._poll_queue()
        self._schedule_refresh()

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=24)
        style.configure("Risk.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Card.TFrame", relief="solid", borderwidth=1)

        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)
        ttk.Label(top, text=APP_NAME, font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Checkbutton(top, text="Auto", variable=self.auto_refresh).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Label(top, text="Interval").pack(side=tk.RIGHT, padx=(10, 4))
        ttk.Spinbox(top, from_=2, to=60, textvariable=self.refresh_interval, width=4).pack(side=tk.RIGHT)

        self.cards = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        self.cards.pack(fill=tk.X)
        self.risk_label = ttk.Label(self.cards, text="Risk: -", style="Risk.TLabel")
        self.risk_label.grid(row=0, column=0, sticky="w", padx=(0, 20))
        self.summary_label = ttk.Label(self.cards, text="-", justify=tk.LEFT)
        self.summary_label.grid(row=0, column=1, sticky="w")
        self.reason_label = ttk.Label(self.cards, text="-", justify=tk.LEFT, foreground="#6b3d00")
        self.reason_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.cards.columnconfigure(1, weight=1)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Checkpoint Logs WAL", command=self.checkpoint_wal).pack(side=tk.LEFT)
        ttk.Button(actions, text="Install TRACE/DEBUG Guard", command=self.install_guard).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(actions, text="Export JSON Report", command=self.export_report).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(actions, textvariable=self.status_text).pack(side=tk.RIGHT)

        panes = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        panes.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        upper = ttk.Frame(panes)
        lower = ttk.Frame(panes)
        panes.add(upper, weight=3)
        panes.add(lower, weight=2)

        self.proc_tree = self._make_tree(
            upper,
            Columns(
                "processes",
                ("PID", "Category", "Name", "Memory", "CPU %", "CPU sec", "Started", "Path"),
                (70, 90, 160, 110, 80, 90, 150, 520),
            ),
        )
        notebook = ttk.Notebook(lower)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.health_text = tk.Text(notebook, height=8, wrap=tk.WORD)
        self.health_text.configure(font=("Consolas", 10))
        notebook.add(self.health_text, text="Health")

        thread_frame = ttk.Frame(notebook)
        self.thread_tree = self._make_tree(
            thread_frame,
            Columns(
                "threads",
                ("Updated", "Model", "Effort", "Tokens", "Title", "CWD", "Thread ID"),
                (150, 90, 90, 90, 240, 320, 260),
            ),
        )
        notebook.add(thread_frame, text="Recent Threads")

    def _make_tree(self, parent: ttk.Frame, columns: Columns) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns.headings, show="headings")
        y_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        for heading, width in zip(columns.headings, columns.widths):
            tree.heading(heading, text=heading)
            tree.column(heading, width=width, anchor=tk.W)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return tree

    def refresh(self) -> None:
        self.status_text.set("Collecting...")
        threading.Thread(target=self._collect_worker, daemon=True).start()

    def _collect_worker(self) -> None:
        try:
            snapshot = collect_snapshot()
            self.queue.put(("snapshot", snapshot))
        except Exception as exc:
            self.queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "snapshot":
                    self._render_snapshot(payload)
                elif kind == "error":
                    self.status_text.set(f"Error: {payload}")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _schedule_refresh(self) -> None:
        if self.auto_refresh.get():
            self.refresh()
        self.root.after(max(self.refresh_interval.get(), 2) * 1000, self._schedule_refresh)

    def _cpu_percent(self, process: dict[str, Any], now: float) -> float:
        pid = process["id"]
        cpu = process["cpu_seconds"]
        previous = self.previous_cpu.get(pid)
        self.previous_cpu[pid] = (cpu, now)
        if previous is None:
            return 0.0
        prev_cpu, prev_time = previous
        elapsed = max(now - prev_time, 0.01)
        cores = os.cpu_count() or 1
        return max((cpu - prev_cpu) / elapsed / cores * 100, 0.0)

    def _render_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.last_snapshot = snapshot
        now = time.time()
        risk = snapshot["risk"]
        totals = risk["totals"]
        memory = snapshot["system_memory"]
        log_health = snapshot["log_health"]
        config = snapshot["config"]

        color = {"OK": "#157347", "WARN": "#a35d00", "CRITICAL": "#b00020"}.get(risk["level"], "#222")
        self.risk_label.configure(text=f"Risk: {risk['level']} ({risk['score']}/100)", foreground=color)
        self.summary_label.configure(
            text=(
                f"Codex memory: {human_bytes(totals['codex_memory'])} across {totals['codex_processes']} processes | "
                f"Runtime memory: {human_bytes(totals['runtime_memory'])} | "
                f"System used: {memory['used_percent']:.1f}% ({human_bytes(memory['used_physical'])}/{human_bytes(memory['total_physical'])})\n"
                f"Model: {config.get('model') or '-'} / {config.get('reasoning_effort') or '-'} | "
                f"logs DB: {human_bytes(log_health.get('db_size'))}, WAL: {human_bytes(log_health.get('wal_size'))}, "
                f"rows: {log_health.get('count')}"
            )
        )
        self.reason_label.configure(text="; ".join(risk["reasons"][:4]))
        self.status_text.set(f"Updated {snapshot['collected_at']}")

        for item in self.proc_tree.get_children():
            self.proc_tree.delete(item)
        for process in snapshot["processes"]:
            cpu_pct = self._cpu_percent(process, now)
            self.proc_tree.insert(
                "",
                tk.END,
                values=(
                    process["id"],
                    process["category"],
                    process["name"],
                    human_bytes(process["working_set"]),
                    f"{cpu_pct:.1f}",
                    f"{process['cpu_seconds']:.1f}",
                    process["start_time"],
                    process["path"],
                ),
            )

        self._render_health(snapshot)
        for item in self.thread_tree.get_children():
            self.thread_tree.delete(item)
        for thread in snapshot["recent_threads"]:
            self.thread_tree.insert(
                "",
                tk.END,
                values=(
                    thread["updated"],
                    thread["model"],
                    thread["reasoning_effort"],
                    thread["tokens_used"],
                    thread["title"],
                    thread["cwd"],
                    thread["id"],
                ),
            )

    def _render_health(self, snapshot: dict[str, Any]) -> None:
        log_health = snapshot["log_health"]
        config = snapshot["config"]
        memory = snapshot["system_memory"]
        page_files = memory.get("page_files") or []
        lines = [
            f"Collected: {snapshot['collected_at']}",
            f"Codex home: {snapshot['codex_home']}",
            "",
            "[Config]",
            f"  model: {config.get('model')}",
            f"  reasoning_effort: {config.get('reasoning_effort')}",
            f"  MCP servers: {config.get('mcp_count')}",
            f"  enabled plugins: {len(config.get('enabled_plugins') or [])}",
            f"  memories enabled: {config.get('memories_enabled')}",
            "",
            "[Logs]",
            f"  path: {log_health.get('path')}",
            f"  db: {human_bytes(log_health.get('db_size'))}",
            f"  wal: {human_bytes(log_health.get('wal_size'))}",
            f"  rows: {log_health.get('count')}",
            f"  max_id: {log_health.get('max_id')}",
            f"  triggers: {', '.join(log_health.get('triggers') or []) or '-'}",
            f"  levels: {log_health.get('levels')}",
            f"  error: {log_health.get('error') or '-'}",
            "",
            "[System Memory]",
            f"  physical: {human_bytes(memory.get('used_physical'))} used / {human_bytes(memory.get('total_physical'))}",
            f"  virtual free: {human_bytes(memory.get('free_virtual'))}",
            f"  page files: {page_files}",
        ]
        self.health_text.configure(state=tk.NORMAL)
        self.health_text.delete("1.0", tk.END)
        self.health_text.insert(tk.END, "\n".join(lines))
        self.health_text.configure(state=tk.DISABLED)

    def checkpoint_wal(self) -> None:
        try:
            result = checkpoint_logs(codex_home())
            messagebox.showinfo(APP_NAME, result["message"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def install_guard(self) -> None:
        try:
            result = install_trace_guard(codex_home())
            messagebox.showinfo(APP_NAME, result["message"])
            self.refresh()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def export_report(self) -> None:
        if not self.last_snapshot:
            messagebox.showwarning(APP_NAME, "No snapshot collected yet.")
            return
        default_name = f"codex-performance-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path = filedialog.asksaveasfilename(
            title="Export JSON report",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.last_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo(APP_NAME, f"Saved {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--once", action="store_true", help="Collect one JSON snapshot and print it.")
    parser.add_argument("--checkpoint", action="store_true", help="Checkpoint/truncate logs_2.sqlite WAL and exit.")
    parser.add_argument("--install-guard", action="store_true", help="Install TRACE/DEBUG log guard and exit.")
    args = parser.parse_args()

    if args.checkpoint:
        print(json.dumps(checkpoint_logs(codex_home()), ensure_ascii=False, indent=2))
        return 0
    if args.install_guard:
        print(json.dumps(install_trace_guard(codex_home()), ensure_ascii=False, indent=2))
        return 0
    if args.once:
        print(json.dumps(collect_snapshot(), ensure_ascii=False, indent=2))
        return 0
    if tk is None or ttk is None:
        print("Tkinter is not available. Try --once for CLI mode.", file=sys.stderr)
        return 2
    root = tk.Tk()
    CodexMonitorApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
