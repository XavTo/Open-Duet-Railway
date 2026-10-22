"""Railway bootstrap. Application auth and approval policies remain upstream-owned."""
import asyncio
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import sys

if os.geteuid() == 0:
    # Fresh Railway volumes are root-owned; the app and model CLIs run unprivileged.
    os.chown('/data', 10001, 10001)
    os.execvp('gosu', ['gosu', 'opendots', sys.executable, __file__])

password = os.environ.get('APP_PASSWORD', '')
if len(password) < 16:
    raise SystemExit('APP_PASSWORD must contain at least 16 characters.')
if not os.environ.get('TOKEN_ENCRYPTION_KEYS'):
    seed = os.environ.get('ENCRYPTION_SECRET', '')
    if len(seed) < 32:
        raise SystemExit('ENCRYPTION_SECRET must contain at least 32 characters.')
    os.environ['TOKEN_ENCRYPTION_KEYS'] = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()).decode()
os.environ['OPEN_DOTS_PORT'] = os.environ.get('PORT', '8000')
subprocess.run([sys.executable, '-m', 'app.server', 'migrate'], check=True)

async def bootstrap_owner():
    from app.auth import store
    from app.db.session import AsyncSessionLocal, engine
    try:
        async with AsyncSessionLocal() as db:
            if not await store.owner_configured(db):
                await store.set_passphrase(db, password, first_time_only=True)
                print('Owner initialized. Sign in with APP_PASSWORD.', flush=True)
    finally:
        await engine.dispose()

asyncio.run(bootstrap_owner())
os.execv(sys.executable, [sys.executable, '-m', 'app.server'])
