@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Gate.io Wallet Sync
echo ============================================================
echo.

python -c "
from gateio_api import GateIOAPI, GateIOWalletSync
import json

api = GateIOAPI()
if api.is_configured():
    print('Gate.io API konfiguriert')
    print()
    
    # Test Verbindung
    print('Teste Verbindung...')
    balances = api.get_spot_balances()
    if balances is not None:
        print(f'  Verbunden! {len(balances)} Currencies mit Balance')
    
    # Wallets synchronisieren
    print()
    print('Synchronisiere Wallets...')
    sync = GateIOWalletSync(api)
    result = sync.sync_all()
    
    print()
    print(f'Neu: {result[\"new\"]}')
    print(f'Aktualisiert: {result[\"updated\"]}')
    print(f'Total: {result[\"total\"]}')
else:
    print('Gate.io API nicht konfiguriert!')
    print()
    print('Erstelle gateio_config.json:')
    print(json.dumps({'api_key': 'DEIN_KEY', 'api_secret': 'DEIN_SECRET'}, indent=2))
"

echo.
pause
