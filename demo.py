"""Isolated local demonstration. Never uses the working application database."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

root = Path(__file__).resolve().parent
demo = root / ".demo"
demo.mkdir(exist_ok=True)
credentials = demo / "access.json"
if credentials.exists():
    password = json.loads(credentials.read_text(encoding="utf-8"))["password"]
else:
    password = secrets.token_urlsafe(24)
    credentials.write_text(json.dumps({"customer": "demo-customer", "restaurant_owner": "demo-owner", "password": password}, indent=2), encoding="utf-8")
environment = os.environ.copy()
environment.update(DJANGO_SQLITE_PATH=str(demo / "db.sqlite3"), DJANGO_DEBUG="true", DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1", DEMO_MODE="true", CRAZYEATS_DEMO_PASSWORD=password, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", DJANGO_TRUST_PROXY="false")
for args in (["migrate", "--noinput"], ["create_demo"]):
    subprocess.run([sys.executable, str(root / "manage.py"), *args], env=environment, cwd=root, check=True)
print("Demo accounts are in .demo/access.json. This database contains synthetic data only.")
if "--no-server" not in sys.argv:
    subprocess.run([sys.executable, str(root / "manage.py"), "runserver", "127.0.0.1:8001", "--noreload"], env=environment, cwd=root, check=True)
