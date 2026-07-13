from typing import Optional

from domain.models import Notification


class InMemoryNotificationRepository:
    def __init__(self):
        self._notifications: dict[str, Notification] = {}

    def save(self, notification: Notification):
        self._notifications[notification.id] = notification

    def find_by_id(self, notification_id: str) -> Optional[Notification]:
        return self._notifications.get(notification_id)

    def find_all(self, recipient_id: str = "", notification_type: str = "") -> list[Notification]:
        result = list(self._notifications.values())
        if recipient_id:
            result = [n for n in result if n.recipient_id == recipient_id]
        if notification_type:
            result = [n for n in result if n.type == notification_type]
        return sorted(result, key=lambda n: n.created_at)
