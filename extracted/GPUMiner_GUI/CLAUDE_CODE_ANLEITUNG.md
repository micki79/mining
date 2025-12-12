# 🚀 Claude Code - Komplette Anleitung für GPU Mining Projekt

## Was ist Claude Code?

Claude Code ist ein **Terminal-Agent** der direkt auf deinem PC arbeitet:
- ✅ Liest und schreibt Dateien
- ✅ Führt Python-Code aus
- ✅ Testet automatisch
- ✅ Fixt Fehler selbstständig
- ✅ Macht Git Commits

**Vorteil:** Du sagst was du willst, Claude macht es!

---

## 📋 Voraussetzungen

| Was | Warum | Download |
|-----|-------|----------|
| Node.js 18+ | Für npm/npx | https://nodejs.org |
| Python 3.8+ | Für dein Projekt | https://python.org |
| Claude Pro/Team | API-Zugang | https://claude.ai |

---

## 🔧 Installation Schritt für Schritt

### Schritt 1: Node.js installieren

```
1. Gehe zu: https://nodejs.org
2. Klicke auf "LTS" (grüner Button)
3. Führe den Installer aus
4. Alle Optionen auf Standard lassen
5. "Next" → "Next" → "Install" → "Finish"
```

**[BILD 1: Node.js Website]**
```
┌─────────────────────────────────────────────────────────┐
│  nodejs.org                                             │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │                 │  │                 │              │
│  │  22.x.x LTS     │  │  23.x.x Current │              │
│  │  Recommended    │  │                 │              │
│  │                 │  │                 │              │
│  │  [DOWNLOAD]  ←──┼──┼─ DIESEN KLICKEN │              │
│  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Prüfen ob installiert:**
```cmd
node --version
# Sollte zeigen: v22.x.x oder höher
```

---

### Schritt 2: Claude Code installieren

Öffne **PowerShell als Administrator**:

```
1. Windows-Taste drücken
2. "PowerShell" tippen
3. Rechtsklick → "Als Administrator ausführen"
```

**[BILD 2: PowerShell als Admin]**
```
┌─────────────────────────────────────────────────────────┐
│  🔍 PowerShell                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Windows PowerShell                              │   │
│  │  ├─ Öffnen                                       │   │
│  │  ├─ Als Administrator ausführen  ← DIESES       │   │
│  │  ├─ Dateispeicherort öffnen                     │   │
│  │  └─ An Start anheften                           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**In PowerShell eingeben:**
```powershell
npm install -g @anthropic-ai/claude-code
```

**[BILD 3: Installation läuft]**
```
┌─────────────────────────────────────────────────────────┐
│  Administrator: Windows PowerShell                      │
│─────────────────────────────────────────────────────────│
│  PS C:\> npm install -g @anthropic-ai/claude-code       │
│                                                         │
│  added 156 packages in 45s                              │
│                                                         │
│  12 packages are looking for funding                    │
│    run `npm fund` for details                           │
│                                                         │
│  PS C:\> _                                              │
│                                                         │
│  ✅ Installation erfolgreich!                           │
└─────────────────────────────────────────────────────────┘
```

---

### Schritt 3: Claude Code starten

```powershell
# In dein Projekt-Verzeichnis wechseln
cd C:\GPUMiner_GUI

# Claude Code starten
claude
```

