from unittest.mock import MagicMock


class TestCreateApp:
    def test_boots_without_broker(self, build_app):
        app = build_app()
        client = app.test_client()
        health = client.get('/health')
        assert health.status_code == 200
        payload = health.get_json()
        assert payload["status"] == "healthy"
        assert payload["service"] == "delivery-service"
        assert client.get('/openapi.yaml').status_code == 200
        missing = client.get('/route-inconnue')
        assert missing.status_code == 404
        assert "error" in missing.get_json()

    def test_boots_with_broker_connected(self, build_app):
        broker_cls = MagicMock()
        app = build_app(rabbitmq_host='localhost', broker_cls=broker_cls)
        assert broker_cls.return_value.connect.called
        assert app.test_client().get('/health').status_code == 200

    def test_boots_when_broker_unavailable(self, build_app):
        broker_cls = MagicMock()
        broker_cls.return_value.connect.side_effect = ConnectionError("rabbitmq down")
        app = build_app(rabbitmq_host='localhost', broker_cls=broker_cls)
        assert app.test_client().get('/health').status_code == 200
