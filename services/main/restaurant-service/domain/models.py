import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class RestaurantException(Exception):
    def __init__(self, message: str, code: str = "RESTAURANT_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class RestaurantNotFound(RestaurantException):
    def __init__(self, restaurant_id: str):
        super().__init__(f"Restaurant {restaurant_id} not found", "RESTAURANT_NOT_FOUND", 404)


class MenuNotFound(RestaurantException):
    def __init__(self, menu_id: str):
        super().__init__(f"Menu {menu_id} not found", "MENU_NOT_FOUND", 404)


class RestaurantClosed(RestaurantException):
    def __init__(self):
        super().__init__("Restaurant is closed", "RESTAURANT_CLOSED", 422)


class CuisineType:
    ITALIAN = "ITALIAN"
    FRENCH = "FRENCH"
    JAPANESE = "JAPANESE"
    MEXICAN = "MEXICAN"
    CHINESE = "CHINESE"
    AMERICAN = "AMERICAN"
    OTHER = "OTHER"


class RestaurantStatus:
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class DayOfWeek:
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


@dataclass
class GeoPoint:
    latitude: float
    longitude: float


@dataclass
class Address:
    street: str
    city: str
    postal_code: str
    coordinates: Optional[GeoPoint] = None


@dataclass
class OpeningHours:
    day: str
    open_time: str
    close_time: str


@dataclass
class MenuOption:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    price: float = 0.0
    is_default: bool = False


@dataclass
class MenuItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    price: float = 0.0
    is_available: bool = True
    options: list[MenuOption] = field(default_factory=list)


@dataclass
class Menu:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str = ""
    name: str = ""
    is_active: bool = True
    items: list[MenuItem] = field(default_factory=list)


@dataclass
class Restaurant:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    address: Optional[Address] = None
    phone: str = ""
    cuisine_type: str = "OTHER"
    opening_hours: dict[str, OpeningHours] = field(default_factory=dict)
    status: str = "ACTIVE"
    rating: float = 0.0
    menus: list[Menu] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def is_open(self) -> bool:
        if self.status != "ACTIVE":
            return False
        if not self.opening_hours:
            return True
        now = datetime.utcnow()
        day_name = now.strftime("%A").upper()
        if day_name not in self.opening_hours:
            return False
        hours = self.opening_hours[day_name]
        current = now.strftime("%H:%M")
        return hours.open_time <= current <= hours.close_time
