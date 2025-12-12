# 🚀 GPU MINING GUI - KOMPLETTE INSTALLATIONS-ANLEITUNG

## 📋 ÜBERSICHT - Was du installieren musst

| Nr. | Was | Warum | Zeit |
|-----|-----|-------|------|
| 1 | Git for Windows | Für Claude Code | 2 Min |
| 2 | Python Pakete | Für die GUI | 2 Min |
| 3 | Projekt-Dateien | Das Mining-Programm | 1 Min |
| 4 | Mining-Software | T-Rex, lolMiner etc. | 3 Min |

**Gesamt: ca. 10 Minuten**

---

# SCHRITT 1: Git for Windows installieren

## 1.1 Download

1. Öffne deinen Browser
2. Gehe zu: **https://git-scm.com/downloads/win**
3. Klicke auf **"Click here to download"** (64-bit)
4. Warte bis Download fertig

## 1.2 Installation

1. Doppelklick auf `Git-2.xx.x-64-bit.exe`
2. **Alle Einstellungen auf Standard lassen** (einfach immer "Next" klicken)
3. Am Ende "Install" klicken
4. Warten bis fertig
5. "Finish" klicken

## 1.3 Prüfen ob es funktioniert

1. **PowerShell NEU öffnen** (wichtig!)
   - Windows-Taste drücken
   - "PowerShell" eingeben
   - Enter drücken

2. Eingeben:
```powershell
git --version
```

3. Du solltest sehen: `git version 2.xx.x`

✅ **Git ist installiert!**

---

# SCHRITT 2: Projekt-Ordner erstellen

In PowerShell eingeben:

```powershell
mkdir C:\GPUMiner_GUI
cd C:\GPUMiner_GUI
```

✅ **Ordner erstellt!**

---

# SCHRITT 3: ZIP-Datei entpacken

## 3.1 ZIP herunterladen

Die Datei `GPUMiner_GUI_COMPLETE_V11.zip` die du von Claude bekommen hast.

## 3.2 Entpacken

1. Rechtsklick auf die ZIP-Datei
2. "Alle extrahieren..." wählen
3. Pfad ändern zu: `C:\GPUMiner_GUI`
4. "Extrahieren" klicken

**WICHTIG:** Die Dateien müssen DIREKT in `C:\GPUMiner_GUI` liegen, NICHT in einem Unterordner!

## 3.3 Prüfen

```powershell
cd C:\GPUMiner_GUI
dir
```

Du solltest sehen:
```
mining_gui.py
TEST_ALL.py
START_GUI.bat
... und viele andere Dateien
```

✅ **Projekt-Dateien sind da!**

---

# SCHRITT 4: Python-Pakete installieren

## 4.1 Alle Pakete auf einmal installieren

In PowerShell (im Ordner `C:\GPUMiner_GUI`):

```powershell
pip install PySide6 pynvml requests PyYAML pyqtgraph psutil Pillow --upgrade
```

Warte bis alles installiert ist (kann 1-2 Minuten dauern).

## 4.2 Prüfen ob alles installiert ist

```powershell
python -c "import PySide6; print('PySide6 OK')"
python -c "import pynvml; print('pynvml OK')"
python -c "import requests; print('requests OK')"
python -c "import yaml; print('PyYAML OK')"
python -c "import pyqtgraph; print('pyqtgraph OK')"
python -c "import psutil; print('psutil OK')"
```

Alle sollten "OK" zeigen.

✅ **Python-Pakete installiert!**

---

# SCHRITT 5: Test ausführen

```powershell
cd C:\GPUMiner_GUI
python TEST_ALL.py
```

Du solltest viele ✅ sehen und am Ende:
```
25 TESTS BESTANDEN!
```

✅ **System funktioniert!**

---

# SCHRITT 6: GUI starten

## Option A: Doppelklick (einfach)

1. Öffne `C:\GPUMiner_GUI` im Explorer
2. Doppelklick auf `START_GUI.bat`

## Option B: PowerShell

```powershell
cd C:\GPUMiner_GUI
python mining_gui.py
```

