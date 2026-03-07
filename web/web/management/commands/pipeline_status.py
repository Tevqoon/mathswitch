"""
Show current pipeline state: counts of Items (per source), Links (per label),
Concepts, and CategorizerResults.

Usage:
    manage.py pipeline_status
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from concepts.models import CategorizerResult, Concept, Item, Link


class Command(BaseCommand):
    help = "Show counts of all data in the pipeline (Items, Links, Concepts, etc.)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Pipeline Status ===\n"))

        # --- Items per source ---
        total_items = Item.objects.count()
        self.stdout.write(f"Items: {total_items} total")
        for source_value, source_label in Item.Source.choices:
            count = Item.objects.filter(source=source_value).count()
            if count > 0:
                self.stdout.write(f"  {source_label:30s} {count:>6}")

        # --- Links per label ---
        total_links = Link.objects.count()
        self.stdout.write(f"\nLinks: {total_links} total")
        for label_value, label_label in Link.Label.choices:
            count = Link.objects.filter(label=label_value).count()
            if count > 0:
                self.stdout.write(f"  {label_label:30s} {count:>6}")

        # --- Concepts ---
        total_concepts = Concept.objects.count()
        assigned_items = Item.objects.exclude(concept__isnull=True).count()
        unassigned_items = Item.objects.filter(concept__isnull=True).count()
        self.stdout.write(f"\nConcepts: {total_concepts} total")
        self.stdout.write(f"  Items with concept:            {assigned_items:>6}")
        self.stdout.write(f"  Items without concept:         {unassigned_items:>6}")

        # Multi-item concepts (concepts that group >1 item)
        multi = Concept.objects.annotate(n=Count("item")).filter(n__gt=1).count()
        self.stdout.write(f"  Multi-item concepts:           {multi:>6}")

        # --- Categorizer results ---
        total_results = CategorizerResult.objects.count()
        if total_results > 0:
            yes_count = CategorizerResult.objects.filter(result_answer=True).count()
            no_count = CategorizerResult.objects.filter(result_answer=False).count()
            self.stdout.write(f"\nCategorizerResults: {total_results} total")
            self.stdout.write(f"  Yes (is math concept):         {yes_count:>6}")
            self.stdout.write(f"  No  (not math concept):        {no_count:>6}")
        else:
            self.stdout.write("\nCategorizerResults: 0")

        self.stdout.write("")
