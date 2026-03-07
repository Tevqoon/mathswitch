"""
Load test fixtures into the database.

Clears existing data first (concepts, links, items), then loads the
fixture file.  This gives you a clean, reproducible starting point
for testing any pipeline stage from link_same onward.

Usage:
    manage.py load_fixtures                           # loads fixtures/test_data.json
    manage.py load_fixtures -i fixtures/custom.json   # custom fixture
    manage.py load_fixtures --no-clear                # load without clearing first
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear DB and load a test fixture for offline pipeline testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--input",
            type=str,
            default="fixtures/test_data.json",
            help="Fixture file to load (default: fixtures/test_data.json)",
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            default=False,
            help="Skip clearing existing data before loading",
        )

    def handle(self, *args, **options):
        import os

        input_path = options["input"]
        skip_clear = options["no_clear"]

        # Resolve to absolute path so loaddata finds it regardless of CWD
        if not os.path.isabs(input_path):
            input_path = os.path.abspath(input_path)

        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(f"Fixture file not found: {input_path}"))
            self.stderr.write(
                "Run 'make test-dump' first to create a fixture from live data."
            )
            return

        if not skip_clear:
            self.stdout.write("Clearing existing data...")
            call_command("clear_concepts")
            # Links are cascade-deleted with items, but clear explicitly
            # to handle orphaned links
            from concepts.models import Link

            Link.objects.all().delete()
            call_command("clear_wikidata")
            call_command("clear_agda_unimath")
            self.stdout.write("  Done.")

        self.stdout.write(f"Loading fixture: {input_path}")
        call_command("loaddata", input_path)

        # Show what we loaded
        call_command("pipeline_status")