✅ **Die Mining-GUI öffnet sich!**

---

# SCHRITT 7: Mining-Software installieren (optional)

Die GUI kann Miner automatisch installieren, aber du kannst es auch manuell machen:

## T-Rex (empfohlen für NVIDIA)

1. Gehe zu: https://github.com/trexminer/T-Rex/releases
2. Download: `t-rex-0.26.8-win.zip` (oder neueste Version)
3. Entpacken
4. Kopiere den Inhalt nach: `C:\GPUMiner_GUI\miners\trex\`

## lolMiner (für verschiedene Coins)

1. Gehe zu: https://github.com/Lolliedieb/lolMiner-releases/releases
2. Download: `lolMiner_v1.xx_Win64.zip`
3. Entpacken
4. Kopiere den Inhalt nach: `C:\GPUMiner_GUI\miners\lolminer\`

---

# SCHRITT 8: Claude Code einrichten (optional)

Falls du Claude Code nutzen willst:

```powershell
cd C:\GPUMiner_GUI
claude
```

Beim ersten Start:
1. Browser öffnet sich
2. Mit Anthropic-Konto anmelden
3. Zurück zum Terminal

Dann kannst du sagen:
```
"Analysiere das Projekt und zeige mir den Status"
```

---

# 📋 SCHNELL-REFERENZ

## Wichtige Befehle

| Was | Befehl |
|-----|--------|
| Zum Projekt | `cd C:\GPUMiner_GUI` |
| GUI starten | `python mining_gui.py` |
| Tests ausführen | `python TEST_ALL.py` |
| CoinEx Wallets laden | `python SYNC_COINEX.py` |
| Claude Code | `claude` |

## Wichtige Dateien

| Datei | Beschreibung |
|-------|--------------|
| `mining_gui.py` | Haupt-GUI Programm |
| `START_GUI.bat` | GUI per Doppelklick starten |
| `TEST_ALL.py` | Alle Tests ausführen |
| `wallets.json` | Deine Wallet-Adressen |
| `coinex_config.json` | CoinEx API Keys |

---

# ❓ PROBLEMLÖSUNG

## "Python nicht gefunden"

Python installieren von: https://www.python.org/downloads/
- Bei Installation: ✅ "Add Python to PATH" aktivieren!

## "pip nicht gefunden"

```powershell
python -m pip install --upgrade pip
```

## "pynvml Fehler"

Du brauchst eine NVIDIA GPU und aktuelle Treiber.
Ohne NVIDIA GPU: Die GUI funktioniert trotzdem, aber ohne GPU-Monitoring.

## "GUI startet nicht"

```powershell
cd C:\GPUMiner_GUI
python mining_gui.py
```

Fehler werden in der Konsole angezeigt.

## "Claude Code funktioniert nicht"

Prüfe ob Git installiert ist:
```powershell
git --version
```

Falls nicht: Schritt 1 wiederholen.

---

# ✅ CHECKLISTE

Hake ab was du erledigt hast:

- [ ] Git for Windows installiert
- [ ] PowerShell NEU geöffnet nach Git-Installation
- [ ] `C:\GPUMiner_GUI` Ordner erstellt
- [ ] ZIP-Datei entpackt nach `C:\GPUMiner_GUI`
- [ ] Python-Pakete installiert (`pip install ...`)
- [ ] Tests ausgeführt (`python TEST_ALL.py`)
- [ ] GUI gestartet (`python mining_gui.py`)
- [ ] Miner installiert (T-Rex/lolMiner)
- [ ] (Optional) Claude Code eingerichtet

---

# 🎉 FERTIG!

Wenn alles funktioniert, hast du:

✅ Eine vollständige Mining-GUI
✅ Auto-Profit-Switching
✅ CoinEx Wallet-Sync (47 Wallets)
✅ Multi-GPU Unterstützung
✅ 50+ Coins konfiguriert
✅ 9 verschiedene Miner
✅ Live-Monitoring

**Viel Erfolg beim Mining! 💎⛏️**

---

*GPU Mining Profit Switcher V11.0*
*Installations-Anleitung - Stand: November 2024*
