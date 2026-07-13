import logging

from domain.models import Notification, RecipientType, NotificationNotFound

logger = logging.getLogger(__name__)


def _get(event: dict, *keys, default=""):
    """Events mix camelCase (order.events) and snake_case (payment/delivery.events)."""
    for key in keys:
        if key in event:
            return event[key]
    return default


class NotificationService:
    """Turns platform events into notifications. Sending is simulated: each
    notification is logged (channel LOG) and persisted for inspection."""

    def __init__(self, repository):
        self.repository = repository

    def notify(self, recipient_id: str, recipient_type: str, notification_type: str,
               message: str, payload: dict) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            type=notification_type,
            message=message,
            payload=payload
        )
        self.repository.save(notification)
        logger.info(f"[NOTIFY {recipient_type} {recipient_id}] {notification_type}: {message}")
        return notification

    def get_notification(self, notification_id: str) -> Notification:
        notification = self.repository.find_by_id(notification_id)
        if not notification:
            raise NotificationNotFound(notification_id)
        return notification

    def get_notifications(self, recipient_id: str = "", notification_type: str = "") -> list[Notification]:
        return self.repository.find_all(recipient_id, notification_type)

    # ---- Event reactions ----

    def on_event(self, routing_key: str, event: dict):
        handler = {
            "order.created": self._on_order_created,
            "order.confirmed": self._on_order_confirmed,
            "order.cancelled": self._on_order_cancelled,
            "order.delivered": self._on_order_delivered,
            "payment.processed": self._on_payment_processed,
            "payment.failed": self._on_payment_failed,
            "payment.refunded": self._on_payment_refunded,
            "delivery.assigned": self._on_delivery_assigned,
            "delivery.in_progress": self._on_delivery_in_progress,
            "delivery.completed": self._on_delivery_completed
        }.get(routing_key)
        if not handler:
            logger.debug(f"No notification rule for {routing_key}")
            return
        handler(event)

    def _on_order_created(self, event):
        order_id = _get(event, "orderId", "order_id")
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "ORDER_RECEIVED", f"Your order {order_id} has been received", event
        )
        self.notify(
            _get(event, "restaurantId", "restaurant_id"), RecipientType.RESTAURANT,
            "NEW_ORDER", f"New order {order_id} to validate", event
        )

    def _on_order_confirmed(self, event):
        order_id = _get(event, "orderId", "order_id")
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "ORDER_CONFIRMED", f"Payment accepted, order {order_id} confirmed", event
        )

    def _on_order_cancelled(self, event):
        order_id = _get(event, "orderId", "order_id")
        reason = _get(event, "reason", default="unknown")
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "ORDER_CANCELLED", f"Order {order_id} cancelled: {reason}", event
        )

    def _on_order_delivered(self, event):
        order_id = _get(event, "orderId", "order_id")
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "ORDER_DELIVERED", f"Order {order_id} delivered. Enjoy!", event
        )

    def _on_payment_processed(self, event):
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "PAYMENT_RECEIPT", f"Payment of {_get(event, 'amount', default=0)} EUR accepted", event
        )

    def _on_payment_failed(self, event):
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "PAYMENT_FAILED", f"Payment failed: {_get(event, 'reason', default='unknown')}", event
        )

    def _on_payment_refunded(self, event):
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "PAYMENT_REFUNDED", f"Refund of {_get(event, 'amount', default=0)} EUR issued", event
        )

    def _on_delivery_assigned(self, event):
        self.notify(
            _get(event, "delivererId", "deliverer_id"), RecipientType.DELIVERER,
            "DELIVERY_PROPOSAL", f"New delivery for order {_get(event, 'orderId', 'order_id')}", event
        )

    def _on_delivery_in_progress(self, event):
        self.notify(
            _get(event, "customerId", "customer_id"), RecipientType.CUSTOMER,
            "DELIVERY_STARTED", f"Your order {_get(event, 'orderId', 'order_id')} is on its way", event
        )

    def _on_delivery_completed(self, event):
        self.notify(
            _get(event, "delivererId", "deliverer_id"), RecipientType.DELIVERER,
            "DELIVERY_COMPLETED", f"Delivery of order {_get(event, 'orderId', 'order_id')} completed", event
        )
