import logging
from typing import Optional

import requests
from concepts.models import Item, Link
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

BASE_URL = "https://unimath.github.io/agda-unimath/"


class AgdaUnimathSlurper:
    JSON_URL = BASE_URL + "concept_index.json"
    # description at https://github.com/UniMath/agda-unimath/pull/884

    def __init__(self):
        self.source = Item.Source.AGDA_UNIMATH
        self.raw_data = None
        self.stats = {
            "fetched": 0,
            "created": 0,
            "skipped_duplicate": 0,
            "links_created": 0,
            "links_wd_missing": 0,
            "links_duplicate": 0,
        }

    def fetch_json(self):
        """Fetch the concept index JSON from the agda-unimath site."""
        response = requests.get(self.JSON_URL, timeout=30)
        response.raise_for_status()
        self.raw_data = response.json()
        self.stats["fetched"] = len(self.raw_data)
        return self.raw_data

    @staticmethod
    def _extract_module_area(entry_id: str) -> Optional[str]:
        """Extract the module area from an entry ID.

        Entry IDs look like:
          group-theory.groups.html#concept-Group
          analysis.convergent-series-real-numbers.html#...

        The module area is the first dot-separated component (before .html),
        with hyphens replaced by spaces.
        """
        # Strip the HTML page part
        page = entry_id.split("#")[0] if "#" in entry_id else entry_id
        # Remove .html suffix
        if page.endswith(".html"):
            page = page[: -len(".html")]
        # The first component is the area (namespace)
        parts = page.split(".")
        if parts:
            return parts[0].replace("-", " ")
        return None

    @staticmethod
    def _extract_module_name(entry_id: str) -> Optional[str]:
        """Extract the module name (second component) from an entry ID.

        E.g., group-theory.groups.html#... -> "groups"
        """
        page = entry_id.split("#")[0] if "#" in entry_id else entry_id
        if page.endswith(".html"):
            page = page[: -len(".html")]
        parts = page.split(".")
        if len(parts) >= 2:
            return parts[1].replace("-", " ")
        return None

    @staticmethod
    def _build_description(json_item: dict) -> Optional[str]:
        """Build a description from available entry fields."""
        parts = []

        # The entry name may include disambiguation in parens
        name = json_item.get("name", "")
        text = json_item.get("text", "")

        # If the full name has disambiguation (in parens), note it
        if "(" in name and text and text != name:
            parts.append(f"Formalized as: {text}")

        # Extract the module area for context
        entry_id = json_item.get("id", "")
        module_name = AgdaUnimathSlurper._extract_module_name(entry_id)
        if module_name:
            parts.append(f"From the agda-unimath library module on {module_name}")

        if json_item.get("definition"):
            parts.append("Has a formal definition in Agda")

        if json_item.get("wikidata"):
            parts.append(f"Wikidata: {json_item['wikidata']}")

        return ". ".join(parts) if parts else None

    @staticmethod
    def _build_keywords(json_item: dict) -> Optional[str]:
        """Build keywords from the module area and text."""
        keywords = set()

        entry_id = json_item.get("id", "")
        area = AgdaUnimathSlurper._extract_module_area(entry_id)
        if area:
            keywords.add(area)

        module_name = AgdaUnimathSlurper._extract_module_name(entry_id)
        if module_name:
            keywords.add(module_name)

        text = json_item.get("text", "")
        if text:
            keywords.add(text.lower())

        # Add "agda-unimath" as a general keyword
        keywords.add("agda-unimath")
        keywords.add("formalized mathematics")

        return ", ".join(sorted(keywords)) if keywords else None

    @staticmethod
    def _build_aliases(json_item: dict) -> Optional[str]:
        """Build aliases from the text field if it differs from name."""
        name = json_item.get("name", "")
        text = json_item.get("text", "")
        if text and text != name:
            return text
        return None

    def json_to_item(self, json_item: dict) -> Item:
        """Convert a JSON entry to an Item model instance."""
        entry_id = json_item["id"]
        link = json_item["link"]
        url = BASE_URL + link

        return Item(
            source=self.source,
            identifier=entry_id,
            url=url,
            name=json_item["name"],
            description=self._build_description(json_item),
            keywords=self._build_keywords(json_item),
            aliases=self._build_aliases(json_item),
        )

    def save_items(self):
        """Save all items from the concept index, creating links to Wikidata items."""
        if self.raw_data is None:
            self.fetch_json()

        for json_item in self.raw_data:
            try:
                item = self.json_to_item(json_item)
                item.save()
                self.stats["created"] += 1

                if "wikidata" in json_item:
                    self._create_wikidata_link(item, json_item["wikidata"])

            except IntegrityError:
                self.stats["skipped_duplicate"] += 1
                logger.debug(
                    "Item %s is already in the database.",
                    json_item.get("id", "unknown"),
                )

        self._log_stats()

    def _create_wikidata_link(self, item: Item, wd_id: str):
        """Create a link from an Agda item to a Wikidata item."""
        try:
            destination = Item.objects.get(
                source=Item.Source.WIKIDATA,
                identifier=wd_id,
            )
            Link.save_new(item, destination, Link.Label.AGDA_UNIMATH)
            self.stats["links_created"] += 1
        except Item.DoesNotExist:
            self.stats["links_wd_missing"] += 1
            logger.debug("Wikidata item %s does not exist.", wd_id)
        except IntegrityError:
            self.stats["links_duplicate"] += 1
            logger.debug(
                "Duplicate link: AUm %s -> WD %s.",
                item.identifier,
                wd_id,
            )

    def _log_stats(self):
        """Log import statistics."""
        logger.info(
            "Agda Unimath import complete: "
            "fetched=%d, created=%d, skipped_duplicate=%d, "
            "links_created=%d, links_wd_missing=%d, links_duplicate=%d",
            self.stats["fetched"],
            self.stats["created"],
            self.stats["skipped_duplicate"],
            self.stats["links_created"],
            self.stats["links_wd_missing"],
            self.stats["links_duplicate"],
        )

    def get_stats_summary(self) -> str:
        """Return a human-readable summary of import statistics."""
        return (
            f"Fetched: {self.stats['fetched']} entries\n"
            f"Created: {self.stats['created']} items\n"
            f"Skipped (duplicate): {self.stats['skipped_duplicate']}\n"
            f"Links created: {self.stats['links_created']}\n"
            f"Links skipped (WD missing): {self.stats['links_wd_missing']}\n"
            f"Links skipped (duplicate): {self.stats['links_duplicate']}"
        )
