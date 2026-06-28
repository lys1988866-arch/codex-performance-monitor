# Codex Performance Monitor

Codex Performance Monitor는 Windows에서 Codex Desktop의 부하를 확인하는 로컬 데스크톱 도구입니다.

Codex 전용 작업 관리자처럼 Codex 프로세스, Node/MCP 런타임, 브라우저/WebView, 시스템 메모리, `logs_2.sqlite`, 모델 설정, 플러그인, 최근 스레드를 보여 줍니다.

## 기능

- Codex 관련 프로세스, 메모리, CPU 표시.
- 시스템 메모리와 페이지 파일 확인.
- `~/.codex/logs_2.sqlite`, WAL 크기, 로그 레벨, 트리거 확인.
- 모델, 추론 수준, MCP 서버, 플러그인 표시.
- 최근 Codex 스레드 표시.
- 위험 점수와 구체적인 이유 표시.
- 실행 가능한 처리 단계 표시.
- 선택한 프로세스를 확인 후 종료.
- 선택한 PID 복사.
- 로그 WAL checkpoint/truncate.
- TRACE/DEBUG 로그 가드 설치.
- JSON 보고서 내보내기.

## 실행

```powershell
.\run.ps1
```

또는:

```powershell
python .\src\codex_monitor_app.py
```

## 검증

```powershell
.\scripts\validate.ps1
```

## EXE 빌드

```powershell
.\scripts\build-exe.ps1
```

출력:

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## 안전성

기본적으로 읽기 전용입니다. 로그 작업 버튼은 로컬 Codex 로그 SQLite 데이터베이스만 수정합니다. 프로세스 종료는 사용자가 선택하고 확인한 단일 프로세스에만 적용됩니다. Codex를 설치/재설치하거나 Codex 프로젝트를 수정하지 않습니다.
