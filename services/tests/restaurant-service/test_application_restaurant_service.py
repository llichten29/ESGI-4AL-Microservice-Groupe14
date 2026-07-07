import pytest
from unittest.mock import MagicMock

from domain.models import (
    Restaurant, Menu, MenuItem, MenuOption,
    Address, GeoPoint, OpeningHours,
    RestaurantNotFound, MenuNotFound, RestaurantClosed, RestaurantException
)
from domain.events import (
    RestaurantRegistered, RestaurantUpdated, RestaurantClosed as RestaurantClosedEvent,
    MenuUpdated, OrderAccepted, OrderRejected, OrderPreparing, OrderReady
)
from infrastructure.repositories import InMemoryRestaurantRepository
from application.restaurant_service import RestaurantService


class TestRestaurantServiceCreate:
    def test_create_restaurant_with_minimal_data(self, restaurant_service_no_broker):
        data = {"name": "Pizza Place", "cuisine_type": "ITALIAN"}
        restaurant = restaurant_service_no_broker.create_restaurant(data)
        assert restaurant.name == "Pizza Place"
        assert restaurant.cuisine_type == "ITALIAN"
        assert restaurant.status == "ACTIVE"
        assert restaurant.id is not None

    def test_create_restaurant_with_full_data(self, restaurant_service_no_broker):
        data = {
            "name": "Full Restaurant",
            "cuisine_type": "FRENCH",
            "phone": "+33123456789",
            "status": "ACTIVE",
            "address": {
                "street": "123 Rue de Paris",
                "city": "Paris",
                "postal_code": "75001",
                "coordinates": {"latitude": 48.8566, "longitude": 2.3522}
            },
            "opening_hours": [
                {"day": "MONDAY", "open_time": "09:00", "close_time": "22:00"},
                {"day": "TUESDAY", "open_time": "09:00", "close_time": "22:00"}
            ]
        }
        restaurant = restaurant_service_no_broker.create_restaurant(data)
        assert restaurant.name == "Full Restaurant"
        assert restaurant.address.street == "123 Rue de Paris"
        assert restaurant.address.coordinates.latitude == 48.8566
        assert "MONDAY" in restaurant.opening_hours
        assert restaurant.opening_hours["MONDAY"].open_time == "09:00"

    def test_create_restaurant_publishes_event(self, restaurant_service, mock_broker):
        data = {"name": "Event Test", "cuisine_type": "JAPANESE"}
        restaurant_service.create_restaurant(data)
        assert mock_broker.publish_event.called
        call_args = mock_broker.publish_event.call_args[1]
        assert call_args["exchange"] == "restaurant.events"
        assert call_args["routing_key"] == "RestaurantRegistered"


class TestRestaurantServiceGet:
    def test_get_restaurant_returns_correct(self, restaurant_service_no_broker):
        data = {"name": "Find Me", "cuisine_type": "MEXICAN"}
        created = restaurant_service_no_broker.create_restaurant(data)
        found = restaurant_service_no_broker.get_restaurant(created.id)
        assert found.id == created.id
        assert found.name == "Find Me"

    def test_get_restaurant_raises_not_found(self, restaurant_service_no_broker):
        with pytest.raises(Exception, match="not found"):
            restaurant_service_no_broker.get_restaurant("nonexistent")

    def test_get_all_restaurants(self, restaurant_service_no_broker):
        restaurant_service_no_broker.create_restaurant({"name": "A"})
        restaurant_service_no_broker.create_restaurant({"name": "B"})
        all_r = restaurant_service_no_broker.get_all_restaurants()
        assert len(all_r) == 2


class TestRestaurantServiceUpdate:
    def test_update_restaurant_fields(self, restaurant_service_no_broker):
        created = restaurant_service_no_broker.create_restaurant({"name": "Old Name"})
        updated = restaurant_service_no_broker.update_restaurant(created.id, {"name": "New Name", "phone": "12345"})
        assert updated.name == "New Name"
        assert updated.phone == "12345"

    def test_update_restaurant_publishes_closed_event(self, restaurant_service, mock_broker):
        created = restaurant_service.create_restaurant({"name": "Closing", "status": "ACTIVE"})
        restaurant_service.update_restaurant(created.id, {"status": "CLOSED", "reason": "Renovation"})
        closed_events = [
            call for call in mock_broker.publish_event.call_args_list
            if call[1]["routing_key"] == "RestaurantClosed"
        ]
        assert len(closed_events) >= 1

    def test_update_restaurant_publishes_updated_event(self, restaurant_service, mock_broker):
        created = restaurant_service.create_restaurant({"name": "Updating"})
        mock_broker.reset_mock()
        restaurant_service.update_restaurant(created.id, {"name": "Updated"})
        updated_events = [
            call for call in mock_broker.publish_event.call_args_list
            if call[1]["routing_key"] == "RestaurantUpdated"
        ]
        assert len(updated_events) >= 1


