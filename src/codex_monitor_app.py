from __future__ import annotations

import argparse
import ctypes
import json
import locale
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
APP_VERSION = "0.4.2"
WATCHED_PROCESS_PATTERN = (
    "Codex|codex|codex-command-runner|node|node_repl|chrome|msedge|msedgewebview2|python|dotnet"
)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-CN": "简体中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}
LANGUAGE_CODES_BY_LABEL = {label: code for code, label in SUPPORTED_LANGUAGES.items()}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "refresh": "Refresh",
        "auto": "Auto",
        "interval": "Interval",
        "language": "Language",
        "risk": "Risk",
        "collecting": "Collecting...",
        "starting": "Starting...",
        "updated": "Updated {time}",
        "error_prefix": "Error",
        "checkpoint": "Checkpoint Logs WAL",
        "install_guard": "Install TRACE/DEBUG Guard",
        "optimize_memory": "Optimize Memory",
        "end_process": "End Selected Process",
        "copy_pid": "Copy PID",
        "export": "Export JSON Report",
        "actions": "Actions",
        "health": "Health",
        "recent_threads": "Recent Threads",
        "col_pid": "PID",
        "col_category": "Category",
        "col_name": "Name",
        "col_memory": "Memory",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU sec",
        "col_started": "Started",
        "col_path": "Path",
        "col_updated": "Updated",
        "col_model": "Model",
        "col_effort": "Effort",
        "col_tokens": "Tokens",
        "col_title": "Title",
        "col_cwd": "CWD",
        "col_thread_id": "Thread ID",
        "summary": (
            "Codex memory: {codex_memory} across {codex_processes} processes | "
            "Runtime memory: {runtime_memory} | "
            "System used: {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "Model: {model} / {effort} | logs DB: {db_size}, WAL: {wal_size}, rows: {rows}"
        ),
        "collected": "Collected",
        "codex_home": "Codex home",
        "config": "Config",
        "model": "model",
        "reasoning_effort": "reasoning_effort",
        "mcp_servers": "MCP servers",
        "enabled_plugins": "enabled plugins",
        "memories_enabled": "memories enabled",
        "logs": "Logs",
        "path": "path",
        "db": "db",
        "wal": "wal",
        "rows": "rows",
        "max_id": "max_id",
        "triggers": "triggers",
        "levels": "levels",
        "error": "error",
        "system_memory": "System Memory",
        "physical": "physical",
        "used": "used",
        "virtual_free": "virtual free",
        "page_files": "page files",
        "no_snapshot": "No snapshot collected yet.",
        "export_title": "Export JSON report",
        "saved": "Saved {path}",
        "optimizing": "Optimizing memory...",
        "confirm_optimize_title": "Optimize memory?",
        "confirm_optimize_memory": (
            "Trim working-set memory for {count} monitored processes?\n\n"
            "This does not kill processes or delete data. Windows may page memory back in later, and busy apps may feel slower briefly."
        ),
        "optimize_done": "Optimized {success}/{attempted} processes. Estimated physical memory released: {released}.",
        "optimize_failed": "Some processes could not be optimized: {failed} failed.",
        "no_process_selected": "Select a process first.",
        "pid_copied": "Copied PID {pid}.",
        "confirm_end_title": "End process?",
        "confirm_end_process": (
            "End this process now?\n\n"
            "PID: {pid}\n"
            "Name: {name}\n"
            "Memory: {memory}\n"
            "Path: {path}\n\n"
            "Ending Codex, Node, browser, or runtime processes can interrupt active tasks. Save work first."
        ),
        "terminate_done": "Terminated PID {pid}.",
        "terminate_failed": "Failed to terminate PID {pid}: {error}",
        "cannot_terminate_self": "The monitor cannot terminate itself.",
        "actions_header": "Recommended actions",
        "actions_top_process": "Top memory process: PID {pid}, {name}, {memory}",
        "actions_selected_process": "Selected process: PID {pid}, {name}, {memory}",
        "actions_no_selection": "No process selected. Select a row in the process table to act on it.",
        "actions_step_select": "1. Sort by Memory and select a stale Node, browser/WebView, or old Codex worker process.",
        "actions_step_optimize": "2. Use Optimize Memory to trim reclaimable working-set memory without killing processes.",
        "actions_step_end": "3. Use End Selected Process only after confirming it is not doing useful work.",
        "actions_step_logs": "4. Use Checkpoint Logs WAL and Install TRACE/DEBUG Guard when log size or WAL growth contributes to risk.",
        "actions_step_threads": "5. Close or archive completed Codex threads, stop unused dev servers, and reduce parallel heavy tasks.",
        "actions_step_restart": "6. If Codex main memory stays high after work is saved, restart Codex Desktop manually.",
        "checkpoint_done": "WAL checkpoint/truncate completed.",
        "guard_done": "TRACE/DEBUG guard installed.",
        "risk_single_process": "A single monitored process is above 1.8 GB.",
        "risk_codex_mem_high": "Total Codex process memory is above 3.5 GB.",
        "risk_codex_mem_warn": "Total Codex process memory is above 2 GB.",
        "risk_many_codex": "Many Codex processes are loaded.",
        "risk_many_runtime": "Many Node/node_repl runtime processes are loaded.",
        "risk_many_browser": "Many browser/WebView processes are loaded.",
        "risk_effort": "Default reasoning effort is {effort}.",
        "risk_db_large": "logs_2.sqlite is very large.",
        "risk_wal_large": "logs_2.sqlite WAL is very large.",
        "risk_guard_missing": "TRACE/DEBUG log guard is not installed.",
        "risk_low_memory": "System free physical memory is below 4 GB.",
        "risk_many_threads": "Many recent threads are in local state.",
        "risk_none": "No immediate Codex performance risk detected.",
        "risk_more_points": "more",
    },
    "zh-CN": {
        "refresh": "刷新",
        "auto": "自动",
        "interval": "间隔",
        "language": "语言",
        "risk": "风险",
        "collecting": "正在采集...",
        "starting": "正在启动...",
        "updated": "已更新 {time}",
        "error_prefix": "错误",
        "checkpoint": "截断日志 WAL",
        "install_guard": "安装 TRACE/DEBUG 拦截",
        "optimize_memory": "优化内存",
        "end_process": "结束选中进程",
        "copy_pid": "复制 PID",
        "export": "导出 JSON 报告",
        "actions": "处理动作",
        "health": "健康状态",
        "recent_threads": "最近会话",
        "col_pid": "PID",
        "col_category": "类别",
        "col_name": "名称",
        "col_memory": "内存",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU 秒",
        "col_started": "启动时间",
        "col_path": "路径",
        "col_updated": "更新时间",
        "col_model": "模型",
        "col_effort": "推理档位",
        "col_tokens": "Token",
        "col_title": "标题",
        "col_cwd": "工作目录",
        "col_thread_id": "会话 ID",
        "summary": (
            "Codex 内存：{codex_memory}，共 {codex_processes} 个进程 | "
            "运行时内存：{runtime_memory} | "
            "系统已用：{used_percent:.1f}%（{used_physical}/{total_physical}）\n"
            "模型：{model} / {effort} | 日志 DB：{db_size}，WAL：{wal_size}，行数：{rows}"
        ),
        "collected": "采集时间",
        "codex_home": "Codex 主目录",
        "config": "配置",
        "model": "模型",
        "reasoning_effort": "推理档位",
        "mcp_servers": "MCP 服务",
        "enabled_plugins": "已启用插件",
        "memories_enabled": "记忆已启用",
        "logs": "日志",
        "path": "路径",
        "db": "数据库",
        "wal": "WAL",
        "rows": "行数",
        "max_id": "最大 ID",
        "triggers": "触发器",
        "levels": "级别",
        "error": "错误",
        "system_memory": "系统内存",
        "physical": "物理内存",
        "used": "已用",
        "virtual_free": "可用虚拟内存",
        "page_files": "分页文件",
        "no_snapshot": "还没有采集快照。",
        "export_title": "导出 JSON 报告",
        "saved": "已保存 {path}",
        "optimizing": "正在优化内存...",
        "confirm_optimize_title": "优化内存？",
        "confirm_optimize_memory": (
            "对 {count} 个受监控进程修剪工作集内存吗？\n\n"
            "这不会结束进程，也不会删除数据。Windows 后续可能会把部分内存重新换入，忙碌中的应用可能短暂变慢。"
        ),
        "optimize_done": "已优化 {success}/{attempted} 个进程。估算释放物理内存：{released}。",
        "optimize_failed": "部分进程无法优化：失败 {failed} 个。",
        "no_process_selected": "请先选中一个进程。",
        "pid_copied": "已复制 PID {pid}。",
        "confirm_end_title": "结束进程？",
        "confirm_end_process": (
            "现在结束这个进程吗？\n\n"
            "PID：{pid}\n"
            "名称：{name}\n"
            "内存：{memory}\n"
            "路径：{path}\n\n"
            "结束 Codex、Node、浏览器或运行时进程可能会中断正在执行的任务。请先确认工作已保存。"
        ),
        "terminate_done": "已结束 PID {pid}。",
        "terminate_failed": "结束 PID {pid} 失败：{error}",
        "cannot_terminate_self": "监控器不能结束自身进程。",
        "actions_header": "建议处理动作",
        "actions_top_process": "最高内存进程：PID {pid}，{name}，{memory}",
        "actions_selected_process": "当前选中进程：PID {pid}，{name}，{memory}",
        "actions_no_selection": "尚未选中进程。请先在进程表格里选中一行。",
        "actions_step_select": "1. 按内存排序，优先选中已经不用的 Node、浏览器/WebView 或旧 Codex worker。",
        "actions_step_optimize": "2. 先点击“优化内存”，在不结束进程的情况下回收可释放工作集内存。",
        "actions_step_end": "3. 确认它不是正在工作的任务后，再点击“结束选中进程”。",
        "actions_step_logs": "4. 如果日志 DB/WAL 偏大，先执行“截断日志 WAL”和“安装 TRACE/DEBUG 拦截”。",
        "actions_step_threads": "5. 关闭或归档已完成的 Codex 会话，停止不用的开发服务器，减少并行重任务。",
        "actions_step_restart": "6. 如果保存工作后 Codex 主进程内存仍长期偏高，手动重启 Codex Desktop。",
        "checkpoint_done": "WAL checkpoint/truncate 已完成。",
        "guard_done": "TRACE/DEBUG 拦截已安装。",
        "risk_single_process": "单个受监控进程超过 1.8 GB。",
        "risk_codex_mem_high": "Codex 进程总内存超过 3.5 GB。",
        "risk_codex_mem_warn": "Codex 进程总内存超过 2 GB。",
        "risk_many_codex": "Codex 进程数量偏多。",
        "risk_many_runtime": "Node/node_repl 运行时进程数量偏多。",
        "risk_many_browser": "浏览器/WebView 进程数量偏多。",
        "risk_effort": "默认推理档位为 {effort}。",
        "risk_db_large": "logs_2.sqlite 文件很大。",
        "risk_wal_large": "logs_2.sqlite WAL 文件很大。",
        "risk_guard_missing": "尚未安装 TRACE/DEBUG 日志拦截。",
        "risk_low_memory": "系统可用物理内存低于 4 GB。",
        "risk_many_threads": "本地最近会话数量偏多。",
        "risk_none": "未检测到明显的 Codex 性能风险。",
        "risk_more_points": "其他",
    },
    "ja": {
        "refresh": "更新",
        "auto": "自動",
        "interval": "間隔",
        "language": "言語",
        "risk": "リスク",
        "collecting": "収集中...",
        "starting": "起動中...",
        "updated": "更新済み {time}",
        "error_prefix": "エラー",
        "checkpoint": "ログ WAL を切り詰め",
        "install_guard": "TRACE/DEBUG ガードを導入",
        "optimize_memory": "メモリ最適化",
        "end_process": "選択プロセスを終了",
        "copy_pid": "PID をコピー",
        "export": "JSON レポートを書き出し",
        "actions": "操作",
        "health": "ヘルス",
        "recent_threads": "最近のスレッド",
    },
    "ko": {
        "refresh": "새로 고침",
        "auto": "자동",
        "interval": "간격",
        "language": "언어",
        "risk": "위험",
        "collecting": "수집 중...",
        "starting": "시작 중...",
        "updated": "업데이트됨 {time}",
        "error_prefix": "오류",
        "checkpoint": "로그 WAL 정리",
        "install_guard": "TRACE/DEBUG 가드 설치",
        "optimize_memory": "메모리 최적화",
        "end_process": "선택한 프로세스 종료",
        "copy_pid": "PID 복사",
        "export": "JSON 보고서 내보내기",
        "actions": "작업",
        "health": "상태",
        "recent_threads": "최근 스레드",
    },
    "es": {
        "refresh": "Actualizar",
        "auto": "Auto",
        "interval": "Intervalo",
        "language": "Idioma",
        "risk": "Riesgo",
        "collecting": "Recopilando...",
        "starting": "Iniciando...",
        "updated": "Actualizado {time}",
        "error_prefix": "Error",
        "checkpoint": "Truncar WAL de logs",
        "install_guard": "Instalar guardia TRACE/DEBUG",
        "optimize_memory": "Optimizar memoria",
        "end_process": "Finalizar proceso seleccionado",
        "copy_pid": "Copiar PID",
        "export": "Exportar informe JSON",
        "actions": "Acciones",
        "health": "Estado",
        "recent_threads": "Hilos recientes",
    },
    "fr": {
        "refresh": "Actualiser",
        "auto": "Auto",
        "interval": "Intervalle",
        "language": "Langue",
        "risk": "Risque",
        "collecting": "Collecte...",
        "starting": "Demarrage...",
        "updated": "Mis a jour {time}",
        "error_prefix": "Erreur",
        "checkpoint": "Tronquer le WAL des logs",
        "install_guard": "Installer la garde TRACE/DEBUG",
        "optimize_memory": "Optimiser la memoire",
        "end_process": "Terminer le processus selectionne",
        "copy_pid": "Copier le PID",
        "export": "Exporter le rapport JSON",
        "actions": "Actions",
        "health": "Sante",
        "recent_threads": "Fils recents",
    },
    "de": {
        "refresh": "Aktualisieren",
        "auto": "Auto",
        "interval": "Intervall",
        "language": "Sprache",
        "risk": "Risiko",
        "collecting": "Sammle...",
        "starting": "Starte...",
        "updated": "Aktualisiert {time}",
        "error_prefix": "Fehler",
        "checkpoint": "Logs-WAL kuerzen",
        "install_guard": "TRACE/DEBUG-Schutz installieren",
        "optimize_memory": "Speicher optimieren",
        "end_process": "Ausgewaehlten Prozess beenden",
        "copy_pid": "PID kopieren",
        "export": "JSON-Bericht exportieren",
        "actions": "Aktionen",
        "health": "Status",
        "recent_threads": "Aktuelle Threads",
    },
}

