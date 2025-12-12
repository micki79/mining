#!/usr/bin/env python3
"""
MSI Afterburner Integration für GPU Mining GUI V11.0
=====================================================

Features:
- Automatische Erkennung ob MSI Afterburner installiert ist
- Automatische Installation wenn nicht vorhanden
- Update-Check für neue Versionen
- OC-Profile erstellen und anwenden
- Funktioniert auch auf Laptops ohne Admin-Rechte!

Author: Claude
Version: 1.0.0
"""

import os
import sys
import json
import time
import shutil
import logging
import winreg
import subprocess
import urllib.request
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============================================================
# KONFIGURATION
# ============================================================

# MSI Afterburner Download URLs
MSI_AB_DOWNLOAD_URL = "https://download.msi.com/uti_exe/vga/MSIAfterburnerSetup.zip"
MSI_AB_VERSION_CHECK_URL = "https://www.msi.com/Landing/afterburner/graphics-cards"

# Standard-Installationspfade
MSI_AB_PATHS = [
    r"C:\Program Files (x86)\MSI Afterburner",
    r"C:\Program Files\MSI Afterburner",
    os.path.expandvars(r"%PROGRAMFILES(X86)%\MSI Afterburner"),
    os.path.expandvars(r"%PROGRAMFILES%\MSI Afterburner"),
]

# Profile-Pfad
MSI_AB_PROFILES_PATH = os.path.expandvars(r"%PROGRAMFILES(X86)%\MSI Afterburner\Profiles")

# Aktuelle Version (für Update-Check)
KNOWN_LATEST_VERSION = "4.6.5"


@dataclass
class OCProfile:
    """Overclocking-Profil für eine GPU"""
    name: str
    gpu_index: int
    core_clock_offset: int = 0      # MHz
    memory_clock_offset: int = 0    # MHz
    power_limit: int = 100          # Prozent
    temp_limit: int = 83            # °C
    fan_speed: int = 0              # 0 = Auto, sonst %
    voltage_offset: int = 0         # mV (meist nicht unterstützt)


