import json
import logging

from domain.models import RouteMatch
from domain.routing import RoutingTable
from infrastructure.service_client import ServiceClient

logger = logging.getLogger(__name__)


class GatewayService:
    def __init__(self, routing_table: RoutingTable, service_client: ServiceClient, service_urls: dict = None):
        self._routing_table = routing_table
        self._service_client = service_client
        self._service_urls = service_urls or {}

    def route_request(self, method: str, path: str, headers: dict, body: any) -> tuple:
        match = self._routing_table.match(method, path)
        if not match:
            logger.warning(f"No route found for {method} {path}")
            return {"error": "Route not found"}, 404

        return self._forward(match, headers, body)

    def _build_forward_url(self, match: RouteMatch) -> str:
        service_url = match.rule.service_url.rstrip('/')
        path = match.rule.path_pattern
        for name, value in match.path_params.items():
            path = path.replace(f'<{name}>', value)
        return f"{service_url}{path}"

    def _forward(self, match: RouteMatch, headers: dict, body: any) -> tuple:
        url = self._build_forward_url(match)
        method = match.rule.method

        try:
            response_data, status_code = self._service_client.request(
                method, url,
                headers=headers,
                json=body,
                timeout=match.rule.timeout
            )
            return response_data, status_code
        except Exception as e:
            logger.exception("Error forwarding request to %s", url)
            return {"error": "Service unavailable", "detail": str(e)}, 503

    def aggregate_order_details(self, order_id: str, headers: dict) -> tuple:
        order_base = self._service_urls.get('order', '')
        order_resp, order_status = self._service_client.request(
            'GET', f'{order_base}/orders/{order_id}', headers=headers
        )
        if order_status != 200:
            return order_resp, order_status

        restaurant_id = order_resp.get('restaurantId') or order_resp.get('restaurant_id')
        if restaurant_id:
            restaurant_base = self._service_urls.get('restaurant', '')
            restaurant_resp, rest_status = self._service_client.request(
                'GET', f'{restaurant_base}/restaurants/{restaurant_id}', headers=headers
            )
            if rest_status == 200:
                order_resp['restaurant_name'] = restaurant_resp.get('name')
                order_resp['restaurant_location'] = restaurant_resp.get('location')

        return order_resp, 200

    def search_restaurants(self, query: str, headers: dict) -> tuple:
        catalog_base = self._service_urls.get('catalog', '')
        return self._service_client.request(
            'GET', f'{catalog_base}/restaurants/search',
            headers=headers, params={'query': query}
        )