RISK_REASON_KEYS = {
    "A single monitored process is above 1.8 GB.": "risk_single_process",
    "Total Codex process memory is above 3.5 GB.": "risk_codex_mem_high",
    "Total Codex process memory is above 2 GB.": "risk_codex_mem_warn",
    "Many Codex processes are loaded.": "risk_many_codex",
    "Many Node/node_repl runtime processes are loaded.": "risk_many_runtime",
    "Many browser/WebView processes are loaded.": "risk_many_browser",
    "logs_2.sqlite is very large.": "risk_db_large",
    "logs_2.sqlite WAL is very large.": "risk_wal_large",
    "TRACE/DEBUG log guard is not installed.": "risk_guard_missing",
    "System free physical memory is below 4 GB.": "risk_low_memory",
    "Many recent threads are in local state.": "risk_many_threads",
    "No immediate Codex performance risk detected.": "risk_none",
}

TRANSLATIONS["ja"].update(
    {
        "col_pid": "PID",
        "col_category": "カテゴリ",
        "col_name": "名前",
        "col_memory": "メモリ",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU 秒",
        "col_started": "開始時刻",
        "col_path": "パス",
        "col_updated": "更新",
        "col_model": "モデル",
        "col_effort": "推論",
        "col_tokens": "トークン",
        "col_title": "タイトル",
        "col_cwd": "作業フォルダ",
        "col_thread_id": "スレッド ID",
        "summary": (
            "Codex メモリ: {codex_memory} / {codex_processes} プロセス | "
            "ランタイム メモリ: {runtime_memory} | "
            "システム使用率: {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "モデル: {model} / {effort} | ログ DB: {db_size}, WAL: {wal_size}, 行: {rows}"
        ),
        "collected": "収集時刻",
        "codex_home": "Codex ホーム",
        "config": "設定",
        "model": "モデル",
        "reasoning_effort": "推論レベル",
        "mcp_servers": "MCP サーバー",
        "enabled_plugins": "有効なプラグイン",
        "memories_enabled": "メモリ有効",
        "logs": "ログ",
        "path": "パス",
        "db": "DB",
        "wal": "WAL",
        "rows": "行",
        "max_id": "最大 ID",
        "triggers": "トリガー",
        "levels": "レベル",
        "error": "エラー",
        "system_memory": "システム メモリ",
        "physical": "物理メモリ",
        "used": "使用中",
        "virtual_free": "空き仮想メモリ",
        "page_files": "ページファイル",
        "no_snapshot": "まだスナップショットがありません。",
        "export_title": "JSON レポートを書き出し",
        "saved": "保存しました: {path}",
        "checkpoint_done": "WAL の checkpoint/truncate が完了しました。",
        "guard_done": "TRACE/DEBUG ガードを導入しました。",
        "risk_single_process": "監視対象の単一プロセスが 1.8 GB を超えています。",
        "risk_codex_mem_high": "Codex プロセスの合計メモリが 3.5 GB を超えています。",
        "risk_codex_mem_warn": "Codex プロセスの合計メモリが 2 GB を超えています。",
        "risk_many_codex": "Codex プロセスが多すぎます。",
        "risk_many_runtime": "Node/node_repl ランタイム プロセスが多すぎます。",
        "risk_many_browser": "ブラウザ/WebView プロセスが多すぎます。",
        "risk_effort": "既定の推論レベルは {effort} です。",
        "risk_db_large": "logs_2.sqlite が非常に大きいです。",
        "risk_wal_large": "logs_2.sqlite の WAL が非常に大きいです。",
        "risk_guard_missing": "TRACE/DEBUG ログ ガードが導入されていません。",
        "risk_low_memory": "空き物理メモリが 4 GB 未満です。",
        "risk_many_threads": "ローカル状態に最近のスレッドが多すぎます。",
        "risk_none": "直近の Codex パフォーマンス リスクは検出されませんでした。",
        "risk_more_points": "その他",
    }
)

