import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class CustomerException(Exception):
    def __init__(self, message: str, code: str = "CUSTOMER_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class CustomerNotFound(CustomerException):
    def __init__(self, customer_id: str):
        super().__init__(f"Customer {customer_id} not found", "CUSTOMER_NOT_FOUND", 404)


class InvalidCredentials(CustomerException):
    def __init__(self):
        super().__init__("Invalid email or password", "INVALID_CREDENTIALS", 401)


class EmailAlreadyExists(CustomerException):
    def __init__(self, email: str):
        super().__init__(f"Email {email} is already registered", "EMAIL_ALREADY_EXISTS", 409)


@dataclass
class CustomerAddress:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    street: str = ""
    city: str = ""
    postal_code: str = ""
    is_default: bool = False


@dataclass
class OrderRef:
    order_id: str = ""
    status: str = ""
    total: float = 0.0
    date: str = ""
    restaurant_name: str = ""


@dataclass
class Customer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    email: str = ""
    password_hash: str = ""
    phone: str = ""
    addresses: list[CustomerAddress] = field(default_factory=list)
    orders: list[OrderRef] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
