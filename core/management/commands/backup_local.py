from contextlib import closing
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

class Command(BaseCommand):
    help = "Create and verify a new SQLite/media recovery archive. Store securely off-server."
    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("For PostgreSQL use pg_dump and a separate media-volume backup; see README.")
        if connection.in_atomic_block:
            raise CommandError("Run backups outside database transactions.")
        target = Path(options["output"]).resolve()
        if target.exists():
            raise CommandError("Output already exists; choose a new backup filename.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temp:
            snapshot = Path(temp) / "db.sqlite3"
            connection.ensure_connection()
            with closing(sqlite3.connect(snapshot)) as dest:
                connection.connection.backup(dest)
                if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise CommandError("Snapshot integrity verification failed.")
            with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "db.sqlite3")
                media = Path(settings.MEDIA_ROOT)
                files = [file for file in media.rglob("*") if file.is_file() and not file.is_symlink() and media.resolve() in file.resolve().parents]
                for file in files:
                    archive.write(file, "media/" + file.relative_to(media).as_posix())
                archive.writestr("manifest.json", json.dumps({"database_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(), "media_files": len(files), "format": 1}))
            with zipfile.ZipFile(target) as archive:
                if archive.testzip() is not None:
                    raise CommandError("Archive verification failed.")
        self.stdout.write("Verified SQLite and media backup created. This archive contains private application data; protect it.")
