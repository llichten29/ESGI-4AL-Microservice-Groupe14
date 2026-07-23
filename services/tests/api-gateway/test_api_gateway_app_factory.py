from unittest.mock import MagicMock


class TestCreateApp:
    def test_boots_and_serves_gateway_endpoints(self, build_app):
        app = build_app(broker_cls=MagicMock())
        client = app.test_client()
        health = client.get('/health')
        assert health.status_code == 200
        assert health.get_json() == {"status": "healthy", "service": "api-gateway"}
        docs = client.get('/docs')
        assert docs.status_code == 200
        assert b"swagger-ui" in docs.data
        spec = client.get('/openapi.yaml')
        assert spec.status_code == 200
        assert b"DashEat" in spec.data
        assert client.get('/route-inconnue').status_code == 404

    def test_routing_table_wired_into_gateway_service(self, build_app):
        app = build_app(broker_cls=MagicMock())
        table = app.gateway_service._routing_table
        assert table.match('POST', '/orders') is not None

    def test_boots_when_broker_unavailable(self, build_app):
        broker_cls = MagicMock()
        broker_cls.return_value.connect.side_effect = ConnectionError("rabbitmq down")
        app = build_app(broker_cls=broker_cls)
        assert app.test_client().get('/health').status_code == 200
