#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miner Auto-Installer - Wird von START_GUI.bat aufgerufen
Prüft und installiert alle Miner automatisch
"""

import sys
import os
import json
import zipfile
import shutil
from pathlib import Path

# Requests importieren oder Fehler abfangen
try:
    import requests
except ImportError:
    print("       requests nicht installiert, ueberspringe Miner-Check...")
    sys.exit(0)

# HTTP Headers für Downloads (verhindert Connection-Fehler)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/octet-stream, application/zip, */*',
}

# Miner-Konfiguration mit aktualisierten URLs
MINERS = {
    'trex': {
        'name': 'T-Rex',
        'file': 't-rex.exe',
        'version': '0.26.8',
        'url': 'https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip',
        'github': 'trexminer/T-Rex',
        'algos': ['kawpow', 'progpow', 'ethash', 'etchash', 'autolykos2', 'firopow', 'octopus']
    },
    'lolminer': {
        'name': 'lolMiner',
        'file': 'lolMiner.exe',
        'version': '1.88',
        'url': 'https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.88/lolMiner_v1.88_Win64.zip',
        'github': 'Lolliedieb/lolMiner-releases',
        'algos': ['cuckatoo32', 'beamhashiii', 'equihash', 'ethash', 'etchash', 'autolykos2']
    },
    'nbminer': {
        'name': 'NBMiner',
        'file': 'nbminer.exe',
        'version': '42.3',
        'url': 'https://github.com/NebuTech/NBMiner/releases/download/v42.3/NBMiner_42.3_Win.zip',
        'github': 'NebuTech/NBMiner',
        'algos': ['kawpow', 'ethash', 'etchash', 'autolykos2', 'octopus']
    },
    'gminer': {
        'name': 'GMiner',
        'file': 'miner.exe',
        'version': '3.44',
        'url': 'https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_windows64.zip',
        'github': 'develsoftware/GMinerRelease',
        'algos': ['kawpow', 'ethash', 'etchash', 'equihash', 'cuckatoo32', 'autolykos2', 'kheavyhash']
    },
    'rigel': {
        'name': 'Rigel',
        'file': 'rigel.exe',
        'version': '1.19.1',
        'url': 'https://github.com/rigelminer/rigel/releases/download/1.19.1/rigel-1.19.1-win.zip',
        'github': 'rigelminer/rigel',
        'algos': ['kawpow', 'ethash', 'etchash', 'autolykos2', 'kheavyhash', 'pyrinhash', 'sha512256d']
    },
    'bzminer': {
        'name': 'BzMiner',
        'file': 'bzminer.exe',
        'version': '22.0.0',
        'url': 'https://github.com/bzminer/bzminer/releases/download/v22.0.0/bzminer_v22.0.0_windows.zip',
        'github': 'bzminer/bzminer',
        'algos': ['kawpow', 'ethash', 'etchash', 'autolykos2', 'kheavyhash', 'karlsenhash', 'pyrinhash']
    },
    'teamredminer': {
        'name': 'TeamRedMiner',
        'file': 'teamredminer.exe',
        'version': '0.10.21',
        'url': 'https://github.com/todxx/teamredminer/releases/download/v0.10.21/teamredminer-v0.10.21-win.zip',
        'github': 'todxx/teamredminer',
        'algos': ['kawpow', 'ethash', 'etchash', 'autolykos2', 'firopow'],
        'gpu_type': 'AMD'
    },
    'srbminer': {
        'name': 'SRBMiner',
        'file': 'SRBMiner-MULTI.exe',
        'version': '2.6.5',
        'url': 'https://github.com/doktor83/SRBMiner-Multi/releases/download/2.6.5/SRBMiner-Multi-2-6-5-win64.zip',
        'github': 'doktor83/SRBMiner-Multi',
        'algos': ['kawpow', 'autolykos2', 'kheavyhash', 'sha512256d', 'randomx'],
        'gpu_type': 'AMD'
    },
    'xmrig': {
        'name': 'XMRig',
        'file': 'xmrig.exe',
        'version': '6.21.1',
        'url': 'https://github.com/xmrig/xmrig/releases/download/v6.21.1/xmrig-6.21.1-msvc-win64.zip',
        'github': 'xmrig/xmrig',
        'algos': ['randomx', 'ghostrider'],
        'type': 'cpu'
    },
}


class MinerInstaller:
    """Miner-Installer Klasse für einzelne und Batch-Installation"""
    
    def __init__(self, miners_dir: str = "miners"):
        self.miners_dir = Path(miners_dir)
        self.miners_dir.mkdir(exist_ok=True)
        self.versions_file = self.miners_dir / 'versions.json'
        self.installed = self._load_versions()
    
    def _load_versions(self) -> dict:
        """Lädt installierte Versionen"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_versions(self):
        """Speichert installierte Versionen"""
        try:
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(self.installed, f, indent=2)
        except Exception as e:
            print(f"       Fehler beim Speichern: {e}")
    
    def is_installed(self, miner_id: str) -> bool:
        """Prüft ob Miner installiert ist"""
        if miner_id not in MINERS:
            return False
        miner_exe = self.miners_dir / miner_id / MINERS[miner_id]['file']
        return miner_exe.exists()
    
    def get_installed_miners(self) -> list:
        """Gibt Liste installierter Miner zurück"""
        return [mid for mid in MINERS.keys() if self.is_installed(mid)]
    
    def check_updates(self) -> dict:
        """
        Prüft auf verfügbare Updates für installierte Miner.
        Returns: Dict mit {miner_id: {'current': version, 'available': version, 'needs_update': bool}}
        """
        updates = {}
        
        for miner_id in self.get_installed_miners():
            if miner_id not in MINERS:
                continue
            
            config = MINERS[miner_id]
            current = self.installed.get(miner_id, '0.0.0')
            available = config['version']
            
            # Version vergleichen
            try:
                current_parts = [int(x) for x in current.replace('v', '').split('.')]
                available_parts = [int(x) for x in available.replace('v', '').split('.')]
                needs_update = available_parts > current_parts
            except:
                needs_update = current != available
            
            updates[miner_id] = {
                'name': config['name'],
                'current': current,
                'available': available,
                'needs_update': needs_update
            }
        
        return updates
    
    def update_miner(self, miner_id: str) -> bool:
        """Aktualisiert einen Miner auf die neueste Version"""
        if not self.is_installed(miner_id):
            return self.install_miner(miner_id)
        
        # Alten Ordner löschen und neu installieren
        miner_dir = self.miners_dir / miner_id
        if miner_dir.exists():
            import shutil
            shutil.rmtree(miner_dir)
        
        return self.install_miner(miner_id)
    
    def install_miner(self, miner_id: str) -> bool:
        """Installiert einen einzelnen Miner"""
        if miner_id not in MINERS:
            print(f"       Unbekannter Miner: {miner_id}")
            return False
        
        config = MINERS[miner_id]
        miner_dir = self.miners_dir / miner_id
        miner_dir.mkdir(exist_ok=True)
        zip_path = miner_dir / 'download.zip'
        
        try:
            print(f"       Downloading {config['name']} v{config['version']}...")
            
            # Download mit Retry
            for attempt in range(3):
                try:
                    r = requests.get(config['url'], stream=True, timeout=120, headers=HEADERS)
                    r.raise_for_status()
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt < 2:
                        print(f"       Retry {attempt+1}/3...")
                        import time
                        time.sleep(2)
                        continue
                    raise e
            
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        print(f"\r       Downloading {config['name']}... {pct}%", end='', flush=True)
            
            print()
            print(f"       Extracting...")
            
            # Entpacken
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(miner_dir)
            
            # EXE aus Unterordner verschieben
            for root, dirs, files in os.walk(miner_dir):
                if config['file'] in files:
                    src_dir = Path(root)
                    if src_dir != miner_dir:
                        for item in src_dir.iterdir():
                            dst = miner_dir / item.name
                            if dst.exists():
                                if dst.is_dir():
                                    shutil.rmtree(dst)
                                else:
                                    dst.unlink()
                            shutil.move(str(item), str(miner_dir))
                    break
            
            # Leere Unterordner entfernen
            for item in miner_dir.iterdir():
                if item.is_dir():
                    try:
                        if not any(item.iterdir()):
                            item.rmdir()
                    except:
                        pass
            
            # ZIP löschen
            if zip_path.exists():
                zip_path.unlink()
            
            # Version speichern
            self.installed[miner_id] = config['version']
            self._save_versions()
            
            print(f"       ✅ {config['name']} v{config['version']} installiert!")
            return True
            
        except Exception as e:
            print(f"       ❌ FEHLER bei {config['name']}: {e}")
            return False
    
    def install_essential(self) -> tuple:
        """Installiert T-Rex + lolMiner (95% Abdeckung)"""
        success = 0
        failed = 0
        
        for miner_id in ['trex', 'lolminer']:
            if self.is_installed(miner_id):
                print(f"       {MINERS[miner_id]['name']} bereits installiert")
                success += 1
            else:
                if self.install_miner(miner_id):
                    success += 1
                else:
                    failed += 1
        
        return success, failed
    
    def install_all(self) -> tuple:
        """Installiert alle Miner"""
        success = 0
        failed = 0
        
        for miner_id in MINERS.keys():
            if self.is_installed(miner_id):
                print(f"       {MINERS[miner_id]['name']} bereits installiert")
                success += 1
            else:
                if self.install_miner(miner_id):
                    success += 1
                else:
                    failed += 1
        
        return success, failed

def main():
    """Hauptfunktion - installiert alle fehlenden Miner"""
    print()
    print("  ============================================================")
    print("   MINER AUTO-INSTALLER")
    print("  ============================================================")
    print()
    
    installer = MinerInstaller()
    
    # Status anzeigen
    installed_count = len(installer.get_installed_miners())
    print(f"       {installed_count}/{len(MINERS)} Miner installiert")
    
    # Fehlende installieren
    to_install = [mid for mid in MINERS.keys() if not installer.is_installed(mid)]
    
    if to_install:
        print()
        print(f"       Installiere {len(to_install)} fehlende Miner:")
        print()
        
        for miner_id in to_install:
            installer.install_miner(miner_id)
            print()
    else:
        print("       Alle Miner bereits installiert!")
    
    print()
    print("  ============================================================")
    print("   FERTIG!")
    print("  ============================================================")
    print()


if __name__ == "__main__":
    main()
