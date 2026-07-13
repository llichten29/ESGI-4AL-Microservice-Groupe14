import logging
from datetime import datetime, timezone

from domain.models import CatalogEntry, CatalogDish

logger = logging.getLogger(__name__)


class CatalogService:
    """CQRS-style read side: maintains a searchable projection of restaurants,
    fed exclusively by events (no direct writes)."""

    def __init__(self, repository):
        self.repository = repository

    # ---- Projections (event reactions) ----

    def _touch(self, entry: CatalogEntry):
        entry.indexed_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(entry)

    def on_restaurant_registered(self, event: dict):
        entry = self.repository.find_by_id(event.get("restaurant_id", "")) or CatalogEntry(
            restaurant_id=event.get("restaurant_id", "")
        )
        entry.name = event.get("name", "")
        entry.cuisine_type = event.get("cuisine_type", "")
        entry.address = event.get("address") or {}
        entry.is_open = True
        self._touch(entry)
        logger.info(f"Indexed restaurant {entry.restaurant_id} ({entry.name})")

    def on_restaurant_updated(self, event: dict):
        entry = self.repository.find_by_id(event.get("restaurant_id", ""))
        if not entry:
            return self.on_restaurant_registered(event)
        if event.get("name"):
            entry.name = event["name"]
        if event.get("cuisine_type"):
            entry.cuisine_type = event["cuisine_type"]
        self._touch(entry)

    def on_restaurant_closed(self, event: dict):
        entry = self.repository.find_by_id(event.get("restaurant_id", ""))
        if not entry:
            return
        entry.is_open = False
        self._touch(entry)

    def on_menu_updated(self, event: dict):
        restaurant_id = event.get("restaurant_id", "")
        entry = self.repository.find_by_id(restaurant_id) or CatalogEntry(restaurant_id=restaurant_id)
        entry.dishes = [
            CatalogDish(
                id=i.get("id", ""),
                name=i.get("name", ""),
                price=float(i.get("price", 0.0))
            )
            for i in event.get("items", [])
        ]
        self._touch(entry)

    def on_rating_created(self, event: dict):
        if event.get("entity_type") != "RESTAURANT":
            return
        entry = self.repository.find_by_id(event.get("entity_id", ""))
        if not entry:
            return
        entry.rating = float(event.get("average_score", 0.0))
        entry.review_count = int(event.get("review_count", 0))
        self._touch(entry)

    # ---- Queries ----

    def search_restaurants(self, query: str = "", cuisine_type: str = "", is_open=None,
                           min_rating: float = 0.0, limit: int = 20, offset: int = 0) -> dict:
        results = self.repository.find_all()

        if query:
            q = query.lower()
            results = [
                e for e in results
                if q in e.name.lower() or any(q in d.name.lower() for d in e.dishes)
            ]
        if cuisine_type:
            results = [e for e in results if e.cuisine_type.upper() == cuisine_type.upper()]
        if is_open is not None:
            results = [e for e in results if e.is_open == is_open]
        if min_rating:
            results = [e for e in results if e.rating >= min_rating]

        results.sort(key=lambda e: (-e.rating, e.name))
        total = len(results)
        return {"total": total, "restaurants": results[offset:offset + limit]}

    def search_dishes(self, query: str = "", restaurant_id: str = "",
                      max_price: float = 0.0, limit: int = 20) -> list[dict]:
        matches = []
        for entry in self.repository.find_all():
            if restaurant_id and entry.restaurant_id != restaurant_id:
                continue
            for dish in entry.dishes:
                if query and query.lower() not in dish.name.lower():
                    continue
                if max_price and dish.price > max_price:
                    continue
                matches.append({
                    "dishId": dish.id,
                    "name": dish.name,
                    "price": dish.price,
                    "restaurantId": entry.restaurant_id,
                    "restaurantName": entry.name
                })
        matches.sort(key=lambda d: d["price"])
        return matches[:limit]
