#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miner Konfiguration - ALLE Miner mit Auto-Download und Update
Teil des GPU Mining Profit Switcher V11.0 Ultimate
"""

import os
import json
import logging
import requests
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# ALLE VERFÜGBAREN MINER
# ============================================================================

MINER_CONFIGS = {
    # === NVIDIA MINER ===
    "trex": {
        "name": "T-Rex",
        "filename": "t-rex.exe",
        "version": "0.26.8",
        "github_repo": "trexminer/T-Rex",
        "download_url": "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip",
        "algorithms": ["kawpow", "autolykos2", "etchash", "blake3", "octopus", "mtp", "progpow"],
        "coins": ["RVN", "ERG", "ETC", "ALPH", "CFX", "FIRO", "CLORE", "XNA", "MEOWCOIN", "NEOXA"],
        "gpu_type": "nvidia",
        "api_port": 4067,
        "fee": 1.0
    },
    "nbminer": {
        "name": "NBMiner",
        "filename": "nbminer.exe",
        "version": "42.3",
        "github_repo": "NebuTech/NBMiner",
        "download_url": "https://github.com/NebuTech/NBMiner/releases/download/v42.3/NBMiner_42.3_Win.zip",
        "algorithms": ["kawpow", "autolykos2", "etchash", "octopus", "ergo", "kheavyhash"],
        "coins": ["RVN", "ERG", "ETC", "CFX", "KAS", "CLORE"],
        "gpu_type": "both",
        "api_port": 22333,
        "fee": 1.0
    },
    "gminer": {
        "name": "GMiner",
        "filename": "miner.exe",
        "version": "3.44",
        "github_repo": "develsoftware/GMinerRelease",
        "download_url": "https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_windows64.zip",
        "algorithms": ["kawpow", "autolykos2", "etchash", "equihash125", "equihash144", "kheavyhash", "blake3", "octopus"],
        "coins": ["RVN", "ERG", "ETC", "FLUX", "BTG", "KAS", "ALPH", "CFX", "CLORE"],
        "gpu_type": "both",
        "api_port": 10555,
        "fee": 0.65
    },
    "lolminer": {
        "name": "lolMiner",
        "filename": "lolMiner.exe",
        "version": "1.88",
        "github_repo": "Lolliedieb/lolMiner-releases",
        "download_url": "https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.88/lolMiner_v1.88_Win64.zip",
        "algorithms": ["etchash", "autolykos2", "equihash125", "equihash144", "beamhash3", "kheavyhash", "nexapow", "cuckatoo32"],
        "coins": ["ETC", "ERG", "FLUX", "BTG", "BEAM", "KAS", "NEXA", "GRIN"],
        "gpu_type": "both",
        "api_port": 8080,
        "fee": 0.7
    },
    "rigel": {
        "name": "Rigel",
        "filename": "rigel.exe",
        "version": "1.19.1",
        "github_repo": "rigelminer/rigel",
        "download_url": "https://github.com/rigelminer/rigel/releases/download/1.19.1/rigel-1.19.1-win.zip",
        "algorithms": ["kheavyhash", "pyrinhash", "sha512256d", "nexapow", "etchash", "autolykos2", "kawpow"],
        "coins": ["KAS", "PYI", "RXD", "NEXA", "ETC", "ERG", "RVN"],
        "gpu_type": "nvidia",
        "api_port": 5555,
        "fee": 0.7
    },
    "bzminer": {
        "name": "BzMiner",
        "filename": "bzminer.exe",
        "version": "22.0.0",
        "github_repo": "bzminer/bzminer",
        "download_url": "https://github.com/bzminer/bzminer/releases/download/v22.0.0/bzminer_v22.0.0_windows.zip",
        "algorithms": ["kawpow", "etchash", "autolykos2", "kheavyhash", "blake3", "sha512256d", "dynexsolve", "karlsenhash"],
        "coins": ["RVN", "ETC", "ERG", "KAS", "ALPH", "RXD", "DNX", "KLS", "CLORE"],
        "gpu_type": "both",
        "api_port": 4014,
        "fee": 0.5
    },
    "onezerominer": {
        "name": "OneZeroMiner",
        "filename": "onezerominer.exe",
        "version": "1.3.5",
        "github_repo": "OneZeroMiner/onezerominer",
        "download_url": "https://github.com/OneZeroMiner/onezerominer/releases/download/v1.3.5/onezerominer-win64-1.3.5.zip",
        "algorithms": ["dynexsolve", "xelishashv2"],
        "coins": ["DNX", "XEL"],
        "gpu_type": "nvidia",
        "api_port": 10240,
        "fee": 1.0
    },
    
    # === AMD MINER ===
    "teamredminer": {
        "name": "TeamRedMiner",
        "filename": "teamredminer.exe",
        "version": "0.10.21",
        "github_repo": "todxx/teamredminer",
        "download_url": "https://github.com/todxx/teamredminer/releases/download/v0.10.21/teamredminer-v0.10.21-win.zip",
        "algorithms": ["kawpow", "autolykos2", "etchash", "firopow", "kheavyhash"],
        "coins": ["RVN", "ERG", "ETC", "FIRO", "KAS", "CLORE"],
        "gpu_type": "amd",
        "api_port": 4028,
        "fee": 1.0
    },
    "srbminer": {
        "name": "SRBMiner-Multi",
        "filename": "SRBMiner-MULTI.exe",
        "version": "2.6.5",
        "github_repo": "doktor83/SRBMiner-Multi",
        "download_url": "https://github.com/doktor83/SRBMiner-Multi/releases/download/2.6.5/SRBMiner-Multi-2-6-5-win64.zip",
        "algorithms": ["kawpow", "autolykos2", "etchash", "kheavyhash", "blake3", "randomx"],
        "coins": ["RVN", "ERG", "ETC", "KAS", "ALPH", "XMR", "CLORE"],
        "gpu_type": "amd",
        "api_port": 21550,
        "fee": 0.85
    },
    "wildrig": {
        "name": "WildRig Multi",
        "filename": "wildrig.exe",
        "version": "0.40.5",
        "github_repo": "andru-kun/wildrig-multi",
        "download_url": "https://github.com/andru-kun/wildrig-multi/releases/download/0.40.5/wildrig-multi-windows-0.40.5.zip",
        "algorithms": ["kawpow", "firopow", "ghostrider", "nexapow"],
        "coins": ["RVN", "FIRO", "RTM", "NEXA", "CLORE"],
        "gpu_type": "amd",
        "api_port": 4065,
        "fee": 1.0
    },
    
    # === MULTI-GPU MINER ===
    "phoenixminer": {
        "name": "PhoenixMiner",
        "filename": "PhoenixMiner.exe",
        "version": "6.2c",
        "github_repo": None,  # Kein offizielles GitHub
        "download_url": "https://phoenixminer.info/downloads/PhoenixMiner_6.2c_Windows.zip",
        "algorithms": ["etchash", "ethash", "ubqhash", "progpow"],
        "coins": ["ETC", "UBQ", "CLO"],
        "gpu_type": "both",
        "api_port": 3333,
        "fee": 0.65
    },
    
    # === CPU MINER ===
    "xmrig": {
        "name": "XMRig",
        "filename": "xmrig.exe",
        "version": "6.21.1",
        "github_repo": "xmrig/xmrig",
        "download_url": "https://github.com/xmrig/xmrig/releases/download/v6.21.1/xmrig-6.21.1-msvc-win64.zip",
        "algorithms": ["randomx", "ghostrider", "argon2", "cn-heavy", "cn-pico"],
        "coins": ["XMR", "ZEPH", "RTM", "DERO", "WOWNERO"],
        "gpu_type": "cpu",  # CPU Miner!
        "api_port": 8080,
        "fee": 1.0,
        "notes": "CPU Mining für RandomX (Monero, Zephyr) - optimal für AMD Ryzen CPUs"
    }
}

# ============================================================================
# MINER INSTALLER UND UPDATER
# ============================================================================

@dataclass
class MinerInfo:
    """Informationen über einen installierten Miner"""
    id: str
    name: str
    version: str
    installed: bool
    path: str
    latest_version: str
    update_available: bool


class MinerInstaller:
    """Automatischer Miner-Installer und Updater"""
    
    def __init__(self, miners_dir: str = "miners"):
        self.miners_dir = Path(miners_dir)
        self.miners_dir.mkdir(exist_ok=True)
        self.version_file = self.miners_dir / "versions.json"
        self.installed_versions = self._load_versions()
    
    def _load_versions(self) -> Dict[str, str]:
        """Lädt installierte Versionen"""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_versions(self):
        """Speichert installierte Versionen"""
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(self.installed_versions, f, indent=2)
    
    def is_installed(self, miner_id: str) -> bool:
        """Prüft ob ein Miner installiert ist"""
        config = MINER_CONFIGS.get(miner_id)
        if not config:
            return False
        
        miner_path = self.miners_dir / miner_id / config['filename']
        return miner_path.exists()
    
    def get_installed_version(self, miner_id: str) -> Optional[str]:
        """Gibt die installierte Version zurück"""
        return self.installed_versions.get(miner_id)
    
    def get_latest_version(self, miner_id: str) -> Optional[str]:
        """Holt die neueste Version von GitHub"""
        config = MINER_CONFIGS.get(miner_id)
        if not config or not config.get('github_repo'):
            return config.get('version') if config else None
        
        try:
            api_url = f"https://api.github.com/repos/{config['github_repo']}/releases/latest"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tag = data.get('tag_name', '')
                # Version aus Tag extrahieren (z.B. "v0.26.8" -> "0.26.8")
                version = tag.lstrip('v')
                return version
        except Exception as e:
            logger.warning(f"Konnte neueste Version für {miner_id} nicht abrufen: {e}")
        
        return config.get('version')
    
    def check_update(self, miner_id: str) -> Tuple[bool, str, str]:
        """
        Prüft ob ein Update verfügbar ist.
        Returns: (update_available, installed_version, latest_version)
        """
        installed = self.get_installed_version(miner_id)
        latest = self.get_latest_version(miner_id)
        
        if not installed:
            return True, "nicht installiert", latest or "?"
        
        if not latest:
            return False, installed, installed
        
        # Versionen vergleichen
        try:
            from packaging import version
            update_available = version.parse(latest) > version.parse(installed)
        except:
            update_available = latest != installed
        
        return update_available, installed, latest
    
    def download_and_extract(self, miner_id: str, url: str) -> bool:
        """Lädt Miner herunter und entpackt ihn"""
        config = MINER_CONFIGS.get(miner_id)
        if not config:
            return False
        
        miner_dir = self.miners_dir / miner_id
        miner_dir.mkdir(exist_ok=True)
        
        zip_path = miner_dir / "download.zip"
        
        try:
            logger.info(f"Lade {config['name']} herunter...")
            print(f"    Downloading {config['name']}...")
            
            # Download mit Fortschritt
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r    Download: {percent:.1f}%", end="", flush=True)
            
            print()  # Neue Zeile nach Progress
            
            # Entpacken
            logger.info(f"Entpacke {config['name']}...")
            print(f"    Extracting...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(miner_dir)
            
            # Suche die .exe Datei (kann in Unterordner sein)
            exe_name = config['filename']
            exe_found = None
            
            for root, dirs, files in os.walk(miner_dir):
                if exe_name in files:
                    exe_found = Path(root) / exe_name
                    break
            
            # Wenn in Unterordner, Dateien verschieben
            if exe_found and exe_found.parent != miner_dir:
                for item in exe_found.parent.iterdir():
                    target = miner_dir / item.name
                    if target.exists():
                        if target.is_dir():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                    shutil.move(str(item), str(miner_dir))
                
                # Leeren Unterordner löschen
                try:
                    exe_found.parent.rmdir()
                except:
                    pass
            
            # ZIP löschen
            zip_path.unlink()
            
            # Version speichern
            self.installed_versions[miner_id] = config['version']
            self._save_versions()
            
            logger.info(f"{config['name']} erfolgreich installiert!")
            print(f"    ✓ {config['name']} installiert!")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Installieren von {miner_id}: {e}")
            print(f"    ✗ Fehler: {e}")
            return False
    
    def install(self, miner_id: str) -> bool:
        """Installiert einen Miner"""
        config = MINER_CONFIGS.get(miner_id)
        if not config:
            logger.error(f"Unbekannter Miner: {miner_id}")
            return False
        
        return self.download_and_extract(miner_id, config['download_url'])
    
    def update(self, miner_id: str) -> bool:
        """Aktualisiert einen Miner auf die neueste Version"""
        # Erst prüfen ob Update verfügbar
        update_available, installed, latest = self.check_update(miner_id)
        
        if not update_available:
            logger.info(f"{miner_id} ist bereits aktuell ({installed})")
            return True
        
        logger.info(f"Update {miner_id}: {installed} -> {latest}")
        
        # Alten Miner-Ordner löschen
        miner_dir = self.miners_dir / miner_id
        if miner_dir.exists():
            shutil.rmtree(miner_dir)
        
        # Neu installieren
        return self.install(miner_id)
    
    def install_all(self, gpu_type: str = "both") -> Dict[str, bool]:
        """
        Installiert alle Miner für den angegebenen GPU-Typ.
        gpu_type: "nvidia", "amd", oder "both"
        """
        results = {}
        
        for miner_id, config in MINER_CONFIGS.items():
            miner_gpu = config.get('gpu_type', 'both')
            
            # Prüfen ob Miner für GPU-Typ geeignet ist
            if gpu_type == "both" or miner_gpu == "both" or miner_gpu == gpu_type:
                if not self.is_installed(miner_id):
                    results[miner_id] = self.install(miner_id)
                else:
                    results[miner_id] = True
        
        return results
    
    def check_all_updates(self) -> Dict[str, Tuple[bool, str, str]]:
        """Prüft Updates für alle installierten Miner"""
        results = {}
        
        for miner_id in MINER_CONFIGS.keys():
            if self.is_installed(miner_id):
                results[miner_id] = self.check_update(miner_id)
        
        return results
    
    def get_all_info(self) -> List[MinerInfo]:
        """Gibt Infos zu allen Minern zurück"""
        infos = []
        
        for miner_id, config in MINER_CONFIGS.items():
            installed = self.is_installed(miner_id)
            installed_version = self.get_installed_version(miner_id) or "-"
            latest_version = config.get('version', '?')
            
            # Update-Check nur für installierte Miner
            update_available = False
            if installed:
                try:
                    update_available, _, latest_version = self.check_update(miner_id)
                except:
                    pass
            
            infos.append(MinerInfo(
                id=miner_id,
                name=config['name'],
                version=installed_version,
                installed=installed,
                path=str(self.miners_dir / miner_id / config['filename']),
                latest_version=latest_version,
                update_available=update_available
            ))
        
        return infos


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_miners_for_coin(coin: str) -> List[str]:
    """Gibt alle Miner zurück die einen Coin unterstützen"""
    miners = []
    for miner_id, config in MINER_CONFIGS.items():
        if coin.upper() in config.get('coins', []):
            miners.append(miner_id)
    return miners


def get_miners_for_algorithm(algorithm: str) -> List[str]:
    """Gibt alle Miner zurück die einen Algorithmus unterstützen"""
    miners = []
    for miner_id, config in MINER_CONFIGS.items():
        if algorithm.lower() in [a.lower() for a in config.get('algorithms', [])]:
            miners.append(miner_id)
    return miners


def get_miner_executable(miner_id: str, miners_dir: str = "miners") -> Optional[Path]:
    """Gibt den Pfad zur Miner-EXE zurück"""
    config = MINER_CONFIGS.get(miner_id)
    if not config:
        return None
    
    return Path(miners_dir) / miner_id / config['filename']


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    installer = MinerInstaller("miners")
    
    print("\n=== VERFÜGBARE MINER ===")
    for info in installer.get_all_info():
        status = "✓" if info.installed else "✗"
        update = " [UPDATE]" if info.update_available else ""
        print(f"  [{status}] {info.name} v{info.version}{update}")
    
    print("\n=== MINER FÜR COINS ===")
    for coin in ["RVN", "ERG", "KAS", "FLUX"]:
        miners = get_miners_for_coin(coin)
        print(f"  {coin}: {', '.join(miners)}")
