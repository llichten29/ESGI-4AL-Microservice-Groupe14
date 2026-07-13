import json
import logging

from domain.models import RouteMatch
from domain.routing import RoutingTable
from infrastructure.service_client import ServiceClient

logger = logging.getLogger(__name__)


class GatewayService:
    def __init__(self, routing_table: RoutingTable, service_client: ServiceClient):
        self._routing_table = routing_table
        self._service_client = service_client

    def route_request(self, method: str, path: str, headers: dict, body: any) -> tuple:
        match = self._routing_table.match(method, path)
        if not match:
            logger.warning(f"No route found for {method} {path}")
            return {"error": "Route not found"}, 404

        return self._forward(match, path, headers, body)

    def _build_forward_url(self, match: RouteMatch, original_path: str) -> str:
        service_url = match.rule.service_url.rstrip('/')
        params = match.path_params
        # Replace path params in the original path with actual values
        for name, value in params.items():
            original_path = original_path.replace(f'<{name}>', value)
        return f"{service_url}{original_path}"

    def _forward(self, match: RouteMatch, path: str, headers: dict, body: any) -> tuple:
        url = self._build_forward_url(match, path)
        method = match.rule.method

        try:
            status_code, response_data = self._service_client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=match.rule.timeout
            )
            return response_data, status_code
        except Exception as e:
            logger.error(f"Error forwarding request to {url}: {e}")
            return {"error": "Service unavailable", "detail": str(e)}, 503

    def aggregate_order_details(self, order_id: str, headers: dict) -> tuple:
        order_resp, order_status = self._service_client.request(
            'GET', f'/orders/{order_id}', headers=headers
        )
        if order_status != 200:
            return order_resp, order_status

        restaurant_id = order_resp.get('restaurantId') or order_resp.get('restaurant_id')
        if restaurant_id:
            restaurant_resp, rest_status = self._service_client.request(
                'GET', f'/restaurants/{restaurant_id}', headers=headers
            )
            if rest_status == 200:
                order_resp['restaurant_name'] = restaurant_resp.get('name')
                order_resp['restaurant_location'] = restaurant_resp.get('location')

        return order_resp, 200

    def search_restaurants(self, query: str, headers: dict) -> tuple:
        return self._service_client.request(
            'GET', '/restaurants/search',
            headers=headers, params={'query': query}
        )
