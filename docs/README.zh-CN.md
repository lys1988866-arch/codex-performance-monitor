# Codex Performance Monitor

Codex Performance Monitor 是一个 Windows 本地桌面工具，用来观察 Codex Desktop 的运行压力。

它像一个专门面向 Codex 的任务管理器：监控 Codex 进程、Node/MCP 运行时、浏览器/WebView 进程、系统内存、`logs_2.sqlite` 日志健康状态、模型配置、插件数量和最近会话。

## 功能

- 查看 Codex 相关进程、内存和 CPU。
- 检查系统内存、分页文件和运行时压力。
- 检查 `~/.codex/logs_2.sqlite`、WAL 大小、日志级别和触发器。
- 显示当前模型、推理档位、MCP 服务和已启用插件。
- 查看最近本地 Codex 会话。
- 给出风险评分和具体原因。
- 一键 checkpoint/truncate 日志 WAL。
- 一键安装 TRACE/DEBUG 日志拦截。
- 导出 JSON 报告。

## 运行

```powershell
.\run.ps1
```

或：

```powershell
python .\src\codex_monitor_app.py
```

命令行摘要：

```powershell
python .\src\codex_monitor_app.py --summary
```

## 验证

```powershell
.\scripts\validate.ps1
```

## 打包

```powershell
.\scripts\build-exe.ps1
```

生成的程序位于：

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## 安全说明

默认只读。只有两个手动按钮会修改本机 Codex 日志数据库：截断 WAL、安装 TRACE/DEBUG 拦截。它不会杀进程、不会安装或重装 Codex，也不会修改你的 Codex 项目。
