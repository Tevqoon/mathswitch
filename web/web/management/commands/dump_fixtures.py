"""
Dump a subset of live DB data as a Django JSON fixture for offline testing.

Samples N items per source, then includes all links between sampled items,
their concepts, and any categorizer results.  The output fixture can be
loaded with `manage.py load_fixtures` (or Django's built-in `loaddata`).

Usage:
    manage.py dump_fixtures                       # 50 items/source -> fixtures/test_data.json
    manage.py dump_fixtures --per-source 100      # 100 items/source
    manage.py dump_fixtures -o my_fixture.json    # custom output path
"""

import json
import random

from django.core.management.base import BaseCommand
from django.core.serializers import serialize

from concepts.models import CategorizerResult, Concept, Item, Link


class Command(BaseCommand):
    help = "Dump a representative subset of DB data as a JSON fixture for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-source",
            type=int,
            default=50,
            help="Number of items to sample per source (default: 50)",
        )
        parser.add_argument(
            "-o",
            "--output",
            type=str,
            default="fixtures/test_data.json",
            help="Output file path (default: fixtures/test_data.json)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible sampling (default: 42)",
        )

    def handle(self, *args, **options):
        per_source = options["per_source"]
        output_path = options["output"]
        seed = options["seed"]

        random.seed(seed)

        # --- 1. Sample items per source ---
        sampled_item_ids = set()
        for source_value, source_label in Item.Source.choices:
            source_items = list(
                Item.objects.filter(source=source_value).values_list("id", flat=True)
            )
            count = len(source_items)
            take = min(per_source, count)
            chosen = random.sample(source_items, take) if take > 0 else []
            sampled_item_ids.update(chosen)
            self.stdout.write(f"  {source_label}: {take}/{count} items sampled")

        if not sampled_item_ids:
            self.stderr.write(self.style.ERROR("No items in DB — nothing to dump."))
            return

        items_qs = Item.objects.filter(id__in=sampled_item_ids)

        # --- 2. Collect links between sampled items ---
        links_qs = Link.objects.filter(
            source_id__in=sampled_item_ids,
            destination_id__in=sampled_item_ids,
        )

        # --- 3. Collect concepts referenced by sampled items ---
        concept_ids = set(
            items_qs.exclude(concept__isnull=True).values_list("concept_id", flat=True)
        )
        concepts_qs = Concept.objects.filter(id__in=concept_ids)

        # --- 4. Collect categorizer results for sampled items ---
        results_qs = CategorizerResult.objects.filter(item_id__in=sampled_item_ids)

        # --- 5. Serialize (concepts first for FK ordering) ---
        fixture_data = []
        fixture_data.extend(json.loads(serialize("json", concepts_qs)))
        fixture_data.extend(json.loads(serialize("json", items_qs)))
        fixture_data.extend(json.loads(serialize("json", links_qs)))
        fixture_data.extend(json.loads(serialize("json", results_qs)))

        # --- 6. Write ---
        import os

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDumped fixture to {output_path}:\n"
                f"  Concepts:           {concepts_qs.count()}\n"
                f"  Items:              {items_qs.count()}\n"
                f"  Links:              {links_qs.count()}\n"
                f"  CategorizerResults: {results_qs.count()}\n"
            )
        )
