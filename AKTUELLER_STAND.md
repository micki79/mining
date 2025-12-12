# GPU Mining Profit Switcher V12.8 Ultimate - AKTUELLER STAND

## 🆕 NEU in V12.8 (11.12.2025)

### 🎮 Feature 1: Multi-GPU Individual Mining (WICHTIGSTES FEATURE!)
**Jede GPU mined den für SIE profitabelsten Coin automatisch!**

**Highlights:**
- **GPU-Erkennung:** Erkennt alle GPUs (1-9) und deren Modelle automatisch
- **GPU-spezifische Hashrates:** Datenbank mit echten Hashrates für 40+ GPU-Modelle
- **Individuelle Coin-Auswahl:** GPU 0 → GRIN, GPU 1 → RVN, GPU 2 → KAS (automatisch)
- **Multi-Miner:** Mehrere Miner-Prozesse gleichzeitig (T-Rex + lolMiner + GMiner)
- **Auto-OC pro GPU:** Jede GPU bekommt optimale OC-Settings für IHREN Coin
- **Auto-Switch:** Wechselt automatisch bei Profit-Änderung (>5%)
- **Dashboard + Tabelle:** Übersicht aller GPUs mit Status, Profit, Hashrate

**Unterstützte GPUs:**
- NVIDIA RTX 40 Series (4090, 4080, 4070 Ti, 4070, 4060 Ti, 4060)
- NVIDIA RTX 30 Series Desktop (3090 Ti, 3090, 3080 Ti, 3080, 3070 Ti, 3070, 3060 Ti, 3060)
- NVIDIA RTX 30 Series Laptop (3080 Laptop, 3070 Laptop, 3060 Laptop)
- NVIDIA RTX 20 Series (2080 Ti, 2080 Super, 2080, 2070 Super, 2070, 2060 Super, 2060)
- NVIDIA GTX 16 Series (1660 Ti, 1660 Super, 1660)
- AMD RX 7000 Series (7900 XTX, 7900 XT)
- AMD RX 6000 Series (6950 XT, 6900 XT, 6800 XT, 6800, 6700 XT, 6600 XT, 6600)

**Beispiel Multi-GPU Setup:**
```
GPU 0 (RTX 3080):    GRIN  → $2.50/Tag → lolMiner → Core+100, PL 85%
GPU 1 (RTX 3070):    RVN   → $1.80/Tag → T-Rex    → Core+100, PL 75%
GPU 2 (RTX 3060):    ERG   → $1.20/Tag → T-Rex    → Core+150, PL 70%
───────────────────────────────────────────────────────────────────
GESAMT:              $5.50/Tag (automatisch optimiert!)
```

### 💰 Feature 2: Portfolio Manager mit Auto-Sell

### 💾 Feature 3: System Memory Manager (AUTO-PAGEFILE!)
**Automatische Speicher-Optimierung für Mining mit PC-Neustart!**

**Das Problem:**
- Mining braucht viel virtuellen Speicher (Pagefile/Swap)
- ETH/ETC DAG: ~6 GB pro GPU
- GRIN Cuckatoo32: ~8 GB pro GPU
- Wenn Pagefile zu klein → Mining crasht!

**Die Lösung - Vollautomatisch:**
1. System prüft RAM + Pagefile
2. AI berechnet Mining-Anforderungen basierend auf GPU-Anzahl & Coins
3. Wenn zu wenig → Pagefile wird automatisch erhöht
4. PC wird neugestartet um Änderungen anzuwenden
5. Nach Neustart: Mining startet automatisch!

**Mining-Richtlinien (eingebaut):**
```
GPU-Anzahl  | Min. Pagefile | Empfohlen
------------|---------------|----------
1 GPU       | 16 GB         | 20 GB
2 GPUs      | 24 GB         | 32 GB
4 GPUs      | 40 GB         | 48 GB
6 GPUs      | 56 GB         | 64 GB
9 GPUs      | 80 GB         | 96 GB
```

**DAG-Größen pro Algorithmus:**
```
Algorithmus    | Pro GPU | Coins
---------------|---------|------------------
etchash        | 6 GB    | ETC
cuckatoo32     | 8 GB    | GRIN
kawpow         | 4 GB    | RVN, CLORE
autolykos2     | 3 GB    | ERG
kheavyhash     | 2 GB    | KAS
blake3         | 2 GB    | ALPH, IRON
equihash125    | 2 GB    | FLUX
```

**GUI-Tab: 💾 Speicher**
- Status-Karten: RAM, Pagefile, Virtual, Disk
- Mining-Anforderungen anzeigen
- AI-Analyse mit Empfehlung
- Auto-Optimize Button mit Neustart-Countdown

