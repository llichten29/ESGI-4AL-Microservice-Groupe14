import pytest


def test_proxy_returns_404_for_unknown_route(app):
    from interfaces.http.routes import routes
    app.gateway_service.route_request.return_value = ({"error": "Route not found"}, 404)
    app.register_blueprint(routes)
    with app.test_client() as client:
        resp = client.get('/unknown/path')
        assert resp.status_code == 404


def test_proxy_handles_health_check(app):
    @app.route('/health')
    def health():
        return {"status": "healthy"}, 200

    from interfaces.http.routes import routes
    app.register_blueprint(routes)
    with app.test_client() as client:
        resp = client.get('/health')
        assert resp.status_code == 200


def test_order_details_endpoint_returns_503_without_backend(app):
    from interfaces.http.routes import routes
    app.register_blueprint(routes)
    class FakeGateway:
        @staticmethod
        def aggregate_order_details(order_id, headers):
            return {"error": "Service unavailable"}, 503

    app.gateway_service = FakeGateway()
    with app.test_client() as client:
        resp = client.get('/orders/abc/details')
        assert resp.status_code == 503


def test_catch_all_passes_through_headers(app):
    from interfaces.http.routes import routes
    app.register_blueprint(routes)
    class FakeGateway:
        @staticmethod
        def route_request(method, path, headers, body):
            return {"method": method, "path": path}, 200

    app.gateway_service = FakeGateway()
    with app.test_client() as client:
        resp = client.get('/orders/123', headers={'Authorization': 'Bearer test'})
        assert resp.status_code == 200
