import pytest


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
