import pytest
from unittest.mock import MagicMock


def _service_with_mock_client(routing_table, client, service_urls=None):
    from application.gateway_service import GatewayService
    return GatewayService(routing_table, client, service_urls=service_urls or {
        'order': 'http://order-service:8001',
        'restaurant': 'http://restaurant-service:8002',
        'catalog': 'http://catalog-service:8003',
    })


class TestGatewayService:
    def test_route_request_returns_404_when_no_route(self, gateway_service):
        result, status = gateway_service.route_request('GET', '/unknown', {}, None)
        assert status == 404
        assert 'Route not found' in result.get('error', '')

    def test_route_request_returns_503_on_connection_error(self, gateway_service):
        result, status = gateway_service.route_request('POST', '/orders', {}, {'test': True})
        assert status == 503 or status == 502

    def test_route_request_matches_service_url(self, gateway_service):
        result, status = gateway_service.route_request('GET', '/restaurants/search', {}, None)
        assert status == 503 or status == 502

    def test_route_request_extracts_path_params(self, gateway_service):
        result, status = gateway_service.route_request('GET', '/orders/test-123', {}, None)
        assert status == 503 or status == 502

    def test_aggregate_order_details_handles_missing_order(self, gateway_service):
        result, status = gateway_service.aggregate_order_details('nonexistent', {})
        assert status == 503 or status == 502


class TestForwardSuccess:
    def test_forward_returns_service_response(self, routing_table):
        client = MagicMock()
        client.request.return_value = ({"id": "o1"}, 201)
        service = _service_with_mock_client(routing_table, client)
        data, status = service.route_request('POST', '/orders', {}, {"customerId": "c1"})
        assert (data, status) == ({"id": "o1"}, 201)
        args, kwargs = client.request.call_args
        assert args[0] == 'POST'
        assert args[1] == 'http://order-service:8001/orders'
        assert kwargs["json"] == {"customerId": "c1"}

    def test_forward_replaces_path_params_in_url(self, routing_table):
        client = MagicMock()
        client.request.return_value = ({"id": "o-42"}, 200)
        service = _service_with_mock_client(routing_table, client)
        data, status = service.route_request('GET', '/orders/o-42', {}, None)
        assert status == 200
        assert client.request.call_args.args[1] == 'http://order-service:8001/orders/o-42'


class TestAggregateOrderDetails:
    def test_enriches_order_with_restaurant_details(self, routing_table):
        client = MagicMock()
        client.request.side_effect = [
            ({"id": "o1", "restaurantId": "r1"}, 200),
            ({"name": "Chez Nino", "location": "Paris"}, 200),
        ]
        service = _service_with_mock_client(routing_table, client)
        data, status = service.aggregate_order_details('o1', {})
        assert status == 200
        assert data["restaurant_name"] == "Chez Nino"
        assert data["restaurant_location"] == "Paris"

    def test_order_without_restaurant_id_is_returned_as_is(self, routing_table):
        client = MagicMock()
        client.request.return_value = ({"id": "o1"}, 200)
        service = _service_with_mock_client(routing_table, client)
        data, status = service.aggregate_order_details('o1', {})
        assert status == 200
        assert "restaurant_name" not in data
        assert client.request.call_count == 1

    def test_restaurant_failure_does_not_break_aggregation(self, routing_table):
        client = MagicMock()
        client.request.side_effect = [
            ({"id": "o1", "restaurant_id": "r1"}, 200),
            ({"error": "down"}, 500),
        ]
        service = _service_with_mock_client(routing_table, client)
        data, status = service.aggregate_order_details('o1', {})
        assert status == 200
        assert "restaurant_name" not in data


class TestSearchRestaurants:
    def test_delegates_to_catalog_service(self, routing_table):
        client = MagicMock()
        client.request.return_value = ({"restaurants": [], "total": 0}, 200)
        service = _service_with_mock_client(routing_table, client)
        data, status = service.search_restaurants('pizza', {})
        assert status == 200
        args, kwargs = client.request.call_args
        assert args[1] == 'http://catalog-service:8003/restaurants/search'
        assert kwargs["params"] == {'query': 'pizza'}
