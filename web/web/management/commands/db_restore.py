"""
Restore a SQLite database snapshot.

Replaces the current database file with a previously saved snapshot.
Use db_snapshot to create snapshots.

Usage:
    manage.py db_restore                          # <- snapshots/snapshot.sqlite3
    manage.py db_restore --name after-import      # <- snapshots/after-import.sqlite3
"""

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Restore a previously saved SQLite database snapshot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            default="snapshot",
            help="Snapshot name to restore (default: 'snapshot')",
        )
        parser.add_argument(
            "--dir",
            type=str,
            default="snapshots",
            help="Directory containing snapshots (default: 'snapshots')",
        )

    def handle(self, *args, **options):
        db_path = str(settings.DATABASES["default"]["NAME"])
        snap_dir = options["dir"]
        snap_name = options["name"]

        if not os.path.isabs(snap_dir):
            snap_dir = os.path.join(str(settings.BASE_DIR), snap_dir)

        src = os.path.join(snap_dir, f"{snap_name}.sqlite3")

        if not os.path.exists(src):
            available = (
                [
                    f.replace(".sqlite3", "")
                    for f in os.listdir(snap_dir)
                    if f.endswith(".sqlite3")
                ]
                if os.path.isdir(snap_dir)
                else []
            )
            msg = f"Snapshot not found: {src}"
            if available:
                msg += f"\nAvailable snapshots: {', '.join(sorted(available))}"
            self.stderr.write(self.style.ERROR(msg))
            return

        # Close any existing connections before replacing
        from django.db import connections

        for conn in connections.all():
            conn.close()

        shutil.copy2(src, db_path)

        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(f"Restored: {src} -> {db_path} ({size_mb:.1f} MB)")
        )
