# Codex Performance Monitor

Codex Performance Monitor ist ein lokales Windows-Desktop-Tool, das die Last von Codex Desktop sichtbar macht.

Es funktioniert wie ein spezialisierter Task-Manager fuer Codex: Codex-Prozesse, Node/MCP-Runtimes, Browser/WebView, Systemspeicher, `logs_2.sqlite`, Modellkonfiguration, Plugins und aktuelle Threads.

## Funktionen

- Tabelle der Codex-bezogenen Prozesse mit Speicher und CPU.
- Uebersicht ueber Systemspeicher und Auslagerungsdateien.
- Zustand von `~/.codex/logs_2.sqlite`, WAL, Log-Leveln und Triggern.
- Aktuelles Modell, Reasoning-Stufe, MCP-Server und aktive Plugins.
- Aktuelle lokale Codex-Threads.
- Risikowert mit konkreten Gruenden.
- Aktionsbereich mit praktischen Schritten.
- Speicher optimieren, indem Working Sets ueberwachter Prozesse gekuerzt werden.
- Ausgewaehlten Prozess nach expliziter Bestaetigung beenden.
- Ausgewaehlte PID kopieren.
- Checkpoint/truncate fuer das Logs-WAL.
- Installation eines TRACE/DEBUG-Log-Schutzes.
- JSON-Bericht exportieren.

## Starten

```powershell
.\run.ps1
```

Oder:

```powershell
python .\src\codex_monitor_app.py
```

## Validieren

```powershell
.\scripts\validate.ps1
```

## EXE bauen

```powershell
.\scripts\build-exe.ps1
```

Ausgabe:

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## Sicherheit

Standardmaessig ist das Tool nur lesend. Die Log-Buttons aendern nur die lokale SQLite-Logdatenbank von Codex. Speicher optimieren fordert Windows nur zum Kuerzen von Working Sets auf und beendet keine Prozesse. Prozessbeenden betrifft nur den ausgewaehlten und bestaetigten Prozess. Es installiert Codex nicht, installiert Codex nicht neu und aendert keine Codex-Projekte.
