import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._session = requests.Session()

    def request(
        self,
        method: str,
        url_or_path: str,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: Optional[float] = None
    ) -> tuple:
        if self._base_url:
            url = f"{self._base_url}/{url_or_path.lstrip('/')}"
        else:
            url = url_or_path
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            for key in ('authorization', 'content-type', 'x-user-id', 'x-correlation-id'):
                if key in headers or key.title() in headers:
                    val = headers.get(key) or headers.get(key.title())
                    if val:
                        request_headers[key.title()] = val

        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json,
                params=params,
                timeout=timeout or self._timeout
            )
            content = response.json() if response.text else {}
            return content, response.status_code
        except requests.Timeout:
            logger.error(f"Timeout calling {method} {url}")
            return {"error": "Service timeout"}, 504
        except requests.ConnectionError:
            logger.error(f"Connection error calling {method} {url}")
            return {"error": "Service unavailable"}, 503
        except Exception as e:
            logger.error(f"Error calling {method} {url}: {e}")
            return {"error": "Internal gateway error"}, 502
