from typing import Optional
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from domain.models import Customer, CustomerAddress, OrderRef


class MongoDBCustomerRepository:
    def __init__(self, mongo_url: str):
        self.client = MongoClient(mongo_url)
        self.db = self.client.get_database()
        self.collection = self.db.customers

    def _doc_to_customer(self, doc) -> Optional[Customer]:
        if not doc:
            return None
        addresses = [
            CustomerAddress(
                id=a.get("id", ""),
                label=a.get("label", ""),
                street=a.get("street", ""),
                city=a.get("city", ""),
                postal_code=a.get("postal_code", ""),
                is_default=a.get("is_default", False)
            )
            for a in doc.get("addresses", [])
        ]
        orders = [
            OrderRef(
                order_id=o.get("order_id", ""),
                status=o.get("status", ""),
                total=o.get("total", 0.0),
                date=o.get("date", ""),
                restaurant_name=o.get("restaurant_name", "")
            )
            for o in doc.get("orders", [])
        ]
        return Customer(
            id=doc.get("_id", ""),
            name=doc.get("name", ""),
            email=doc.get("email", ""),
            password_hash=doc.get("password_hash", ""),
            phone=doc.get("phone", ""),
            addresses=addresses,
            orders=orders,
            created_at=doc.get("created_at", ""),
            updated_at=doc.get("updated_at", "")
        )

    def _customer_to_doc(self, customer: Customer) -> dict:
        return {
            "_id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "password_hash": customer.password_hash,
            "phone": customer.phone,
            "addresses": [
                {
                    "id": a.id,
                    "label": a.label,
                    "street": a.street,
                    "city": a.city,
                    "postal_code": a.postal_code,
                    "is_default": a.is_default
                }
                for a in customer.addresses
            ],
            "orders": [
                {
                    "order_id": o.order_id,
                    "status": o.status,
                    "total": o.total,
                    "date": o.date,
                    "restaurant_name": o.restaurant_name
                }
                for o in customer.orders
            ],
            "created_at": customer.created_at,
            "updated_at": customer.updated_at
        }

    def find_by_id(self, customer_id: str) -> Optional[Customer]:
        doc = self.collection.find_one({"_id": customer_id})
        return self._doc_to_customer(doc)

    def find_by_email(self, email: str) -> Optional[Customer]:
        doc = self.collection.find_one({"email": email})
        return self._doc_to_customer(doc)

    def save(self, customer: Customer):
        doc = self._customer_to_doc(customer)
        self.collection.replace_one({"_id": customer.id}, doc, upsert=True)

    def delete(self, customer_id: str):
        self.collection.delete_one({"_id": customer_id})
