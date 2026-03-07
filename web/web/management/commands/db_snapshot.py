"""
Snapshot the current SQLite database to a named file.

This is the fastest way to save/restore pipeline state at any stage.
Use db_restore to restore a snapshot.

Usage:
    manage.py db_snapshot                         # -> snapshots/snapshot.sqlite3
    manage.py db_snapshot --name after-import     # -> snapshots/after-import.sqlite3
    manage.py db_snapshot --name after-links
"""

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Snapshot the current SQLite database file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            default="snapshot",
            help="Snapshot name (used as filename, default: 'snapshot')",
        )
        parser.add_argument(
            "--dir",
            type=str,
            default="snapshots",
            help="Directory to store snapshots (default: 'snapshots')",
        )

    def handle(self, *args, **options):
        db_path = settings.DATABASES["default"]["NAME"]
        snap_dir = options["dir"]
        snap_name = options["name"]

        if not os.path.isabs(snap_dir):
            snap_dir = os.path.join(settings.BASE_DIR, snap_dir)

        os.makedirs(snap_dir, exist_ok=True)

        dest = os.path.join(snap_dir, f"{snap_name}.sqlite3")
        shutil.copy2(str(db_path), dest)

        size_mb = os.path.getsize(dest) / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(f"Snapshot saved: {dest} ({size_mb:.1f} MB)")
        )
