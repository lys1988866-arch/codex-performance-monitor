# Codex Performance Monitor

Codex Performance Monitor は、Windows 上の Codex Desktop の負荷を確認するためのローカル デスクトップ ツールです。

Codex 専用のタスク マネージャーのように、Codex プロセス、Node/MCP ランタイム、ブラウザ/WebView、システム メモリ、`logs_2.sqlite`、モデル設定、プラグイン、最近のスレッドを表示します。

## 機能

- Codex 関連プロセス、メモリ、CPU の表示。
- システム メモリとページファイルの確認。
- `~/.codex/logs_2.sqlite`、WAL サイズ、ログ レベル、トリガーの確認。
- モデル、推論レベル、MCP サーバー、プラグインの表示。
- 最近の Codex スレッドの表示。
- リスク スコアと理由の表示。
- ログ WAL の checkpoint/truncate。
- TRACE/DEBUG ログ ガードの導入。
- JSON レポートの書き出し。

## 実行

```powershell
.\run.ps1
```

または：

```powershell
python .\src\codex_monitor_app.py
```

## 検証

```powershell
.\scripts\validate.ps1
```

## EXE ビルド

```powershell
.\scripts\build-exe.ps1
```

出力先：

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## 安全性

既定では読み取り専用です。手動操作ボタンはローカルの Codex ログ SQLite データベースだけを変更します。プロセスを終了したり、Codex をインストール/再インストールしたり、Codex プロジェクトを変更したりしません。
