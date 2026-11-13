"""Run the UI and API together with settings from backend/.env."""
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from config import settings

if __name__ == '__main__':
    print(f'File Storage: http://{settings.APP_HOST}:{settings.APP_PORT}', flush=True)
    uvicorn.run('app:app', host=settings.APP_HOST, port=settings.APP_PORT, log_level='info')