**[BILD 4: Claude Code startet]**
```
┌─────────────────────────────────────────────────────────┐
│  C:\GPUMiner_GUI                                        │
│─────────────────────────────────────────────────────────│
│                                                         │
│   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗     │
│  ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝     │
│  ██║     ██║     ███████║██║   ██║██║  ██║█████╗       │
│  ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝       │
│  ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗     │
│   ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝     │
│                                                         │
│  Claude Code v1.0.60                                    │
│  Working directory: C:\GPUMiner_GUI                     │
│                                                         │
│  Type your request or /help for commands                │
│                                                         │
│  > _                                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### Schritt 4: Mit Anthropic-Konto anmelden

Beim ersten Start öffnet sich ein Browser-Fenster:

**[BILD 5: Login-Fenster]**
```
┌─────────────────────────────────────────────────────────┐
│  🌐 Claude Code Authentication                          │
│─────────────────────────────────────────────────────────│
│                                                         │
│     ┌─────────────────────────────────────────┐        │
│     │                                         │        │
│     │   Sign in to Claude Code                │        │
│     │                                         │        │
│     │   [Google]  [Continue with Google]      │        │
│     │                                         │        │
│     │   ─────── or ───────                    │        │
│     │                                         │        │
│     │   Email: [________________]             │        │
│     │                                         │        │
│     │   [Continue with Email]                 │        │
│     │                                         │        │
│     └─────────────────────────────────────────┘        │
│                                                         │
│  Nutze dasselbe Konto wie für claude.ai!               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎮 Claude Code Befehle für dein Mining-Projekt

### Basis-Befehle

| Befehl | Was passiert |
|--------|--------------|
| `/help` | Zeigt alle Befehle |
| `/clear` | Leert den Chat |
| `/compact` | Komprimiert Kontext |
| `/cost` | Zeigt API-Kosten |
| `/quit` | Beendet Claude Code |

---

## 🔨 Praktische Beispiele für dein Projekt

### Test 1: Alle Module testen
```
> Führe python TEST_ALL.py aus und zeige mir die Ergebnisse
```

**[BILD 6: Test-Ausführung]**
```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│─────────────────────────────────────────────────────────│
│  > Führe python TEST_ALL.py aus und zeige mir die       │
│    Ergebnisse                                           │
│                                                         │
│  ⏳ Running: python TEST_ALL.py                         │
│                                                         │
│  ╔══════════════════════════════════════════════════╗  │
│  ║  FINALE TESTS - GPU MINING PROFIT SWITCHER       ║  │
│  ╠══════════════════════════════════════════════════╣  │
│  ║  ✅ Python Syntax:     9/9 Dateien OK            ║  │
│  ║  ✅ Module Imports:    6/6 Module OK             ║  │
│  ║  ✅ Algorithmen:       28/28 mit Hashrate        ║  │
│  ║  ✅ Pool-Config:       23 Coins mit Pools        ║  │
│  ║  ❌ pynvml:            Nicht installiert         ║  │
│  ╚══════════════════════════════════════════════════╝  │
│                                                         │
│  Ich sehe dass pynvml fehlt. Soll ich es installieren? │
│                                                         │
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Test 2: Fehler automatisch fixen
```
> Ja, installiere pynvml und alle anderen fehlenden Module
```

**[BILD 7: Auto-Fix]**
```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│─────────────────────────────────────────────────────────│
│  > Ja, installiere pynvml und alle anderen fehlenden    │
│    Module                                               │
│                                                         │
│  ⏳ Running: pip install pynvml PySide6 pyqtgraph       │
│                                                         │
│  Collecting pynvml                                      │
│    Downloading pynvml-11.5.0-py3-none-any.whl           │
│  Collecting PySide6                                     │
│    Downloading PySide6-6.6.1-cp311-win_amd64.whl        │
│  Collecting pyqtgraph                                   │
│    Downloading pyqtgraph-0.13.3-py3-none-any.whl        │
│                                                         │
│  ✅ Successfully installed:                             │
│     - pynvml 11.5.0                                     │
│     - PySide6 6.6.1                                     │
│     - pyqtgraph 0.13.3                                  │
│                                                         │
│  Soll ich die Tests erneut ausführen?                   │
│                                                         │
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Test 3: GUI starten und prüfen
```
> Starte die Mining GUI und prüfe ob sie ohne Fehler startet
```

