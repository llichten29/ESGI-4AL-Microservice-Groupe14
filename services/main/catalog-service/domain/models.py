from dataclasses import dataclass, field
from datetime import datetime, timezone


class CatalogException(Exception):
    def __init__(self, message: str, code: str = "CATALOG_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


@dataclass
class CatalogDish:
    id: str = ""
    name: str = ""
    price: float = 0.0


@dataclass
class CatalogEntry:
    """Read model of a restaurant, projected from restaurant.events and rating.events."""
    restaurant_id: str = ""
    name: str = ""
    cuisine_type: str = ""
    address: dict = field(default_factory=dict)
    is_open: bool = True
    rating: float = 0.0
    review_count: int = 0
    dishes: list[CatalogDish] = field(default_factory=list)
    indexed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