### 💰 Feature 4: Portfolio Manager mit Auto-Sell
Vollautomatisches Trading-System für Mining-Einnahmen!

**Highlights:**
- **Wallet-Tracking:** Überwacht Mining-Einzahlungen auf CoinEx/Gate.io automatisch
- **Auto-Sell:** Verkauft geminte Coins automatisch zu Stablecoins
- **Stop-Loss:** 15-20% Hard Stop-Loss für volatile Mining-Coins
- **Trailing Stop:** 8-12% Trailing Stop nach +15-25% Gewinn
- **Dump-Erkennung:** RSI + Volume-Spike Detection
- **Activity Log:** Alle Aktionen mit Checkboxen zum Abhaken

**Basierend auf Mining-Community Research:**
- Stop-Loss optimal für Mining-Coins mit 100-200% jährlicher Volatilität
- RSI 9er Periode (statt Standard 14) mit 80/20 Thresholds
- Auto-Sell 60% für Stromkosten-Deckung

### 🔧 Feature 2: AI Code Repair
Automatische Python-Fehlerbehebung!

**Highlights:**
- **Fehler-Erkennung:** Erkennt Python Tracebacks/Exceptions automatisch im Log
- **Fix-Generierung:** LLM (GROQ/DeepSeek/Gemini) generiert intelligente Fixes
- **Auto-Apply:** Fixes werden automatisch angewendet (mit Backup!)
- **Neustart:** Startet NUR das Programm neu (NICHT den PC!)
- **Syntax-Check:** Validierung vor Anwendung
- **Rollback:** Bei Fehlern sofortiger Rollback

**Fixbare Fehler:**
- SyntaxError, IndentationError, TabError
- NameError, TypeError, KeyError, AttributeError
- ImportError, ModuleNotFoundError
- ValueError, IndexError, FileNotFoundError

### 📝 Feature 3: Dokumentations-System
Vollständige Dokumentation aller Aktionen!

**Neue Datenbank-Tabellen:**
- `repair_actions` - Code-Fixes Historie mit Status
- `trade_orders` - Trading Historie mit P&L
- `mining_deposits` - Mining-Einnahmen Tracking
- `daily_stats` - Tägliche Profit-Statistiken
- `activity_log` - Alle Aktionen mit Checkbox

---

## 🐛 BUGFIXES V12.7.1 (10.12.2025)

### Fix 1: lolMiner Hashrate in GUI ✅
**Problem:** lolMiner zeigt 0.47 g/s im Terminal, GUI zeigt 0.00 g/s
**Ursache:** 
- Falscher API Endpoint (`/summary` statt `/` root)
- Unvollständiger JSON Parser für lolMiner Format
**Lösung:**
- API Endpoint korrigiert
- Parser komplett überarbeitet mit Support für alle Feldnamen
- Automatische Hashrate-Einheit Erkennung (g/s, Sol/s, etc.)

### Fix 2: OC-Werte für alle Coins ✅
**Problem:** OC-Profile für GRIN und andere Coins fehlten
**Lösung:** Fallback-Profile erweitert:
- GRIN (Cuckatoo): Core +100, Mem +500, PL 85%
- IRON (Blake3): Core +200, PL 60%
- CFX (Octopus): Mem +800, PL 75%
- NEXA, DNX, ZEPH Profile hinzugefügt

### Fix 3: AI Agent Auto-Monitoring ✅
**Problem:** AI Agent initialisiert aber nicht aktiv bei Mining-Start
**Lösung:**
- `auto_start_monitoring()` - Startet bei Mining-Start automatisch
- `auto_stop_monitoring()` - Stoppt bei Mining-Stop automatisch

---

## 🆕 NEU in V12.7: AI AGENT + CPU MINING

### 🤖 AI Agent - Intelligente System-Überwachung
Der neue AI Agent überwacht dein Mining-System rund um die Uhr:

**Features:**
- **Multi-LLM Support** - GROQ, Gemini, DeepSeek, HuggingFace, OpenRouter
- **Automatische Fehlererkennung** - GPU Temp, Miner Crash, Pool Fehler, OC Instabilität
- **Automatische Problemlösung** - Miner neustarten, OC anpassen, Pool wechseln
- **Web-Suche** - Findet Lösungen im Internet (DuckDuckGo)
- **Lernfähig** - Merkt sich erfolgreiche Lösungen in lokaler Wissensbasis
- **Chat-Interface** - Sprich mit dem Agent über Probleme
- **System-Eingriff** - Kann OC ändern, Prozesse beenden, Miner steuern