**[BILD 8: GUI-Start]**
```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│─────────────────────────────────────────────────────────│
│  > Starte die Mining GUI und prüfe ob sie ohne Fehler   │
│    startet                                              │
│                                                         │
│  ⏳ Running: python mining_gui.py                       │
│                                                         │
│  2024-11-30 15:30:01 - INFO - GUI initialisiert         │
│  2024-11-30 15:30:02 - INFO - Theme geladen: dark       │
│  2024-11-30 15:30:03 - INFO - Tabs erstellt             │
│  2024-11-30 15:30:04 - INFO - CoinEx Sync gestartet     │
│  2024-11-30 15:30:35 - INFO - 47 Wallets geladen        │
│                                                         │
│  ✅ GUI läuft erfolgreich!                              │
│                                                         │
│  Erkannte Komponenten:                                  │
│  - Dashboard Tab: OK                                    │
│  - Auto-Profit Tab: OK (47 Coins mit Wallets)           │
│  - Multi-GPU Tab: OK (1 GPU erkannt: RTX 3080)          │
│  - Miner Tab: OK (T-Rex, lolMiner installiert)          │
│                                                         │
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Test 4: CoinEx Wallets synchronisieren
```
> Synchronisiere alle Wallets von CoinEx und zeige mir welche geladen wurden
```

**[BILD 9: Wallet-Sync]**
```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│─────────────────────────────────────────────────────────│
│  > Synchronisiere alle Wallets von CoinEx               │
│                                                         │
│  ⏳ Running: python SYNC_COINEX.py                      │
│                                                         │
│  ═══════════════════════════════════════════════════    │
│    COINEX WALLET SYNC                                   │
│  ═══════════════════════════════════════════════════    │
│                                                         │
│  ✅ API konfiguriert: 57C8835180...                     │
│  ✅ Verbindung OK                                       │
│  ⏳ Lade Wallets... (kann 30-60 Sekunden dauern)        │
│                                                         │
│  ✅ 47 Wallets geladen!                                 │
│                                                         │
│  Mining-Coins gefunden:                                 │
│  ✅ RVN   → RUVuL3CG2c9qTX3bCr32...                     │
│  ✅ ERG   → 9gXA8UYPGvh4FMy5K1JQ...                     │
│  ✅ ETC   → 0x132070583632ef5c5b...                     │
│  ✅ FLUX  → t1N6QKc6YgvGiQ5m2XEy...                     │
│  ✅ KAS   → kaspa:qrmkhf524evudd...                     │
│  ✅ GRIN  → grin1qvxy3j4k5l6m7n...                      │
│  ... und 41 weitere                                     │
│                                                         │
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Test 5: Kompletten Bug-Fix
```
> Finde und fixe alle Fehler in der GUI. Teste danach ob alles funktioniert.
```

