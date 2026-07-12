from typing import Optional
from pymongo import MongoClient

from domain.models import Deliverer, DelivererStatus


class MongoDBDelivererRepository:
    def __init__(self, mongo_url: str, client: Optional[MongoClient] = None):
        self.client = client or MongoClient(mongo_url)
        self.db = self.client.get_database()
        self.collection = self.db.deliverers

    def _doc_to_deliverer(self, doc) -> Optional[Deliverer]:
        if not doc:
            return None
        return Deliverer(
            id=doc.get("_id", ""),
            name=doc.get("name", ""),
            phone=doc.get("phone", ""),
            vehicle=doc.get("vehicle", "BIKE"),
            status=doc.get("status", DelivererStatus.OFFLINE),
            location=doc.get("location", {}),
            created_at=doc.get("created_at", ""),
            updated_at=doc.get("updated_at", "")
        )

    def _deliverer_to_doc(self, deliverer: Deliverer) -> dict:
        return {
            "_id": deliverer.id,
            "name": deliverer.name,
            "phone": deliverer.phone,
            "vehicle": deliverer.vehicle,
            "status": deliverer.status,
            "location": deliverer.location,
            "created_at": deliverer.created_at,
            "updated_at": deliverer.updated_at
        }

    def save(self, deliverer: Deliverer):
        self.collection.replace_one({"_id": deliverer.id}, self._deliverer_to_doc(deliverer), upsert=True)

    def find_by_id(self, deliverer_id: str) -> Optional[Deliverer]:
        return self._doc_to_deliverer(self.collection.find_one({"_id": deliverer_id}))

    def find_all(self) -> list[Deliverer]:
        return [self._doc_to_deliverer(d) for d in self.collection.find()]

    def find_first_available(self) -> Optional[Deliverer]:
        return self._doc_to_deliverer(self.collection.find_one({"status": DelivererStatus.AVAILABLE}))