**Integrierte API-Keys:**
```
GROQ:        sk-or-v1-d054c10d... (Llama 3.3 70B)
Gemini:      AIzaSyCZoIF6q6k... (Google AI)
DeepSeek:    sk-e152b4f94b0c... (DeepSeek Chat)
HuggingFace: hf_LWmcfBdPgJeO... (Mixtral 8x7B)
OpenRouter:  sk-or-v1-d054c10d... (Multi-Model)
```

### 💻 CPU Mining (XMRig)
Vollständige CPU-Mining Integration:

**Features:**
- **Automatischer Download** - XMRig v6.21.1 wird automatisch installiert
- **Multi-Coin Support** - XMR, ZEPH, RTM, WOW, DERO
- **CPU-Monitoring** - Auslastung, Temperatur, Threads
- **Optimierte Einstellungen** - Huge Pages, Thread-Priorität
- **Live-Stats** - Hashrate, Shares, Difficulty

**Unterstützte Coins:**
| Coin | Name | Algorithmus | Pools |
|------|------|-------------|-------|
| XMR | Monero | RandomX | SupportXMR, 2Miners, Nanopool |
| ZEPH | Zephyr | RandomX | HeroMiners, 2Miners |
| RTM | Raptoreum | GhostRider | Suprnova, Official |
| WOW | Wownero | RandomX/WOW | Official |
| DERO | Dero | AstroBWT | HeroMiners |

## ✅ Vollständige Feature-Liste

### GPU Mining
- ✅ Auto-Profit Switcher (Top 15 Coins)
- ✅ Multi-GPU Support (NVIDIA + AMD)
- ✅ Flight Sheets Management
- ✅ Automatisches Overclocking (hashrate.no)
- ✅ MSI Afterburner Integration
- ✅ Live GPU-Monitoring (Temp, Power, Fan, Clocks)
- ✅ Echtzeit Hashrate-Charts

### Börsen-Integration
- ✅ Binance, Kraken, KuCoin, Bybit
- ✅ OKX, Gate.io, MEXC, Bitget
- ✅ CoinEx API Integration
- ✅ Automatische Wallet-Adressen

### AI Features (V12.7)
- ✅ 🤖 AI Agent Tab mit Chat-Interface
- ✅ 💻 CPU Mining Tab (XMRig)
- ✅ 🔧 Automatische Fehlererkennung
- ✅ 📚 Lernfähige Wissensbasis
- ✅ 🌐 Web-Suche nach Lösungen

### NEU in V12.8
- ✅ 🎮 **Multi-GPU Individual Mining** (Jede GPU eigener Coin!)
- ✅ 📊 GPU-spezifische Hashrate-Datenbank (40+ GPU-Modelle)
- ✅ 🔄 Multi-Miner Manager (mehrere Miner gleichzeitig)
- ✅ 💾 **System Memory Manager** (Auto-Pagefile für Mining!)
- ✅ 🔄 Automatischer PC-Neustart bei Speicher-Optimierung
- ✅ 🤖 AI-Entscheidung für Speicher-Anforderungen
- ✅ 💰 Portfolio Manager Tab
- ✅ 📈 Auto-Sell Trading System
- ✅ 🛑 Stop-Loss & Trailing Stop
- ✅ 🔧 AI Code Repair (Auto-Fix)
- ✅ 📝 Activity Log mit Checkboxen
- ✅ 🔄 Automatischer Programm-Neustart

## 📂 Neue Dateien

```
GPUMiner_GUI/
├── ai_agent.py              # AI Agent Kern-Modul
├── ai_agent_widget.py       # AI Agent GUI Widget
├── cpu_mining.py            # CPU Mining / XMRig
├── portfolio_manager.py     # V12.8: Portfolio + Auto-Sell
├── portfolio_widget.py      # V12.8: Portfolio GUI Widget
├── code_repair.py           # V12.8: Automatische Code-Reparatur
├── multi_gpu_profit.py      # V12.8: GPU-spezifische Profit-Berechnung
├── multi_miner_manager.py   # V12.8: Mehrere Miner gleichzeitig
├── multi_gpu_mining_widget.py # V12.8: Multi-GPU GUI Widget
├── system_memory_manager.py # 🆕 V12.8: Auto-Pagefile + Neustart
├── memory_manager_widget.py # 🆕 V12.8: Memory Manager GUI
├── ai_agent_config.json     # AI Agent Konfiguration (auto-erstellt)
├── ai_agent_knowledge.db    # Wissensbasis SQLite (auto-erstellt)
├── portfolio_config.json    # Portfolio Konfiguration (auto-erstellt)
├── portfolio.db             # Portfolio Datenbank (auto-erstellt)
├── repair_history.db        # Repair Historie (auto-erstellt)
├── code_backups/            # Code Backups Ordner (auto-erstellt)
├── xmrig_config.json        # XMRig Konfiguration (auto-erstellt)
└── miners/xmrig/            # XMRig Installation (auto-download)
```

