from typing import Optional

from domain.models import Rating


class InMemoryRatingRepository:
    def __init__(self):
        self._ratings: dict[str, Rating] = {}

    def save(self, rating: Rating):
        self._ratings[rating.id] = rating

    def find_by_id(self, rating_id: str) -> Optional[Rating]:
        return self._ratings.get(rating_id)

    def find_by_target(self, target_id: str, target_type: str) -> list[Rating]:
        return [
            r for r in self._ratings.values()
            if r.target_id == target_id and r.target_type == target_type
        ]

    def find_all(self) -> list[Rating]:
        return list(self._ratings.values())
