import pytest
from unittest.mock import MagicMock
import jwt

from domain.models import (
    Customer, CustomerAddress, OrderRef,
    CustomerNotFound, InvalidCredentials, EmailAlreadyExists, CustomerException
)
from application.customer_service import CustomerService


class TestCustomerServiceRegister:
    def test_register_creates_customer_and_token(self, customer_service_no_broker):
        customer, token = customer_service_no_broker.register({
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secure123"
        })
        assert customer.name == "Alice"
        assert customer.email == "alice@example.com"
        assert customer.password_hash != "secure123"
        assert token is not None

        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["customer_id"] == customer.id
        assert decoded["email"] == "alice@example.com"

    def test_register_raises_for_duplicate_email(self, customer_service_no_broker):
        customer_service_no_broker.register({
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secure123"
        })
        with pytest.raises(Exception, match="already registered"):
            customer_service_no_broker.register({
                "name": "Alice 2",
                "email": "alice@example.com",
                "password": "secure456"
            })

    def test_register_raises_for_short_password(self, customer_service_no_broker):
        with pytest.raises(Exception, match="at least 6 characters"):
            customer_service_no_broker.register({
                "name": "Bob",
                "email": "bob@example.com",
                "password": "12345"
            })

    def test_register_raises_for_missing_email(self, customer_service_no_broker):
        with pytest.raises(Exception, match="Email is required"):
            customer_service_no_broker.register({
                "name": "Bob",
                "email": "",
                "password": "secure123"
            })

    def test_register_with_address(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Carol",
            "email": "carol@example.com",
            "password": "secure123",
            "address": {
                "label": "Home",
                "street": "1 Rue de Paris",
                "city": "Paris",
                "postal_code": "75001"
            }
        })
        assert len(customer.addresses) == 1
        assert customer.addresses[0].label == "Home"
        assert customer.addresses[0].is_default is True

    def test_register_publishes_event(self, customer_service, mock_broker):
        customer_service.register({
            "name": "Event",
            "email": "event@example.com",
            "password": "secure123"
        })
        assert mock_broker.publish_event.called
        call_args = mock_broker.publish_event.call_args[1]
        assert call_args["exchange"] == "customer.events"
        assert call_args["routing_key"] == "CustomerRegistered"

    def test_register_does_not_publish_without_broker(self, customer_service_no_broker):
        customer_service_no_broker.register({
            "name": "No Broker",
            "email": "nobroker@example.com",
            "password": "secure123"
        })

    def test_register_normalizes_email(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Case",
            "email": "UPPERCASE@Example.COM",
            "password": "secure123"
        })
        assert customer.email == "uppercase@example.com"


class TestCustomerServiceLogin:
    def test_login_with_valid_credentials(self, customer_service_no_broker):
        customer_service_no_broker.register({
            "name": "Login",
            "email": "login@example.com",
            "password": "secure123"
        })
        customer, token = customer_service_no_broker.login("login@example.com", "secure123")
        assert customer.email == "login@example.com"
        assert token is not None

    def test_login_raises_for_wrong_email(self, customer_service_no_broker):
        with pytest.raises(Exception, match="Invalid email or password"):
            customer_service_no_broker.login("unknown@example.com", "secure123")

    def test_login_raises_for_wrong_password(self, customer_service_no_broker):
        customer_service_no_broker.register({
            "name": "Wrong",
            "email": "wrong@example.com",
            "password": "secure123"
        })
        with pytest.raises(Exception, match="Invalid email or password"):
            customer_service_no_broker.login("wrong@example.com", "wrongpass")


class TestCustomerServiceProfile:
    def test_get_profile(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Profile",
            "email": "profile@example.com",
            "password": "secure123"
        })
        found = customer_service_no_broker.get_profile(customer.id)
        assert found.id == customer.id
        assert found.name == "Profile"

    def test_get_profile_raises_not_found(self, customer_service_no_broker):
        with pytest.raises(Exception, match="not found"):
            customer_service_no_broker.get_profile("nonexistent")

    def test_update_profile(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Old Name",
            "email": "update@example.com",
            "password": "secure123"
        })
        updated = customer_service_no_broker.update_profile(customer.id, {"name": "New Name", "phone": "12345"})
        assert updated.name == "New Name"
        assert updated.phone == "12345"

    def test_update_profile_email_already_exists(self, customer_service_no_broker):
        customer_service_no_broker.register({
            "name": "First",
            "email": "first@example.com",
            "password": "secure123"
        })
        customer2, _ = customer_service_no_broker.register({
            "name": "Second",
            "email": "second@example.com",
            "password": "secure123"
        })
        with pytest.raises(Exception, match="already registered"):
            customer_service_no_broker.update_profile(customer2.id, {"email": "first@example.com"})


