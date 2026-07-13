import uuid
import logging
from datetime import datetime, timezone

from domain.models import (
    Rating, RatingSummary, TargetType,
    RatingException, InvalidScore, RatingNotFound
)
from domain.events import RatingCreated

logger = logging.getLogger(__name__)


class RatingService:
    def __init__(self, repository, broker=None):
        self.repository = repository
        self.broker = broker
        self.exchange = "rating.events"

    def _publish(self, event):
        if not self.broker:
            return
        try:
            self.broker.publish_event(
                exchange=self.exchange,
                routing_key=event.get_routing_key(),
                event_data=event.to_dict()
            )
        except Exception as e:
            logging.exception(f"Failed to publish event {event.event_type}: {e}")

    def _recompute_summary(self, target_id: str, target_type: str):
        ratings = self.repository.find_by_target(target_id, target_type)
        count = len(ratings)
        average = round(sum(r.score for r in ratings) / count, 2) if count > 0 else 0.0
        return average, count

    def create_rating(self, data: dict) -> Rating:
        target_id = data.get("target_id", "")
        target_type = data.get("target_type", TargetType.RESTAURANT)
        score = int(data.get("score", 0))

        if score < 1 or score > 5:
            raise InvalidScore(score)

        rating = Rating(
            id=str(uuid.uuid4()),
            order_id=data.get("order_id", ""),
            rater_id=data.get("rater_id", ""),
            rater_type=data.get("rater_type", "CUSTOMER"),
            target_id=target_id,
            target_type=target_type,
            score=score,
            comment=data.get("comment", "")
        )
        self.repository.save(rating)

        average_score, review_count = self._recompute_summary(target_id, target_type)

        self._publish(RatingCreated(
            entity_type=target_type,
            entity_id=target_id,
            score=score,
            average_score=average_score,
            review_count=review_count
        ))

        return rating

    def get_rating(self, rating_id: str) -> Rating:
        rating = self.repository.find_by_id(rating_id)
        if not rating:
            raise RatingNotFound(rating_id)
        return rating

    def get_ratings_for_target(self, target_id: str, target_type: str) -> list[Rating]:
        return self.repository.find_by_target(target_id, target_type)

    def get_summary(self, target_id: str, target_type: str) -> RatingSummary:
        average_score, review_count = self._recompute_summary(target_id, target_type)
        return RatingSummary(
            target_id=target_id,
            target_type=target_type,
            average_score=average_score,
            review_count=review_count
        )
