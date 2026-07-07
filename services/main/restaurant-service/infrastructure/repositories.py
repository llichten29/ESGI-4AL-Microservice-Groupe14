from typing import Optional
from domain.models import Restaurant


class InMemoryRestaurantRepository:
    def __init__(self):
        self._restaurants: dict[str, Restaurant] = {}

    def save(self, restaurant: Restaurant):
        self._restaurants[restaurant.id] = restaurant

    def find_by_id(self, restaurant_id: str) -> Optional[Restaurant]:
        return self._restaurants.get(restaurant_id)

    def find_all(self) -> list[Restaurant]:
        return list(self._restaurants.values())

    def delete(self, restaurant_id: str):
        self._restaurants.pop(restaurant_id, None)
