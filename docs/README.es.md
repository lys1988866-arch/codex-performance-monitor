# Codex Performance Monitor

Codex Performance Monitor es una herramienta de escritorio local para Windows que muestra la presion de rendimiento de Codex Desktop.

Funciona como un administrador de tareas especializado para Codex: muestra procesos de Codex, runtimes Node/MCP, navegador/WebView, memoria del sistema, `logs_2.sqlite`, configuracion del modelo, plugins y conversaciones recientes.

## Funciones

- Tabla de procesos relacionados con Codex, memoria y CPU.
- Resumen de memoria del sistema y archivo de paginacion.
- Estado de `~/.codex/logs_2.sqlite`, WAL, niveles de log y triggers.
- Modelo actual, nivel de razonamiento, servidores MCP y plugins activos.
- Conversaciones locales recientes.
- Puntuacion de riesgo con razones concretas.
- Panel de acciones con pasos practicos.
- Optimizar memoria recortando el working set de procesos supervisados.
- Finalizar un proceso seleccionado con confirmacion explicita.
- Copiar el PID seleccionado.
- Checkpoint/truncate del WAL de logs.
- Instalacion de guardia para logs TRACE/DEBUG.
- Exportacion de informe JSON.

## Ejecutar

```powershell
.\run.ps1
```

O:

```powershell
python .\src\codex_monitor_app.py
```

## Validar

```powershell
.\scripts\validate.ps1
```

## Crear EXE

```powershell
.\scripts\build-exe.ps1
```

Salida:

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## Seguridad

Por defecto es de solo lectura. Los botones de logs solo modifican la base SQLite local de logs de Codex. Optimizar memoria solo pide a Windows recortar working sets y no mata procesos. La accion de finalizar proceso solo termina el proceso seleccionado y confirmado. No instala ni reinstala Codex y no modifica proyectos de Codex.