class TestCustomerServiceAddress:
    def test_add_address(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Addr",
            "email": "addr@example.com",
            "password": "secure123"
        })
        address = customer_service_no_broker.add_address(customer.id, {
            "label": "Work",
            "street": "2 Rue de Lyon",
            "city": "Lyon",
            "postal_code": "69001"
        })
        assert address.label == "Work"
        assert address.is_default is True

    def test_add_second_address_not_default(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Multi",
            "email": "multi@example.com",
            "password": "secure123"
        })
        customer_service_no_broker.add_address(customer.id, {"label": "Home", "street": "1 Paris", "city": "Paris"})
        addr2 = customer_service_no_broker.add_address(customer.id, {
            "label": "Work",
            "street": "2 Lyon",
            "city": "Lyon",
            "is_default": False
        })
        assert addr2.is_default is False
        addresses = customer_service_no_broker.get_addresses(customer.id)
        assert addresses[0].is_default is True
        assert addresses[1].is_default is False

    def test_add_second_address_default_changes_first(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Def",
            "email": "def@example.com",
            "password": "secure123"
        })
        customer_service_no_broker.add_address(customer.id, {"label": "Old", "street": "1", "city": "A"})
        addr2 = customer_service_no_broker.add_address(customer.id, {
            "label": "New", "street": "2", "city": "B", "is_default": True
        })
        assert addr2.is_default is True
        addresses = customer_service_no_broker.get_addresses(customer.id)
        assert addresses[0].is_default is False

    def test_get_addresses(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Get Addr",
            "email": "getaddr@example.com",
            "password": "secure123"
        })
        customer_service_no_broker.add_address(customer.id, {"label": "Home", "street": "1", "city": "A"})
        addresses = customer_service_no_broker.get_addresses(customer.id)
        assert len(addresses) == 1

    def test_update_address(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Upd Addr",
            "email": "updaddr@example.com",
            "password": "secure123"
        })
        address = customer_service_no_broker.add_address(customer.id, {"label": "Old", "street": "Old St"})
        updated = customer_service_no_broker.update_address(customer.id, address.id, {"label": "New", "city": "NewCity"})
        assert updated.label == "New"
        assert updated.city == "NewCity"

    def test_delete_address(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Del Addr",
            "email": "deladdr@example.com",
            "password": "secure123"
        })
        address = customer_service_no_broker.add_address(customer.id, {"label": "Temp", "street": "T"})
        customer_service_no_broker.delete_address(customer.id, address.id)
        assert len(customer_service_no_broker.get_addresses(customer.id)) == 0

    def test_update_address_not_found(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Not Found",
            "email": "notfound@example.com",
            "password": "secure123"
        })
        with pytest.raises(Exception, match="not found"):
            customer_service_no_broker.update_address(customer.id, "nonexistent", {})

    def test_delete_address_not_found(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Del NF",
            "email": "delnf@example.com",
            "password": "secure123"
        })
        with pytest.raises(Exception, match="not found"):
            customer_service_no_broker.delete_address(customer.id, "nonexistent")


class TestCustomerServiceOrders:
    def test_get_orders_returns_empty_list(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Orders",
            "email": "orders@example.com",
            "password": "secure123"
        })
        orders = customer_service_no_broker.get_orders(customer.id)
        assert orders == []

    def test_add_order_ref(self, customer_service_no_broker):
        customer, _ = customer_service_no_broker.register({
            "name": "Order Ref",
            "email": "orderref@example.com",
            "password": "secure123"
        })
        customer_service_no_broker.add_order_ref(customer.id, {
            "order_id": "order-1",
            "status": "CREATED",
            "total": 25.50,
            "date": "2026-01-01",
            "restaurant_name": "Test Restaurant"
        })
        orders = customer_service_no_broker.get_orders(customer.id)
        assert len(orders) == 1
        assert orders[0].order_id == "order-1"
        assert orders[0].total == 25.50