TRANSLATIONS["ko"].update(
    {
        "col_pid": "PID",
        "col_category": "분류",
        "col_name": "이름",
        "col_memory": "메모리",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU 초",
        "col_started": "시작 시간",
        "col_path": "경로",
        "col_updated": "업데이트",
        "col_model": "모델",
        "col_effort": "추론",
        "col_tokens": "토큰",
        "col_title": "제목",
        "col_cwd": "작업 폴더",
        "col_thread_id": "스레드 ID",
        "summary": (
            "Codex 메모리: {codex_memory}, {codex_processes}개 프로세스 | "
            "런타임 메모리: {runtime_memory} | "
            "시스템 사용: {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "모델: {model} / {effort} | 로그 DB: {db_size}, WAL: {wal_size}, 행: {rows}"
        ),
        "collected": "수집 시간",
        "codex_home": "Codex 홈",
        "config": "설정",
        "model": "모델",
        "reasoning_effort": "추론 수준",
        "mcp_servers": "MCP 서버",
        "enabled_plugins": "활성 플러그인",
        "memories_enabled": "메모리 활성",
        "logs": "로그",
        "path": "경로",
        "db": "DB",
        "wal": "WAL",
        "rows": "행",
        "max_id": "최대 ID",
        "triggers": "트리거",
        "levels": "레벨",
        "error": "오류",
        "system_memory": "시스템 메모리",
        "physical": "물리 메모리",
        "used": "사용됨",
        "virtual_free": "가상 메모리 여유",
        "page_files": "페이지 파일",
        "no_snapshot": "아직 수집된 스냅샷이 없습니다.",
        "export_title": "JSON 보고서 내보내기",
        "saved": "저장됨: {path}",
        "checkpoint_done": "WAL checkpoint/truncate가 완료되었습니다.",
        "guard_done": "TRACE/DEBUG 가드가 설치되었습니다.",
        "risk_single_process": "감시 중인 단일 프로세스가 1.8 GB를 초과했습니다.",
        "risk_codex_mem_high": "Codex 프로세스 총 메모리가 3.5 GB를 초과했습니다.",
        "risk_codex_mem_warn": "Codex 프로세스 총 메모리가 2 GB를 초과했습니다.",
        "risk_many_codex": "Codex 프로세스가 많이 실행 중입니다.",
        "risk_many_runtime": "Node/node_repl 런타임 프로세스가 많이 실행 중입니다.",
        "risk_many_browser": "브라우저/WebView 프로세스가 많이 실행 중입니다.",
        "risk_effort": "기본 추론 수준은 {effort}입니다.",
        "risk_db_large": "logs_2.sqlite 파일이 매우 큽니다.",
        "risk_wal_large": "logs_2.sqlite WAL 파일이 매우 큽니다.",
        "risk_guard_missing": "TRACE/DEBUG 로그 가드가 설치되어 있지 않습니다.",
        "risk_low_memory": "시스템 여유 물리 메모리가 4 GB 미만입니다.",
        "risk_many_threads": "로컬 상태에 최근 스레드가 많습니다.",
        "risk_none": "즉각적인 Codex 성능 위험이 감지되지 않았습니다.",
        "risk_more_points": "기타",
    }
)

