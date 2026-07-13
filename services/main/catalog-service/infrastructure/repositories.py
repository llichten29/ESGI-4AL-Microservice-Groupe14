from typing import Optional

from domain.models import CatalogEntry


class InMemoryCatalogRepository:
    """In-memory search index. The docker-compose still provisions Elasticsearch:
    swapping this repository for an ES-backed one is the documented evolution path."""

    def __init__(self):
        self._entries: dict[str, CatalogEntry] = {}

    def save(self, entry: CatalogEntry):
        self._entries[entry.restaurant_id] = entry

    def find_by_id(self, restaurant_id: str) -> Optional[CatalogEntry]:
        return self._entries.get(restaurant_id)

    def find_all(self) -> list[CatalogEntry]:
        return list(self._entries.values())
