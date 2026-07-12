import os
import json
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class DelivererClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("DELIVERER_SERVICE_URL", "http://deliverer-service:8009")

    def _post(self, path: str, data: Optional[dict] = None) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data else b""
        try:
            req = Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            with urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            logger.exception(f"Deliverer client error {path}: {e}")
            return None

    def assign_available(self) -> Optional[dict]:
        result = self._post("/deliverers/assign")
        if result and result.get("deliverer"):
            return result["deliverer"]
        return None

    def release_deliverer(self, deliverer_id: str) -> bool:
        result = self._post(f"/deliverers/{deliverer_id}/release")
        return result is not None