TRANSLATIONS["es"].update(
    {
        "col_pid": "PID",
        "col_category": "Categoria",
        "col_name": "Nombre",
        "col_memory": "Memoria",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU s",
        "col_started": "Inicio",
        "col_path": "Ruta",
        "col_updated": "Actualizado",
        "col_model": "Modelo",
        "col_effort": "Razonamiento",
        "col_tokens": "Tokens",
        "col_title": "Titulo",
        "col_cwd": "Directorio",
        "col_thread_id": "ID de hilo",
        "summary": (
            "Memoria de Codex: {codex_memory} en {codex_processes} procesos | "
            "Memoria de runtime: {runtime_memory} | "
            "Sistema usado: {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "Modelo: {model} / {effort} | DB de logs: {db_size}, WAL: {wal_size}, filas: {rows}"
        ),
        "collected": "Recopilado",
        "codex_home": "Inicio de Codex",
        "config": "Configuracion",
        "model": "modelo",
        "reasoning_effort": "nivel de razonamiento",
        "mcp_servers": "servidores MCP",
        "enabled_plugins": "plugins activos",
        "memories_enabled": "memoria activa",
        "logs": "Logs",
        "path": "ruta",
        "db": "db",
        "wal": "wal",
        "rows": "filas",
        "max_id": "id maximo",
        "triggers": "triggers",
        "levels": "niveles",
        "error": "error",
        "system_memory": "Memoria del sistema",
        "physical": "fisica",
        "used": "usada",
        "virtual_free": "virtual libre",
        "page_files": "archivos de paginacion",
        "no_snapshot": "Aun no hay una captura.",
        "export_title": "Exportar informe JSON",
        "saved": "Guardado: {path}",
        "checkpoint_done": "WAL checkpoint/truncate completado.",
        "guard_done": "Guardia TRACE/DEBUG instalada.",
        "risk_single_process": "Un proceso supervisado supera 1.8 GB.",
        "risk_codex_mem_high": "La memoria total de procesos Codex supera 3.5 GB.",
        "risk_codex_mem_warn": "La memoria total de procesos Codex supera 2 GB.",
        "risk_many_codex": "Hay muchos procesos Codex cargados.",
        "risk_many_runtime": "Hay muchos procesos Node/node_repl cargados.",
        "risk_many_browser": "Hay muchos procesos de navegador/WebView cargados.",
        "risk_effort": "El razonamiento predeterminado es {effort}.",
        "risk_db_large": "logs_2.sqlite es muy grande.",
        "risk_wal_large": "El WAL de logs_2.sqlite es muy grande.",
        "risk_guard_missing": "La guardia de logs TRACE/DEBUG no esta instalada.",
        "risk_low_memory": "La memoria fisica libre esta por debajo de 4 GB.",
        "risk_many_threads": "Hay muchos hilos recientes en el estado local.",
        "risk_none": "No se detecto un riesgo inmediato de rendimiento de Codex.",
        "risk_more_points": "mas",
    }
)

TRANSLATIONS["fr"].update(
    {
        "col_pid": "PID",
        "col_category": "Categorie",
        "col_name": "Nom",
        "col_memory": "Memoire",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU s",
        "col_started": "Demarre",
        "col_path": "Chemin",
        "col_updated": "Mis a jour",
        "col_model": "Modele",
        "col_effort": "Raisonnement",
        "col_tokens": "Tokens",
        "col_title": "Titre",
        "col_cwd": "Dossier",
        "col_thread_id": "ID du fil",
        "summary": (
            "Memoire Codex : {codex_memory} sur {codex_processes} processus | "
            "Memoire runtime : {runtime_memory} | "
            "Systeme utilise : {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "Modele : {model} / {effort} | DB logs : {db_size}, WAL : {wal_size}, lignes : {rows}"
        ),
        "collected": "Collecte",
        "codex_home": "Dossier Codex",
        "config": "Configuration",
        "model": "modele",
        "reasoning_effort": "niveau de raisonnement",
        "mcp_servers": "serveurs MCP",
        "enabled_plugins": "plugins actifs",
        "memories_enabled": "memoire active",
        "logs": "Logs",
        "path": "chemin",
        "db": "db",
        "wal": "wal",
        "rows": "lignes",
        "max_id": "id max",
        "triggers": "triggers",
        "levels": "niveaux",
        "error": "erreur",
        "system_memory": "Memoire systeme",
        "physical": "physique",
        "used": "utilisee",
        "virtual_free": "virtuelle libre",
        "page_files": "fichiers d'echange",
        "no_snapshot": "Aucune capture collectee.",
        "export_title": "Exporter le rapport JSON",
        "saved": "Enregistre : {path}",
        "checkpoint_done": "WAL checkpoint/truncate termine.",
        "guard_done": "Garde TRACE/DEBUG installee.",
        "risk_single_process": "Un processus surveille depasse 1.8 Go.",
        "risk_codex_mem_high": "La memoire totale des processus Codex depasse 3.5 Go.",
        "risk_codex_mem_warn": "La memoire totale des processus Codex depasse 2 Go.",
        "risk_many_codex": "De nombreux processus Codex sont charges.",
        "risk_many_runtime": "De nombreux processus Node/node_repl sont charges.",
        "risk_many_browser": "De nombreux processus navigateur/WebView sont charges.",
        "risk_effort": "Le niveau de raisonnement par defaut est {effort}.",
        "risk_db_large": "logs_2.sqlite est tres volumineux.",
        "risk_wal_large": "Le WAL de logs_2.sqlite est tres volumineux.",
        "risk_guard_missing": "La garde TRACE/DEBUG n'est pas installee.",
        "risk_low_memory": "La memoire physique libre est inferieure a 4 Go.",
        "risk_many_threads": "L'etat local contient beaucoup de fils recents.",
        "risk_none": "Aucun risque immediat de performance Codex detecte.",
        "risk_more_points": "autres",
    }
)

