import uuid
import logging
from datetime import datetime, timezone

from domain.models import (
    Order, OrderItem, OrderStatus, SagaState,
    OrderException, OrderNotFound, InvalidOrder, RestaurantUnavailable, CancellationNotAllowed
)
from domain.events import OrderCreated, OrderConfirmed, OrderCancelled, OrderDelivered
from main.shared.circuit_breaker import CircuitBreakerException

logger = logging.getLogger(__name__)

DELIVERY_FEE = 2.99


class OrderService:
    """Orchestrator of the order placement SAGA.

    Flow (see documentation/07-SAGA_PATTERN.md):
    1. POST /orders  -> sync validation at the restaurant (circuit breaker) -> order.created
    2. payment.processed -> PAID -> order.confirmed
       payment.failed    -> compensation: CANCELLED -> order.cancelled
    3. OrderAccepted/OrderPreparing/OrderReady (restaurant) -> CONFIRMED/PREPARING/READY
       OrderRejected -> compensation: refund payment (retry + circuit breaker) -> order.cancelled
    4. delivery.assigned/in_progress/completed -> ASSIGNED/DELIVERING/DELIVERED -> order.delivered
    """

    def __init__(self, repository, restaurant_client=None, payment_client=None, broker=None):
        self.repository = repository
        self.restaurant_client = restaurant_client
        self.payment_client = payment_client
        self.broker = broker
        self.exchange = "order.events"

    def _publish(self, event):
        if not self.broker:
            return
        try:
            self.broker.publish_event(
                exchange=self.exchange,
                routing_key=event.routing_key,
                event_data=event.to_dict()
            )
        except Exception as e:
            logging.exception(f"Failed to publish event {event.event_type}: {e}")

    # ---- SAGA step 1: order creation ----

    def create_order(self, data: dict) -> Order:
        customer_id = data.get("customerId", "")
        restaurant_id = data.get("restaurantId", "")
        raw_items = data.get("items", [])
        if not customer_id or not restaurant_id:
            raise InvalidOrder("customerId and restaurantId are required")
        if not raw_items:
            raise InvalidOrder("Order must contain at least one item")

        validation = self._validate_at_restaurant(restaurant_id, raw_items)
        if not validation.get("isValid", False):
            raise InvalidOrder(validation.get("reason", "Order rejected by the restaurant"))

        restaurant = self._fetch_restaurant(restaurant_id)
        items = self._price_items(raw_items, restaurant)

        order = Order(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant.get("name", ""),
            items=items,
            delivery_fee=DELIVERY_FEE,
            total_price=round(sum(i.subtotal for i in items) + DELIVERY_FEE, 2),
            delivery_address=data.get("deliveryAddress", {}),
            payment=data.get("payment", {}),
            status=OrderStatus.CREATED
        )
        order.advance_saga(SagaState.STARTED, "Order validated by restaurant")
        order.advance_saga(SagaState.PAYMENT_PENDING, "order.created published, awaiting payment")
        self.repository.save(order)

        self._publish(OrderCreated(
            order_id=order.id,
            customer_id=order.customer_id,
            restaurant_id=order.restaurant_id,
            restaurant_name=order.restaurant_name,
            total_price=order.total_price,
            items=[{
                "dishId": i.dish_id,
                "name": i.name,
                "quantity": i.quantity,
                "unitPrice": i.unit_price
            } for i in order.items],
            delivery_address=order.delivery_address,
            payment=order.payment
        ))

        return order

    def _validate_at_restaurant(self, restaurant_id: str, items: list) -> dict:
        if not self.restaurant_client:
            return {"isValid": True}
        try:
            return self.restaurant_client.validate_order(restaurant_id, items)
        except CircuitBreakerException:
            logger.warning("Restaurant circuit breaker is OPEN - failing fast")
            raise RestaurantUnavailable()
        except Exception as e:
            logger.warning(f"Restaurant validation failed: {e}")
            raise RestaurantUnavailable(f"Could not validate order: {e}")

    def _fetch_restaurant(self, restaurant_id: str) -> dict:
        if not self.restaurant_client:
            return {}
        try:
            return self.restaurant_client.get_restaurant(restaurant_id)
        except CircuitBreakerException:
            raise RestaurantUnavailable()
        except Exception as e:
            raise RestaurantUnavailable(f"Could not fetch restaurant: {e}")

    def _price_items(self, raw_items: list, restaurant: dict) -> list[OrderItem]:
        prices = {}
        names = {}
        for menu in restaurant.get("menus", []):
            for item in menu.get("items", []):
                prices[item.get("id")] = item.get("price", 0.0)
                names[item.get("id")] = item.get("name", "")

        items = []
        for raw in raw_items:
            dish_id = raw.get("dishId", "")
            quantity = int(raw.get("quantity", 1))
            if quantity < 1:
                raise InvalidOrder(f"Invalid quantity for dish {dish_id}")
            items.append(OrderItem(
                dish_id=dish_id,
                name=names.get(dish_id, raw.get("name", "")),
                quantity=quantity,
                unit_price=float(prices.get(dish_id, raw.get("unitPrice", 0.0)))
            ))
        return items

    # ---- Queries ----

    def get_order(self, order_id: str) -> Order:
        order = self.repository.find_by_id(order_id)
        if not order:
            raise OrderNotFound(order_id)
        return order

    def get_customer_orders(self, customer_id: str) -> list[Order]:
        return self.repository.find_by_customer(customer_id)

    def get_circuit_breakers(self) -> list[dict]:
        breakers = []
        if self.restaurant_client:
            breakers.append(self.restaurant_client.circuit_breaker.get_state())
        if self.payment_client:
            breakers.append(self.payment_client.circuit_breaker.get_state())
        return breakers

    # ---- Cancellation (customer initiated) ----

    def cancel_order(self, order_id: str, reason: str = "Cancelled by customer") -> Order:
        order = self.get_order(order_id)
        if order.status == OrderStatus.CANCELLED:
            return order
        if order.status not in (OrderStatus.CREATED, OrderStatus.PAID):
            raise CancellationNotAllowed(order.status)

        if order.payment_id:
            self._refund(order, reason)

        self._cancel(order, reason)
        return order

    # ---- SAGA reactions to events ----

    def on_payment_processed(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order:
            logger.warning(f"payment.processed for unknown order {event.get('order_id')}")
            return
        if order.status != OrderStatus.CREATED:
            logger.info(f"Order {order.id} already in {order.status} - ignoring payment.processed")
            return

        order.status = OrderStatus.PAID
        order.payment_id = event.get("payment_id", "")
        order.advance_saga(SagaState.PAYMENT_COMPLETED, f"Payment {order.payment_id} completed")
        order.advance_saga(SagaState.AWAITING_ACCEPTANCE, "Awaiting restaurant acceptance")
        self.repository.save(order)

        self._publish(OrderConfirmed(
            order_id=order.id,
            customer_id=order.customer_id,
            restaurant_id=order.restaurant_id,
            payment_id=order.payment_id,
            total_price=order.total_price
        ))

    def on_payment_failed(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order:
            return
        if order.status == OrderStatus.CANCELLED:
            return

        reason = f"Payment failed: {event.get('reason', 'unknown')}"
        order.advance_saga(SagaState.COMPENSATED, reason)
        self._cancel(order, reason, advance_saga=False)

    def on_order_accepted(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status != OrderStatus.PAID:
            return
        order.status = OrderStatus.CONFIRMED
        order.advance_saga(SagaState.ACCEPTED, f"Accepted by restaurant {order.restaurant_id}")
        self.repository.save(order)

    def on_order_preparing(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status not in (OrderStatus.PAID, OrderStatus.CONFIRMED):
            return
        order.status = OrderStatus.PREPARING
        order.advance_saga(SagaState.PREPARING, "Order in preparation")
        self.repository.save(order)

    def on_order_ready(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status not in (
            OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARING
        ):
            return
        order.status = OrderStatus.READY
        order.advance_saga(SagaState.READY_FOR_DELIVERY, "Ready, awaiting deliverer")
        self.repository.save(order)

    def on_order_rejected(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status == OrderStatus.CANCELLED:
            return

        reason = f"Rejected by restaurant: {event.get('reason', 'OTHER')}"
        if order.payment_id:
            self._refund(order, reason)
        order.advance_saga(SagaState.COMPENSATED, reason)
        self._cancel(order, reason, advance_saga=False)

    def on_delivery_assigned(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status != OrderStatus.READY:
            return
        order.status = OrderStatus.ASSIGNED
        order.delivery_id = event.get("delivery_id", "")
        order.advance_saga(SagaState.DELIVERY_ASSIGNED, f"Delivery {order.delivery_id} assigned")
        self.repository.save(order)

    def on_delivery_in_progress(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status not in (OrderStatus.READY, OrderStatus.ASSIGNED):
            return
        order.status = OrderStatus.DELIVERING
        order.advance_saga(SagaState.DELIVERING, "Delivery in progress")
        self.repository.save(order)

    def on_delivery_completed(self, event: dict):
        order = self.repository.find_by_id(event.get("order_id", ""))
        if not order or order.status == OrderStatus.DELIVERED:
            return

        order.status = OrderStatus.DELIVERED
        order.advance_saga(SagaState.COMPLETED, "Order delivered")
        order.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(order)

        self._publish(OrderDelivered(
            order_id=order.id,
            customer_id=order.customer_id,
            restaurant_id=order.restaurant_id,
            delivery_id=order.delivery_id
        ))

    # ---- Compensation helpers ----

    def _refund(self, order: Order, reason: str):
        if not self.payment_client:
            return
        try:
            self.payment_client.refund(order.payment_id, amount=0.0, reason=reason)
            logger.info(f"Payment {order.payment_id} refunded for order {order.id}")
        except Exception as e:
            # Compensation could not complete: flag the SAGA for manual intervention.
            logging.exception(f"CRITICAL: refund of {order.payment_id} failed for order {order.id}: {e}")
            order.advance_saga(SagaState.FAILED, f"Refund failed: {e}")

    def _cancel(self, order: Order, reason: str, advance_saga: bool = True):
        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = reason
        if advance_saga:
            order.advance_saga(SagaState.COMPENSATED, reason)
        self.repository.save(order)

        self._publish(OrderCancelled(
            order_id=order.id,
            customer_id=order.customer_id,
            restaurant_id=order.restaurant_id,
            reason=reason
        ))
