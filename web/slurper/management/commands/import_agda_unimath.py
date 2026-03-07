from django.core.management.base import BaseCommand
from slurper.source_agda_unimath import AgdaUnimathSlurper


class Command(BaseCommand):
    help = "Import items from the agda-unimath concept index"

    def handle(self, *args, **options):
        slurper = AgdaUnimathSlurper()
        self.stdout.write("Fetching concept_index.json from agda-unimath...")
        slurper.fetch_json()
        self.stdout.write(f"Fetched {slurper.stats['fetched']} entries")
        self.stdout.write("Importing items...")
        slurper.save_items()
        self.stdout.write("")
        self.stdout.write(slurper.get_stats_summary())
        self.stdout.write(self.style.SUCCESS("\nAgda Unimath import complete."))