## 🚀 Installation

### Schnellstart
```cmd
# 1. ZIP entpacken
# 2. Abhängigkeiten installieren
pip install -r requirements_gui.txt

# 3. Optionale Abhängigkeiten für AI Agent
pip install requests beautifulsoup4

# 4. GUI starten
python mining_gui.py
# oder
START.bat
```

### Erste Schritte mit AI Agent
1. Starte die GUI
2. Gehe zum **🤖 AI Agent** Tab
3. API-Keys sind bereits konfiguriert
4. Klicke **▶️ Starten** für automatische Überwachung
5. Chatte mit dem Agent über Probleme

### Erste Schritte mit CPU Mining
1. Starte die GUI
2. Gehe zum **💻 CPU Mining** Tab
3. Klicke **📥 XMRig installieren** (einmalig)
4. Gib deine Wallet-Adresse ein
5. Wähle Coin und Pool
6. Klicke **▶️ Starten**

## 🔧 AI Agent - Erkannte Fehlertypen

Der AI Agent erkennt und löst automatisch:

| Fehlertyp | Erkennung | Automatische Lösung |
|-----------|-----------|---------------------|
| GPU zu heiß | >85°C | Lüfter erhöhen, Power reduzieren |
| Miner Crash | Prozess beendet | Miner neustarten |
| Pool Fehler | Connection Failed | Pool wechseln |
| Shares Rejected | >5% Rejected | OC reduzieren |
| OC Instabil | GPU Error | Memory/Core reduzieren |
| Low Hashrate | <50% Expected | OC/Einstellungen prüfen |
| VRAM voll | Memory Error | Algo wechseln |

## 💡 Tipps

### AI Agent optimal nutzen
- Aktiviere **Auto-Fix** für automatische Problemlösung
- Aktiviere **Lernen** damit der Agent sich verbessert
- Nutze **Quick Actions** für häufige Fragen
- Der Agent kann Web-Suchen durchführen

### CPU Mining Optimierung
- **Huge Pages** aktivieren für beste Performance
- Threads auf **Auto** lassen (reserviert System-Threads)
- RandomX profitiert von viel RAM
- GhostRider nutzt CPU-Cache intensiv

## 📝 Changelog

### V12.8 (Aktuell - 11.12.2025)
- 🆕 💰 Portfolio Manager mit Auto-Sell Trading
- 🆕 🔧 AI Code Repair (automatische Fehlerbehebung)
- 🆕 📝 Activity Log mit Checkboxen
- 🆕 🛑 Stop-Loss & Trailing Stop System
- 🆕 📈 CoinGecko API Integration
- 🆕 🔄 Automatischer Programm-Neustart

### V12.7.1 (10.12.2025)
- 🐛 lolMiner API Parser Fix
- 🐛 OC-Profile für alle Coins
- 🐛 AI Agent Auto-Monitoring

### V12.7 (Dezember 2025)
- 🆕 AI Agent mit Multi-LLM Support
- 🆕 CPU Mining Tab (XMRig)
- 🆕 Automatische Fehlererkennung
- 🆕 Lernfähige Wissensbasis
- 🆕 Web-Suche Integration
- 🆕 Chat-Interface mit KI

### V12.6
- ✅ Auto-Profit Switcher
- ✅ 8 Börsen-APIs
- ✅ Beste Pools pro Coin
- ✅ GUI komplett funktionsfähig

## 🛠️ Bekannte Einschränkungen

- AMD GPU Monitoring limitiert ohne pyamdgpuinfo
- OC-Funktionen benötigen Admin-Rechte
- Huge Pages benötigen Windows-Konfiguration
- AI Agent benötigt Internet für Web-Suche
- Portfolio Auto-Sell benötigt Exchange API-Keys

## 📞 Support

Bei Problemen:
1. Prüfe die **📝 Logs** Tab
2. Frag den **🤖 AI Agent**
3. Prüfe **💰 Portfolio** Activity Log
4. Nutze die Web-Suche Funktion

---
**GPU Mining Profit Switcher V12.8 Ultimate**
*Mit Portfolio Manager, AI Code Repair und intelligentem Auto-Sell System*
