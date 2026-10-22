"""Railway bootstrap. Application auth and approval policies remain upstream-owned."""
import asyncio
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import signal
import time

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
proxy = os.environ.get('RAILWAY_HTTPS_PROXY') == 'true'
port = int(os.environ.get('PORT', '8000'))
if not 1024 <= port <= 65535:
    raise SystemExit('PORT must be an unprivileged TCP port.')
if proxy:
    # Only the same-container proxy may supply the backend's HTTPS scheme.
    # Railway's public edge accepts HTTPS and redirects plain HTTP itself.
    os.environ['OPEN_DOTS_HOST'] = '127.0.0.1'
    os.environ['DUET_BACKEND_PORT'] = '8001' if port != 8001 else '8002'
    os.environ['OPEN_DOTS_PORT'] = os.environ['DUET_BACKEND_PORT']
else:
    os.environ['OPEN_DOTS_PORT'] = str(port)
subprocess.run([sys.executable, '-m', 'app.server', 'migrate'], check=True)

# This launcher lives outside the backend; make its Docker WORKDIR importable.
sys.path.insert(0, os.getcwd())

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
if not proxy:
    os.execv(sys.executable, [sys.executable, '-m', 'app.server'])

stopping = False
def stop(signum, frame):
    global stopping
    stopping = True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
children = []
code = 0
try:
    children.append(subprocess.Popen([sys.executable, '-m', 'app.server']))
    children.append(subprocess.Popen(['caddy', 'run', '--config', '/opt/railway/Caddyfile', '--adapter', 'caddyfile']))
    while not stopping:
        exited = next((child for child in children if child.poll() is not None), None)
        if exited is not None:
            code = exited.returncode or 1
            break
        time.sleep(0.2)
finally:
    # Stop accepting requests first, then give the backend time to flush SQLite.
    for child in reversed(children):
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
raise SystemExit(code)
