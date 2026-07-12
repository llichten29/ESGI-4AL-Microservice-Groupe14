class TestDelivererClient:
    def test_assign_available_handles_connection_error(self):
        from infrastructure.deliverer_client import DelivererClient
        client = DelivererClient(base_url="http://localhost:1")
        result = client.assign_available()
        assert result is None

    def test_release_deliverer_handles_connection_error(self):
        from infrastructure.deliverer_client import DelivererClient
        client = DelivererClient(base_url="http://localhost:1")
        result = client.release_deliverer("del-1")
        assert result is False