**[BILD 10: Automatischer Bug-Fix]**
```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│─────────────────────────────────────────────────────────│
│  > Finde und fixe alle Fehler in der GUI                │
│                                                         │
│  🔍 Analysiere Code...                                  │
│                                                         │
│  Gefundene Probleme:                                    │
│  1. multi_gpu_widget.py:156 - pynvml Funktion falsch    │
│  2. mining_gui.py:892 - Pool "N/A" nicht behandelt      │
│  3. coinex_api.py:234 - Wallet-Format inkonsistent      │
│                                                         │
│  🔧 Fixe Problem 1/3...                                 │
│  ✅ multi_gpu_widget.py aktualisiert                    │
│                                                         │
│  🔧 Fixe Problem 2/3...                                 │
│  ✅ mining_gui.py aktualisiert                          │
│                                                         │
│  🔧 Fixe Problem 3/3...                                 │
│  ✅ coinex_api.py aktualisiert                          │
│                                                         │
│  🧪 Führe Tests aus...                                  │
│  ✅ Alle 25 Tests bestanden!                            │
│                                                         │
│  📝 Änderungen:                                         │
│  - 3 Dateien geändert                                   │
│  - 15 Zeilen hinzugefügt                                │
│  - 8 Zeilen entfernt                                    │
│                                                         │
│  Soll ich die Änderungen committen?                     │
│                                                         │
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Die wichtigsten Befehle für dein Mining-Projekt

### Einmalige Setup-Befehle
```
> Installiere alle benötigten Python-Module aus requirements_gui.txt
> Installiere T-Rex und lolMiner Miner
> Synchronisiere Wallets von CoinEx
```

### Tägliche Entwicklungs-Befehle
```
> Führe alle Tests aus
> Starte die GUI
> Zeige mir den aktuellen Projekt-Status
```

### Bug-Fixing Befehle
```
> Finde alle Fehler und fixe sie
> Der Multi-GPU Tab zeigt keine GPUs - fixe das
> Die Pools zeigen "N/A" - warum?
```

### Feature-Entwicklung
```
> Füge Binance-Unterstützung hinzu
> Erstelle einen neuen Tab für Pool-Statistiken
> Implementiere automatische Miner-Updates
```

---

## ⚠️ Wichtige Hinweise

### Kosten
- Claude Code nutzt dein Claude Pro/Team Abo
- Komplexe Tasks können viele Tokens verbrauchen
- Prüfe mit `/cost` den Verbrauch

### Sicherheit
- Claude Code kann Dateien ändern!
- Bei kritischen Änderungen fragt es nach Bestätigung
- Mache vorher ein Backup deines Projekts

### Grenzen
- Kann keine GUI-Fenster "sehen"
- Braucht Netzwerk für API-Calls
- Manche System-Operationen brauchen Admin-Rechte

---

## 🔄 Workflow: Von Fehler zu Fix

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   1. PROBLEM BESCHREIBEN                                │
│   ┌─────────────────────────────────────────────────┐  │
│   │ > Die CoinEx Wallets werden nicht geladen       │  │
│   └─────────────────────────────────────────────────┘  │
│                        ↓                                │
│   2. CLAUDE ANALYSIERT                                  │
│   ┌─────────────────────────────────────────────────┐  │
│   │ 🔍 Lese coinex_api.py...                        │  │
│   │ 🔍 Prüfe wallets.json...                        │  │
│   │ 🔍 Teste API-Verbindung...                      │  │
│   └─────────────────────────────────────────────────┘  │
│                        ↓                                │
│   3. CLAUDE ERKLÄRT                                     │
│   ┌─────────────────────────────────────────────────┐  │
│   │ Problem gefunden: API-Key abgelaufen            │  │
│   │ Lösung: Neuen Key in coinex_config.json         │  │
│   └─────────────────────────────────────────────────┘  │
│                        ↓                                │
│   4. CLAUDE FIXT (mit Bestätigung)                     │
│   ┌─────────────────────────────────────────────────┐  │
│   │ Soll ich coinex_config.json aktualisieren?      │  │
│   │ > Ja                                            │  │
│   │ ✅ Datei aktualisiert                           │  │
│   └─────────────────────────────────────────────────┘  │
│                        ↓                                │
│   5. CLAUDE TESTET                                      │
│   ┌─────────────────────────────────────────────────┐  │
│   │ 🧪 Teste CoinEx API...                          │  │
│   │ ✅ 47 Wallets erfolgreich geladen!              │  │
│   └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Checkliste: Ist Claude Code bereit?

- [ ] Node.js installiert (`node --version` zeigt v18+)
- [ ] Claude Code installiert (`claude --version` zeigt v1.x)
- [ ] Mit Anthropic-Konto angemeldet
- [ ] Im richtigen Projekt-Ordner (`cd C:\GPUMiner_GUI`)
- [ ] Backup des Projekts gemacht

---

## 🚀 Los geht's!

Nach der Installation einfach:

```powershell
cd C:\GPUMiner_GUI
claude
```

Und dann:
```
> Analysiere das Projekt und zeige mir den Status
```

Claude Code macht den Rest! 🎉
