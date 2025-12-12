# 🎮 GPU Mining Profit Switcher V12.8 Ultimate

**Automatischer GPU/CPU Mining Profit Switcher mit AI-Unterstützung**

Ein vollautomatisches Mining-System das:
- ⛏️ Automatisch zum profitabelsten Coin wechselt
- 🎮 Jede GPU kann einen eigenen Coin minen
- 💾 Virtuellen Speicher automatisch optimiert
- 🤖 AI-gestützte Überwachung und Fehlerkorrektur
- 💰 Portfolio-Management mit Auto-Sell

---

## 📋 Inhaltsverzeichnis

- [Features](#-features)
- [Installation](#-installation)
- [Schnellstart](#-schnellstart)
- [Module](#-module)
- [Konfiguration](#-konfiguration)
- [Mining-Richtlinien](#-mining-richtlinien)
- [Unterstützte Hardware](#-unterstützte-hardware)
- [API-Integrationen](#-api-integrationen)
- [Entwicklung](#-entwicklung)
- [Changelog](#-changelog)

---

## 🚀 Features

### ⛏️ Multi-GPU Individual Mining (NEU V12.8!)
Jede GPU mined automatisch den für SIE profitabelsten Coin:
```
GPU 0 (RTX 3080): GRIN  → $2.50/Tag → lolMiner
GPU 1 (RTX 3070): RVN   → $1.80/Tag → T-Rex
GPU 2 (RTX 3060): ERG   → $1.20/Tag → T-Rex
─────────────────────────────────────────────
GESAMT:                   $5.50/Tag
```

### 💾 Auto Memory Manager (NEU V12.8!)
- Prüft RAM + Pagefile vor Mining-Start
- Berechnet Anforderungen basierend auf GPU-Anzahl & Coins
- Erhöht Pagefile automatisch wenn nötig
- Führt PC-Neustart durch für Änderungen

### 💰 Portfolio Manager (NEU V12.8!)
- Automatische Mining-Einzahlung Erkennung
- Stop-Loss und Trailing-Stop
- Auto-Sell bei Zielpreis
- CoinEx und Gate.io Integration

### 🔧 AI Code Repair (NEU V12.8!)
- Erkennt Code-Fehler automatisch
- Generiert Fixes mit LLM (GROQ, DeepSeek, Gemini)
- Wendet Fixes an mit Backup
- Automatischer Programm-Neustart

### 🤖 AI Agent (V12.7)
- Multi-LLM Support (GROQ, Gemini, DeepSeek, HuggingFace)
- Wissensbasis mit Lernfähigkeit
- Mining-Optimierungsvorschläge
- 24/7 automatische Überwachung

### ⚡ Weitere Features
- **Auto-Profit Switching**: Wechselt alle X Minuten zum profitabelsten Coin
- **MSI Afterburner Integration**: Automatisches OC pro Coin
- **hashrate.no API**: Community-optimierte OC-Profile
- **Flight Sheets**: HiveOS-Style Mining-Konfiguration
- **CPU Mining**: XMRig Integration für Monero
- **Multi-Pool Failover**: Automatischer Pool-Wechsel
- **Tray Icon**: Läuft im Hintergrund

---

## 📥 Installation

### Voraussetzungen
- Windows 10/11 (64-bit)
- Python 3.10+
- NVIDIA GPU mit aktuellen Treibern
- MSI Afterburner (empfohlen für OC)

### Schnell-Installation
```batch
# 1. Repository klonen oder ZIP entpacken
# 2. Dependencies installieren
pip install -r requirements_gui.txt

# 3. Miner herunterladen
DOWNLOAD_MINERS.bat

# 4. Starten
START.bat
```

### Dependencies
```
PySide6>=6.5.0
requests>=2.28.0
pynvml>=11.5.0
psutil>=5.9.0
pyqtgraph>=0.13.0
cryptography>=41.0.0
```

---

## 🎯 Schnellstart

### 1. Wallets einrichten
Im Tab "💳 Wallets" deine Wallet-Adressen eintragen:
```json
{
  "RVN": "deine_rvn_wallet",
  "ERG": "deine_erg_wallet",
  "ETC": "deine_etc_wallet",
  "KAS": "deine_kas_wallet"
}
```

### 2. Flight Sheet erstellen
Im Tab "📋 Flight Sheets":
- Name: z.B. "RVN Mining"
- Coin: RVN
- Pool: 2Miners
- Miner: T-Rex

### 3. Mining starten
- **Einzelner Coin**: Flight Sheet aktivieren → "▶️ Start Mining"
- **Auto-Profit**: Tab "💰 Auto-Profit" → Coins auswählen → "▶️ Start"
- **Multi-GPU**: Tab "🎮 Multi-GPU" → "▶️ Alle Starten (Optimal)"

---

## 📦 Module

### Core Mining
| Datei | Beschreibung |
|-------|--------------|
| `mining_gui.py` | Haupt-GUI (4700+ Zeilen) |
| `miner_manager.py` | Miner-Prozess Verwaltung |
| `miner_api.py` | API-Kommunikation mit Minern |
| `auto_profit_switcher.py` | Profit-basiertes Switching |

### Multi-GPU (V12.8)
| Datei | Beschreibung |
|-------|--------------|
| `multi_gpu_profit.py` | GPU-spezifische Hashrate-DB |
| `multi_miner_manager.py` | Mehrere Miner gleichzeitig |
| `multi_gpu_mining_widget.py` | Multi-GPU GUI |

### Memory Manager (V12.8)
| Datei | Beschreibung |
|-------|--------------|
| `system_memory_manager.py` | Auto-Pagefile + Neustart |
| `memory_manager_widget.py` | Memory Manager GUI |

### Portfolio (V12.8)
| Datei | Beschreibung |
|-------|--------------|
| `portfolio_manager.py` | Portfolio + Auto-Sell |
| `portfolio_widget.py` | Portfolio GUI |

### AI (V12.7/V12.8)
| Datei | Beschreibung |
|-------|--------------|
| `ai_agent.py` | Multi-LLM AI Agent |
| `ai_agent_widget.py` | AI Agent GUI |
| `code_repair.py` | Automatische Code-Reparatur |

### Overclocking
| Datei | Beschreibung |
|-------|--------------|
| `overclock_manager.py` | NVML OC-Steuerung |
| `msi_afterburner.py` | MSI AB Integration |
| `hashrateno_api.py` | Community OC-Profile |
| `gpu_auto_tuner.py` | Automatische OC-Optimierung |

### GPU Monitoring
| Datei | Beschreibung |
|-------|--------------|
| `gpu_monitor.py` | NVML GPU-Überwachung |
| `gpu_database.py` | GPU-Spezifikations-Datenbank |
| `hardware_db.py` | Hardware-Erkennung |

### Exchange Integration
| Datei | Beschreibung |
|-------|--------------|
| `exchange_manager.py` | Exchange-Verwaltung |
| `coinex_api.py` | CoinEx API |
| `gateio_api.py` | Gate.io API |

---

## ⚙️ Konfiguration

### wallets.json
```json
{
  "wallets": {
    "RVN": "RVN_WALLET_ADDRESS",
    "ERG": "9f...",
    "ETC": "0x...",
    "KAS": "kaspa:...",
    "FLUX": "t1..."
  }
}
```

### oc_profiles.json
```json
{
  "RVN": {
    "RTX 3080": {"core": 100, "mem": 500, "pl": 75},
    "RTX 3070": {"core": 100, "mem": 500, "pl": 70}
  }
}
```

### flight_sheets.json
```json
{
  "sheets": [
    {
      "id": "uuid",
      "name": "RVN Mining",
      "coin": "RVN",
      "algorithm": "kawpow",
      "pool_url": "stratum+tcp://rvn.2miners.com:6060",
      "miner": "t-rex"
    }
  ]
}
```

---

## 📊 Mining-Richtlinien

### Speicher-Anforderungen (Pagefile)
| GPU-Anzahl | Minimum | Empfohlen |
|------------|---------|-----------|
| 1 GPU | 16 GB | 20 GB |
| 2 GPUs | 24 GB | 32 GB |
| 4 GPUs | 40 GB | 48 GB |
| 6 GPUs | 56 GB | 64 GB |
| 9 GPUs | 80 GB | 96 GB |

### DAG-Größen pro Algorithmus
| Algorithmus | Pro GPU | Coins |
|-------------|---------|-------|
| cuckatoo32 | 8 GB | GRIN |
| etchash | 6 GB | ETC |
| kawpow | 4 GB | RVN, CLORE |
| autolykos2 | 3 GB | ERG |
| kheavyhash | 2 GB | KAS |
| blake3 | 2 GB | ALPH, IRON |
| equihash125 | 2 GB | FLUX |

### OC-Empfehlungen
| Coin | Core | Memory | Power Limit |
|------|------|--------|-------------|
| RVN | +100 | +500 | 75% |
| ERG | +150 | +800 | 70% |
| ETC | +100 | +800 | 70% |
| GRIN | +100 | +500 | 85% |
| KAS | +150 | +1000 | 65% |

---

## 🖥️ Unterstützte Hardware

### NVIDIA GPUs
**RTX 40 Series**
- RTX 4090, 4080, 4070 Ti, 4070, 4060 Ti, 4060

**RTX 30 Series Desktop**
- RTX 3090 Ti, 3090, 3080 Ti, 3080, 3070 Ti, 3070, 3060 Ti, 3060

**RTX 30 Series Laptop**
- RTX 3080 Laptop, 3070 Laptop, 3060 Laptop

**RTX 20 Series**
- RTX 2080 Ti, 2080 Super, 2080, 2070 Super, 2070, 2060 Super, 2060

**GTX 16 Series**
- GTX 1660 Ti, 1660 Super, 1660

### AMD GPUs
**RX 7000 Series**
- RX 7900 XTX, 7900 XT

**RX 6000 Series**
- RX 6950 XT, 6900 XT, 6800 XT, 6800, 6700 XT, 6600 XT, 6600

### Unterstützte Miner
| Miner | Algorithmen |
|-------|-------------|
| T-Rex | kawpow, autolykos2, etchash, octopus |
| lolMiner | equihash, beamhash, cuckatoo, kaspa |
| GMiner | equihash, cuckatoo, autolykos2 |
| NBMiner | kawpow, etchash, autolykos2 |
| Rigel | kheavyhash, autolykos2, nexapow |
| XMRig | randomx (CPU) |

---

## 🔌 API-Integrationen

### Profit-APIs
- **WhatToMine**: Aktuelle Coin-Profitabilität
- **minerstat**: Backup Profit-Daten

### OC-APIs
- **hashrate.no**: Community OC-Profile

### Exchange-APIs
- **CoinEx**: Trading, Portfolio
- **Gate.io**: Trading, Portfolio
- **CoinGecko**: Preise

### AI-APIs
- **GROQ**: Llama 3 (schnell, kostenlos)
- **Google Gemini**: Gemini Pro
- **DeepSeek**: DeepSeek Chat
- **HuggingFace**: Open-Source Modelle
- **OpenRouter**: Multi-Model Gateway

---

## 👨‍💻 Entwicklung

### Projekt-Struktur
```
GPUMiner_GUI/
├── mining_gui.py           # Haupt-GUI
├── multi_gpu_profit.py     # GPU-Hashrate DB
├── multi_miner_manager.py  # Multi-Miner
├── system_memory_manager.py # Auto-Pagefile
├── portfolio_manager.py    # Portfolio
├── ai_agent.py             # AI Agent
├── code_repair.py          # Auto-Fix
├── msi_afterburner.py      # MSI AB
├── hashrateno_api.py       # OC API
├── wallets.json            # Wallets
├── oc_profiles.json        # OC Profile
├── flight_sheets.json      # Flight Sheets
├── miners/                 # Miner-Binaries
│   ├── t-rex/
│   ├── lolminer/
│   ├── gminer/
│   └── xmrig/
└── README.md
```

### Entwicklungsregeln
Siehe [README_REGELN.md](README_REGELN.md)

---

## 📝 Changelog

### V12.8 (12.12.2024)
- ✅ Multi-GPU Individual Mining (jede GPU eigener Coin)
- ✅ System Memory Manager (Auto-Pagefile + Neustart)
- ✅ Portfolio Manager mit Auto-Sell
- ✅ AI Code Repair
- ✅ GPU-Hashrate Datenbank (40+ Modelle)

### V12.7 (11.12.2024)
- ✅ AI Agent mit Multi-LLM
- ✅ CPU Mining (XMRig)
- ✅ lolMiner Hashrate Fix
- ✅ hashrate.no OC Integration

### V12.6
- ✅ MSI Afterburner Integration
- ✅ Flight Sheets
- ✅ Auto-Profit Switching

### V12.5
- ✅ GPU Monitor (NVML)
- ✅ Overclock Manager
- ✅ Exchange Integration

---

## 📄 Lizenz

Dieses Projekt ist für den persönlichen Gebrauch bestimmt.

---

## 🙏 Credits

- **Mining Software**: T-Rex, lolMiner, GMiner, NBMiner, Rigel, XMRig
- **APIs**: WhatToMine, hashrate.no, CoinGecko
- **GUI Framework**: PySide6 (Qt for Python)

---

**Made with ❤️ for Miners**
