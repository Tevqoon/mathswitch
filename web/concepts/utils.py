import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from unidecode import unidecode

logger = logging.getLogger(__name__)


class UnionFind:
    def __init__(self, items, links):
        """Initialize union-find with a list of items
        and a list of links given as pairs of items."""
        self.item_to_element: Dict[Any, int] = {}
        self.components: Dict[int, List[int]] = {}
        self.element_links: List[Tuple[int, int]] = []

        self.size = len(items)
        self.item_list = list(items)
        self.parent = list(range(self.size))
        self.rank = [0] * self.size
        for i, item in enumerate(self.item_list):
            self.item_to_element[item] = i
        for link in links:
            resolved = self._resolve_link(link)
            if resolved is not None:
                self.element_links.append(resolved)
        self._compute_components()

    def _resolve_link(self, link) -> Optional[Tuple[int, int]]:
        """Convert a link (pair of items) to a pair of element indices.
        Returns None if either item is not found."""
        items = tuple(link)
        if len(items) != 2:
            logger.warning(
                "Link with %d items (expected 2), skipping: %s", len(items), items
            )
            return None
        a = self.item_to_element.get(items[0])
        b = self.item_to_element.get(items[1])
        if a is None or b is None:
            logger.debug("Link references unknown item(s), skipping: %s", items)
            return None
        return (a, b)

    # find the root element for given element
    def _find_representative(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self._find_representative(self.parent[x])
        return self.parent[x]

    def _union(self, root_x: int, root_y: int):
        if root_x != root_y:
            if self.rank[root_x] < self.rank[root_y]:
                self.parent[root_x] = root_y
            elif self.rank[root_x] > self.rank[root_y]:
                self.parent[root_y] = root_x
            else:
                self.parent[root_y] = root_x
                self.rank[root_x] += 1

    def _connect_elements(self):
        for a, b in self.element_links:
            root_a = self._find_representative(a)
            root_b = self._find_representative(b)
            self._union(root_a, root_b)

    def _compute_components(self):
        self._connect_elements()
        for i in range(self.size):
            root = self._find_representative(i)
            if root not in self.components:
                self.components[root] = [i]
            else:
                self.components[root].append(i)

    def get_item_components(self, sort_key):
        def elements_to_sorted_items(elements: List[int]):
            items = list(map(lambda e: self.item_list[e], elements))
            items.sort(key=sort_key)
            return items

        return list(map(elements_to_sorted_items, self.components.values()))


def normalize_concept_name(name: str) -> str:
    decoded = unquote(name) if name else ""
    nyoo = unidecode(decoded).replace("_", "-").replace(" ", "-").lower()
    return "".join(filter(lambda x: x.isalnum() or x == "-", nyoo))


# German-umlaut digraphs and the single-letter form unidecode already produces
# for the diacritic itself (ö -> o, ä -> a, ü -> u).
_UMLAUT_DIGRAPHS = (("oe", "o"), ("ae", "a"), ("ue", "u"))


def search_variants(name: str) -> set:
    """Expand a search query into the slugs worth matching against.

    Returns the normalized slug plus a German-digraph-collapsed variant, so a
    typed ``moebius`` also matches a stored ``mobius``. This is query-only: it
    does not touch ``normalize_concept_name`` or any stored data. If new fuzzing
    cases come up, add them here rather than re-normalizing the database.
    """
    base = normalize_concept_name(name)
    collapsed = base
    for digraph, single in _UMLAUT_DIGRAPHS:
        collapsed = collapsed.replace(digraph, single)
    return {base, collapsed}


def humanize_concept_name(name: str) -> str:
    """Turn a raw source name into a human-readable UI label.

    Unlike :func:`normalize_concept_name` (which produces a lowercase, ASCII,
    URL-safe slug for lookups and routing), this keeps the original casing and
    diacritics and only undoes the artifacts of URL-derived names: it
    percent-decodes the string and turns underscores back into spaces.

    Examples:
        ``Sasakian_manifold``   -> ``Sasakian manifold``
        ``M%C3%B6bius_strip``   -> ``Möbius strip``
        ``Möbius strip``        -> ``Möbius strip`` (unchanged)
    """
    return unquote(name).replace("_", " ") if name else ""
