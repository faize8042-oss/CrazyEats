"""Temporary, read-only catalog preview. Never exposes the working database."""
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / ".preview"
PREVIEW.mkdir(exist_ok=True)
os.environ.update(DJANGO_DEBUG="false", DEMO_MODE="true", DJANGO_SQLITE_PATH=str(PREVIEW / "db.sqlite3"), DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1", DJANGO_SECRET_KEY=secrets.token_urlsafe(64), DJANGO_TRUST_PROXY="false", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CrazyEats.settings")
if "--prepare" in sys.argv:
    subprocess.run([sys.executable, str(ROOT / "manage.py"), "migrate", "--noinput"], env=os.environ.copy(), check=True, cwd=ROOT)
import django
django.setup()
from django.core.wsgi import get_wsgi_application
from core.models import User, Restaurant, Category, Food

if "--prepare" in sys.argv:
    # Only public catalog fields are copied. No customers, orders or credentials.
    source = sqlite3.connect(f"file:{(ROOT / 'db.sqlite3').as_posix()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    owner, _ = User.objects.get_or_create(username="catalog-preview-owner", defaults={"is_active": False})
    for table, model, where, exclude in [
        ("core_restaurant", Restaurant, "is_approved = 1", {"owner_id"}),
        ("core_category", Category, "restaurant_id IN (SELECT id FROM core_restaurant WHERE is_approved = 1)", set()),
        ("core_food", Food, "is_available = 1 AND restaurant_id IN (SELECT id FROM core_restaurant WHERE is_approved = 1)", set()),
    ]:
        for row in source.execute(f"SELECT * FROM {table} WHERE {where}"):
            data = {key: row[key] for key in row.keys() if key not in exclude | {"id", "created_at", "updated_at"}}
            if model is Restaurant: data["owner_id"] = owner.pk
            model.objects.update_or_create(pk=row["id"], defaults=data)
    source.close()
    print("Read-only preview catalog prepared; working accounts and orders excluded.")
    sys.exit(0)

application = get_wsgi_application()
allowed_media = {str(value) for value in Food.objects.values_list("image", flat=True) if value}
for field in ("logo", "cover_image"):
    allowed_media.update(str(value) for value in Restaurant.objects.values_list(field, flat=True) if value)
allowed_media.update(str(value) for value in Category.objects.values_list("image", flat=True) if value)

def response(start, status, text):
    body = text.encode()
    start(status, [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body))), ("X-Robots-Tag", "noindex, nofollow"), ("Cache-Control", "no-store")])
    return [body]

def preview(environ, start):
    path = environ.get("PATH_INFO", "/")
    if environ.get("REQUEST_METHOD") not in {"GET", "HEAD"}:
        return response(start, "405 Method Not Allowed", "This client preview is read-only. Orders are not fulfilled.")
    if path.startswith(("/static/", "/media/")):
        media = path.startswith("/media/")
        relative = path.split("/", 2)[-1]
        if media and relative not in allowed_media:
            return response(start, "404 Not Found", "Not found")
        base = ROOT / ("media" if media else "static")
        target = (base / relative).resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            return response(start, "404 Not Found", "Not found")
        content = target.read_bytes()
        start("200 OK", [("Content-Type", mimetypes.guess_type(target)[0] or "application/octet-stream"), ("Content-Length", str(len(content))), ("X-Content-Type-Options", "nosniff"), ("X-Robots-Tag", "noindex, nofollow")])
        return [] if environ["REQUEST_METHOD"] == "HEAD" else [content]
    if not re.fullmatch(r"/|/restaurants/|/restaurants/[0-9]+/|/food/[0-9]+/|/health/", path):
        return response(start, "403 Forbidden", "Client preview: browse the homepage and restaurant menus. Accounts, administration and checkout are unavailable in this read-only preview.")
    environ["wsgi.url_scheme"] = "https"
    environ["HTTP_HOST"] = "localhost"
    def headers(status, values, exc_info=None):
        values.append(("X-Robots-Tag", "noindex, nofollow"))
        return start(status, values, exc_info)
    return application(environ, headers)

class PreviewServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

with make_server("127.0.0.1", 8002, preview, server_class=PreviewServer) as server:
    print("Read-only client preview ready on 127.0.0.1:8002", flush=True)
    server.serve_forever()
