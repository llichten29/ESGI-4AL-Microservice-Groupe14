import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class RatingException(Exception):
    def __init__(self, message: str, code: str = "RATING_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class InvalidScore(RatingException):
    def __init__(self, score: float):
        super().__init__(
            f"Score {score} is invalid. Must be between 1 and 5",
            "INVALID_SCORE", 422
        )


class RatingNotFound(RatingException):
    def __init__(self, rating_id: str):
        super().__init__(f"Rating {rating_id} not found", "RATING_NOT_FOUND", 404)


class TargetType:
    RESTAURANT = "RESTAURANT"
    DELIVERER = "DELIVERER"
    CUSTOMER = "CUSTOMER"


class RaterType:
    CUSTOMER = "CUSTOMER"
    DELIVERER = "DELIVERER"
    RESTAURANT = "RESTAURANT"


@dataclass
class Rating:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    rater_id: str = ""
    rater_type: str = RaterType.CUSTOMER
    target_id: str = ""
    target_type: str = TargetType.RESTAURANT
    score: int = 0
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RatingSummary:
    target_id: str = ""
    target_type: str = ""
    average_score: float = 0.0
    review_count: int = 0