class MSIAfterburnerManager:
    """
    Manager für MSI Afterburner Integration
    
    Ermöglicht:
    - Installation prüfen/durchführen
    - OC-Profile erstellen und anwenden
    - Update-Check
    """
    
    def __init__(self):
        self.install_path: Optional[str] = None
        self.exe_path: Optional[str] = None
        self.version: Optional[str] = None
        self.is_installed = False
        self.is_running = False
        
        # hashrate.no API Referenz (wird später gesetzt)
        self.hashrate_api = None
        
        # Hardware-DB Referenz (wird später gesetzt)
        self.hardware_db = None
        
        # Profile-Speicher
        self.profiles: Dict[str, OCProfile] = {}
        self.profiles_file = Path("msi_ab_profiles.json")
        
        # Initial-Check
        self._detect_installation()
        self._load_profiles()
    
    # ============================================================
    # INSTALLATION DETECTION
    # ============================================================
    
    def _detect_installation(self) -> bool:
        """Erkennt ob MSI Afterburner installiert ist"""
        
        # 1. Registry prüfen
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Afterburner"
            )
            install_path = winreg.QueryValueEx(key, "InstallLocation")[0]
            winreg.CloseKey(key)
            
            if install_path and os.path.exists(install_path):
                self.install_path = install_path
                self.exe_path = os.path.join(install_path, "MSIAfterburner.exe")
                self.is_installed = os.path.exists(self.exe_path)
                
                if self.is_installed:
                    self._get_version()
                    logger.info(f"MSI Afterburner gefunden: {self.install_path} (v{self.version})")
                    return True
        except WindowsError:
            pass
        
        # 2. Standard-Pfade prüfen
        for path in MSI_AB_PATHS:
            exe = os.path.join(path, "MSIAfterburner.exe")
            if os.path.exists(exe):
                self.install_path = path
                self.exe_path = exe
                self.is_installed = True
                self._get_version()
                logger.info(f"MSI Afterburner gefunden: {path} (v{self.version})")
                return True
        
        # 3. PATH durchsuchen
        result = shutil.which("MSIAfterburner.exe")
        if result:
            self.exe_path = result
            self.install_path = os.path.dirname(result)
            self.is_installed = True
            self._get_version()
            logger.info(f"MSI Afterburner in PATH: {result}")
            return True
        
        logger.warning("MSI Afterburner nicht gefunden")
        self.is_installed = False
        return False
    
    def _get_version(self) -> Optional[str]:
        """Liest die installierte Version aus"""
        if not self.exe_path or not os.path.exists(self.exe_path):
            return None
        
        try:
            # Version aus Datei-Properties lesen
            import ctypes
            from ctypes import wintypes
            
            size = ctypes.windll.version.GetFileVersionInfoSizeW(self.exe_path, None)
            if size == 0:
                return None
            
            buffer = ctypes.create_string_buffer(size)
            ctypes.windll.version.GetFileVersionInfoW(self.exe_path, 0, size, buffer)
            
            # FixedFileInfo extrahieren
            ptr = ctypes.c_void_p()
            length = wintypes.UINT()
            ctypes.windll.version.VerQueryValueW(
                buffer, "\\", ctypes.byref(ptr), ctypes.byref(length)
            )
            
            class VS_FIXEDFILEINFO(ctypes.Structure):
                _fields_ = [
                    ("dwSignature", wintypes.DWORD),
                    ("dwStrucVersion", wintypes.DWORD),
                    ("dwFileVersionMS", wintypes.DWORD),
                    ("dwFileVersionLS", wintypes.DWORD),
                    ("dwProductVersionMS", wintypes.DWORD),
                    ("dwProductVersionLS", wintypes.DWORD),
                    ("dwFileFlagsMask", wintypes.DWORD),
                    ("dwFileFlags", wintypes.DWORD),
                    ("dwFileOS", wintypes.DWORD),
                    ("dwFileType", wintypes.DWORD),
                    ("dwFileSubtype", wintypes.DWORD),
                    ("dwFileDateMS", wintypes.DWORD),
                    ("dwFileDateLS", wintypes.DWORD),
                ]
            
            info = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
            ms = info.dwFileVersionMS
            ls = info.dwFileVersionLS
            
            self.version = f"{(ms >> 16) & 0xffff}.{ms & 0xffff}.{(ls >> 16) & 0xffff}.{ls & 0xffff}"
            return self.version
            
        except Exception as e:
            logger.debug(f"Version konnte nicht gelesen werden: {e}")
            self.version = "Unknown"
            return None
    
    def check_running(self) -> bool:
        """Prüft ob MSI Afterburner läuft"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq MSIAfterburner.exe"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.is_running = "MSIAfterburner.exe" in result.stdout
            return self.is_running
        except:
            return False
    
    # ============================================================
    # INSTALLATION
    # ============================================================
    
    def download_and_install(self, progress_callback=None) -> Tuple[bool, str]:
        """
        Lädt MSI Afterburner herunter und startet Installation
        
        Args:
            progress_callback: Optional callback(percent, message)
            
        Returns:
            (success, message)
        """
        if self.is_installed:
            return True, f"MSI Afterburner bereits installiert: v{self.version}"
        
        try:
            if progress_callback:
                progress_callback(0, "Starte Download...")
            
            # Temp-Verzeichnis
            temp_dir = tempfile.mkdtemp(prefix="msi_ab_")
            zip_path = os.path.join(temp_dir, "MSIAfterburnerSetup.zip")
            
            # Download
            logger.info(f"Downloading MSI Afterburner von {MSI_AB_DOWNLOAD_URL}")
            
            def download_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = min(int(block_num * block_size * 100 / total_size), 100)
                    progress_callback(percent, f"Downloading... {percent}%")
            
            urllib.request.urlretrieve(MSI_AB_DOWNLOAD_URL, zip_path, download_progress)
            
            if progress_callback:
                progress_callback(100, "Download abgeschlossen")
            
            # Entpacken
            if progress_callback:
                progress_callback(0, "Entpacke Installer...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Installer finden
            installer = None
            for f in os.listdir(temp_dir):
                if f.lower().endswith('.exe') and 'afterburner' in f.lower():
                    installer = os.path.join(temp_dir, f)
                    break
            
            if not installer:
                # Suche in Unterordnern
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        if f.lower().endswith('.exe') and 'setup' in f.lower():
                            installer = os.path.join(root, f)
                            break
            
            if not installer:
                return False, "Installer nicht gefunden im ZIP"
            
            if progress_callback:
                progress_callback(50, "Starte Installation...")
            
            # Installation starten
            logger.info(f"Starte Installer: {installer}")
            
            # Silent-Installation versuchen
            result = subprocess.run(
                [installer, "/S"],  # Silent mode
                capture_output=True, timeout=300  # 5 Minuten Timeout
            )
            
            # Nach Installation erneut prüfen
            time.sleep(2)
            self._detect_installation()
            
            # Cleanup
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            if self.is_installed:
                if progress_callback:
                    progress_callback(100, f"Installation erfolgreich! v{self.version}")
                return True, f"MSI Afterburner v{self.version} erfolgreich installiert!"
            else:
                # Manuelle Installation erforderlich
                if progress_callback:
                    progress_callback(100, "Manuelle Installation erforderlich")
                
                # Installer ohne /S starten
                subprocess.Popen([installer])
                return False, "Bitte installiere MSI Afterburner manuell (Installer wurde geöffnet)"
                
        except Exception as e:
            logger.error(f"Installation fehlgeschlagen: {e}")
            return False, f"Installation fehlgeschlagen: {e}"
    
    def check_for_updates(self) -> Tuple[bool, str, str]:
        """
        Prüft auf Updates
        
        Returns:
            (update_available, current_version, latest_version)
        """
        if not self.is_installed:
            return False, "Nicht installiert", KNOWN_LATEST_VERSION
        
        current = self.version or "0.0.0"
        latest = KNOWN_LATEST_VERSION
        
        # Version vergleichen (vereinfacht)
        try:
            current_parts = [int(x) for x in current.split('.')[:3]]
            latest_parts = [int(x) for x in latest.split('.')[:3]]
            
            update_available = latest_parts > current_parts
            return update_available, current, latest
            
        except:
            return False, current, latest
    
    # ============================================================
    # AFTERBURNER STARTEN/STOPPEN
    # ============================================================
    
    def start_afterburner(self, minimized: bool = True) -> bool:
        """Startet MSI Afterburner"""
        if not self.is_installed or not self.exe_path:
            logger.error("MSI Afterburner nicht installiert")
            return False
        
        if self.check_running():
            logger.info("MSI Afterburner läuft bereits")
            return True
        
        try:
            args = [self.exe_path]
            if minimized:
                args.append("/m")  # Minimized starten
            
            subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Warten bis gestartet
            for _ in range(10):
                time.sleep(0.5)
                if self.check_running():
                    logger.info("MSI Afterburner gestartet")
                    return True
            
            return self.check_running()
            
        except Exception as e:
            logger.error(f"Fehler beim Starten: {e}")
            return False
    
    def stop_afterburner(self) -> bool:
        """Beendet MSI Afterburner"""
        if not self.check_running():
            return True
        
        try:
            subprocess.run(
                ["taskkill", "/IM", "MSIAfterburner.exe"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(1)
            return not self.check_running()
        except:
            return False
    
    # ============================================================
    # OC-PROFILE VERWALTUNG
    # ============================================================
    
    def _load_profiles(self):
        """Lädt gespeicherte Profile"""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, profile_data in data.items():
                        self.profiles[name] = OCProfile(**profile_data)
                logger.info(f"Geladen: {len(self.profiles)} MSI AB Profile")
            except Exception as e:
                logger.warning(f"Profile laden fehlgeschlagen: {e}")
    
    def _save_profiles(self):
        """Speichert Profile"""
        try:
            data = {}
            for name, profile in self.profiles.items():
                data[name] = {
                    'name': profile.name,
                    'gpu_index': profile.gpu_index,
                    'core_clock_offset': profile.core_clock_offset,
                    'memory_clock_offset': profile.memory_clock_offset,
                    'power_limit': profile.power_limit,
                    'temp_limit': profile.temp_limit,
                    'fan_speed': profile.fan_speed,
                    'voltage_offset': profile.voltage_offset,
                }
            
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Profile speichern fehlgeschlagen: {e}")
    
    def create_profile(self, name: str, gpu_index: int = 0,
                      core_offset: int = 0, memory_offset: int = 0,
                      power_limit: int = 100, temp_limit: int = 83,
                      fan_speed: int = 0) -> OCProfile:
        """Erstellt ein neues OC-Profil"""
        profile = OCProfile(
            name=name,
            gpu_index=gpu_index,
            core_clock_offset=core_offset,
            memory_clock_offset=memory_offset,
            power_limit=power_limit,
            temp_limit=temp_limit,
            fan_speed=fan_speed
        )
        self.profiles[name] = profile
        self._save_profiles()
        logger.info(f"Profil erstellt: {name}")
        return profile
    
    def get_profile(self, name: str) -> Optional[OCProfile]:
        """Gibt ein Profil zurück"""
        return self.profiles.get(name)
    
    def delete_profile(self, name: str) -> bool:
        """Löscht ein Profil"""
        if name in self.profiles:
            del self.profiles[name]
            self._save_profiles()
            return True
        return False
    
    def list_profiles(self) -> List[str]:
        """Listet alle Profile"""
        return list(self.profiles.keys())
    
    # ============================================================
    # OC ANWENDEN (über MSI Afterburner Profile)
    # ============================================================
    
    def apply_profile(self, profile_name: str) -> Tuple[bool, str]:
        """
        Wendet ein gespeichertes Profil an
        
        Nutzt MSI Afterburner Profile (1-5) zum Anwenden
        """
        if not self.is_installed:
            return False, "MSI Afterburner nicht installiert"
        
        profile = self.profiles.get(profile_name)
        if not profile:
            return False, f"Profil '{profile_name}' nicht gefunden"
        
        # MSI Afterburner muss laufen
        if not self.check_running():
            if not self.start_afterburner(minimized=True):
                return False, "MSI Afterburner konnte nicht gestartet werden"
            time.sleep(2)
        
        # Profil in MSI Afterburner Profile-Datei schreiben
        success = self._write_msi_profile(profile, slot=1)
        
        if not success:
            return False, "Profil konnte nicht geschrieben werden"
        
        # Profil anwenden über Command-Line
        try:
            subprocess.run(
                [self.exe_path, "/Profile1"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            logger.info(f"Profil angewendet: {profile_name}")
            return True, f"Profil '{profile_name}' angewendet: Core {profile.core_clock_offset:+d}, Mem {profile.memory_clock_offset:+d}, PL {profile.power_limit}%"
            
        except Exception as e:
            return False, f"Fehler beim Anwenden: {e}"
    
    def _write_msi_profile(self, profile: OCProfile, slot: int = 1) -> bool:
        r"""
        Schreibt ein Profil in MSI Afterburner Profile-Datei
        
        HINWEIS: Erfordert Admin-Rechte für Program Files!
        Bei Permission Denied wird stattdessen Profil-Wechsel empfohlen.
        """
        try:
            profiles_dir = os.path.join(self.install_path, "Profiles")
            
            if not os.path.exists(profiles_dir):
                logger.warning(f"Profiles-Verzeichnis nicht gefunden: {profiles_dir}")
                return False
            
            # Profile-Dateien finden
            profile_files = [f for f in os.listdir(profiles_dir) if f.endswith('.cfg')]
            
            if not profile_files:
                logger.warning("Keine Profile-Dateien gefunden")
                return False
            
            # Für jede GPU das Profil setzen
            write_errors = []
            for cfg_file in profile_files:
                cfg_path = os.path.join(profiles_dir, cfg_file)
                
                try:
                    # CFG-Datei lesen
                    with open(cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Profile Section finden/erstellen (Format: [Profile1] bis [Profile5])
                    section = f"[Profile{slot}]"
                    
                    # Neue Werte
                    new_values = {
                        'CoreClkBoost': str(profile.core_clock_offset * 1000),  # In kHz
                        'MemClkBoost': str(profile.memory_clock_offset * 1000),
                        'PowerLimit': str(profile.power_limit * 1000),  # In 0.001%
                        'ThermalLimit': str(profile.temp_limit * 256),  # Skaliert
                        'FanSpeedTarget': str(profile.fan_speed * 256) if profile.fan_speed > 0 else '0',
                        'FanMode': '0' if profile.fan_speed == 0 else '1',  # 0=Auto, 1=Manual
                    }
                    
                    # Profil-Section aktualisieren
                    lines = content.split('\n')
                    new_lines = []
                    in_profile_section = False
                    profile_written = False
                    
                    for line in lines:
                        if line.strip() == section:
                            in_profile_section = True
                            new_lines.append(line)
                            # Neue Werte einfügen
                            for key, value in new_values.items():
                                new_lines.append(f"{key}={value}")
                            profile_written = True
                            continue
                        
                        if in_profile_section:
                            if line.startswith('['):
                                in_profile_section = False
                                new_lines.append(line)
                            elif '=' in line:
                                key = line.split('=')[0].strip()
                                if key not in new_values:
                                    new_lines.append(line)
                            continue
                        
                        new_lines.append(line)
                    
                    # Falls Section nicht existiert, hinzufügen
                    if not profile_written:
                        new_lines.append('')
                        new_lines.append(section)
                        for key, value in new_values.items():
                            new_lines.append(f"{key}={value}")
                    
                    # Datei schreiben
                    with open(cfg_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                    
                    logger.debug(f"Profil geschrieben: {cfg_path}")
                    
                except PermissionError as e:
                    write_errors.append(f"{cfg_file}: Permission denied")
                    logger.warning(f"Fehler bei {cfg_file}: {e}")
                    continue
                except Exception as e:
                    write_errors.append(f"{cfg_file}: {e}")
                    logger.warning(f"Fehler bei {cfg_file}: {e}")
                    continue
            
            # Wenn alle Dateien Permission Denied hatten
            if len(write_errors) == len(profile_files):
                logger.error("Keine Profile konnten geschrieben werden (Permission denied)")
                logger.info("TIPP: Erstelle Profile manuell in MSI Afterburner oder starte als Admin")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Profil schreiben fehlgeschlagen: {e}")
            return False
    
    def apply_profile_by_number(self, profile_number: int) -> Tuple[bool, str]:
        """
        Wechselt zu einem vordefinierten MSI Afterburner Profil (1-5)
        
        EMPFOHLEN: Erstelle Profile manuell in MSI Afterburner:
        - Profil 1: RVN/KAWPOW (Core +100, Mem +500, PL 75%)
        - Profil 2: ETC/ETCHASH (Core -200, Mem +1000, PL 65%)
        - Profil 3: ERG/AUTOLYKOS (Core +150, Mem +800, PL 70%)
        - Profil 4: KAS/KHEAVYHASH (Core +200, Mem 0, PL 60%)
        - Profil 5: Default (Core 0, Mem 0, PL 100%)
        """
        if not self.is_installed or not self.exe_path:
            return False, "MSI Afterburner nicht installiert"
        
        if profile_number < 1 or profile_number > 5:
            return False, "Profil muss zwischen 1 und 5 sein"
        
        if not self.check_running():
            self.start_afterburner(minimized=True)
            time.sleep(2)
        
        try:
            subprocess.run(
                [self.exe_path, f"/Profile{profile_number}"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True, f"Profil {profile_number} aktiviert"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def apply_oc_direct(self, gpu_index: int = 0, 
                       core_offset: int = 0, memory_offset: int = 0,
                       power_limit: int = 100, fan_speed: int = 0) -> Tuple[bool, str]:
        """
        Wendet OC-Settings DIREKT an über MSI Afterburner.
        
        Erfordert Admin-Rechte! (START_GUI.bat startet automatisch als Admin)
        """
        if not self.is_installed or not self.exe_path:
            return False, "MSI Afterburner nicht installiert"
        
        # MSI AB starten falls nicht läuft
        if not self.check_running():
            logger.info("Starte MSI Afterburner...")
            self.start_afterburner(minimized=True)
            time.sleep(2)
        
        # Temporäres Profil erstellen
        temp_profile = OCProfile(
            name="_auto_oc_",
            gpu_index=gpu_index,
            core_clock_offset=core_offset,
            memory_clock_offset=memory_offset,
            power_limit=power_limit,
            fan_speed=fan_speed
        )
        
        # In Profil-Slot 1 schreiben und aktivieren
        if self._write_msi_profile(temp_profile, slot=1):
            try:
                subprocess.run(
                    [self.exe_path, "/Profile1"],
                    capture_output=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                msg = f"OC angewendet: Core {core_offset:+d}, Mem {memory_offset:+d}, PL {power_limit}%"
                logger.info(msg)
                return True, msg
            except Exception as e:
                return False, f"Profil-Aktivierung fehlgeschlagen: {e}"
        
        # Fallback: Profil-basierter Ansatz
        logger.warning("Direktes OC fehlgeschlagen, nutze Profil-Fallback")
        return False, "Profil konnte nicht geschrieben werden (Admin-Rechte?)"
    
    def get_profile_for_coin(self, coin: str) -> int:
        """
        Gibt die Profil-Nummer (1-5) für einen Coin zurück.
        
        WICHTIG - Erstelle diese Profile einmalig in MSI Afterburner:
        
        Profil 1: KAWPOW (RVN, CLORE, AIPG)
                  → Core +100, Memory +500, Power Limit 75%
        
        Profil 2: ETCHASH (ETC)  
                  → Core -200, Memory +1000, Power Limit 65%
        
        Profil 3: AUTOLYKOS (ERG)
                  → Core +150, Memory +800, Power Limit 70%
        
        Profil 4: KHEAVYHASH/BLAKE3 (KAS, ALPH, DNX)
                  → Core +200, Memory +0, Power Limit 60%
        
        Profil 5: DEFAULT (Reset/Andere)
                  → Core +0, Memory +0, Power Limit 100%
        """
        coin_to_profile = {
            # Profil 1: KAWPOW
            'RVN': 1, 'CLORE': 1, 'AIPG': 1,
            # Profil 2: ETCHASH  
            'ETC': 2,
            # Profil 3: AUTOLYKOS
            'ERG': 3,
            # Profil 4: Core-lastig
            'KAS': 4, 'ALPH': 4, 'DNX': 4, 'NEXA': 4, 'RXD': 4,
            # Profil 5: Andere/Default
            'ZEC': 5, 'FLUX': 5, 'BEAM': 5, 'XMR': 5, 'CFX': 5,
        }
        return coin_to_profile.get(coin.upper(), 5)
    
    def apply_profile_for_coin(self, coin: str) -> Tuple[bool, str]:
        """
        Wechselt zum passenden MSI Afterburner Profil für einen Coin.
        
        KEINE Admin-Rechte erforderlich!
        
        Args:
            coin: Coin-Symbol (z.B. "RVN", "ETC", "KAS")
            
        Returns:
            (Erfolg, Nachricht)
        """
        if not self.is_installed or not self.exe_path:
            return False, "MSI Afterburner nicht installiert"
        
        profile_num = self.get_profile_for_coin(coin)
        
        # MSI AB starten falls nicht läuft
        if not self.check_running():
            logger.info("Starte MSI Afterburner...")
            self.start_afterburner(minimized=True)
            time.sleep(2)
        
        # Profil wechseln über Kommandozeile
        try:
            result = subprocess.run(
                [self.exe_path, f"/Profile{profile_num}"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            profile_info = {
                1: "KAWPOW (Core+100, Mem+500, PL75%)",
                2: "ETCHASH (Core-200, Mem+1000, PL65%)",
                3: "AUTOLYKOS (Core+150, Mem+800, PL70%)",
                4: "KHEAVYHASH (Core+200, Mem+0, PL60%)",
                5: "DEFAULT (Core+0, Mem+0, PL100%)",
            }
            
            msg = f"Profil {profile_num} aktiviert: {profile_info.get(profile_num, 'Custom')}"
            logger.info(f"MSI AB: {msg}")
            return True, msg
            
        except Exception as e:
            logger.error(f"Profil-Wechsel fehlgeschlagen: {e}")
            return False, f"Fehler: {e}"
    
    def reset_oc(self) -> Tuple[bool, str]:
        """Setzt OC auf Standard zurück"""
        return self.apply_oc_direct(
            core_offset=0,
            memory_offset=0,
            power_limit=100,
            fan_speed=0
        )
    
    # ============================================================
    # HASHRATE.NO INTEGRATION FÜR GPU-SPEZIFISCHE SETTINGS
    # ============================================================
    
    def set_hashrate_api(self, api):
        """Setzt die hashrate.no API Referenz"""
        self.hashrate_api = api
        logger.info("MSI AB: hashrate.no API verbunden")
    
    def get_gpu_names(self) -> List[str]:
        """Erkennt alle GPU-Namen im System"""
        gpu_names = []
        
        try:
            # NVIDIA GPUs via nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        gpu_names.append(line.strip())
        except:
            pass
        
        # Fallback: WMI
        if not gpu_names:
            try:
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                        name = line.strip()
                        if name and 'nvidia' in name.lower():
                            gpu_names.append(name)
            except:
                pass
        
        logger.info(f"GPUs erkannt: {gpu_names}")
        return gpu_names
    
    def set_hardware_db(self, db):
        """Setzt die Hardware-Datenbank Referenz"""
        self.hardware_db = db
        logger.info("MSI AB: Hardware-DB verbunden")
    
    def get_oc_from_hardware_db(self, gpu_name: str, coin: str) -> Optional[OCProfile]:
        """
        Holt OC-Settings aus der lokalen Hardware-Datenbank
        
        Args:
            gpu_name: GPU Name
            coin: Coin
            
        Returns:
            OCProfile oder None
        """
        if not hasattr(self, 'hardware_db') or not self.hardware_db:
            return None
        
        try:
            oc_data = self.hardware_db.get_oc_settings(gpu_name, coin)
            
            if oc_data:
                logger.info(f"Hardware-DB OC für {gpu_name}/{coin}: "
                           f"Core {oc_data.get('core_offset', 0):+d}, "
                           f"Mem {oc_data.get('memory_offset', 0):+d}, "
                           f"PL {oc_data.get('power_limit', 100)}%")
                
                return OCProfile(
                    name=f"{coin}_cached",
                    gpu_index=0,
                    core_clock_offset=oc_data.get('core_offset', 0),
                    memory_clock_offset=oc_data.get('memory_offset', 0),
                    power_limit=oc_data.get('power_limit', 100),
                    fan_speed=oc_data.get('fan_speed', 0)
                )
        except Exception as e:
            logger.debug(f"Hardware-DB Fehler: {e}")
        
        return None
    
    def get_oc_from_hashrate_no(self, gpu_name: str, coin: str) -> Optional[OCProfile]:
        """
        Holt OC-Settings von hashrate.no für eine spezifische GPU
        
        Reihenfolge:
        1. Lokale Hardware-DB (gecached)
        2. hashrate.no API (live)
        
        Args:
            gpu_name: GPU Name (z.B. "NVIDIA GeForce RTX 3080")
            coin: Coin (z.B. "RVN")
            
        Returns:
            OCProfile mit optimalen Settings oder None
        """
        # 1. Erst Hardware-DB prüfen (schneller, gecached)
        profile = self.get_oc_from_hardware_db(gpu_name, coin)
        if profile:
            return profile
        
        # 2. hashrate.no API abfragen
        if not hasattr(self, 'hashrate_api') or not self.hashrate_api:
            logger.debug("hashrate.no API nicht verfügbar")
            return None
        
        try:
            # OC-Settings von hashrate.no holen
            oc_settings = self.hashrate_api.get_oc_settings(gpu_name, coin)
            
            if oc_settings and oc_settings.source != "default":
                logger.info(f"hashrate.no OC für {gpu_name}/{coin}: "
                           f"Core {oc_settings.core_clock_offset:+d}, "
                           f"Mem {oc_settings.memory_clock_offset:+d}, "
                           f"PL {oc_settings.power_limit_percent}%")
                
                return OCProfile(
                    name=f"{coin}_hashrateno",
                    gpu_index=0,
                    core_clock_offset=oc_settings.core_clock_offset,
                    memory_clock_offset=oc_settings.memory_clock_offset,
                    power_limit=oc_settings.power_limit_percent,
                    fan_speed=oc_settings.fan_speed
                )
        except Exception as e:
            logger.warning(f"hashrate.no API Fehler: {e}")
        
        return None
    
    # ============================================================
    # MINING-SPEZIFISCHE PROFILE (mit hashrate.no Fallback)
    # ============================================================
    
    def get_mining_profile(self, coin: str, gpu_name: str = "") -> Optional[OCProfile]:
        """
        Gibt empfohlene OC-Settings für einen Coin zurück
        
        Reihenfolge:
        1. hashrate.no API (GPU-spezifisch!)
        2. Statische Fallback-Profile
        """
        # 1. Versuche hashrate.no für GPU-spezifische Settings
        if gpu_name:
            profile = self.get_oc_from_hashrate_no(gpu_name, coin)
            if profile:
                return profile
        
        # 2. Fallback: Statische Profile für verschiedene Coins/Algorithmen
        mining_profiles = {
            # KAWPOW (RVN, AIPG, CLORE)
            "RVN": {"core": 100, "mem": 500, "pl": 75},
            "AIPG": {"core": 100, "mem": 500, "pl": 75},
            "CLORE": {"core": 100, "mem": 500, "pl": 75},
            
            # ETCHASH (ETC)
            "ETC": {"core": -200, "mem": 1000, "pl": 65},
            
            # AUTOLYKOS2 (ERG)
            "ERG": {"core": 150, "mem": 800, "pl": 70},
            
            # KHEAVYHASH (KAS) - Core-limitiert
            "KAS": {"core": 200, "mem": 0, "pl": 60},
            
            # BLAKE3 (ALPH) - Core-limitiert
            "ALPH": {"core": 200, "mem": 0, "pl": 55},
            
            # EQUIHASH (ZEC, FLUX)
            "ZEC": {"core": 100, "mem": 0, "pl": 80},
            "FLUX": {"core": 100, "mem": 0, "pl": 80},
            
            # BEAMHASH (BEAM)
            "BEAM": {"core": 0, "mem": 0, "pl": 80},
            
            # CUCKATOO (GRIN) - GPU-intensiv
            "GRIN": {"core": 100, "mem": 500, "pl": 85},
            
            # IRONFISH (IRON) - Blake3
            "IRON": {"core": 200, "mem": 0, "pl": 60},
            
            # OCTOPUS (CFX)
            "CFX": {"core": 0, "mem": 800, "pl": 75},
            
            # NEXA
            "NEXA": {"core": 200, "mem": 0, "pl": 55},
            
            # DYNEX (DNX)
            "DNX": {"core": 0, "mem": 500, "pl": 70},
            
            # RANDOMX (XMR, ZEPH) - CPU-Mining, GPU nicht relevant
            "XMR": {"core": 0, "mem": 0, "pl": 100},
            "ZEPH": {"core": 0, "mem": 0, "pl": 100},
        }
        
        if coin.upper() in mining_profiles:
            settings = mining_profiles[coin.upper()]
            return OCProfile(
                name=f"{coin}_fallback",
                gpu_index=0,
                core_clock_offset=settings["core"],
                memory_clock_offset=settings["mem"],
                power_limit=settings["pl"]
            )
        
        return None
    
    def apply_mining_profile(self, coin: str) -> Tuple[bool, str]:
        """
        Wendet optimierte Mining-Settings für einen Coin an.
        
        Holt automatisch GPU-spezifische Settings von:
        1. hashrate.no API (GPU-spezifisch)
        2. Lokale Hardware-DB (gecached)
        3. Fallback-Profile (statisch)
        
        Erfordert Admin-Rechte für direktes OC!
        """
        # GPU-Namen erkennen
        gpu_names = self.get_gpu_names()
        
        if not gpu_names:
            # Fallback ohne GPU-Namen
            profile = self.get_mining_profile(coin)
            if profile:
                return self.apply_oc_direct(
                    core_offset=profile.core_clock_offset,
                    memory_offset=profile.memory_clock_offset,
                    power_limit=profile.power_limit
                )
            return False, f"Keine OC-Empfehlung für {coin}"
        
        # Für jede GPU optimale Settings anwenden
        results = []
        all_success = True
        
        for i, gpu_name in enumerate(gpu_names):
            # GPU-spezifische Settings holen (hashrate.no → Hardware-DB → Fallback)
            profile = self.get_mining_profile(coin, gpu_name)
            
            if profile:
                success, msg = self.apply_oc_direct(
                    gpu_index=i,
                    core_offset=profile.core_clock_offset,
                    memory_offset=profile.memory_clock_offset,
                    power_limit=profile.power_limit
                )
                
                source = "hashrate.no" if "hashrateno" in profile.name else "Fallback"
                result_msg = f"GPU {i} ({gpu_name}): {source} - Core {profile.core_clock_offset:+d}, Mem {profile.memory_clock_offset:+d}, PL {profile.power_limit}%"
                results.append(result_msg)
                logger.info(result_msg)
                
                if not success:
                    all_success = False
        
        if results:
            return all_success, "\n".join(results)
        
        return False, f"Keine OC-Empfehlung für {coin}"
    
    def apply_oc_all_gpus(self, coin: str) -> Dict[int, Tuple[bool, str]]:
        """
        Wendet OC für ALLE GPUs an mit GPU-spezifischen Settings.
        
        Returns:
            Dict mit GPU-Index -> (success, message)
        """
        results = {}
        gpu_names = self.get_gpu_names()
        
        if not gpu_names:
            # Keine GPUs erkannt - versuche generisches Profil
            profile = self.get_mining_profile(coin)
            if profile:
                success, msg = self.apply_oc_direct(
                    core_offset=profile.core_clock_offset,
                    memory_offset=profile.memory_clock_offset,
                    power_limit=profile.power_limit
                )
                results[0] = (success, msg)
            else:
                results[0] = (False, "Keine GPU erkannt")
            return results
        
        for i, gpu_name in enumerate(gpu_names):
            profile = self.get_mining_profile(coin, gpu_name)
            
            if profile:
                success, msg = self.apply_oc_direct(
                    gpu_index=i,
                    core_offset=profile.core_clock_offset,
                    memory_offset=profile.memory_clock_offset,
                    power_limit=profile.power_limit
                )
                source = "hashrate.no" if "hashrateno" in profile.name else "Fallback"
                results[i] = (success, f"{gpu_name}: {source} - Core {profile.core_clock_offset:+d}, Mem {profile.memory_clock_offset:+d}, PL {profile.power_limit}%")
            else:
                results[i] = (False, f"{gpu_name}: Keine Settings gefunden")
        
        return results


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = MSIAfterburnerManager()
    
    print("\n=== MSI Afterburner Manager ===")
    print(f"Installiert: {manager.is_installed}")
    print(f"Pfad: {manager.install_path}")
    print(f"Version: {manager.version}")
    print(f"Läuft: {manager.check_running()}")
    
    # Update-Check
    update, current, latest = manager.check_for_updates()
    print(f"\nUpdate verfügbar: {update}")
    print(f"Aktuelle Version: {current}")
    print(f"Neueste Version: {latest}")
    
    # Profile auflisten
    print(f"\nGespeicherte Profile: {manager.list_profiles()}")
    
    # Mining-Profil für RVN
    rvn_profile = manager.get_mining_profile("RVN")
    if rvn_profile:
        print(f"\nRVN Empfehlung:")
        print(f"  Core: {rvn_profile.core_clock_offset:+d} MHz")
        print(f"  Memory: {rvn_profile.memory_clock_offset:+d} MHz")
        print(f"  Power: {rvn_profile.power_limit}%")
