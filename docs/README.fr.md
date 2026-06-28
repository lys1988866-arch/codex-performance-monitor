# Codex Performance Monitor

Codex Performance Monitor est un outil de bureau local pour Windows qui rend visible la pression de performance de Codex Desktop.

Il fonctionne comme un gestionnaire de taches specialise pour Codex : processus Codex, runtimes Node/MCP, navigateur/WebView, memoire systeme, `logs_2.sqlite`, configuration du modele, plugins et fils recents.

## Fonctions

- Tableau des processus lies a Codex, memoire et CPU.
- Resume de la memoire systeme et des fichiers d'echange.
- Etat de `~/.codex/logs_2.sqlite`, WAL, niveaux de logs et triggers.
- Modele courant, niveau de raisonnement, serveurs MCP et plugins actifs.
- Fils locaux recents.
- Score de risque avec raisons concretes.
- Panneau d'actions avec etapes pratiques.
- Terminer un processus selectionne apres confirmation explicite.
- Copier le PID selectionne.
- Checkpoint/truncate du WAL des logs.
- Installation d'une garde pour les logs TRACE/DEBUG.
- Export de rapport JSON.

## Lancer

```powershell
.\run.ps1
```

Ou :

```powershell
python .\src\codex_monitor_app.py
```

## Valider

```powershell
.\scripts\validate.ps1
```

## Construire l'EXE

```powershell
.\scripts\build-exe.ps1
```

Sortie :

```powershell
.\dist\CodexPerformanceMonitor\CodexPerformanceMonitor.exe
```

## Securite

Par defaut l'outil est en lecture seule. Les boutons de logs ne modifient que la base SQLite locale des logs Codex. L'action de terminaison ne concerne que le processus selectionne et confirme. Il n'installe pas Codex, ne reinstalle pas Codex et ne modifie pas les projets Codex.