TRANSLATIONS["de"].update(
    {
        "col_pid": "PID",
        "col_category": "Kategorie",
        "col_name": "Name",
        "col_memory": "Speicher",
        "col_cpu_pct": "CPU %",
        "col_cpu_sec": "CPU s",
        "col_started": "Start",
        "col_path": "Pfad",
        "col_updated": "Aktualisiert",
        "col_model": "Modell",
        "col_effort": "Reasoning",
        "col_tokens": "Tokens",
        "col_title": "Titel",
        "col_cwd": "Ordner",
        "col_thread_id": "Thread-ID",
        "summary": (
            "Codex-Speicher: {codex_memory} in {codex_processes} Prozessen | "
            "Runtime-Speicher: {runtime_memory} | "
            "System genutzt: {used_percent:.1f}% ({used_physical}/{total_physical})\n"
            "Modell: {model} / {effort} | Logs-DB: {db_size}, WAL: {wal_size}, Zeilen: {rows}"
        ),
        "collected": "Erfasst",
        "codex_home": "Codex-Home",
        "config": "Konfiguration",
        "model": "Modell",
        "reasoning_effort": "Reasoning-Stufe",
        "mcp_servers": "MCP-Server",
        "enabled_plugins": "aktive Plugins",
        "memories_enabled": "Memory aktiv",
        "logs": "Logs",
        "path": "Pfad",
        "db": "DB",
        "wal": "WAL",
        "rows": "Zeilen",
        "max_id": "max_id",
        "triggers": "Trigger",
        "levels": "Level",
        "error": "Fehler",
        "system_memory": "Systemspeicher",
        "physical": "physisch",
        "used": "genutzt",
        "virtual_free": "virtuell frei",
        "page_files": "Auslagerungsdateien",
        "no_snapshot": "Noch kein Snapshot erfasst.",
        "export_title": "JSON-Bericht exportieren",
        "saved": "Gespeichert: {path}",
        "checkpoint_done": "WAL checkpoint/truncate abgeschlossen.",
        "guard_done": "TRACE/DEBUG-Schutz installiert.",
        "risk_single_process": "Ein ueberwachter Prozess liegt ueber 1.8 GB.",
        "risk_codex_mem_high": "Der gesamte Codex-Prozessspeicher liegt ueber 3.5 GB.",
        "risk_codex_mem_warn": "Der gesamte Codex-Prozessspeicher liegt ueber 2 GB.",
        "risk_many_codex": "Viele Codex-Prozesse sind geladen.",
        "risk_many_runtime": "Viele Node/node_repl-Runtime-Prozesse sind geladen.",
        "risk_many_browser": "Viele Browser/WebView-Prozesse sind geladen.",
        "risk_effort": "Die Standard-Reasoning-Stufe ist {effort}.",
        "risk_db_large": "logs_2.sqlite ist sehr gross.",
        "risk_wal_large": "Das WAL von logs_2.sqlite ist sehr gross.",
        "risk_guard_missing": "TRACE/DEBUG-Log-Schutz ist nicht installiert.",
        "risk_low_memory": "Freier physischer Speicher liegt unter 4 GB.",
        "risk_many_threads": "Viele aktuelle Threads sind im lokalen Zustand.",
        "risk_none": "Kein unmittelbares Codex-Performance-Risiko erkannt.",
        "risk_more_points": "weitere",
    }
)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def detect_language() -> str:
    language = (locale.getlocale()[0] or "").replace("_", "-").lower()
    if language.startswith("zh"):
        return "zh-CN"
    for code in ("ja", "ko", "es", "fr", "de"):
        if language.startswith(code):
            return code
    return "en"


