# 📝 CHANGELOG - GPU Mining Profit Switcher

Alle Änderungen am Projekt dokumentiert.

---

## [V12.8] - 12.12.2024

### 🆕 Hinzugefügt

#### Multi-GPU Individual Mining
- **multi_gpu_profit.py**: GPU-Hashrate Datenbank mit 40+ GPU-Modellen
  - NVIDIA RTX 40/30/20 Series (Desktop & Laptop)
  - NVIDIA GTX 16 Series
  - AMD RX 7000/6000 Series
  - Echte Hashrates pro Algorithmus
  
- **multi_miner_manager.py**: Multi-Miner Prozess-Verwaltung
  - Mehrere Miner gleichzeitig (je GPU eigener Prozess)
  - Automatische API-Port Zuweisung
  - Koordiniertes Start/Stop
  - OC pro GPU und Coin

- **multi_gpu_mining_widget.py**: GUI für Multi-GPU Mining
  - Dashboard mit Gesamt-Profit
  - GPU-Status Karten
  - Detail-Tabelle
  - Auto-Switch Toggle

#### System Memory Manager
- **system_memory_manager.py**: Automatische Pagefile-Optimierung
  - RAM + Pagefile Prüfung
  - Mining-Anforderungen berechnen
  - Auto-Pagefile Erhöhung
  - PC-Neustart Automation
  - Mining-Richtlinien eingebaut

- **memory_manager_widget.py**: GUI für Memory Manager
  - Status-Karten (RAM, Pagefile, Virtual, Disk)
  - AI-Analyse mit Empfehlung
  - Neustart-Countdown Dialog

#### Portfolio Manager
- **portfolio_manager.py**: Portfolio + Trading
  - Mining-Einzahlung Erkennung
  - Auto-Sell bei Zielpreis
  - Stop-Loss
  - Trailing Stop
  - CoinEx/Gate.io Integration

- **portfolio_widget.py**: Portfolio GUI
  - Balance-Übersicht
  - Trading-Interface
  - Activity Log

#### AI Code Repair
- **code_repair.py**: Automatische Code-Reparatur
  - Traceback-Erkennung
  - LLM Fix-Generierung (GROQ, DeepSeek, Gemini)
  - Backup vor Änderung
  - Syntax-Validierung
  - Auto-Rollback bei Fehler

### 🔧 Geändert
- **mining_gui.py**: Integration aller neuen Module
  - Multi-GPU Tab hinzugefügt
  - Speicher Tab hinzugefügt
  - Portfolio Tab hinzugefügt
  - Speicher-Check vor Mining-Start

### 🐛 Behoben
- Doppelte MULTI_GPU_AVAILABLE Variable entfernt
- Tab-Naming Konflikte behoben

---

## [V12.7] - 11.12.2024

### 🆕 Hinzugefügt

#### AI Agent
- **ai_agent.py**: Multi-LLM AI Agent
  - GROQ (Llama 3.3 70B)
  - Google Gemini
  - DeepSeek
  - HuggingFace
  - OpenRouter
  - Wissensbasis mit SQLite
  - Lernfähigkeit

- **ai_agent_widget.py**: AI Agent GUI
  - Chat-Interface
  - Provider-Auswahl
  - Monitoring-Toggle
  - Wissensbasis-Verwaltung

#### CPU Mining
- **cpu_mining.py**: XMRig Integration
  - Automatischer Download
  - Config-Generierung
  - CPU-Thread Erkennung
  - Temperatur-Überwachung

### 🐛 Behoben
- lolMiner Hashrate-Parsing (Session vs Total)
- hashrate.no OC-Profile Fetching
- AI Agent Automation Loop

---

## [V12.6] - 10.12.2024

### 🆕 Hinzugefügt

#### MSI Afterburner Integration
- **msi_afterburner.py**: MSI AB Steuerung
  - Automatische Erkennung
  - Profile pro Coin
  - Hotkey-Support
  - Auto-Start Option

#### Flight Sheets
- **flight_sheets.py**: HiveOS-Style Mining-Profile
  - Vorkonfigurierte Profile
  - Ein-Klick Aktivierung
  - Import/Export

#### hashrate.no API
- **hashrateno_api.py**: Community OC-Profile
  - API Integration
  - GPU-spezifische Settings
  - Automatischer Download
  - Fallback-Profile

### 🔧 Geändert
- Auto-Profit Switcher erweitert
- OC-Anwendung verbessert

---

## [V12.5] - 01.12.2024

### 🆕 Hinzugefügt

#### GUI Grundgerüst
- **mining_gui.py**: Haupt-GUI mit PySide6
  - Dashboard
  - Tabs System
  - GPU-Übersicht
  - Miner-Logs

#### GPU Monitoring
- **gpu_monitor.py**: NVML GPU-Überwachung
  - Temperatur
  - Power
  - Utilization
  - Memory

#### Overclocking
- **overclock_manager.py**: NVML OC-Steuerung
  - Power Limit
  - Clock Offsets
  - Fan Control

#### Exchange Integration
- **exchange_manager.py**: Exchange-Verwaltung
- **coinex_api.py**: CoinEx API
- **gateio_api.py**: Gate.io API

### 🔧 Geändert
- Projekt-Struktur etabliert
- Config-Dateien Format

---

## [V12.4 und früher]

### Basis-Features
- Miner-Manager
- Pool-Konfiguration
- Wallet-Verwaltung
- Profit-Berechnung
- Auto-Switching Grundlagen

---

## 📊 Statistiken

| Version | Neue Dateien | Geänderte Dateien | Zeilen Code |
|---------|--------------|-------------------|-------------|
| V12.8 | 7 | 3 | +3500 |
| V12.7 | 3 | 2 | +2000 |
| V12.6 | 3 | 2 | +1500 |
| V12.5 | 15 | - | +8000 |

---

## 🏷️ Versions-Schema

```
V{major}.{minor}

Major (X.0): Große Features, Breaking Changes
Minor (X.Y): Neue Features, Bugfixes

Beispiele:
- V12.8: Minor Release mit neuen Features
- V13.0: Nächster Major Release
```

---

## 📌 Geplant (Roadmap)

### V12.9
- [ ] Dual-Mining Support
- [ ] Mehr Exchange APIs
- [ ] Mobile App Notifications

### V13.0
- [ ] Web-Interface
- [ ] Multi-Rig Support
- [ ] Cloud-Sync

---

**Letztes Update: 12.12.2024**
