import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from domain.models import (
    Restaurant, Menu, MenuItem, MenuOption,
    Address, GeoPoint, OpeningHours,
    RestaurantException, RestaurantNotFound, MenuNotFound, RestaurantClosed
)
from domain.events import (
    RestaurantRegistered, RestaurantUpdated, RestaurantClosed as RestaurantClosedEvent,
    MenuUpdated, OrderAccepted, OrderRejected, OrderPreparing, OrderReady
)

logger = logging.getLogger(__name__)


class RestaurantService:
    def __init__(self, repository, broker=None):
        self.repository = repository
        self.broker = broker
        self.exchange = "restaurant.events"

    def _publish(self, event):
        if not self.broker:
            return
        try:
            self.broker.publish_event(
                exchange=self.exchange,
                routing_key=event.event_type,
                event_data=event.to_dict()
            )
        except Exception as e:
            logging.exception(f"Failed to publish event {event.event_type}: {e}")

    # ---- Restaurant CRUD ----

    def create_restaurant(self, data: dict) -> Restaurant:
        address = None
        if data.get("address"):
            addr = data["address"]
            coords = None
            if addr.get("coordinates"):
                coords = GeoPoint(
                    latitude=addr["coordinates"]["latitude"],
                    longitude=addr["coordinates"]["longitude"]
                )
            address = Address(
                street=addr.get("street", ""),
                city=addr.get("city", ""),
                postal_code=addr.get("postal_code", ""),
                coordinates=coords
            )

        opening_hours = {}
        for oh_data in data.get("opening_hours", []):
            hours = OpeningHours(
                day=oh_data["day"],
                open_time=oh_data["open_time"],
                close_time=oh_data["close_time"]
            )
            opening_hours[hours.day] = hours

        restaurant = Restaurant(
            id=str(uuid.uuid4()),
            name=data.get("name", ""),
            address=address,
            phone=data.get("phone", ""),
            cuisine_type=data.get("cuisine_type", "OTHER"),
            opening_hours=opening_hours,
            status=data.get("status", "ACTIVE"),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )

        self.repository.save(restaurant)

        self._publish(RestaurantRegistered(
            restaurant_id=restaurant.id,
            name=restaurant.name,
            address=address and {
                "street": address.street,
                "city": address.city,
                "postal_code": address.postal_code
            },
            cuisine_type=restaurant.cuisine_type
        ))

        return restaurant

    def get_restaurant(self, restaurant_id: str) -> Restaurant:
        restaurant = self.repository.find_by_id(restaurant_id)
        if not restaurant:
            raise RestaurantNotFound(restaurant_id)
        return restaurant

    def get_all_restaurants(self) -> list[Restaurant]:
        return self.repository.find_all()

    def update_restaurant(self, restaurant_id: str, data: dict) -> Restaurant:
        restaurant = self.get_restaurant(restaurant_id)

        if "name" in data:
            restaurant.name = data["name"]
        if "phone" in data:
            restaurant.phone = data["phone"]
        if "cuisine_type" in data:
            restaurant.cuisine_type = data["cuisine_type"]
        if "status" in data:
            old_status = restaurant.status
            restaurant.status = data["status"]
            if data["status"] == "CLOSED" and old_status != "CLOSED":
                self._publish(RestaurantClosedEvent(
                    restaurant_id=restaurant.id,
                    reason=data.get("reason", "Manual close")
                ))
        if "address" in data:
            addr = data["address"]
            coords = None
            if addr.get("coordinates"):
                coords = GeoPoint(
                    latitude=addr["coordinates"]["latitude"],
                    longitude=addr["coordinates"]["longitude"]
                )
            restaurant.address = Address(
                street=addr.get("street", ""),
                city=addr.get("city", ""),
                postal_code=addr.get("postal_code", ""),
                coordinates=coords
            )
        if "opening_hours" in data:
            opening_hours = {}
            for oh_data in data["opening_hours"]:
                hours = OpeningHours(
                    day=oh_data["day"],
                    open_time=oh_data["open_time"],
                    close_time=oh_data["close_time"]
                )
                opening_hours[oh_data["day"]] = hours
            restaurant.opening_hours = opening_hours

        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(RestaurantUpdated(
            restaurant_id=restaurant.id,
            name=restaurant.name,
            cuisine_type=restaurant.cuisine_type
        ))

        return restaurant

    # ---- Menu CRUD ----

    def add_menu(self, restaurant_id: str, data: dict) -> Menu:
        restaurant = self.get_restaurant(restaurant_id)

        menu = Menu(
            id=str(uuid.uuid4()),
            restaurant_id=restaurant_id,
            name=data.get("name", ""),
            is_active=data.get("is_active", True)
        )
        restaurant.menus.append(menu)
        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu.id,
            items=[{"id": i.id, "name": i.name, "price": i.price} for i in menu.items]
        ))

        return menu

    def get_menus(self, restaurant_id: str) -> list[Menu]:
        restaurant = self.get_restaurant(restaurant_id)
        return restaurant.menus

    def get_menu(self, restaurant_id: str, menu_id: str) -> Menu:
        restaurant = self.get_restaurant(restaurant_id)
        for menu in restaurant.menus:
            if menu.id == menu_id:
                return menu
        raise MenuNotFound(menu_id)

    def update_menu(self, restaurant_id: str, menu_id: str, data: dict) -> Menu:
        restaurant = self.get_restaurant(restaurant_id)
        menu = self.get_menu(restaurant_id, menu_id)

        if "name" in data:
            menu.name = data["name"]
        if "is_active" in data:
            menu.is_active = data["is_active"]

        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu.id,
            items=[{"id": i.id, "name": i.name, "price": i.price} for i in menu.items]
        ))

        return menu

    def delete_menu(self, restaurant_id: str, menu_id: str):
        restaurant = self.get_restaurant(restaurant_id)
        menu = self.get_menu(restaurant_id, menu_id)
        restaurant.menus.remove(menu)
        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu_id,
            items=[]
        ))

    # ---- Menu Items CRUD ----

    def add_menu_item(self, restaurant_id: str, menu_id: str, data: dict) -> MenuItem:
        menu = self.get_menu(restaurant_id, menu_id)

        options = []
        for opt_data in data.get("options", []):
            options.append(MenuOption(
                name=opt_data.get("name", ""),
                price=opt_data.get("price", 0.0),
                is_default=opt_data.get("is_default", False)
            ))

        item = MenuItem(
            id=str(uuid.uuid4()),
            name=data.get("name", ""),
            description=data.get("description", ""),
            price=data.get("price", 0.0),
            is_available=data.get("is_available", True),
            options=options
        )
        menu.items.append(item)

        restaurant = self.get_restaurant(restaurant_id)
        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu_id,
            items=[{"id": i.id, "name": i.name, "price": i.price} for i in menu.items]
        ))

        return item

    def update_menu_item(self, restaurant_id: str, menu_id: str, item_id: str, data: dict) -> MenuItem:
        menu = self.get_menu(restaurant_id, menu_id)

        item = None
        for i in menu.items:
            if i.id == item_id:
                item = i
                break
        if not item:
            raise RestaurantException(f"Item {item_id} not found", "ITEM_NOT_FOUND", 404)

        if "name" in data:
            item.name = data["name"]
        if "description" in data:
            item.description = data["description"]
        if "price" in data:
            item.price = data["price"]
        if "is_available" in data:
            item.is_available = data["is_available"]
        if "options" in data:
            item.options = [
                MenuOption(
                    name=o.get("name", ""),
                    price=o.get("price", 0.0),
                    is_default=o.get("is_default", False)
                )
                for o in data["options"]
            ]

        restaurant = self.get_restaurant(restaurant_id)
        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu_id,
            items=[{"id": i.id, "name": i.name, "price": i.price} for i in menu.items]
        ))

        return item

    def delete_menu_item(self, restaurant_id: str, menu_id: str, item_id: str):
        menu = self.get_menu(restaurant_id, menu_id)

        item = None
        for i in menu.items:
            if i.id == item_id:
                item = i
                break
        if not item:
            raise RestaurantException(f"Item {item_id} not found", "ITEM_NOT_FOUND", 404)

        menu.items.remove(item)

        restaurant = self.get_restaurant(restaurant_id)
        restaurant.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(restaurant)

        self._publish(MenuUpdated(
            restaurant_id=restaurant_id,
            menu_id=menu_id,
            items=[{"id": i.id, "name": i.name, "price": i.price} for i in menu.items]
        ))

    # ---- Order Management ----

    def validate_items(self, restaurant_id: str, items: list[dict], requested_delivery_time: Optional[str] = None) -> dict:
        restaurant = self.get_restaurant(restaurant_id)

        if not restaurant.is_open:
            raise RestaurantClosed()

        unavailable = []
        for req_item in items:
            found = False
            for menu in restaurant.menus:
                for menu_item in menu.items:
                    if menu_item.id == req_item.get("dishId") and menu_item.is_available:
                        found = True
                        break
            if not found:
                unavailable.append(req_item.get("dishId"))

        if unavailable:
            return {
                "isValid": False,
                "reason": "Dish not in stock",
                "dishId": unavailable[0]
            }

        return {
            "isValid": True,
            "estimatedPrepTime": 25,
            "notes": "Available"
        }

    def accept_order(self, restaurant_id: str, order_id: str, estimated_prep_time: int = 0) -> dict:
        restaurant = self.get_restaurant(restaurant_id)

        if not restaurant.is_open:
            raise RestaurantClosed()

        self._publish(OrderAccepted(
            restaurant_id=restaurant_id,
            order_id=order_id,
            estimated_prep_time=estimated_prep_time
        ))

        return {"status": "ACCEPTED", "estimatedPrepTime": estimated_prep_time}

    def reject_order(self, restaurant_id: str, order_id: str, reason: str = "OTHER") -> dict:
        self.get_restaurant(restaurant_id)

        self._publish(OrderRejected(
            restaurant_id=restaurant_id,
            order_id=order_id,
            reason=reason
        ))

        return {"status": "REJECTED", "rejectionReason": reason}

    def update_order_status(self, restaurant_id: str, order_id: str, status: str):
        self.get_restaurant(restaurant_id)

        if status == "PREPARING":
            self._publish(OrderPreparing(
                restaurant_id=restaurant_id,
                order_id=order_id,
                estimated_prep_time=0
            ))
        elif status == "READY":
            self._publish(OrderReady(
                restaurant_id=restaurant_id,
                order_id=order_id
            ))

        return {"orderId": order_id, "status": status, "updatedAt": datetime.now(timezone.utc).isoformat()}