class TestRestaurantServiceMenu:
    def test_add_menu(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "With Menu"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Lunch Menu"})
        assert menu.name == "Lunch Menu"
        assert menu.restaurant_id == restaurant.id

    def test_get_menus(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Menus"})
        restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Breakfast"})
        restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Dinner"})
        menus = restaurant_service_no_broker.get_menus(restaurant.id)
        assert len(menus) == 2

    def test_get_menu_by_id(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Menu Detail"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Special"})
        found = restaurant_service_no_broker.get_menu(restaurant.id, menu.id)
        assert found.id == menu.id

    def test_get_menu_raises_not_found(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "No Menu"})
        with pytest.raises(Exception, match="not found"):
            restaurant_service_no_broker.get_menu(restaurant.id, "nonexistent")

    def test_update_menu(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Menu Upd"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Old"})
        updated = restaurant_service_no_broker.update_menu(restaurant.id, menu.id, {"name": "New", "is_active": False})
        assert updated.name == "New"
        assert updated.is_active is False

    def test_delete_menu(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Menu Del"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "To Delete"})
        restaurant_service_no_broker.delete_menu(restaurant.id, menu.id)
        assert len(restaurant_service_no_broker.get_menus(restaurant.id)) == 0


class TestRestaurantServiceMenuItem:
    def test_add_menu_item(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Item Add"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        item = restaurant_service_no_broker.add_menu_item(
            restaurant.id, menu.id,
            {"name": "Pizza", "price": 12.50, "description": "Delicious"}
        )
        assert item.name == "Pizza"
        assert item.price == 12.50

    def test_add_menu_item_with_options(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Options"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        item = restaurant_service_no_broker.add_menu_item(
            restaurant.id, menu.id,
            {
                "name": "Burger",
                "price": 10.00,
                "options": [
                    {"name": "Extra Cheese", "price": 1.50, "is_default": False},
                    {"name": "Bacon", "price": 2.00, "is_default": True}
                ]
            }
        )
        assert len(item.options) == 2
        assert item.options[0].name == "Extra Cheese"

    def test_update_menu_item(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Item Upd"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        item = restaurant_service_no_broker.add_menu_item(restaurant.id, menu.id, {"name": "Old", "price": 5.0})
        updated = restaurant_service_no_broker.update_menu_item(
            restaurant.id, menu.id, item.id,
            {"name": "New", "price": 8.0, "is_available": False}
        )
        assert updated.name == "New"
        assert updated.price == 8.0
        assert updated.is_available is False

    def test_delete_menu_item(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Item Del"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        item = restaurant_service_no_broker.add_menu_item(restaurant.id, menu.id, {"name": "X", "price": 1.0})
        restaurant_service_no_broker.delete_menu_item(restaurant.id, menu.id, item.id)
        menu = restaurant_service_no_broker.get_menu(restaurant.id, menu.id)
        assert len(menu.items) == 0

    def test_update_menu_item_not_found(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Not Found"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        with pytest.raises(Exception, match="not found"):
            restaurant_service_no_broker.update_menu_item(restaurant.id, menu.id, "nonexistent", {})


class TestRestaurantServiceOrder:
    def test_validate_items_valid(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Validate"})
        menu = restaurant_service_no_broker.add_menu(restaurant.id, {"name": "Menu"})
        item = restaurant_service_no_broker.add_menu_item(restaurant.id, menu.id, {"name": "Dish", "price": 10.0})
        result = restaurant_service_no_broker.validate_items(
            restaurant.id,
            [{"dishId": item.id, "quantity": 1}]
        )
        assert result["isValid"] is True

    def test_validate_items_unavailable(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Unavail"})
        result = restaurant_service_no_broker.validate_items(
            restaurant.id,
            [{"dishId": "unknown", "quantity": 1}]
        )
        assert result["isValid"] is False
        assert result["reason"] == "Dish not in stock"

    def test_validate_items_closed_restaurant(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({
            "name": "Closed",
            "status": "CLOSED"
        })
        with pytest.raises(Exception, match="closed"):
            restaurant_service_no_broker.validate_items(restaurant.id, [])

    def test_accept_order(self, restaurant_service, mock_broker):
        restaurant = restaurant_service.create_restaurant({"name": "Accept"})
        result = restaurant_service.accept_order(restaurant.id, "order-123", 20)
        assert result["status"] == "ACCEPTED"
        assert result["estimatedPrepTime"] == 20

    def test_accept_order_closed_restaurant(self, restaurant_service_no_broker):
        restaurant = restaurant_service_no_broker.create_restaurant({"name": "Closed", "status": "CLOSED"})
        with pytest.raises(Exception, match="closed"):
            restaurant_service_no_broker.accept_order(restaurant.id, "order-123")

    def test_reject_order(self, restaurant_service, mock_broker):
        restaurant = restaurant_service.create_restaurant({"name": "Reject"})
        result = restaurant_service.reject_order(restaurant.id, "order-123", "OUT_OF_STOCK")
        assert result["status"] == "REJECTED"
        assert result["rejectionReason"] == "OUT_OF_STOCK"

    def test_update_order_status_preparing(self, restaurant_service, mock_broker):
        restaurant = restaurant_service.create_restaurant({"name": "Preparing"})
        result = restaurant_service.update_order_status(restaurant.id, "order-1", "PREPARING")
        assert result["status"] == "PREPARING"

    def test_update_order_status_ready(self, restaurant_service, mock_broker):
        restaurant = restaurant_service.create_restaurant({"name": "Ready"})
        result = restaurant_service.update_order_status(restaurant.id, "order-1", "READY")
        assert result["status"] == "READY"