def translate(language: str, key: str, **kwargs: Any) -> str:
    template = TRANSLATIONS.get(language, {}).get(key) or TRANSLATIONS["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template


def translate_risk_reason(language: str, reason: str) -> str:
    prefix = "Default reasoning effort is "
    if reason.startswith(prefix) and reason.endswith("."):
        effort = reason.removeprefix(prefix).removesuffix(".")
        return translate(language, "risk_effort", effort=effort)
    key = RISK_REASON_KEYS.get(reason)
    if key:
        return translate(language, key)
    return reason


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
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
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
        startupinfo=startupinfo,
        creationflags=creationflags,
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


def terminate_process(pid: int) -> dict[str, Any]:
    if pid == os.getpid():
        return {"ok": False, "error": "cannot_terminate_self"}
    if os.name != "nt":
        return {"ok": False, "error": "Process termination is implemented only on Windows."}

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    open_process.restype = ctypes.c_void_p
    terminate = kernel32.TerminateProcess
    terminate.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    terminate.restype = ctypes.c_int
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int

    process_terminate = 0x0001
    handle = open_process(process_terminate, 0, int(pid))
    if not handle:
        error = ctypes.get_last_error()
        return {"ok": False, "error": ctypes.FormatError(error).strip() or f"Windows error {error}"}
    try:
        if not terminate(handle, 1):
            error = ctypes.get_last_error()
            return {"ok": False, "error": ctypes.FormatError(error).strip() or f"Windows error {error}"}
    finally:
        close_handle(handle)
    return {"ok": True}


def optimize_working_sets(processes: list[dict[str, Any]]) -> dict[str, Any]:
    if os.name != "nt":
        return {"ok": False, "error": "Memory optimization is implemented only on Windows."}

    current_pid = os.getpid()
    targets: dict[int, dict[str, Any]] = {}
    for process in processes:
        pid = int(process.get("id") or 0)
        if pid and pid != current_pid:
            targets[pid] = process

    if not targets:
        return {"ok": True, "attempted": 0, "success": 0, "failed": 0, "released": 0, "failures": []}

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    open_process.restype = ctypes.c_void_p
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    empty_working_set = psapi.EmptyWorkingSet
    empty_working_set.argtypes = [ctypes.c_void_p]
    empty_working_set.restype = ctypes.c_int

    process_query_information = 0x0400
    process_set_quota = 0x0100
    access = process_query_information | process_set_quota
    failures: list[dict[str, Any]] = []
    success = 0

    for pid, process in targets.items():
        handle = open_process(access, 0, pid)
        if not handle:
            error = ctypes.get_last_error()
            failures.append(
                {
                    "pid": pid,
                    "name": process.get("name", ""),
                    "error": ctypes.FormatError(error).strip() or f"Windows error {error}",
                }
            )
            continue
        try:
            if empty_working_set(handle):
                success += 1
            else:
                error = ctypes.get_last_error()
                failures.append(
                    {
                        "pid": pid,
                        "name": process.get("name", ""),
                        "error": ctypes.FormatError(error).strip() or f"Windows error {error}",
                    }
                )
        finally:
            close_handle(handle)

    time.sleep(0.5)
    after = {process["id"]: process for process in collect_processes()}
    released = 0
    for pid, before_process in targets.items():
        after_process = after.get(pid)
        if after_process:
            released += max(int(before_process.get("working_set") or 0) - int(after_process.get("working_set") or 0), 0)

    return {
        "ok": True,
        "attempted": len(targets),
        "success": success,
        "failed": len(failures),
        "released": released,
        "failures": failures,
    }


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
    raw_score = 0
    load_score = 0
    pressure_score = 0
    reasons: list[str] = []
    factors: list[dict[str, Any]] = []
    used_percent = float(memory.get("used_percent") or 0.0)
    free_physical = int(memory.get("free_physical") or 0)
    memory_is_healthy = free_physical >= 16 * 1024**3 and used_percent < 75.0

    def add_factor(points: int, reason: str, kind: str = "pressure") -> None:
        nonlocal raw_score, load_score, pressure_score
        raw_score += points
        if kind == "load":
            load_score += points
        else:
            pressure_score += points
        reasons.append(reason)
        factors.append({"points": points, "reason": reason, "kind": kind})

    if max_proc > 1.8 * 1024**3:
        add_factor(35, "A single monitored process is above 1.8 GB.")
    if codex_mem > 3.5 * 1024**3:
        add_factor(30, "Total Codex process memory is above 3.5 GB.")
    elif codex_mem > 2.0 * 1024**3:
        add_factor(18, "Total Codex process memory is above 2 GB.")
    if len(codex_processes) >= 6:
        add_factor(12, "Many Codex processes are loaded.", "load")
    if len(runtime_processes) >= 12:
        add_factor(10, "Many Node/node_repl runtime processes are loaded.", "load")
    if len(browser_processes) >= 10:
        add_factor(8, "Many browser/WebView processes are loaded.", "load")
    if effort in {"xhigh", "max"}:
        add_factor(15, f"Default reasoning effort is {effort}.", "load")
    if db_size > 250 * 1024**2:
        add_factor(25, "logs_2.sqlite is very large.")
    if wal_size > 100 * 1024**2:
        add_factor(25, "logs_2.sqlite WAL is very large.")
    if "codex_block_trace_debug_logs_insert" not in triggers:
        add_factor(15, "TRACE/DEBUG log guard is not installed.")
    if memory.get("free_physical", 0) < 4 * 1024**3:
        add_factor(30, "System free physical memory is below 4 GB.")
    if recent_threads >= 20:
        add_factor(8, "Many recent threads are in local state.", "load")

    # High-reasoning Codex workloads can look large while the host is still healthy.
    # Keep the load visible, but do not let load-only factors permanently pin the app at 100.
    score = pressure_score + (min(load_score, 15) if memory_is_healthy else load_score)

    level = "OK"
    if score >= 75:
        level = "CRITICAL"
    elif score >= 35:
        level = "WARN"
    return {
        "score": min(score, 100),
        "raw_score": raw_score,
        "pressure_score": pressure_score,
        "load_score": load_score,
        "memory_is_healthy": memory_is_healthy,
        "level": level,
        "reasons": reasons or ["No immediate Codex performance risk detected."],
        "factors": factors,
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


def summarize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    log_health = snapshot["log_health"]
    config = snapshot["config"]
    risk = snapshot["risk"]
    totals = risk["totals"]
    memory = snapshot["system_memory"]
    return {
        "app": snapshot["app"],
        "collected_at": snapshot["collected_at"],
        "risk": {
            "level": risk["level"],
            "score": risk["score"],
            "raw_score": risk.get("raw_score"),
            "pressure_score": risk.get("pressure_score"),
            "load_score": risk.get("load_score"),
            "memory_is_healthy": risk.get("memory_is_healthy"),
            "reasons": risk["reasons"],
            "factors": risk.get("factors", []),
        },
        "processes": {
            "total": len(snapshot["processes"]),
            "codex": totals["codex_processes"],
            "runtime": totals["runtime_processes"],
            "browser": totals["browser_processes"],
            "codex_memory": totals["codex_memory"],
            "runtime_memory": totals["runtime_memory"],
        },
        "system_memory": {
            "used_percent": memory.get("used_percent"),
            "free_physical": memory.get("free_physical"),
            "total_physical": memory.get("total_physical"),
        },
        "logs": {
            "db_size": log_health.get("db_size"),
            "wal_size": log_health.get("wal_size"),
            "rows": log_health.get("count"),
            "max_id": log_health.get("max_id"),
            "triggers": log_health.get("triggers"),
        },
        "config": {
            "model": config.get("model"),
            "reasoning_effort": config.get("reasoning_effort"),
            "mcp_count": config.get("mcp_count"),
            "enabled_plugins": len(config.get("enabled_plugins") or []),
        },
        "recent_threads": len(snapshot.get("recent_threads") or []),
    }


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
        self.language = tk.StringVar(value=SUPPORTED_LANGUAGES[detect_language()])
        self.status_text = tk.StringVar(value=self._t("starting"))
        self._build_ui()
        self.refresh()
        self._poll_queue()
        self._schedule_refresh()

    def _language_code(self) -> str:
        return LANGUAGE_CODES_BY_LABEL.get(self.language.get(), "en")

    def _t(self, key: str, **kwargs: Any) -> str:
        return translate(self._language_code(), key, **kwargs)

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
        self.refresh_button = ttk.Button(top, text=self._t("refresh"), command=self.refresh)
        self.refresh_button.pack(side=tk.RIGHT, padx=(6, 0))
        self.auto_check = ttk.Checkbutton(top, text=self._t("auto"), variable=self.auto_refresh)
        self.auto_check.pack(side=tk.RIGHT, padx=(6, 0))
        self.interval_label = ttk.Label(top, text=self._t("interval"))
        self.interval_label.pack(side=tk.RIGHT, padx=(10, 4))
        ttk.Spinbox(top, from_=2, to=60, textvariable=self.refresh_interval, width=4).pack(side=tk.RIGHT)
        self.language_combo = ttk.Combobox(
            top,
            textvariable=self.language,
            values=list(SUPPORTED_LANGUAGES.values()),
            state="readonly",
            width=12,
        )
        self.language_combo.pack(side=tk.RIGHT, padx=(12, 0))
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_change)
        self.language_label = ttk.Label(top, text=self._t("language"))
        self.language_label.pack(side=tk.RIGHT, padx=(10, 4))

        self.cards = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        self.cards.pack(fill=tk.X)
        self.risk_label = ttk.Label(self.cards, text=f"{self._t('risk')}: -", style="Risk.TLabel")
        self.risk_label.grid(row=0, column=0, sticky="w", padx=(0, 20))
        self.summary_label = ttk.Label(self.cards, text="-", justify=tk.LEFT)
        self.summary_label.grid(row=0, column=1, sticky="w")
        self.reason_label = ttk.Label(self.cards, text="-", justify=tk.LEFT, foreground="#6b3d00")
        self.reason_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.cards.columnconfigure(1, weight=1)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.pack(fill=tk.X)
        self.checkpoint_button = ttk.Button(actions, text=self._t("checkpoint"), command=self.checkpoint_wal)
        self.checkpoint_button.pack(side=tk.LEFT)
        self.guard_button = ttk.Button(actions, text=self._t("install_guard"), command=self.install_guard)
        self.guard_button.pack(side=tk.LEFT, padx=(8, 0))
        self.optimize_memory_button = ttk.Button(actions, text=self._t("optimize_memory"), command=self.optimize_memory)
        self.optimize_memory_button.pack(side=tk.LEFT, padx=(8, 0))
        self.end_process_button = ttk.Button(actions, text=self._t("end_process"), command=self.end_selected_process)
        self.end_process_button.pack(side=tk.LEFT, padx=(8, 0))
        self.copy_pid_button = ttk.Button(actions, text=self._t("copy_pid"), command=self.copy_selected_pid)
        self.copy_pid_button.pack(side=tk.LEFT, padx=(8, 0))
        self.export_button = ttk.Button(actions, text=self._t("export"), command=self.export_report)
        self.export_button.pack(side=tk.LEFT, padx=(8, 0))
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
                ("col_pid", "col_category", "col_name", "col_memory", "col_cpu_pct", "col_cpu_sec", "col_started", "col_path"),
                (70, 90, 160, 110, 80, 90, 150, 520),
            ),
        )
        self.proc_tree.bind("<<TreeviewSelect>>", self._on_process_select)
        self.notebook = ttk.Notebook(lower)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.actions_text = tk.Text(self.notebook, height=8, wrap=tk.WORD)
        self.actions_text.configure(font=("Segoe UI", 10))
        self.notebook.add(self.actions_text, text=self._t("actions"))

        self.health_text = tk.Text(self.notebook, height=8, wrap=tk.WORD)
        self.health_text.configure(font=("Consolas", 10))
        self.notebook.add(self.health_text, text=self._t("health"))

        thread_frame = ttk.Frame(self.notebook)
        self.thread_tree = self._make_tree(
            thread_frame,
            Columns(
                "threads",
                ("col_updated", "col_model", "col_effort", "col_tokens", "col_title", "col_cwd", "col_thread_id"),
                (150, 90, 90, 90, 240, 320, 260),
            ),
        )
        self.notebook.add(thread_frame, text=self._t("recent_threads"))

    def _on_language_change(self, _event: object | None = None) -> None:
        self._apply_language()

    def _apply_language(self) -> None:
        self.refresh_button.configure(text=self._t("refresh"))
        self.auto_check.configure(text=self._t("auto"))
        self.interval_label.configure(text=self._t("interval"))
        self.language_label.configure(text=self._t("language"))
        self.checkpoint_button.configure(text=self._t("checkpoint"))
        self.guard_button.configure(text=self._t("install_guard"))
        self.optimize_memory_button.configure(text=self._t("optimize_memory"))
        self.end_process_button.configure(text=self._t("end_process"))
        self.copy_pid_button.configure(text=self._t("copy_pid"))
        self.export_button.configure(text=self._t("export"))
        self.notebook.tab(0, text=self._t("actions"))
        self.notebook.tab(1, text=self._t("health"))
        self.notebook.tab(2, text=self._t("recent_threads"))
        for column in self.proc_tree["columns"]:
            self.proc_tree.heading(column, text=self._t(column))
        for column in self.thread_tree["columns"]:
            self.thread_tree.heading(column, text=self._t(column))
        if self.last_snapshot:
            self._render_snapshot(self.last_snapshot)
        else:
            self.risk_label.configure(text=f"{self._t('risk')}: -")
            self.status_text.set(self._t("starting"))

    def _on_process_select(self, _event: object | None = None) -> None:
        if self.last_snapshot:
            self._render_actions(self.last_snapshot)

    def _make_tree(self, parent: ttk.Frame, columns: Columns) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns.headings, show="headings")
        y_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        for heading, width in zip(columns.headings, columns.widths):
            tree.heading(heading, text=self._t(heading))
            tree.column(heading, width=width, anchor=tk.W)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return tree

    def refresh(self) -> None:
        self.status_text.set(self._t("collecting"))
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
                    self.status_text.set(f"{self._t('error_prefix')}: {payload}")
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
        self.risk_label.configure(text=f"{self._t('risk')}: {risk['level']} ({risk['score']}/100)", foreground=color)
        self.summary_label.configure(
            text=self._t(
                "summary",
                codex_memory=human_bytes(totals["codex_memory"]),
                codex_processes=totals["codex_processes"],
                runtime_memory=human_bytes(totals["runtime_memory"]),
                used_percent=memory["used_percent"],
                used_physical=human_bytes(memory["used_physical"]),
                total_physical=human_bytes(memory["total_physical"]),
                model=config.get("model") or "-",
                effort=config.get("reasoning_effort") or "-",
                db_size=human_bytes(log_health.get("db_size")),
                wal_size=human_bytes(log_health.get("wal_size")),
                rows=log_health.get("count"),
            )
        )
        factors = risk.get("factors") or []
        if factors:
            localized_reasons = [
                f"+{factor['points']} {translate_risk_reason(self._language_code(), factor['reason'])}"
                for factor in factors[:6]
            ]
            if len(factors) > 6:
                localized_reasons.append(
                    f"+{sum(factor['points'] for factor in factors[6:])} {self._t('risk_more_points')}"
                )
        else:
            localized_reasons = [translate_risk_reason(self._language_code(), reason) for reason in risk["reasons"][:4]]
        self.reason_label.configure(text="; ".join(localized_reasons))
        self.status_text.set(self._t("updated", time=snapshot["collected_at"]))

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

        self._render_actions(snapshot)
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

    def _selected_process(self) -> dict[str, Any] | None:
        selected = self.proc_tree.selection()
        if not selected or not self.last_snapshot:
            return None
        values = self.proc_tree.item(selected[0], "values")
        if not values:
            return None
        try:
            pid = int(values[0])
        except (TypeError, ValueError):
            return None
        for process in self.last_snapshot.get("processes", []):
            if process.get("id") == pid:
                return process
        return None

    def _render_actions(self, snapshot: dict[str, Any]) -> None:
        processes = snapshot.get("processes") or []
        top_process = processes[0] if processes else None
        selected = self._selected_process()
        lines = [self._t("actions_header"), ""]
        if top_process:
            lines.append(
                self._t(
                    "actions_top_process",
                    pid=top_process["id"],
                    name=top_process["name"],
                    memory=human_bytes(top_process["working_set"]),
                )
            )
        if selected:
            lines.append(
                self._t(
                    "actions_selected_process",
                    pid=selected["id"],
                    name=selected["name"],
                    memory=human_bytes(selected["working_set"]),
                )
            )
        else:
            lines.append(self._t("actions_no_selection"))
        lines.extend(
            [
                "",
                self._t("actions_step_select"),
                self._t("actions_step_optimize"),
                self._t("actions_step_end"),
                self._t("actions_step_logs"),
                self._t("actions_step_threads"),
                self._t("actions_step_restart"),
            ]
        )
        self.actions_text.configure(state=tk.NORMAL)
        self.actions_text.delete("1.0", tk.END)
        self.actions_text.insert(tk.END, "\n".join(lines))
        self.actions_text.configure(state=tk.DISABLED)

    def _render_health(self, snapshot: dict[str, Any]) -> None:
        log_health = snapshot["log_health"]
        config = snapshot["config"]
        memory = snapshot["system_memory"]
        page_files = memory.get("page_files") or []
        lines = [
            f"{self._t('collected')}: {snapshot['collected_at']}",
            f"{self._t('codex_home')}: {snapshot['codex_home']}",
            "",
            f"[{self._t('config')}]",
            f"  {self._t('model')}: {config.get('model')}",
            f"  {self._t('reasoning_effort')}: {config.get('reasoning_effort')}",
            f"  {self._t('mcp_servers')}: {config.get('mcp_count')}",
            f"  {self._t('enabled_plugins')}: {len(config.get('enabled_plugins') or [])}",
            f"  {self._t('memories_enabled')}: {config.get('memories_enabled')}",
            "",
            f"[{self._t('logs')}]",
            f"  {self._t('path')}: {log_health.get('path')}",
            f"  {self._t('db')}: {human_bytes(log_health.get('db_size'))}",
            f"  {self._t('wal')}: {human_bytes(log_health.get('wal_size'))}",
            f"  {self._t('rows')}: {log_health.get('count')}",
            f"  {self._t('max_id')}: {log_health.get('max_id')}",
            f"  {self._t('triggers')}: {', '.join(log_health.get('triggers') or []) or '-'}",
            f"  {self._t('levels')}: {log_health.get('levels')}",
            f"  {self._t('error')}: {log_health.get('error') or '-'}",
            "",
            f"[{self._t('system_memory')}]",
            f"  {self._t('physical')}: {human_bytes(memory.get('used_physical'))} {self._t('used')} / {human_bytes(memory.get('total_physical'))}",
            f"  {self._t('virtual_free')}: {human_bytes(memory.get('free_virtual'))}",
            f"  {self._t('page_files')}: {page_files}",
        ]
        self.health_text.configure(state=tk.NORMAL)
        self.health_text.delete("1.0", tk.END)
        self.health_text.insert(tk.END, "\n".join(lines))
        self.health_text.configure(state=tk.DISABLED)

    def optimize_memory(self) -> None:
        if not self.last_snapshot:
            messagebox.showwarning(APP_NAME, self._t("no_snapshot"))
            return
        processes = list(self.last_snapshot.get("processes") or [])
        targets = [process for process in processes if int(process.get("id") or 0) != os.getpid()]
        if not targets:
            messagebox.showwarning(APP_NAME, self._t("no_process_selected"))
            return
        confirmed = messagebox.askyesno(
            self._t("confirm_optimize_title"),
            self._t("confirm_optimize_memory", count=len(targets)),
            icon=messagebox.WARNING,
        )
        if not confirmed:
            return
        self.status_text.set(self._t("optimizing"))
        self.root.update_idletasks()
        result = optimize_working_sets(targets)
        if not result.get("ok"):
            messagebox.showerror(APP_NAME, str(result.get("error") or "Memory optimization failed."))
            return
        message = self._t(
            "optimize_done",
            success=result.get("success", 0),
            attempted=result.get("attempted", 0),
            released=human_bytes(result.get("released", 0)),
        )
        if result.get("failed"):
            message = f"{message}\n{self._t('optimize_failed', failed=result.get('failed'))}"
        messagebox.showinfo(APP_NAME, message)
        self.refresh()

    def copy_selected_pid(self) -> None:
        process = self._selected_process()
        if not process:
            messagebox.showwarning(APP_NAME, self._t("no_process_selected"))
            return
        pid = str(process["id"])
        self.root.clipboard_clear()
        self.root.clipboard_append(pid)
        self.status_text.set(self._t("pid_copied", pid=pid))

    def end_selected_process(self) -> None:
        process = self._selected_process()
        if not process:
            messagebox.showwarning(APP_NAME, self._t("no_process_selected"))
            return
        pid = int(process["id"])
        if pid == os.getpid():
            messagebox.showwarning(APP_NAME, self._t("cannot_terminate_self"))
            return
        confirmed = messagebox.askyesno(
            self._t("confirm_end_title"),
            self._t(
                "confirm_end_process",
                pid=pid,
                name=process["name"],
                memory=human_bytes(process["working_set"]),
                path=process["path"] or "-",
            ),
            icon=messagebox.WARNING,
        )
        if not confirmed:
            return
        result = terminate_process(pid)
        if result.get("ok"):
            self.status_text.set(self._t("terminate_done", pid=pid))
            self.refresh()
            return
        error = result.get("error")
        if error == "cannot_terminate_self":
            message = self._t("cannot_terminate_self")
        else:
            message = self._t("terminate_failed", pid=pid, error=error)
        messagebox.showerror(APP_NAME, message)

    def checkpoint_wal(self) -> None:
        try:
            result = checkpoint_logs(codex_home())
            message = self._t("checkpoint_done") if result.get("ok") else result["message"]
            messagebox.showinfo(APP_NAME, message)
            self.refresh()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def install_guard(self) -> None:
        try:
            result = install_trace_guard(codex_home())
            message = self._t("guard_done") if result.get("ok") else result["message"]
            messagebox.showinfo(APP_NAME, message)
            self.refresh()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def export_report(self) -> None:
        if not self.last_snapshot:
            messagebox.showwarning(APP_NAME, self._t("no_snapshot"))
            return
        default_name = f"codex-performance-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path = filedialog.asksaveasfilename(
            title=self._t("export_title"),
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.last_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo(APP_NAME, self._t("saved", path=path))


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--once", action="store_true", help="Collect one JSON snapshot and print it.")
    parser.add_argument("--summary", action="store_true", help="Collect one compact JSON summary and print it.")
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
    if args.summary:
        print(json.dumps(summarize_snapshot(collect_snapshot()), ensure_ascii=False, indent=2))
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
