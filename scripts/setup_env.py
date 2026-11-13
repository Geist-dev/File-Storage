"""Create local configuration once. Never print or overwrite an existing secret."""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'backend' / '.env'
if path.exists():
    print('Using existing backend/.env (unchanged).')
else:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write('# Local configuration. Do not commit this file.\n')
        output.write(f'JWT_SECRET={secrets.token_urlsafe(48)}\n')
        output.write('APP_HOST=127.0.0.1\nAPP_PORT=8000\nMAX_UPLOAD_MB=50\n')
    print('Created backend/.env with a private random secret.')
