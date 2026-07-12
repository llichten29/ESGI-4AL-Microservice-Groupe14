import uuid
import logging
import jwt
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash

from domain.models import (
    Customer, CustomerAddress, OrderRef,
    CustomerException, CustomerNotFound, InvalidCredentials, EmailAlreadyExists
)
from domain.events import CustomerRegistered

logger = logging.getLogger(__name__)


class CustomerService:
    def __init__(self, repository, broker=None, jwt_secret="dev-secret"):
        self.repository = repository
        self.broker = broker
        self.jwt_secret = jwt_secret
        self.exchange = "customer.events"

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

    def register(self, data: dict) -> tuple[Customer, str]:
        email = data.get("email", "").strip().lower()
        if not email:
            raise CustomerException("Email is required", "INVALID_INPUT", 400)

        existing = self.repository.find_by_email(email)
        if existing:
            raise EmailAlreadyExists(email)

        password = data.get("password", "")
        if len(password) < 6:
            raise CustomerException("Password must be at least 6 characters", "WEAK_PASSWORD", 400)

        address_data = data.get("address")
        addresses = []
        if address_data:
            addresses.append(CustomerAddress(
                id=str(uuid.uuid4()),
                label=address_data.get("label", "Default"),
                street=address_data.get("street", ""),
                city=address_data.get("city", ""),
                postal_code=address_data.get("postal_code", ""),
                is_default=True
            ))

        customer = Customer(
            id=str(uuid.uuid4()),
            name=data.get("name", ""),
            email=email,
            password_hash=generate_password_hash(password),
            phone=data.get("phone", ""),
            addresses=addresses,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )

        self.repository.save(customer)
        token = self._generate_token(customer)

        self._publish(CustomerRegistered(
            customer_id=customer.id,
            name=customer.name,
            email=customer.email
        ))

        return customer, token

    def login(self, email: str, password: str) -> tuple[Customer, str]:
        customer = self.repository.find_by_email(email.strip().lower())
        if not customer:
            raise InvalidCredentials()
        if not check_password_hash(customer.password_hash, password):
            raise InvalidCredentials()

        token = self._generate_token(customer)
        return customer, token

    def _generate_token(self, customer: Customer) -> str:
        payload = {
            "customer_id": customer.id,
            "email": customer.email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def get_profile(self, customer_id: str) -> Customer:
        customer = self.repository.find_by_id(customer_id)
        if not customer:
            raise CustomerNotFound(customer_id)
        return customer

    def update_profile(self, customer_id: str, data: dict) -> Customer:
        customer = self.get_profile(customer_id)

        if "name" in data:
            customer.name = data["name"]
        if "phone" in data:
            customer.phone = data["phone"]
        if "email" in data:
            new_email = data["email"].strip().lower()
            if new_email != customer.email:
                existing = self.repository.find_by_email(new_email)
                if existing:
                    raise EmailAlreadyExists(new_email)
                customer.email = new_email

        customer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(customer)
        return customer

    def add_address(self, customer_id: str, data: dict) -> CustomerAddress:
        customer = self.get_profile(customer_id)

        address = CustomerAddress(
            id=str(uuid.uuid4()),
            label=data.get("label", ""),
            street=data.get("street", ""),
            city=data.get("city", ""),
            postal_code=data.get("postal_code", ""),
            is_default=data.get("is_default", False)
        )

        if address.is_default or not customer.addresses:
            for a in customer.addresses:
                a.is_default = False
            address.is_default = True

        customer.addresses.append(address)
        customer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(customer)
        return address

    def get_addresses(self, customer_id: str) -> list[CustomerAddress]:
        customer = self.get_profile(customer_id)
        return customer.addresses

    def _apply_address_fields(self, address: CustomerAddress, data: dict) -> None:
        if "label" in data:
            address.label = data["label"]
        if "street" in data:
            address.street = data["street"]
        if "city" in data:
            address.city = data["city"]
        if "postal_code" in data:
            address.postal_code = data["postal_code"]

    def _set_address_as_default(self, address: CustomerAddress, customer: Customer) -> None:
        for a in customer.addresses:
            a.is_default = False
        address.is_default = True

    def update_address(self, customer_id: str, address_id: str, data: dict) -> CustomerAddress:
        customer = self.get_profile(customer_id)

        for address in customer.addresses:
            if address.id == address_id:
                self._apply_address_fields(address, data)
                if data.get("is_default"):
                    self._set_address_as_default(address, customer)

                customer.updated_at = datetime.now(timezone.utc).isoformat()
                self.repository.save(customer)
                return address

        raise CustomerException(f"Address {address_id} not found", "ADDRESS_NOT_FOUND", 404)

    def delete_address(self, customer_id: str, address_id: str):
        customer = self.get_profile(customer_id)

        for address in customer.addresses:
            if address.id == address_id:
                customer.addresses.remove(address)
                if address.is_default and customer.addresses:
                    customer.addresses[0].is_default = True
                customer.updated_at = datetime.now(timezone.utc).isoformat()
                self.repository.save(customer)
                return

        raise CustomerException(f"Address {address_id} not found", "ADDRESS_NOT_FOUND", 404)

    def get_orders(self, customer_id: str) -> list[OrderRef]:
        customer = self.get_profile(customer_id)
        return customer.orders

    def add_order_ref(self, customer_id: str, order_data: dict):
        customer = self.get_profile(customer_id)
        customer.orders.append(OrderRef(
            order_id=order_data.get("order_id", ""),
            status=order_data.get("status", ""),
            total=order_data.get("total", 0.0),
            date=order_data.get("date", ""),
            restaurant_name=order_data.get("restaurant_name", "")
        ))
        customer.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save(customer)
