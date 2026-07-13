class TestOrderRoutes:
    def test_post_orders_returns_201(self, order_client, order_payload):
        resp = order_client.post('/orders', json=order_payload)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "CREATED"
        assert body["totalPrice"] == 33.99
        assert body["sagaState"] == "PAYMENT_PENDING"

    def test_post_orders_without_body_returns_400(self, order_client):
        resp = order_client.post('/orders', content_type='application/json', data='null')
        assert resp.status_code == 400

    def test_post_orders_invalid_returns_422(self, order_client, order_payload, restaurant_client):
        restaurant_client.validate_order.return_value = {"isValid": False, "reason": "Closed"}
        resp = order_client.post('/orders', json=order_payload)
        assert resp.status_code == 422

    def test_post_orders_circuit_open_returns_503(self, order_client, order_payload, restaurant_client):
        from main.shared.circuit_breaker import CircuitBreakerException
        restaurant_client.validate_order.side_effect = CircuitBreakerException("OPEN")
        resp = order_client.post('/orders', json=order_payload)
        assert resp.status_code == 503
        assert resp.get_json()["error"]["code"] == "RESTAURANT_UNAVAILABLE"

    def test_get_order(self, order_client, order_payload):
        created = order_client.post('/orders', json=order_payload).get_json()
        resp = order_client.get(f"/orders/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == created["id"]

    def test_get_unknown_order_returns_404(self, order_client):
        resp = order_client.get('/orders/nope')
        assert resp.status_code == 404

    def test_delete_order_cancels_it(self, order_client, order_payload):
        created = order_client.post('/orders', json=order_payload).get_json()
        resp = order_client.delete(f"/orders/{created['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "CANCELLED"

    def test_get_customer_orders(self, order_client, order_payload):
        order_client.post('/orders', json=order_payload)
        order_client.post('/orders', json=order_payload)
        resp = order_client.get('/customers/cust-1/orders')
        assert resp.status_code == 200
        assert len(resp.get_json()["orders"]) == 2

    def test_get_saga_history(self, order_client, order_payload):
        created = order_client.post('/orders', json=order_payload).get_json()
        resp = order_client.get(f"/orders/{created['id']}/saga")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["sagaState"] == "PAYMENT_PENDING"
        assert [s["state"] for s in body["history"]] == ["STARTED", "PAYMENT_PENDING"]

    def test_get_circuit_breakers(self, order_client):
        resp = order_client.get('/orders/circuit-breakers')
        assert resp.status_code == 200
        assert len(resp.get_json()["circuitBreakers"]) == 2
