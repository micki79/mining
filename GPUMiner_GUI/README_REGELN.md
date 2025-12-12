# 📜 ENTWICKLUNGSREGELN - GPU Mining Profit Switcher

## ⚠️ WICHTIG - IMMER BEFOLGEN!

Diese Regeln sind **VERBINDLICH** für jede Entwicklungssession.

---

## 🔴 DIE 3 GOLDENEN REGELN

### 1️⃣ NEVER OMIT ANYTHING
```
❌ FALSCH: Code kürzen, Funktionen weglassen, "..." verwenden
✅ RICHTIG: Immer vollständigen Code liefern, alles erhalten
```

**Bedeutet:**
- Bestehende Funktionen NIEMALS löschen
- Vollständige Dateien liefern, nicht nur Ausschnitte
- Keine "..." oder "// rest bleibt gleich" Kommentare
- Alles was existiert bleibt erhalten

### 2️⃣ ONLY ADD/FIX WHAT I SAY
```
❌ FALSCH: "Ich habe auch noch X verbessert und Y geändert"
✅ RICHTIG: Nur exakt das umsetzen was angefragt wurde
```

**Bedeutet:**
- Keine unaufgeforderten Änderungen
- Keine "Verbesserungen" ohne Nachfrage
- Keine Refactorings ohne Erlaubnis
- Fokus auf die konkrete Anfrage

### 3️⃣ ALWAYS ASK BEFORE CHANGING ANYTHING
```
❌ FALSCH: Einfach ändern und hoffen dass es passt
✅ RICHTIG: "Soll ich X ändern?" → Warten auf Bestätigung
```

**Bedeutet:**
- Bei Unklarheiten IMMER nachfragen
- Vor strukturellen Änderungen fragen
- Optionen vorstellen, User entscheiden lassen
- Lieber einmal mehr fragen als falsch machen

---

## 📋 VERSIONS-REGELN

### Eine Version - Immer weiter
```
❌ FALSCH: V12.7, V12.7-fix, V12.7-neu, V12.8-alt, V12.8-neu
✅ RICHTIG: V12.7 → V12.8 → V12.9 → V13.0
```

**Bedeutet:**
- Immer auf der LETZTEN Version aufbauen
- Keine parallelen Versionen
- Keine Branches oder Forks
- Lineare Entwicklung

### Version benennen
```
Format: V{major}.{minor}
Beispiel: V12.8

Major: Große Features, Breaking Changes
Minor: Neue Features, Bugfixes
```

---

## 📁 DATEI-REGELN

### Neue Dateien
```python
# Immer am Anfang:
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[Modulname] - [Kurzbeschreibung]
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Feature 1
- Feature 2

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""
```

### Bestehende Dateien ändern
1. Erst vollständig lesen
2. Nur die angefragte Stelle ändern
3. Rest UNVERÄNDERT lassen
4. Syntax-Test nach jeder Änderung

### Dateien löschen
```
❌ NIEMALS ohne explizite Anweisung löschen
✅ Nur wenn User sagt: "Lösche Datei X"
```

---

## 🧪 TEST-REGELN

### Nach jeder Änderung
```bash
python -m py_compile datei.py
```

### Vor Abschluss
```bash
# Alle geänderten Dateien testen
python -m py_compile *.py
```

### Bei Fehlern
1. Fehler analysieren
2. NUR den Fehler beheben
3. Keine anderen Änderungen
4. Erneut testen

---

## 📦 ZIP-REGELN

### Benennung
```
GPUMiner_GUI_V{version}_{beschreibung}.zip

Beispiele:
- GPUMiner_GUI_V12_8_FINAL.zip
- GPUMiner_GUI_V12_8_MULTI_GPU.zip
```

### Ausschlüsse
```bash
zip -r output.zip GPUMiner_GUI/ \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "*.db" \
    -x "code_backups/*"
```

### Verifizierung
Nach dem Erstellen immer prüfen:
```bash
unzip -l archive.zip | grep wichtige_datei.py
```

---

## 💬 KOMMUNIKATIONS-REGELN

### Bei Anfragen
1. Anfrage verstehen
2. Bei Unklarheiten nachfragen
3. Plan vorstellen
4. Nach Bestätigung umsetzen

### Bei Problemen
```
✅ "Ich habe ein Problem gefunden: X. Soll ich Y machen?"
❌ "Ich habe das Problem gefunden und behoben."
```

### Bei Fertigstellung
```
✅ Zusammenfassung was gemacht wurde
✅ Liste der geänderten Dateien
✅ Syntax-Test Ergebnisse
✅ ZIP-Datei bereitstellen
```

---

## 🔧 CODE-STYLE

### Python
```python
# Imports gruppiert
import os
import sys
from typing import Dict, List, Optional

# Konstanten UPPERCASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Klassen CamelCase
class MiningManager:
    pass

# Funktionen snake_case
def start_mining():
    pass

# Private mit Unterstrich
def _internal_function():
    pass
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Details für Debugging")
logger.info("Normale Information")
logger.warning("Warnung")
logger.error("Fehler")
```

### Docstrings
```python
def function(param1: str, param2: int) -> bool:
    """
    Kurze Beschreibung.
    
    Args:
        param1: Beschreibung
        param2: Beschreibung
        
    Returns:
        Beschreibung
    """
    pass
```

---

## 📊 STATUS-TRACKING

### AKTUELLER_STAND.md
Bei ~90% Token-Nutzung automatisch aktualisieren:

```markdown
# GPU Mining Profit Switcher V12.8 - AKTUELLER STAND

## 🆕 NEU in V12.8
- Feature 1
- Feature 2

## ✅ Abgeschlossen
- Task 1
- Task 2

## 🔄 In Arbeit
- Task 3

## 📂 Geänderte Dateien
- datei1.py
- datei2.py
```

---

## ❌ VERBOTEN

1. **Code kürzen** - Niemals "..." oder Auslassungen
2. **Ungefragt ändern** - Nur was angefragt wurde
3. **Dateien löschen** - Ohne explizite Anweisung
4. **Versionen mischen** - Immer linear weiterentwickeln
5. **Eigenmächtig refactorn** - Erst fragen
6. **Features entfernen** - Alles bleibt erhalten
7. **Annahmen treffen** - Bei Unklarheit fragen

---

## ✅ ERLAUBT

1. **Vollständigen Code liefern** - Immer komplett
2. **Nachfragen** - Bei jeder Unklarheit
3. **Optionen vorstellen** - User entscheidet
4. **Fehler melden** - Transparent kommunizieren
5. **Tests durchführen** - Nach jeder Änderung
6. **Dokumentieren** - Code und Änderungen

---

## 📝 CHECKLISTE VOR ABSCHLUSS

- [ ] Nur angefragte Änderungen gemacht?
- [ ] Keine bestehenden Features gelöscht?
- [ ] Syntax-Tests bestanden?
- [ ] AKTUELLER_STAND.md aktualisiert?
- [ ] ZIP erstellt und verifiziert?
- [ ] Zusammenfassung geschrieben?

---

**Diese Regeln gelten IMMER. Keine Ausnahmen.**

```
MERKE:
🔴 NEVER omit anything
🟡 ONLY add/fix what I say  
🟢 ALWAYS ask before changing anything
```
