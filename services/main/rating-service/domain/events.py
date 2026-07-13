from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import ClassVar


@dataclass
class BaseEvent:
    event_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    ROUTING_KEY: ClassVar[str] = ""

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def routing_key(self) -> str:
        return self.ROUTING_KEY or self.event_type

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RatingCreated(BaseEvent):
    ROUTING_KEY = "rating.created"
    entity_type: str = ""
    entity_id: str = ""
    score: int = 0
    average_score: float = 0.0
    review_count: int = 0
